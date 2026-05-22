from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.errors import DuplicateKeyError
from pymongo import DESCENDING
from pymongo.database import Database

from app.db.mongo import get_database
from app.models import (
    CatalogFacetsResponse,
    CollectionListResponse,
    CollectionResponse,
    DashboardSummaryResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    HealthResponse,
    MediaCreate,
    MediaDetailResponse,
    MediaGraphResponse,
    MediaListResponse,
    MediaResponse,
    NamedCountResponse,
    RecommendationResponse,
    ReviewCreate,
    ReviewResponse,
    SearchResponse,
    UserCreate,
    UserDetailResponse,
    UserListResponse,
    UserMediaAction,
    UserResponse,
)
from app.services.archive_service import (
    build_curated_collections,
    build_dashboard_summary,
    build_media_graph,
)
from app.services.media_service import (
    build_media_filters,
    get_media_or_404,
    get_user_or_404,
    parse_object_id,
    serialize_media,
    serialize_review,
    serialize_user,
    unique_preserving_order,
    update_media_user_rating,
)
from app.services.recommendations import build_recommendations

router = APIRouter()


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, 48))


@router.get("/health", response_model=HealthResponse)
def health_check(db: Database = Depends(get_database)) -> HealthResponse:
    db.command("ping")
    return HealthResponse(status="ok", database="connected")


@router.get("/catalog/facets", response_model=CatalogFacetsResponse)
def catalog_facets(db: Database = Depends(get_database)) -> CatalogFacetsResponse:
    genres = sorted({genre for genre in db.media.distinct("genres") if genre})
    years = sorted({year for year in db.media.distinct("release_year") if isinstance(year, int)}, reverse=True)
    decades = sorted({year - (year % 10) for year in years}, reverse=True)
    media_types = sorted({media_type for media_type in db.media.distinct("type") if media_type})
    tags = sorted({tag for tag in db.media.distinct("tags") if tag})
    platforms = sorted({platform for platform in db.media.distinct("sources.platform") if platform})
    return CatalogFacetsResponse(
        genres=genres,
        years=years,
        decades=decades,
        types=media_types,
        tags=tags,
        platforms=platforms,
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(db: Database = Depends(get_database)) -> DashboardSummaryResponse:
    payload = build_dashboard_summary(db)
    return DashboardSummaryResponse(
        metrics=payload["metrics"],
        top_genres=[NamedCountResponse(**item) for item in payload["top_genres"]],
        top_platforms=[NamedCountResponse(**item) for item in payload["top_platforms"]],
        top_types=[NamedCountResponse(**item) for item in payload["top_types"]],
        featured_media=[MediaResponse(**item) for item in payload["featured_media"]],
        recent_reviews=[ReviewResponse(**item) for item in payload["recent_reviews"]],
    )


@router.get("/collections", response_model=CollectionListResponse)
def curated_collections(
    limit: int = Query(default=5, ge=1, le=12),
    db: Database = Depends(get_database),
) -> CollectionListResponse:
    collections = build_curated_collections(db, limit=limit)
    return CollectionListResponse(
        items=[
            CollectionResponse(
                slug=item["slug"],
                title=item["title"],
                description=item["description"],
                items=[MediaResponse(**media_item) for media_item in item["items"]],
            )
            for item in collections
        ]
    )


@router.post("/media", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
def add_media(payload: MediaCreate, db: Database = Depends(get_database)) -> MediaResponse:
    document = payload.model_dump()
    document["genres"] = unique_preserving_order(document.get("genres", []))
    document["creators"] = unique_preserving_order(document.get("creators", []))
    document["cast"] = unique_preserving_order(document.get("cast", []))
    document["tags"] = unique_preserving_order(document.get("tags", []))
    document["related"] = [
        {
            "media_id": parse_object_id(item["media_id"], "related media id"),
            "relation_type": item["relation_type"].strip(),
        }
        for item in document.get("related", [])
    ]
    document["added_at"] = datetime.now(timezone.utc)
    document["popularity_score"] = 0
    document["analytics"] = {"views": 0, "watchlisted": 0, "search_hits": 0}

    result = db.media.insert_one(document)
    created = db.media.find_one({"_id": result.inserted_id})
    return MediaResponse(**serialize_media(created))


@router.get("/media", response_model=MediaListResponse)
def list_media(
    media_type: str | None = Query(default=None, alias="type"),
    genre: str | None = None,
    year: int | None = Query(default=None, ge=1800, le=2100),
    tag: str | None = None,
    platform: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=48),
    sort: str = Query(default="recent", pattern="^(recent|trending|title|release_year)$"),
    db: Database = Depends(get_database),
) -> MediaListResponse:
    query = build_media_filters(
        media_type=media_type,
        genre=genre,
        year=year,
        tag=tag,
        platform=platform,
    )
    sort_map = {
        "recent": [("added_at", DESCENDING), ("release_year", DESCENDING)],
        "trending": [("popularity_score", DESCENDING), ("ratings.user", DESCENDING)],
        "title": [("title", 1)],
        "release_year": [("release_year", DESCENDING), ("title", 1)],
    }
    page_limit = clamp_limit(limit)
    skip = (page - 1) * page_limit
    total = db.media.count_documents(query)
    items = [
        MediaResponse(**serialize_media(document))
        for document in db.media.find(query).sort(sort_map[sort]).skip(skip).limit(page_limit)
    ]
    return MediaListResponse(items=items, total=total, page=page, limit=page_limit)


@router.get("/search", response_model=SearchResponse)
def search_media(
    q: str = Query(min_length=1),
    media_type: str | None = Query(default=None, alias="type"),
    genre: str | None = None,
    year: int | None = Query(default=None, ge=1800, le=2100),
    tag: str | None = None,
    platform: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=48),
    db: Database = Depends(get_database),
) -> SearchResponse:
    base_filters = build_media_filters(
        media_type=media_type,
        genre=genre,
        year=year,
        tag=tag,
        platform=platform,
    )
    text_query = {"$text": {"$search": q}}
    final_query = {"$and": [text_query, base_filters]} if base_filters else text_query

    projection = {"score": {"$meta": "textScore"}}
    items = list(
        db.media.find(final_query, projection).sort(
            [("score", {"$meta": "textScore"}), ("popularity_score", -1)]
        )
    )

    if not items:
        fallback = {
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"genres": {"$regex": q, "$options": "i"}},
                {"tags": {"$regex": q, "$options": "i"}},
            ]
        }
        final_query = {"$and": [fallback, base_filters]} if base_filters else fallback
        items = list(db.media.find(final_query).sort([("popularity_score", -1), ("added_at", -1)]))

    matched_ids = [item["_id"] for item in items]
    if matched_ids:
        db.media.update_many(
            {"_id": {"$in": matched_ids}},
            {"$inc": {"analytics.search_hits": 1, "popularity_score": 1}},
        )

    page_limit = clamp_limit(limit)
    start = (page - 1) * page_limit
    paged_items = [MediaResponse(**serialize_media(item)) for item in items[start : start + page_limit]]
    return SearchResponse(query=q, items=paged_items, total=len(items), page=page, limit=page_limit)


