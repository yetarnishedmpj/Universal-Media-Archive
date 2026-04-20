from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient, TEXT
from bson import ObjectId
from datetime import datetime, timedelta
import os
import sys
import random
import math

sys.path.append(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
CORS(app, resources={r"/*": {"origins": allowed_origins}})

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "universal_media_archive")

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["5000 per day", "500 per hour"],
    storage_uri=MONGO_URI
)

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

media_col = db["media"]
users_col = db["users"]
reviews_col = db["reviews"]
analytics_col = db["analytics"]

# Indexes
try:
    media_col.drop_index("title_text_genres_text_tags_text_description_text")
except Exception:
    pass
media_col.create_index([(("title", TEXT)), ("genres", TEXT), ("tags", TEXT), ("description", TEXT)])
media_col.create_index("type")
media_col.create_index("release_year")
media_col.create_index("genres")
media_col.create_index("view_count")
reviews_col.create_index([("media_id", 1), ("user_id", 1)])


def to_oid(id_str):
    """Safely convert string to ObjectId, returns None if invalid"""
    try:
        return ObjectId(id_str) if ObjectId.is_valid(id_str) else None
    except Exception:
        return None


def serialize(doc):
    if doc is None:
        return None
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


def serialize_list(docs):
    return [serialize(d) for d in docs]


# ─── ROOT ───
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "name": "Universal Media Archive API",
        "version": "2.0.0",
        "endpoints": ["/media", "/search", "/review", "/reviews/<media_id>",
                      "/users", "/recommendations", "/analytics/trending",
                      "/analytics/searches", "/analytics/genres", "/analytics/types",
                      "/analytics/dashboard", "/analytics/activity",
                      "/ai/recommend", "/ai/similar/<media_id>",
                      "/timecapsule/<decade>", "/genres", "/health"]
    })


# ─── HEALTH ───
@app.route("/health", methods=["GET"])
def health():
    total = media_col.count_documents({})
    return jsonify({"status": "ok", "db": DB_NAME, "total_items": total})


# ─── MEDIA ───
@app.route("/media", methods=["POST"])
def add_media():
    data = request.json
    required = ["title", "type"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"Missing required field: {f}"}), 400

    valid_types = ["movie", "book", "song", "game", "show", "video", "comic"]
    if data["type"] not in valid_types:
        return jsonify({"error": f"Invalid type. Must be one of {valid_types}"}), 400

    doc = {
        "title": data["title"],
        "type": data["type"],
        "genres": data.get("genres", []),
        "release_year": data.get("release_year"),
        "creators": data.get("creators", []),
        "cast": data.get("cast", []),
        "description": data.get("description", ""),
        "thumbnail": data.get("thumbnail", ""),
        "ratings": data.get("ratings", {"imdb": None, "user": None}),
        "sources": data.get("sources", []),
        "tags": data.get("tags", []),
        "related": data.get("related", []),
        "added_at": datetime.utcnow(),
        "view_count": data.get("view_count", 0),
        "ai_score": 0.0,
    }
    result = media_col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return jsonify(doc), 201


@app.route("/media", methods=["GET"])
def get_media():
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    media_type = request.args.get("type")
    genre = request.args.get("genre")
    year = request.args.get("year")
    year_from = request.args.get("year_from")
    year_to = request.args.get("year_to")
    sort_by = request.args.get("sort", "added_at")

    query = {}
    if media_type:
        query["type"] = media_type
    if genre:
        query["genres"] = {"$in": [genre]}
    if year_from or year_to:
        yr = {}
        if year_from: yr["$gte"] = int(year_from)
        if year_to: yr["$lte"] = int(year_to)
        query["release_year"] = yr
    elif year:
        query["release_year"] = int(year)

    sort_map = {
        "added_at": [("added_at", -1)],
        "title": [("title", 1)],
        "year": [("release_year", -1)],
        "views": [("view_count", -1)],
        "rating": [("ratings.imdb", -1)],
        "ai_score": [("ai_score", -1)],
    }
    sort_order = sort_map.get(sort_by, [("added_at", -1)])
    total = media_col.count_documents(query)
    items = list(media_col.find(query).sort(sort_order).skip((page - 1) * limit).limit(limit))

    return jsonify({
        "data": serialize_list(items),
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "limit": limit,
    })


