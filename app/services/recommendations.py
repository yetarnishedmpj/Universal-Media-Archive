from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo.database import Database

from app.services.media_service import normalize_token, serialize_media


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

    candidates = list(db.media.find({"_id": {"$nin": list(excluded_ids)}}))
    scored_items: list[tuple[float, dict[str, Any]]] = []

    for document in candidates:
        genres = {normalize_token(genre) for genre in document.get("genres", [])}
        tags = {normalize_token(tag) for tag in document.get("tags", [])}
        creators = {normalize_token(creator) for creator in document.get("creators", [])}
        related_targets = {
            relation.get("media_id")
            for relation in document.get("related", [])
            if relation.get("media_id") is not None
        }

        score = document.get("popularity_score", 0) / 20
        score += len((preference_terms | history_genres) & genres) * 2.8
        score += len((preference_terms | history_tags) & tags) * 2.0
        score += len(history_creators & creators) * 1.5
        if history_media_ids & related_targets:
            score += 3.5

        if score > 0 or not preference_terms:
            scored_items.append((score, document))

    if not scored_items:
        return get_trending_media(db, limit)

    scored_items.sort(
        key=lambda item: (
            item[0],
            item[1].get("popularity_score", 0),
            item[1].get("release_year", 0),
        ),
        reverse=True,
    )
    return [serialize_media(document) for _, document in scored_items[:limit]]