@router.get("/media/{media_id}", response_model=MediaDetailResponse)
def media_detail(media_id: str, db: Database = Depends(get_database)) -> MediaDetailResponse:
    media = get_media_or_404(db, media_id)
    review_pipeline = [
        {"$match": {"media_id": media["_id"]}},
        {"$sort": {"created_at": -1}},
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user",
            }
        },
        {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"username": "$user.username"}},
        {"$project": {"user": 0}},
    ]
    review_documents = list(db.reviews.aggregate(review_pipeline))

    related_ids = [item["media_id"] for item in media.get("related", []) if item.get("media_id")]
    related_documents = list(db.media.find({"_id": {"$in": related_ids}})) if related_ids else []

    payload = serialize_media(media)
    payload["reviews"] = [ReviewResponse(**serialize_review(document)) for document in review_documents]
    payload["related_items"] = [MediaResponse(**serialize_media(document)) for document in related_documents]
    return MediaDetailResponse(**payload)


@router.get("/media/{media_id}/graph", response_model=MediaGraphResponse)
def media_graph(media_id: str, db: Database = Depends(get_database)) -> MediaGraphResponse:
    media = get_media_or_404(db, media_id)
    payload = build_media_graph(db, media)
    return MediaGraphResponse(
        root_id=payload["root_id"],
        nodes=[GraphNodeResponse(**item) for item in payload["nodes"]],
        edges=[GraphEdgeResponse(**item) for item in payload["edges"]],
    )