@app.route("/media/<media_id>", methods=["GET"])
def get_media_detail(media_id):
    oid = to_oid(media_id)
    if not oid:
        return jsonify({"error": "Invalid media ID"}), 400

    doc = media_col.find_one_and_update(
        {"_id": oid},
        {"$inc": {"view_count": 1}},
        return_document=True
    )

    if not doc:
        return jsonify({"error": "Media not found"}), 404

    # Fetch reviews
    reviews = list(reviews_col.find({"media_id": media_id}))
    doc["reviews"] = serialize_list(reviews)

    # Efficient batch fetch for related media
    rel_entries = doc.get("related", [])
    rel_ids = [to_oid(r.get("media_id")) for r in rel_entries if r.get("media_id")]
    rel_ids = [i for i in rel_ids if i][:6] # Limit to 6

    if rel_ids:
        related_docs = list(media_col.find({"_id": {"$in": rel_ids}}))
        # Keep original order if possible
        id_map = {str(d["_id"]): d for d in related_docs}
        ordered_related = []
        for rid in rel_ids:
            srid = str(rid)
            if srid in id_map:
                ordered_related.append(serialize(id_map[srid]))
        doc["related_media"] = ordered_related
    else:
        doc["related_media"] = []

    # Update hourly analytics
    analytics_col.update_one(
        {"media_id": media_id, "date": datetime.utcnow().strftime("%Y-%m-%d")},
        {"$inc": {"views": 1}},
        upsert=True
    )
    return jsonify(serialize(doc))


@app.route("/media/<media_id>", methods=["PUT"])
def update_media(media_id):
    oid = to_oid(media_id)
    if not oid:
        return jsonify({"error": "Invalid media ID"}), 400

    data = request.json
    data.pop("_id", None)
    result = media_col.update_one({"_id": oid}, {"$set": data})

    if result.matched_count == 0:
        return jsonify({"error": "Media not found"}), 404
    return jsonify({"message": "Updated successfully"})


try:
    from utils.vidking import get_vidking_source
    HAS_VIDKING = True
except ImportError:
    HAS_VIDKING = False

@app.route("/get_stream/<media_id>")
def get_stream(media_id):
    try:
        item = media_col.find_one({"_id": ObjectId(media_id)})
    except:
        return {"error": "Invalid ID"}, 400

    if not item:
        return {"error": "Not found"}, 404

    if item.get("stream"):
        return {"sources": [item["stream"]]}

    if HAS_VIDKING:
        sources = get_vidking_source(item["title"])
        if sources:
            media_col.update_one({"_id": item["_id"]}, {"$set": {"stream": sources[0]}})
            return {"sources": sources}

    return {
        "fallback": f"https://www.vidking.net/search?q={item['title'].replace(' ', '+')}"
    }


@app.route("/media/<media_id>", methods=["DELETE"])
def delete_media(media_id):
    oid = to_oid(media_id)
    if not oid:
        return jsonify({"error": "Invalid media ID"}), 400
    result = media_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"error": "Media not found"}), 404
    return jsonify({"message": "Deleted successfully"})


