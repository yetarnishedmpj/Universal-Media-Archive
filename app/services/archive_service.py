from __future__ import annotations

from collections import Counter
from typing import Any

from bson import ObjectId
from pymongo.database import Database

from app.services.media_service import serialize_media, serialize_review


def _top_named_counts(values: list[str], limit: int) -> list[dict[str, int | str]]:
    counter = Counter(value for value in values if value)
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def build_dashboard_summary(db: Database) -> dict[str, Any]:
    total_media = db.media.count_documents({})
    total_reviews = db.reviews.count_documents({})
    total_users = db.users.count_documents({})
    total_sources = sum(len(document.get("sources", [])) for document in db.media.find({}, {"sources": 1}))
    total_relationships = sum(len(document.get("related", [])) for document in db.media.find({}, {"related": 1}))

    all_genres = [genre for document in db.media.find({}, {"genres": 1}) for genre in document.get("genres", [])]
    all_platforms = [
        source.get("platform")
        for document in db.media.find({}, {"sources": 1})
        for source in document.get("sources", [])
        if source.get("platform")
    ]
    all_types = [document.get("type") for document in db.media.find({}, {"type": 1}) if document.get("type")]
    active_decades = len({
        year - (year % 10)
        for year in db.media.distinct("release_year")
        if isinstance(year, int)
    })

    featured_media = [
        serialize_media(document)
        for document in db.media.find().sort(
            [("popularity_score", -1), ("ratings.user", -1), ("added_at", -1)]
        ).limit(6)
    ]

    review_pipeline = [
        {"$sort": {"created_at": -1}},
        {"$limit": 6},
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user",
            }
        },
        {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "media",
                "localField": "media_id",
                "foreignField": "_id",
                "as": "media",
            }
        },
        {"$unwind": {"path": "$media", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "username": "$user.username",
                "media_title": "$media.title",
                "media_type": "$media.type",
            }
        },
        {"$project": {"user": 0, "media": 0}},
    ]
    recent_reviews = [serialize_review(document) for document in db.reviews.aggregate(review_pipeline)]

    metrics = [
        {"label": "Media entities", "value": total_media, "hint": "Unified records across formats"},
        {"label": "Source links", "value": total_sources, "hint": "Outbound access points"},
        {"label": "Relationships", "value": total_relationships, "hint": "Knowledge-graph edges"},
        {"label": "Archive decades", "value": active_decades, "hint": "Browseable eras"},
        {"label": "Community reviews", "value": total_reviews, "hint": "Annotations from users"},
        {"label": "Demo users", "value": total_users, "hint": "Profiles for testing recommendations"},
    ]

    return {
        "metrics": metrics,
        "top_genres": _top_named_counts(all_genres, 8),
        "top_platforms": _top_named_counts(all_platforms, 8),
        "top_types": _top_named_counts(all_types, 8),
        "featured_media": featured_media,
        "recent_reviews": recent_reviews,
    }


