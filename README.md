# Universal Media Archive

Universal Media Archive is a full-stack web application inspired by the preservation-first spirit of the Internet Archive. It does **not** host copyrighted media. Instead, it stores rich metadata, relationships, user activity, and external source links so people can discover movies, shows, books, comics, songs, games, and online videos from one place.

## Stack

- Backend: FastAPI
- Database: MongoDB
- Frontend: Server-rendered HTML with CSS and vanilla JavaScript
- Data model: Unified `media` schema with type-specific `attributes`

## Features

- Unified media catalog across movies, books, comics, songs, games, shows, and videos
- MongoDB text search on title, genres, and tags
- Filtering by media type, genre, release year, tag, and source platform
- Pagination for archive browsing
- Dashboard summary with archive metrics, top genres, top platforms, and recent review activity
- Curated archive collections for adaptations, preservation, playable stories, and more
- Detailed media pages with metadata, related entities, reviews, and external access links
- Knowledge-graph endpoint for relationship mapping around each media entity
- Recommendation engine based on user preferences plus watch/history signals
- Watchlist and history tracking for demo users
- Archive Mode toggle for a denser, metadata-first browsing layout
- Time Capsule browsing by decade
- Expanded seed data with 39 media entries, 7 users, and 21 reviews for quick testing
- Deploy-ready containerization with Docker, Compose, health checks, and Render configuration

## Folder Structure

```text
universal-media-archive/
|-- app/
|   |-- api/
|   |-- core/
|   |-- db/
|   |-- services/
|   |-- static/
|   |-- templates/
|   `-- main.py
|-- scripts/
|-- .dockerignore
|-- .env.example
|-- Dockerfile
|-- docker-compose.yml
|-- render.yaml
|-- requirements.txt
`-- README.md
```

## MongoDB Collections

### `media`

Core fields:

- `title`
- `type`
- `genres`
- `release_year`
- `creators`
- `cast`
- `description`
- `ratings`
- `sources`
- `tags`
- `related`

Flexible extension fields:

- `thumbnail_url`
- `attributes`
- `added_at`
- `popularity_score`
- `analytics`

Indexes created automatically:

- Text index on `title`, `genres`, and `tags`
- Compound index on `type` and `release_year`
- Sort indexes for `added_at` and `popularity_score`

### `users`

- `username`
- `watchlist`
- `history`
- `preferences`

### `reviews`

- `user_id`
- `media_id`
- `rating`
- `comment`

## API Endpoints

### Required endpoints

- `POST /media` -> add new media
- `GET /media` -> fetch media with filtering, sorting, and pagination
- `GET /search?q=` -> search title, genre, and tags
- `GET /media/{id}` -> detailed media view with related items and reviews
- `POST /review` -> add a review
- `GET /recommendations?user_id=` -> personalized recommendations

### Supporting endpoints

- `GET /catalog/facets` -> available genres, years, types, and decades
- `GET /dashboard/summary` -> archive totals, type mix, platform coverage, featured media, recent reviews
- `GET /collections` -> curated media shelves for key archive themes
- `GET /time-capsule?decade=` -> browse media by decade
- `GET /media/{id}/graph` -> graph nodes and edges centered on a media entity
- `GET /users` -> list demo users
- `GET /users/{id}` -> fetch a user plus watchlist/history items
- `POST /users` -> create a new user
- `POST /users/{id}/watchlist` -> add a media item to watchlist
- `POST /users/{id}/history` -> add a media item to history
- `GET /health` -> confirm database connectivity

## Setup

### 1. Create a virtual environment

```powershell
cd C:\Users\mahar\OneDrive\Documents\universal-media-archive
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Start MongoDB

Option A: local MongoDB installation

- Make sure MongoDB is running on `mongodb://localhost:27017`

Option B: Docker

```powershell
docker compose up -d
```

### 4. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Adjust values if your MongoDB URI or database name is different.

### 5. Run the application

```powershell
uvicorn app.main:app --reload
```

Then open:

- App UI: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- FastAPI docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

If port `8000` is already occupied on your machine, use another port:

```powershell
uvicorn app.main:app --reload --port 8010
```

## Deployment

### Docker Compose

Run the full app plus MongoDB:

```powershell
docker compose up --build
```

Then open:

- App UI: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Docker only

For environments where MongoDB is provided externally, set `MONGODB_URI` and build the app image:

```powershell
docker build -t universal-media-archive .
docker run --rm -p 8000:8000 -e MONGODB_URI="<your-mongodb-uri>" universal-media-archive
```

### Render

A starter [render.yaml](./render.yaml) is included. Use a managed MongoDB connection such as MongoDB Atlas, then set:

- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `APP_ENVIRONMENT=production`
- `SEED_ON_STARTUP=false` for long-lived production data

## Seed Data

The application seeds sample media, users, and reviews automatically on startup if the database is empty.

You can also seed manually:

```powershell
python scripts/seed_db.py
```

To wipe existing demo data and recreate it:

```powershell
python scripts/seed_db.py --reset
```

The current demo archive includes:

- 39 media entities across movies, shows, books, comics, songs, videos, and games
- 7 demo user profiles with different preference patterns
- 21 seeded reviews to drive recommendation and analytics surfaces

## Example Usage

### List recent archive entries

```text
GET /media?sort=recent&limit=6
```

### Search for science fiction media

```text
GET /search?q=science%20fiction
```

### Filter by tag and platform

```text
GET /media?tag=adaptation&platform=Netflix
```

### Get recommendations for a user

```text
GET /recommendations?user_id=<user-id>&limit=5
```

### Get dashboard analytics

```text
GET /dashboard/summary
```

### Get curated collections

```text
GET /collections?limit=4
```

## Design Notes

- The platform is preservation-first and discovery-oriented.
- Media is stored in a unified collection so the archive can scale without rigid relational constraints.
- Type-specific metadata lives in `attributes`, keeping the schema flexible for future formats.
- Related entities create a lightweight knowledge graph for adaptations, companions, inspirations, and peers.
- External links point users to legitimate sources instead of hosting files locally.

## Next Extensions

- Live ingestion from OMDb, Spotify, or YouTube APIs
- Moderation and admin ingestion flows
- Graph visualization of media relationships with richer front-end rendering
- Authentication and personal profiles beyond seeded demo users
