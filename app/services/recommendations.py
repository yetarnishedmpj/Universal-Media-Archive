from __future__ import annotations

import math
from typing import Any

from bson import ObjectId
from pymongo.database import Database

from app.services.media_service import normalize_token, serialize_media


def compute_ai_score(
    item: dict[str, Any],
    genre_weights: dict[str, float],
    media_type_boost: str | None,
) -> float:
    """
    Weighted scoring: genre affinity (35%) + popularity (25%) + recency (15%) + type boost (10%) + imdb (15%)
    """
    score = 0.0
    genres = item.get("genres", [])
    if genres:
        genre_score = sum(genre_weights.get(normalize_token(g), 0.5) for g in genres) / len(genres)
        score += genre_score * 0.35

    popularity = item.get("popularity_score", 0)
    score += min(popularity / 1000.0, 1.0) * 0.25

    release_year = item.get("release_year")
    if release_year and isinstance(release_year, int):
        # Logistic decay for older movies (centered around 2010)
        recency = 1 / (1 + math.exp(-0.1 * (release_year - 2010)))
        score += recency * 0.15

    if media_type_boost and item.get("type") == media_type_boost:
        score += 0.1

    imdb = item.get("ratings", {}).get("imdb")
    if imdb:
        score += (float(imdb) / 10.0) * 0.15

    return round(score, 4)


def get_trending_media(db: Database, limit: int) -> list[dict[str, Any]]:
    cursor = db.media.find().sort(
        [
            ("popularity_score", -1),
            ("ratings.user", -1),
            ("added_at", -1),
        ]
    ).limit(limit)
    return [serialize_media(document) for document in cursor]


def build_recommendations(
    db: Database,
    user_document: dict[str, Any] | None,
    limit: int,
) -> list[dict[str, Any]]:
    if user_document is None:
        return get_trending_media(db, limit)

    history_ids = [item for item in user_document.get("history", []) if isinstance(item, ObjectId)]
    watchlist_ids = [item for item in user_document.get("watchlist", []) if isinstance(item, ObjectId)]
    excluded_ids = set(history_ids + watchlist_ids)

    preference_terms = {
        normalize_token(value)
        for value in user_document.get("preferences", [])
        if value.strip()
    }

    history_documents = list(db.media.find({"_id": {"$in": history_ids}}))

    history_genres = {
        normalize_token(genre)
        for document in history_documents
        for genre in document.get("genres", [])
    }
    history_tags = {
        normalize_token(tag)
        for document in history_documents
        for tag in document.get("tags", [])
    }
    history_creators = {
        normalize_token(creator)
        for document in history_documents
        for creator in document.get("creators", [])
    }
    history_media_ids = {document["_id"] for document in history_documents}

    candidates = list(db.media.find({"_id": {"$nin": list(excluded_ids)}}).sort("popularity_score", -1).limit(200))
    
    # Simple genre weights based on user preferences
    genre_weights = {term: 2.0 for term in preference_terms}
    for g in history_genres:
        genre_weights[g] = genre_weights.get(g, 1.0) + 1.0

    scored_items: list[tuple[float, dict[str, Any]]] = []

    for document in candidates:
        score = compute_ai_score(document, genre_weights, None)
        
        # Boost if related to history
        related_targets = {
            relation.get("media_id")
            for relation in document.get("related", [])
            if relation.get("media_id") is not None
        }
        if history_media_ids & related_targets:
            score += 0.2

        scored_items.append((score, document))

    if not scored_items:
        return get_trending_media(db, limit)

    scored_items.sort(
        key=lambda item: item[0],
        reverse=True,
    )
    return [serialize_media(document) for _, document in scored_items[:limit]]
