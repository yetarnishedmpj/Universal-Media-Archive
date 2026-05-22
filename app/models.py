from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

MediaType = Literal["movie", "book", "song", "game", "show", "video", "comic"]


class RatingsModel(BaseModel):
    imdb: float | None = None
    user: float | None = None


class SourceLinkModel(BaseModel):
    platform: str
    url: str
    availability: str = "unknown"


class RelatedMediaModel(BaseModel):
    media_id: str
    relation_type: str


class MediaBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: MediaType
    genres: list[str] = Field(default_factory=list)
    release_year: int = Field(ge=1800, le=2100)
    creators: list[str] = Field(default_factory=list)
    cast: list[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=5000)
    ratings: RatingsModel = Field(default_factory=RatingsModel)
    sources: list[SourceLinkModel] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    related: list[RelatedMediaModel] = Field(default_factory=list)
    thumbnail_url: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class MediaCreate(MediaBase):
    pass


class MediaResponse(MediaBase):
    id: str
    added_at: datetime | None = None
    popularity_score: int = 0
    analytics: dict[str, int] = Field(default_factory=dict)


class ReviewCreate(BaseModel):
    user_id: str
    media_id: str
    rating: float = Field(ge=0, le=10)
    comment: str = Field(min_length=1, max_length=2000)


class ReviewResponse(BaseModel):
    id: str
    user_id: str
    media_id: str
    rating: float
    comment: str
    username: str | None = None
    media_title: str | None = None
    media_type: str | None = None
    created_at: datetime | None = None


class MediaDetailResponse(MediaResponse):
    related_items: list[MediaResponse] = Field(default_factory=list)
    reviews: list[ReviewResponse] = Field(default_factory=list)


class MediaListResponse(BaseModel):
    items: list[MediaResponse] = Field(default_factory=list)
    total: int
    page: int
    limit: int


class SearchResponse(MediaListResponse):
    query: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    preferences: list[str] = Field(default_factory=list)
    watchlist: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)


class UserMediaAction(BaseModel):
    media_id: str


class UserResponse(BaseModel):
    id: str
    username: str
    preferences: list[str] = Field(default_factory=list)
    watchlist: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)


class UserDetailResponse(UserResponse):
    watchlist_items: list[MediaResponse] = Field(default_factory=list)
    history_items: list[MediaResponse] = Field(default_factory=list)


class UserListResponse(BaseModel):
    items: list[UserResponse] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    user_id: str | None = None
    items: list[MediaResponse] = Field(default_factory=list)


class CatalogFacetsResponse(BaseModel):
    genres: list[str] = Field(default_factory=list)
    years: list[int] = Field(default_factory=list)
    decades: list[int] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)


class NamedCountResponse(BaseModel):
    name: str
    count: int


class DashboardMetricResponse(BaseModel):
    label: str
    value: int
    hint: str | None = None


class DashboardSummaryResponse(BaseModel):
    metrics: list[DashboardMetricResponse] = Field(default_factory=list)
    top_genres: list[NamedCountResponse] = Field(default_factory=list)
    top_platforms: list[NamedCountResponse] = Field(default_factory=list)
    top_types: list[NamedCountResponse] = Field(default_factory=list)
    featured_media: list[MediaResponse] = Field(default_factory=list)
    recent_reviews: list[ReviewResponse] = Field(default_factory=list)


class CollectionResponse(BaseModel):
    slug: str
    title: str
    description: str
    items: list[MediaResponse] = Field(default_factory=list)


class CollectionListResponse(BaseModel):
    items: list[CollectionResponse] = Field(default_factory=list)


class GraphNodeResponse(BaseModel):
    id: str
    title: str
    type: str
    release_year: int | None = None


class GraphEdgeResponse(BaseModel):
    source_id: str
    target_id: str
    relation_type: str


class MediaGraphResponse(BaseModel):
    root_id: str
    nodes: list[GraphNodeResponse] = Field(default_factory=list)
    edges: list[GraphEdgeResponse] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    database: str