@router.post("/review", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def add_review(payload: ReviewCreate, db: Database = Depends(get_database)) -> ReviewResponse:
    user = get_user_or_404(db, payload.user_id)
    media_object_id = parse_object_id(payload.media_id, "media id")
    media_exists = db.media.find_one({"_id": media_object_id}, {"_id": 1})
    if media_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")

    document = payload.model_dump()
    document["user_id"] = parse_object_id(payload.user_id, "user id")
    document["media_id"] = media_object_id
    document["created_at"] = datetime.now(timezone.utc)
    result = db.reviews.insert_one(document)

    update_media_user_rating(db, media_object_id)
    db.media.update_one({"_id": media_object_id}, {"$inc": {"popularity_score": 2}})
    created = db.reviews.find_one({"_id": result.inserted_id})
    created["username"] = user["username"]
    return ReviewResponse(**serialize_review(created))


@router.get("/recommendations", response_model=RecommendationResponse)
def recommendations(
    user_id: str | None = None,
    limit: int = Query(default=8, ge=1, le=24),
    db: Database = Depends(get_database),
) -> RecommendationResponse:
    user_document = get_user_or_404(db, user_id) if user_id else None
    items = build_recommendations(db, user_document, limit=limit)
    return RecommendationResponse(user_id=user_id, items=[MediaResponse(**item) for item in items])


@router.get("/time-capsule", response_model=MediaListResponse)
def time_capsule(
    decade: int = Query(ge=1800, le=2100),
    limit: int = Query(default=12, ge=1, le=48),
    db: Database = Depends(get_database),
) -> MediaListResponse:
    start_year = decade - (decade % 10)
    end_year = start_year + 9
    query = {"release_year": {"$gte": start_year, "$lte": end_year}}
    page_limit = clamp_limit(limit)
    items = [
        MediaResponse(**serialize_media(document))
        for document in db.media.find(query).sort([("release_year", -1), ("popularity_score", -1)]).limit(page_limit)
    ]
    total = db.media.count_documents(query)
    return MediaListResponse(items=items, total=total, page=1, limit=page_limit)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Database = Depends(get_database)) -> UserResponse:
    watchlist = [parse_object_id(media_id, "watchlist media id") for media_id in payload.watchlist]
    history = [parse_object_id(media_id, "history media id") for media_id in payload.history]
    document = {
        "username": payload.username.strip(),
        "preferences": unique_preserving_order(payload.preferences),
        "watchlist": watchlist,
        "history": history,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = db.users.insert_one(document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username already exists. Choose a different one.",
        ) from exc
    created = db.users.find_one({"_id": result.inserted_id})
    return UserResponse(**serialize_user(created))


@router.get("/users", response_model=UserListResponse)
def list_users(db: Database = Depends(get_database)) -> UserListResponse:
    users = [UserResponse(**serialize_user(document)) for document in db.users.find().sort("username", 1)]
    return UserListResponse(items=users)


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def user_detail(user_id: str, db: Database = Depends(get_database)) -> UserDetailResponse:
    user = get_user_or_404(db, user_id)

    watchlist_items = list(db.media.find({"_id": {"$in": user.get("watchlist", [])}}))
    history_ids = [item for item in user.get("history", []) if item]
    history_items = list(db.media.find({"_id": {"$in": history_ids[-12:]}}))

    payload = serialize_user(user)
    payload["watchlist_items"] = [MediaResponse(**serialize_media(document)) for document in watchlist_items]
    payload["history_items"] = [MediaResponse(**serialize_media(document)) for document in history_items]
    return UserDetailResponse(**payload)


@router.post("/users/{user_id}/watchlist", response_model=UserResponse)
def add_to_watchlist(
    user_id: str,
    payload: UserMediaAction,
    db: Database = Depends(get_database),
) -> UserResponse:
    get_user_or_404(db, user_id)
    media = get_media_or_404(db, payload.media_id)
    user_object_id = parse_object_id(user_id, "user id")

    db.users.update_one(
        {"_id": user_object_id},
        {"$addToSet": {"watchlist": media["_id"]}},
    )
    db.media.update_one(
        {"_id": media["_id"]},
        {"$inc": {"analytics.watchlisted": 1, "popularity_score": 1}},
    )
    updated = db.users.find_one({"_id": user_object_id})
    return UserResponse(**serialize_user(updated))


@router.post("/users/{user_id}/history", response_model=UserResponse)
def add_to_history(
    user_id: str,
    payload: UserMediaAction,
    db: Database = Depends(get_database),
) -> UserResponse:
    get_user_or_404(db, user_id)
    media = get_media_or_404(db, payload.media_id)
    user_object_id = parse_object_id(user_id, "user id")

    db.users.update_one(
        {"_id": user_object_id},
        {"$push": {"history": {"$each": [media["_id"]], "$slice": -50}}},
    )
    db.media.update_one(
        {"_id": media["_id"]},
        {"$inc": {"analytics.views": 1, "popularity_score": 1}},
    )
    updated = db.users.find_one({"_id": user_object_id})
    return UserResponse(**serialize_user(updated))