# ─── SEARCH ───
@app.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip()
    media_type = request.args.get("type")
    genre = request.args.get("genre")
    year_from = request.args.get("year_from")
    year_to = request.args.get("year_to")
    decade = request.args.get("decade")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))

    query = {}
    if q:
        query["$text"] = {"$search": q}
    if media_type:
        query["type"] = media_type
    if genre:
        query["genres"] = {"$in": [genre]}
    if decade:
        decade_start = int(decade)
        query["release_year"] = {"$gte": decade_start, "$lt": decade_start + 10}
    elif year_from or year_to:
        yr = {}
        if year_from:
            yr["$gte"] = int(year_from)
        if year_to:
            yr["$lte"] = int(year_to)
        query["release_year"] = yr

    projection = None
    sort_order = [("view_count", -1)]
    if q:
        projection = {"score": {"$meta": "textScore"}}
        sort_order = [("score", {"$meta": "textScore"})]

    total = media_col.count_documents(query)
    if projection:
        items = list(media_col.find(query, projection).sort(sort_order).skip((page - 1) * limit).limit(limit))
    else:
        items = list(media_col.find(query).sort(sort_order).skip((page - 1) * limit).limit(limit))

    if q:
        analytics_col.update_one(
            {"type": "search", "query": q},
            {"$inc": {"count": 1}, "$set": {"last_searched": datetime.utcnow()}},
            upsert=True
        )

    return jsonify({
        "data": serialize_list(items),
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "query": q,
    })


# ─── REVIEWS ───
@app.route("/review", methods=["POST"])
@limiter.limit("10 per hour")
def add_review():
    data = request.json
    required = ["user_id", "media_id", "rating"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"Missing: {f}"}), 400

    rating = float(data["rating"])
    if not (0 <= rating <= 10):
        return jsonify({"error": "Rating must be 0–10"}), 400

    doc = {
        "user_id": data["user_id"],
        "media_id": data["media_id"],
        "rating": rating,
        "comment": data.get("comment", ""),
        "created_at": datetime.utcnow(),
    }
    reviews_col.insert_one(doc)
    all_reviews = list(reviews_col.find({"media_id": data["media_id"]}))
    avg = sum(r["rating"] for r in all_reviews) / len(all_reviews)
    media_col.update_one(
        {"_id": ObjectId(data["media_id"])},
        {"$set": {"ratings.user": round(avg, 1), "ratings.review_count": len(all_reviews)}}
    )
    return jsonify(serialize(doc)), 201


@app.route("/reviews/<media_id>", methods=["GET"])
def get_reviews(media_id):
    reviews = list(reviews_col.find({"media_id": media_id}).sort("created_at", -1))
    return jsonify(serialize_list(reviews))


# ─── USERS ───
@app.route("/users", methods=["POST"])
@limiter.limit("5 per minute")
def create_user():
    data = request.json
    if not data.get("username"):
        return jsonify({"error": "Username required"}), 400
    if users_col.find_one({"username": data["username"]}):
        return jsonify({"error": "Username already exists"}), 409

    doc = {
        "username": data["username"],
        "email": data.get("email", ""),
        "watchlist": [],
        "history": [],
        "preferences": data.get("preferences", []),
        "created_at": datetime.utcnow(),
    }
    result = users_col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return jsonify(doc), 201


@app.route("/users/<user_id>", methods=["GET"])
def get_user(user_id):
    try:
        user = users_col.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(serialize(user))


@app.route("/users/<user_id>/watchlist", methods=["POST"])
def add_to_watchlist(user_id):
    data = request.json
    media_id = data.get("media_id")
    if not media_id:
        return jsonify({"error": "media_id required"}), 400
    try:
        users_col.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"watchlist": media_id}})
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400
    return jsonify({"message": "Added to watchlist"})


@app.route("/users/<user_id>/history", methods=["POST"])
def add_to_history(user_id):
    data = request.json
    media_id = data.get("media_id")
    if not media_id:
        return jsonify({"error": "media_id required"}), 400
    try:
        users_col.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"history": media_id}})
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400
    return jsonify({"message": "Added to history"})


