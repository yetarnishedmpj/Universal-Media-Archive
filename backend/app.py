from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient, TEXT
from bson import ObjectId
from datetime import datetime
import os
import sys

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
media_col.create_index([("title", TEXT), ("genres", TEXT), ("tags", TEXT), ("description", TEXT)])
media_col.create_index("type")
media_col.create_index("release_year")
media_col.create_index("genres")
media_col.create_index("added_at", expireAfterSeconds=2592000) # 30 Days TTL
reviews_col.create_index([("media_id", 1), ("user_id", 1)])


def serialize(doc):
    if doc is None:
        return None
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
        "version": "1.0.0",
        "endpoints": ["/media", "/search", "/review", "/reviews/<media_id>",
                      "/users", "/recommendations", "/analytics/trending",
                      "/analytics/searches", "/analytics/genres", "/analytics/types",
                      "/timecapsule/<decade>", "/genres", "/health"]
    })


# ─── HEALTH ───
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "db": DB_NAME})


# ─── MEDIA ───
@app.route("/media", methods=["POST"])
def add_media():
    data = request.json
    required = ["title", "type"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"Missing required field: {f}"}), 400

    valid_types = ["movie", "book", "song", "game", "show", "video", "comic", "podcast"]
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
        "view_count": 0,
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
    try:
        doc = media_col.find_one_and_update(
            {"_id": ObjectId(media_id)},
            {"$inc": {"view_count": 1}},
            return_document=True
        )
    except Exception:
        return jsonify({"error": "Invalid media ID"}), 400

    if not doc:
        return jsonify({"error": "Media not found"}), 404

    reviews = list(reviews_col.find({"media_id": media_id}))
    doc["reviews"] = serialize_list(reviews)

    related_ids = [r.get("media_id") for r in doc.get("related", []) if r.get("media_id")]
    related_docs = []
    for rid in related_ids[:6]:
        try:
            rel = media_col.find_one({"_id": ObjectId(rid)})
            if rel:
                related_docs.append(serialize(rel))
        except Exception:
            pass
    doc["related_media"] = related_docs

    analytics_col.update_one(
        {"media_id": media_id, "date": datetime.utcnow().strftime("%Y-%m-%d")},
        {"$inc": {"views": 1}},
        upsert=True
    )
    return jsonify(serialize(doc))


@app.route("/media/<media_id>", methods=["PUT"])
def update_media(media_id):
    try:
        data = request.json
        data.pop("_id", None)
        result = media_col.update_one({"_id": ObjectId(media_id)}, {"$set": data})
    except Exception:
        return jsonify({"error": "Invalid media ID"}), 400
    if result.matched_count == 0:
        return jsonify({"error": "Media not found"}), 404
    return jsonify({"message": "Updated successfully"})

from utils.vidking import get_vidking_source

@app.route("/get_stream/<media_id>")
def get_stream(media_id):
    try:
        item = media_col.find_one({"_id": ObjectId(media_id)})
    except:
        return {"error": "Invalid ID"}, 400

    if not item:
        return {"error": "Not found"}, 404

    # ✅ CACHE
    if item.get("stream"):
        return {"sources": [item["stream"]]}

    # 🔥 SCRAPE HERE (ONLY HERE)
    sources = get_vidking_source(item["title"])

    if sources:
        media_col.update_one(
            {"_id": item["_id"]},
            {"$set": {"stream": sources[0]}}
        )
        return {"sources": sources}

    return {
        "fallback": f"https://www.vidking.net/search?q={item['title'].replace(' ', '+')}"
    }


@app.route("/media/<media_id>", methods=["DELETE"])
def delete_media(media_id):
    try:
        result = media_col.delete_one({"_id": ObjectId(media_id)})
    except Exception:
        return jsonify({"error": "Invalid media ID"}), 400
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
    sort_order = [("added_at", -1)]
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


# ─── RECOMMENDATIONS ───
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
    items = list(media_col.find().sort("view_count", -1).limit(limit))
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
        {"$group": {"_id": "$genres", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    result = list(media_col.aggregate(pipeline))
    return jsonify({"data": [{"genre": r["_id"], "count": r["count"]} for r in result]})


@app.route("/analytics/types", methods=["GET"])
def type_breakdown():
    pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    result = list(media_col.aggregate(pipeline))
    return jsonify({"data": [{"type": r["_id"], "count": r["count"]} for r in result]})


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
