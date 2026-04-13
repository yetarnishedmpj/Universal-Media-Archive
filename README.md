# Universal Media Archive

A metadata-rich media discovery and aggregation platform inspired by the Internet Archive. Centralize, search, and explore all forms of human media — movies, books, music, games, comics, podcasts, and more — through a unified system that links to external sources without hosting copyrighted content.

---

## Architecture

```
universal-media-archive/
├── backend/
│   ├── app.py              # Flask REST API
│   └── requirements.txt    # Python dependencies
├── frontend/
│   └── index.html          # Single-file web UI
├── scripts/
│   └── seed.py             # MongoDB seed data
└── README.md
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.9+ | https://python.org |
| MongoDB | 6.0+ | https://www.mongodb.com/try/download/community |
| pip | latest | bundled with Python |

---

## Quick Start

### 1. Start MongoDB

**Windows:**
```bash
# If installed as a service, it may already be running.
# Otherwise:
"C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe" --dbpath="C:\data\db"
```

**macOS:**
```bash
brew services start mongodb-community
```

**Linux:**
```bash
sudo systemctl start mongod
```

Verify it's running:
```bash
mongosh --eval "db.adminCommand('ping')"
```

---

### 2. Set Up the Backend

```bash
cd backend
pip install -r requirements.txt
```

Optional — create a `.env` file to override defaults:
```env
MONGO_URI=mongodb://localhost:27017/
DB_NAME=universal_media_archive
```

Start the server:
```bash
python app.py
```

The API will be available at: **http://localhost:5000**

Verify:
```bash
curl http://localhost:5000/health
# {"db": "universal_media_archive", "status": "ok"}
```

---

### 3. Seed the Database

```bash
cd scripts
python seed.py
```

This inserts 15 sample media items across all types (movies, shows, books, songs, games, comics, podcasts, videos), 3 users, and 6 reviews.

---

### 4. Launch the Frontend

Open `frontend/index.html` directly in your browser:

**Windows:**
```bash
start frontend\index.html
```

**macOS:**
```bash
open frontend/index.html
```

**Linux:**
```bash
xdg-open frontend/index.html
```

Or serve it with Python's built-in server (recommended to avoid CORS issues):
```bash
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

---

## API Reference

### Media

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/media` | List all media (paginated) |
| `POST` | `/media` | Add new media item |
| `GET` | `/media/<id>` | Get media detail (increments view count) |
| `PUT` | `/media/<id>` | Update media item |
| `DELETE` | `/media/<id>` | Delete media item |

**GET /media params:**
- `page` (default: 1)
- `limit` (default: 20)
- `type` — filter by type (movie, book, song, game, show, video, comic, podcast)
- `genre` — filter by genre string
- `year` — exact release year
- `sort` — `added_at` | `title` | `year` | `views`

**POST /media body:**
```json
{
  "title": "Inception",
  "type": "movie",
  "genres": ["Sci-Fi", "Thriller"],
  "release_year": 2010,
  "creators": ["Christopher Nolan"],
  "cast": ["Leonardo DiCaprio"],
  "description": "A thief who steals corporate secrets...",
  "thumbnail": "https://example.com/poster.jpg",
  "ratings": {"imdb": 8.8},
  "sources": [
    {"platform": "Netflix", "url": "https://netflix.com/...", "availability": "subscription"}
  ],
  "tags": ["mind-bending", "heist"]
}
```

---

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/search?q=inception` | Full-text search |

**Search params:**
- `q` — search query (title, genres, tags, description)
- `type` — filter by media type
- `genre` — filter by genre
- `year_from` / `year_to` — year range
- `decade` — e.g., `1990` for 1990–1999
- `page`, `limit`

---

### Reviews

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/review` | Add a review |
| `GET` | `/reviews/<media_id>` | Get all reviews for a media item |

**POST /review body:**
```json
{
  "user_id": "<mongo_id>",
  "media_id": "<mongo_id>",
  "rating": 9.5,
  "comment": "Absolutely brilliant."
}
```

---

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/users` | Create a user |
| `GET` | `/users/<id>` | Get user profile |
| `POST` | `/users/<id>/watchlist` | Add to watchlist |
| `POST` | `/users/<id>/history` | Add to history |

