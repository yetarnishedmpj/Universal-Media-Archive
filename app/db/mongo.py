from __future__ import annotations

import logging

from fastapi import HTTPException, status
from pymongo import ASCENDING, DESCENDING, TEXT, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.db.seed_data import build_seed_payload

logger = logging.getLogger(__name__)

_client: MongoClient | None = None
_database: Database | None = None


def ensure_indexes(db: Database) -> None:
    db.media.create_index(
        [("title", TEXT), ("genres", TEXT), ("tags", TEXT)],
        name="media_text_search",
    )
    db.media.create_index([("type", ASCENDING), ("release_year", DESCENDING)])
    db.media.create_index([("added_at", DESCENDING)])
    db.media.create_index([("popularity_score", DESCENDING)])
    db.users.create_index([("username", ASCENDING)], unique=True)
    db.reviews.create_index([("media_id", ASCENDING), ("created_at", DESCENDING)])
    db.reviews.create_index([("user_id", ASCENDING), ("media_id", ASCENDING)])


def recompute_user_ratings(db: Database) -> None:
    pipeline = [
        {
            "$group": {
                "_id": "$media_id",
                "average_rating": {"$avg": "$rating"},
            }
        }
    ]
    for result in db.reviews.aggregate(pipeline):
        db.media.update_one(
            {"_id": result["_id"]},
            {"$set": {"ratings.user": round(result["average_rating"], 1)}},
        )


def seed_database(db: Database, force: bool = False) -> None:
    if force:
        db.reviews.delete_many({})
        db.users.delete_many({})
        db.media.delete_many({})

    if db.media.count_documents({}) > 0:
        return

    media_documents, user_documents, review_documents = build_seed_payload()
    db.media.insert_many(media_documents)
    db.users.insert_many(user_documents)
    db.reviews.insert_many(review_documents)
    recompute_user_ratings(db)


def connect_to_mongo() -> Database | None:
    global _client, _database

    if _database is not None:
        return _database

    try:
        _client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
        )
        _client.admin.command("ping")
        _database = _client[settings.mongodb_db_name]
        ensure_indexes(_database)
        if settings.seed_on_startup:
            seed_database(_database, force=settings.seed_force_reset)
        logger.info("Connected to MongoDB database '%s'.", settings.mongodb_db_name)
        return _database
    except PyMongoError as exc:
        logger.warning("MongoDB connection unavailable: %s", exc)
        _client = None
        _database = None
        return None


def get_database() -> Database:
    database = _database if _database is not None else connect_to_mongo()
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "MongoDB is unavailable. Start MongoDB and confirm the MONGODB_URI "
                "setting before using the archive."
            ),
        )
    return database


def close_mongo_connection() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None