# ─── AI RECOMMENDATIONS ENGINE ───
def compute_ai_score(item, genre_weights, type_boost, trending_ids):
    """
    Weighted scoring: genre affinity (35%) + popularity (25%) + recency (15%) + type boost (10%) + imdb (15%)
    """
    score = 0.0
    genres = item.get("genres", [])
    if genres:
        genre_score = sum(genre_weights.get(g, 0) for g in genres) / len(genres)
        score += genre_score * 0.35

    view_count = item.get("view_count", 0)
    score += min(view_count / 5000.0, 1.0) * 0.25

    release_year = item.get("release_year")
    if release_year:
        # Logistic decay for older movies
        recency = 1 / (1 + math.exp(-0.1 * (release_year - 2000)))
        score += recency * 0.15

    if type_boost and item.get("type") == type_boost:
        score += 0.1

    if str(item.get("_id", "")) in trending_ids:
        score += 0.15

    imdb = item.get("ratings", {}).get("imdb")
    if imdb:
        score += (float(imdb) / 10.0) * 0.15

    return round(score, 4)


@app.route("/ai/recommend", methods=["GET"])
def ai_recommend():
    """Advanced AI recommendation with weighted scoring"""
    genres = request.args.getlist("genre")
    media_type = request.args.get("type")
    exclude_ids = request.args.getlist("exclude")
    limit = int(request.args.get("limit", 12))
    strategy = request.args.get("strategy", "hybrid")  # hybrid, trending, discovery

    # Build genre weights from analytics (popularity-weighted)
    genre_pipeline = [
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres", "total_views": {"$sum": "$view_count"}, "count": {"$sum": 1}}},
        {"$sort": {"total_views": -1}},
        {"$limit": 50}
    ]
    genre_stats = list(media_col.aggregate(genre_pipeline))
    max_views = max((g["total_views"] for g in genre_stats), default=1) or 1
    genre_weights = {g["_id"]: g["total_views"] / max_views for g in genre_stats}

    # Boost requested genres
    for g in genres:
        genre_weights[g] = genre_weights.get(g, 0) + 2.0

    # Get trending IDs for scoring boost
    trending = list(media_col.find({}, {"_id": 1}).sort("view_count", -1).limit(20))
    trending_ids = {str(t["_id"]) for t in trending}

    # Query
    query = {}
    if media_type:
        query["type"] = media_type
    if genres:
        query["genres"] = {"$in": genres}
    if exclude_ids:
        try:
            query["_id"] = {"$nin": [ObjectId(i) for i in exclude_ids if ObjectId.is_valid(i)]}
        except Exception:
            pass

    # Fetch candidates
    if strategy == "discovery":
        # Less popular items for discovery mode
        candidates = list(media_col.find(query).sort("view_count", 1).limit(limit * 5))
    elif strategy == "trending":
        candidates = list(media_col.find(query).sort("view_count", -1).limit(limit * 3))
    else:
        # Hybrid: mix of popular and diverse
        top = list(media_col.find(query).sort("view_count", -1).limit(limit * 2))
        recent = list(media_col.find(query).sort("added_at", -1).limit(limit * 2))
        seen = set()
        candidates = []
        for item in top + recent:
            k = str(item["_id"])
            if k not in seen:
                seen.add(k)
                candidates.append(item)

    # Score all candidates
    scored = []
    for item in candidates:
        s = compute_ai_score(item, genre_weights, media_type, trending_ids)
        item["_ai_score"] = s
        scored.append(item)

    scored.sort(key=lambda x: x["_ai_score"], reverse=True)
    top_items = scored[:limit]

    result = serialize_list(top_items)
    for r, s in zip(result, [x["_ai_score"] for x in top_items]):
        r["ai_confidence"] = round(min(s * 100, 99.9), 1)

    return jsonify({
        "data": result,
        "strategy": strategy,
        "genre_weights": {k: round(v, 3) for k, v in list(genre_weights.items())[:10]},
        "total_candidates": len(candidates),
    })