---

### Recommendations & Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/recommendations` | Get recommendations |
| `GET` | `/analytics/trending` | Most viewed media |
| `GET` | `/analytics/searches` | Top search queries |
| `GET` | `/analytics/genres` | Genre breakdown |
| `GET` | `/analytics/types` | Type breakdown |
| `GET` | `/timecapsule/<decade>` | Media from a specific decade |
| `GET` | `/genres` | All genres in database |

**GET /recommendations params:**
- `user_id` — personalized recommendations based on preferences/history
- `genre` — genre-based recommendations (multi)
- `type` — filter by media type
- `limit` — default 10

---

## MongoDB Schema

### `media` collection

```javascript
{
  _id: ObjectId,
  title: String,           // required
  type: String,            // required: movie|book|song|game|show|video|comic|podcast
  genres: [String],
  release_year: Number,
  creators: [String],      // directors, authors, artists
  cast: [String],
  description: String,
  thumbnail: String,       // URL only — no hosted content
  ratings: {
    imdb: Number,          // 0–10
    user: Number,          // computed from reviews
    review_count: Number
  },
  sources: [{
    platform: String,      // Netflix, Spotify, YouTube, etc.
    url: String,
    availability: String   // free | subscription | purchase | trailer
  }],
  tags: [String],
  related: [{
    media_id: String,
    relation: String       // adaptation, sequel, inspiration, etc.
  }],
  added_at: Date,
  view_count: Number
}
```

### `users` collection

```javascript
{
  _id: ObjectId,
  username: String,        // unique
  email: String,
  watchlist: [String],     // array of media_ids
  history: [String],       // array of media_ids
  preferences: [String],   // genres/tags
  created_at: Date
}
```

### `reviews` collection

```javascript
{
  _id: ObjectId,
  user_id: String,
  media_id: String,
  rating: Number,          // 0–10
  comment: String,
  created_at: Date
}
```

### Indexes

- `media`: text index on `title + genres + tags + description`
- `media`: single-field on `type`, `release_year`, `genres`
- `reviews`: compound on `(media_id, user_id)`

---

## Features

### Core
- Universal search across all media types (full-text MongoDB)
- Filtering by type, genre, year, decade
- Pagination on all list endpoints
- Media detail view with external source links
- User reviews and ratings (0–10 scale)
- Watchlist and history tracking per user
- Recommendation engine based on user preferences

### Frontend
- **Standard Mode** — grid layout with thumbnails
- **Archive Mode** — compact, information-dense horizontal layout (toggle top-right)
- **Time Capsule Mode** — browse media by decade
- Global search with live results
- Category tabs for each media type
- Media detail modal with source links and reviews
- Keyboard shortcuts: `/` to focus search, `Esc` to close modal

### Analytics
- View count tracking per media item
- Search query analytics
- Trending media (most viewed)
- Genre and type breakdowns

---

## Design Philosophy

- **Preservation-first** — inspired by archive.org's mission to preserve human culture
- **Media neutrality** — all formats treated as equal "media entities"
- **No piracy** — platform links to official/legal external sources only
- **Information density** — archive mode prioritises metadata over visuals
- **Modularity** — REST API can support any frontend (mobile, desktop, CLI)

---

## Extending the System

### Add API integration (OMDb)
```python
import requests

def enrich_from_omdb(title, year=None):
    params = {'apikey': 'YOUR_OMDB_KEY', 't': title}
    if year:
        params['y'] = year
    res = requests.get('http://www.omdbapi.com/', params=params)
    return res.json()
```

### Add a new media type
1. Add the type string to `valid_types` in `app.py`
2. Add type-specific fields to the POST /media body
3. Add the emoji to `TYPE_EMOJI` in `index.html`

### Deploy to production
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Use nginx as a reverse proxy and serve the frontend as static files.

---

## License

This project is for educational and personal archiving purposes. It does not host, distribute, or facilitate access to copyrighted content. All media links point to official external platforms.
