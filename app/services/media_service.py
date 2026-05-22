from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from pymongo.database import Database


def unique_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for raw_value in values:
        value = raw_value.strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(value)

    return result


def normalize_token(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_object_id(raw_id: str, label: str = "id") -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label}: '{raw_id}'",
        ) from exc


def build_media_filters(
    media_type: str | None = None,
    genre: str | None = None,
    year: int | None = None,
    tag: str | None = None,
    platform: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}

    if media_type:
        query["type"] = media_type
    if genre:
        query["genres"] = {"$regex": f"^{re.escape(genre.strip())}$", "$options": "i"}
    if year:
        query["release_year"] = year
    if tag:
        query["tags"] = {"$regex": f"^{re.escape(tag.strip())}$", "$options": "i"}
    if platform:
        query["sources.platform"] = {"$regex": f"^{re.escape(platform.strip())}$", "$options": "i"}

    return query


def serialize_media(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "title": document.get("title"),
        "type": document.get("type"),
        "genres": document.get("genres", []),
        "release_year": document.get("release_year"),
        "creators": document.get("creators", []),
        "cast": document.get("cast", []),
        "description": document.get("description", ""),
        "ratings": document.get("ratings", {}),
        "sources": document.get("sources", []),
        "tags": document.get("tags", []),
        "related": [
            {
                "media_id": str(item["media_id"]) if isinstance(item.get("media_id"), ObjectId) else item.get("media_id"),
                "relation_type": item.get("relation_type"),
            }
            for item in document.get("related", [])
        ],
        "thumbnail_url": document.get("thumbnail_url"),
        "attributes": document.get("attributes", {}),
        "added_at": document.get("added_at"),
        "popularity_score": int(document.get("popularity_score", 0)),
        "analytics": document.get("analytics", {"views": 0, "watchlisted": 0, "search_hits": 0}),
    }


def serialize_review(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "user_id": str(document.get("user_id")),
        "media_id": str(document.get("media_id")),
        "rating": document.get("rating"),
        "comment": document.get("comment"),
        "username": document.get("username"),
        "media_title": document.get("media_title"),
        "media_type": document.get("media_type"),
        "created_at": document.get("created_at"),
    }


def serialize_user(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "username": document.get("username"),
        "preferences": document.get("preferences", []),
        "watchlist": [str(item) for item in document.get("watchlist", [])],
        "history": [str(item) for item in document.get("history", [])],
    }


def get_media_or_404(db: Database, media_id: str) -> dict[str, Any]:
    object_id = parse_object_id(media_id, "media id")
    media = db.media.find_one({"_id": object_id})
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    return media


def get_user_or_404(db: Database, user_id: str) -> dict[str, Any]:
    object_id = parse_object_id(user_id, "user id")
    user = db.users.find_one({"_id": object_id})
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


def update_media_user_rating(db: Database, media_id: ObjectId) -> None:
    pipeline = [
        {"$match": {"media_id": media_id}},
        {"$group": {"_id": "$media_id", "average_rating": {"$avg": "$rating"}}},
    ]
    result = next(iter(db.reviews.aggregate(pipeline)), None)
    rating_value = round(result["average_rating"], 1) if result else None
    db.media.update_one({"_id": media_id}, {"$set": {"ratings.user": rating_value}})