def build_curated_collections(db: Database, limit: int) -> list[dict[str, Any]]:
    collection_definitions = [
        {
            "slug": "adaptation-atlas",
            "title": "Adaptation Atlas",
            "description": "Stories that jump between books, film, television, comics, and games.",
            "query": {
                "$or": [
                    {"tags": {"$regex": "adaptation", "$options": "i"}},
                    {"related.relation_type": {"$regex": "based on|adaptation", "$options": "i"}},
                ]
            },
        },
        {
            "slug": "preservation-shelf",
            "title": "Preservation Shelf",
            "description": "Documentaries, histories, and archival works that foreground cultural memory.",
            "query": {
                "$or": [
                    {"tags": {"$regex": "preservation|history|archive", "$options": "i"}},
                    {"genres": {"$regex": "Documentary|History", "$options": "i"}},
                ]
            },
        },
        {
            "slug": "mythic-worlds",
            "title": "Mythic Worlds",
            "description": "Fantasy and mythology across animation, games, songs, and graphic storytelling.",
            "query": {
                "$or": [
                    {"genres": {"$regex": "Fantasy", "$options": "i"}},
                    {"tags": {"$regex": "mythology|dreams|mythic", "$options": "i"}},
                ]
            },
        },
        {
            "slug": "study-signal",
            "title": "Study Signal",
            "description": "Ambient, essayistic, and low-friction media for quiet exploration.",
            "query": {
                "$or": [
                    {"tags": {"$regex": "study|ambient|community", "$options": "i"}},
                    {"type": {"$in": ["song", "video"]}},
                ]
            },
        },
        {
            "slug": "playable-stories",
            "title": "Playable Stories",
            "description": "Games that carry strong narrative, systems, and worldbuilding signatures.",
            "query": {
                "$and": [
                    {"type": "game"},
                    {
                        "$or": [
                            {"tags": {"$regex": "narrative|exploration|indie|worldbuilding", "$options": "i"}},
                            {"genres": {"$regex": "Adventure|Drama", "$options": "i"}},
                        ]
                    },
                ]
            },
        },
        {
            "slug": "time-capsule-essentials",
            "title": "Time Capsule Essentials",
            "description": "Older but still resonant works that give the archive historical depth.",
            "query": {"release_year": {"$lte": 1999}},
        },
    ]

    collections: list[dict[str, Any]] = []
    for definition in collection_definitions:
        cursor = db.media.find(definition["query"]).sort(
            [("popularity_score", -1), ("release_year", -1), ("title", 1)]
        ).limit(limit)
        collections.append(
            {
                "slug": definition["slug"],
                "title": definition["title"],
                "description": definition["description"],
                "items": [serialize_media(document) for document in cursor],
            }
        )
    return collections


def build_media_graph(db: Database, root_document: dict[str, Any]) -> dict[str, Any]:
    root_id = root_document["_id"]
    outgoing_relations = root_document.get("related", [])
    incoming_documents = list(db.media.find({"related.media_id": root_id}))

    nodes: dict[ObjectId, dict[str, Any]] = {root_id: root_document}
    edges: list[dict[str, str]] = []

    neighbor_ids = {relation.get("media_id") for relation in outgoing_relations if relation.get("media_id")}
    neighbor_ids.update(document["_id"] for document in incoming_documents)

    if neighbor_ids:
        for document in db.media.find({"_id": {"$in": list(neighbor_ids)}}):
            nodes[document["_id"]] = document

    for relation in outgoing_relations:
        target_id = relation.get("media_id")
        if target_id is None:
            continue
        edges.append(
            {
                "source_id": str(root_id),
                "target_id": str(target_id),
                "relation_type": relation.get("relation_type", "related"),
            }
        )

    for document in incoming_documents:
        for relation in document.get("related", []):
            if relation.get("media_id") == root_id:
                edges.append(
                    {
                        "source_id": str(document["_id"]),
                        "target_id": str(root_id),
                        "relation_type": relation.get("relation_type", "related"),
                    }
                )

    node_id_set = set(nodes.keys())
    for document in list(nodes.values()):
        for relation in document.get("related", []):
            target_id = relation.get("media_id")
            if target_id in node_id_set and target_id != document["_id"]:
                edge = {
                    "source_id": str(document["_id"]),
                    "target_id": str(target_id),
                    "relation_type": relation.get("relation_type", "related"),
                }
                if edge not in edges:
                    edges.append(edge)

    serialized_nodes = [
        {
            "id": str(document["_id"]),
            "title": document.get("title"),
            "type": document.get("type"),
            "release_year": document.get("release_year"),
        }
        for document in sorted(
            nodes.values(),
            key=lambda item: (item["_id"] != root_id, item.get("title", "")),
        )
    ]

    return {"root_id": str(root_id), "nodes": serialized_nodes, "edges": edges}