@app.route("/ai/similar/<media_id>", methods=["GET"])
def ai_similar(media_id):
    """Find similar items using content-based filtering"""
    try:
        source = media_col.find_one({"_id": ObjectId(media_id)})
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400

    if not source:
        return jsonify({"error": "Not found"}), 404

    limit = int(request.args.get("limit", 8))
    source_genres = set(source.get("genres", []))
    source_type = source.get("type")
    source_year = source.get("release_year", 2000)
    source_tags = set(source.get("tags", []))

    candidates = list(media_col.find(
        {"_id": {"$ne": ObjectId(media_id)}},
    ).limit(500))

    scored = []
    for item in candidates:
        score = 0.0
        item_genres = set(item.get("genres", []))
        item_tags = set(item.get("tags", []))
        item_year = item.get("release_year", 2000)

        # Genre overlap (Jaccard similarity)
        union = source_genres | item_genres
        intersection = source_genres & item_genres
        if union:
            score += (len(intersection) / len(union)) * 0.5

        # Tag overlap
        tag_union = source_tags | item_tags
        tag_intersection = source_tags & item_tags
        if tag_union:
            score += (len(tag_intersection) / len(tag_union)) * 0.2

        # Same type boost
        if item.get("type") == source_type:
            score += 0.15

        # Era proximity
        year_diff = abs((item_year or 2000) - (source_year or 2000))
        era_sim = max(0, 1 - year_diff / 50)
        score += era_sim * 0.1

        # Popularity
        score += min((item.get("view_count", 0) / 1000.0), 0.5) * 0.05

        item["_sim_score"] = round(score, 4)
        scored.append(item)

    scored.sort(key=lambda x: x["_sim_score"], reverse=True)
    result = serialize_list(scored[:limit])
    for r, s in zip(result, [x["_sim_score"] for x in scored[:limit]]):
        r["similarity"] = round(s * 100, 1)

    return jsonify({
        "source": serialize(source),
        "similar": result
    })


# ─── RECOMMENDATIONS (legacy) ───
@app.route("/recommendations", methods=["GET"])
def get_recommendations():
    user_id = request.args.get("user_id")
    genres = request.args.getlist("genre")
    media_type = request.args.get("type")
    limit = int(request.args.get("limit", 10))

    query = {}
    if user_id:
        try:
            user = users_col.find_one({"_id": ObjectId(user_id)})
            if user:
                prefs = user.get("preferences", [])
                history = user.get("history", [])
                if prefs:
                    query["genres"] = {"$in": prefs}
                if history:
                    query["_id"] = {"$nin": [ObjectId(h) for h in history if ObjectId.is_valid(h)]}
        except Exception:
            pass
    elif genres:
        query["genres"] = {"$in": genres}

    if media_type:
        query["type"] = media_type

    items = list(media_col.find(query).sort("view_count", -1).limit(limit))
    return jsonify({"data": serialize_list(items)})


# ─── ANALYTICS ───
@app.route("/analytics/trending", methods=["GET"])
def trending():
    limit = int(request.args.get("limit", 10))
    media_type = request.args.get("type")
    query = {}
    if media_type:
        query["type"] = media_type
    items = list(media_col.find(query).sort("view_count", -1).limit(limit))
    return jsonify({"data": serialize_list(items)})


@app.route("/analytics/searches", methods=["GET"])
def top_searches():
    limit = int(request.args.get("limit", 10))
    items = list(analytics_col.find({"type": "search"}).sort("count", -1).limit(limit))
    return jsonify({"data": serialize_list(items)})


@app.route("/analytics/genres", methods=["GET"])
def genre_breakdown():
    pipeline = [
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres", "count": {"$sum": 1}, "total_views": {"$sum": "$view_count"}}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    result = list(media_col.aggregate(pipeline))
    return jsonify({"data": [{"genre": r["_id"], "count": r["count"], "total_views": r.get("total_views", 0)} for r in result]})


@app.route("/analytics/types", methods=["GET"])
def type_breakdown():
    pipeline = [
        {"$group": {
            "_id": "$type",
            "count": {"$sum": 1},
            "total_views": {"$sum": "$view_count"},
            "avg_rating": {"$avg": "$ratings.imdb"}
        }},
        {"$sort": {"count": -1}}
    ]
    result = list(media_col.aggregate(pipeline))
    return jsonify({"data": [{
        "type": r["_id"],
        "count": r["count"],
        "total_views": r.get("total_views", 0),
        "avg_rating": round(r["avg_rating"], 1) if r.get("avg_rating") else None
    } for r in result]})


@app.route("/analytics/dashboard", methods=["GET"])
def dashboard():
    """Comprehensive dashboard stats endpoint"""
    total = media_col.count_documents({})
    total_views = list(media_col.aggregate([{"$group": {"_id": None, "sum": {"$sum": "$view_count"}}}]))
    total_views = total_views[0]["sum"] if total_views else 0

    total_reviews = reviews_col.count_documents({})

    # Type breakdown
    type_pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}, "views": {"$sum": "$view_count"}}},
        {"$sort": {"count": -1}}
    ]
    types = list(media_col.aggregate(type_pipeline))

    # Genre breakdown (top 15)
    genre_pipeline = [
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres", "count": {"$sum": 1}, "views": {"$sum": "$view_count"}}},
        {"$sort": {"views": -1}},
        {"$limit": 15}
    ]
    genres = list(media_col.aggregate(genre_pipeline))

    # Year distribution
    year_pipeline = [
        {"$match": {"release_year": {"$ne": None, "$gt": 1900}}},
        {"$group": {"_id": {"$subtract": ["$release_year", {"$mod": ["$release_year", 10]}]},
                    "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    years = list(media_col.aggregate(year_pipeline))

    # Top 5 trending
    top_trending = list(media_col.find({}, {
        "title": 1, "type": 1, "view_count": 1, "thumbnail": 1, "ratings": 1
    }).sort("view_count", -1).limit(5))

    # Top searches
    top_searches = list(analytics_col.find({"type": "search"}).sort("count", -1).limit(5))

    # Recently added
    recently_added = list(media_col.find({}, {
        "title": 1, "type": 1, "added_at": 1, "thumbnail": 1
    }).sort("added_at", -1).limit(5))

    # Average ratings by type
    rating_pipeline = [
        {"$match": {"ratings.imdb": {"$ne": None}}},
        {"$group": {"_id": "$type", "avg_imdb": {"$avg": "$ratings.imdb"}, "count": {"$sum": 1}}},
        {"$sort": {"avg_imdb": -1}}
    ]
    ratings_by_type = list(media_col.aggregate(rating_pipeline))

    # Unique genres count
    all_genres = list(media_col.aggregate([
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres"}}
    ]))

    return jsonify({
        "overview": {
            "total_items": total,
            "total_views": total_views,
            "total_reviews": total_reviews,
            "unique_genres": len(all_genres),
            "media_types": len(types),
        },
        "types": [{"type": t["_id"], "count": t["count"], "views": t.get("views", 0)} for t in types],
        "genres": [{"genre": g["_id"], "count": g["count"], "views": g.get("views", 0)} for g in genres],
        "year_distribution": [{"decade": y["_id"], "count": y["count"]} for y in years],
        "top_trending": serialize_list(top_trending),
        "top_searches": serialize_list(top_searches),
        "recently_added": serialize_list(recently_added),
        "ratings_by_type": [{"type": r["_id"], "avg_imdb": round(r["avg_imdb"], 1), "count": r["count"]} for r in ratings_by_type],
    })


@app.route("/analytics/activity", methods=["GET"])
def activity_feed():
    """
    Enhanced real-time activity feed simulation.
    Returns richer event details: user metadata, location, device, and event duration.
    """
    limit = int(request.args.get("limit", 20))

    # Fetch recent active items
    recent_items = list(media_col.find({}, {
        "title": 1, "type": 1, "view_count": 1, "thumbnail": 1, "genres": 1
    }).sort("view_count", -1).limit(60))

    if not recent_items:
        return jsonify({"events": []})

    locations = ["Coruscant", "Tatooine", "Naboo", "Hoth", "Endor", "Bespin", "Alderaan", "Kamino", "Dagobah", "Mustafar"]
    devices = ["Holocron", "Comm-Link", "Datapad", "Terminal", "Neural-Link", "Starship Console"]
    user_ranks = ["Padawan", "Jedi Knight", "Jedi Master", "Archivist", "Scholar", "Historian", "Council Member"]
    
    action_types = [
        ("viewed", 0.40, "icon_eye"),
        ("searched", 0.15, "icon_search"),
        ("rated", 0.10, "icon_star"),
        ("collected", 0.12, "icon_box"),
        ("shared", 0.08, "icon_share"),
        ("downloaded", 0.05, "icon_download"),
        ("translated", 0.10, "icon_globe")
    ]

    events = []
    now = datetime.utcnow()
    
    # Simulate a "Hot Trend" item
    viral_item = random.choice(recent_items) if recent_items else None
    
    for i in range(limit):
        # 30% chance for the "Hot Trend" item to appear in the feed
        item = viral_item if (viral_item and random.random() < 0.3) else random.choice(recent_items)
        
        # Weighted random action
        r = random.random()
        cumul = 0
        action, icon = "viewed", "icon_eye"
        for act, prob, ic in action_types:
            cumul += prob
            if r < cumul:
                action, icon = act, ic
                break
        
        minutes_ago = random.randint(0, 180)
        timestamp = (now - timedelta(minutes=minutes_ago))
        
        user_id = random.randint(1100, 9999)
        events.append({
            "id": f"evt_{i}_{timestamp.timestamp()}",
            "action": action,
            "action_icon": icon,
            "media_id": str(item["_id"]),
            "title": item["title"],
            "type": item["type"],
            "thumbnail": item.get("thumbnail", ""),
            "genres": item.get("genres", [])[:2],
            "timestamp": timestamp.isoformat(),
            "user": {
                "name": f"User-{user_id}",
                "rank": random.choice(user_ranks),
                "location": random.choice(locations),
                "device": random.choice(devices),
                "avatar_seed": user_id
            },
            "metadata": {
                "duration_min": random.randint(1, 120) if action == "viewed" else None,
                "rating": random.randint(7, 10) if action == "rated" else None,
                "sector": f"Sector-{random.randint(1, 24)}"
            }
        })

    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify({
        "events": events, 
        "generated_at": now.isoformat(),
        "active_node": "Coruscant-Main-Server",
        "load_factor": round(random.uniform(0.1, 0.4), 2)
    })


# ─── TIME CAPSULE ───
@app.route("/timecapsule/<int:decade>", methods=["GET"])
def time_capsule(decade):
    limit = int(request.args.get("limit", 30))
    media_type = request.args.get("type")
    query = {"release_year": {"$gte": decade, "$lt": decade + 10}}
    if media_type:
        query["type"] = media_type

    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$type", "items": {"$push": "$$ROOT"}, "count": {"$sum": 1}}},
    ]
    result = list(media_col.aggregate(pipeline))
    grouped = {}
    for r in result:
        grouped[r["_id"]] = serialize_list(r["items"][:5])

    total = media_col.count_documents(query)
    sample = list(media_col.find(query).sort("view_count", -1).limit(limit))

    return jsonify({
        "decade": decade,
        "total": total,
        "by_type": grouped,
        "highlights": serialize_list(sample),
    })


# ─── GENRES ───
@app.route("/genres", methods=["GET"])
def get_genres():
    pipeline = [
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres"}},
        {"$sort": {"_id": 1}}
    ]
    result = list(media_col.aggregate(pipeline))
    return jsonify({"genres": [r["_id"] for r in result]})


if __name__ == "__main__":
    is_debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=is_debug, host="0.0.0.0", port=5000)
