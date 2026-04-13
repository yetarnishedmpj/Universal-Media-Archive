import requests
import base64
import random
from pymongo import MongoClient
from datetime import datetime, UTC
import time
import os
import json
import threading
import hashlib
import gc

# ─── CONFIG ───
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "universal_media_archive")

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

SYNC_INTERVAL = 1800

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
media_col = db["media"]

http = requests.Session()

# ─── HELPERS ───
def normalize_date(date_str):
    if not date_str:
        return "1900-01-01"
    return str(date_str)[:10]

def exists(title, t):
    return media_col.find_one({"title": title, "type": t}) is not None

def count_type(t):
    return media_col.count_documents({"type": t})

# ─── FETCH FUNCTIONS ───

def get_provider_search_url(provider, title):
    from urllib.parse import quote
    p = provider.lower()
    t = quote(title)
    if "netflix" in p: return f"https://www.netflix.com/search?q={t}"
    if "hulu" in p: return f"https://www.hulu.com/search?q={t}"
    if "amazon" in p: return f"https://www.amazon.com/s?k={t}&i=instant-video"
    if "apple" in p: return f"https://tv.apple.com/us/search?q={t}"
    if "disney" in p: return f"https://www.disneyplus.com/search?q={t}"
    if "max" in p or "hbo" in p: return f"https://play.max.com/search?q={t}"
    if "google" in p: return f"https://play.google.com/store/search?q={t}&c=movies"
    if "youtube" in p: return f"https://www.youtube.com/results?search_query={t}+movie"
    if "paramount" in p: return f"https://www.paramountplus.com/shows/"
    return None

def fetch_movies():
    print("[Movies] Fetching...")
    random_start = random.randint(1, 100)
    pages = range(random_start, random_start + 10)
    TMDB_GENRES = {28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime', 99: 'Documentary', 18: 'Drama', 10751: 'Family', 14: 'Fantasy', 36: 'History', 27: 'Horror', 10402: 'Music', 9648: 'Mystery', 10749: 'Romance', 878: 'Sci-Fi', 10770: 'TV Movie', 53: 'Thriller', 10752: 'War', 37: 'Western'}
    for page in pages:
        try:
            url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&page={page}"
            data = http.get(url).json()

            for m in data.get("results", []):
                try:
                    title = m.get("title")
                    if not title or exists(title, "movie"):
                        continue
                    
                    movie_id = m.get("id")
                    sources = []
                    if movie_id:
                        prov_url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}"
                        prov_res = http.get(prov_url).json()
                        us_prov = prov_res.get("results", {}).get("US", {})
                        prov_link = us_prov.get("link")
                        
                        added_provs = set()
                        for category in ["flatrate", "rent", "buy"]:
                            for p in us_prov.get(category, []):
                                prov_name = p.get("provider_name")
                                if prov_name and prov_name not in added_provs:
                                    search_url = get_provider_search_url(prov_name, title)
                                    sources.append({
                                        "platform": prov_name, 
                                        "url": search_url if search_url else (prov_link if prov_link else f"https://www.themoviedb.org/movie/{movie_id}"), 
                                        "availability": category
                                    })
                                    added_provs.add(prov_name)
                    
                    doc = {
                        "title": title,
                        "type": "movie",
                        "tmdb_id": movie_id,
                        "genres": [TMDB_GENRES.get(gid, "Other") for gid in m.get("genre_ids", [])][:3],
                        "release_date": normalize_date(m.get("release_date")),
                        "release_year": int(normalize_date(m.get("release_date"))[:4]),
                        "view_count": int(m.get("popularity", 0) * 100),
                        "thumbnail": f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}",
                        "added_at": datetime.now(UTC),
                        "sources": sources
                    }
                    media_col.update_one({'title': title, 'type': doc['type']}, {'$set': doc}, upsert=True)
                except Exception as e:
                    print(f"Error parsing movie: {e}")

        except Exception as e:
            print(f"Error fetching movies page {page}: {e}")


def fetch_shows():
    print("[Shows] Fetching...")
    random_start = random.randint(1, 100)
    pages = range(random_start, random_start + 10)
    TMDB_GENRES = {10759: 'Action & Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime', 99: 'Documentary', 18: 'Drama', 10751: 'Family', 10762: 'Kids', 9648: 'Mystery', 10763: 'News', 10764: 'Reality', 10765: 'Sci-Fi & Fantasy', 10766: 'Soap', 10767: 'Talk', 10768: 'War & Politics', 37: 'Western'}
    for page in pages:
        try:
            url = f"https://api.themoviedb.org/3/tv/popular?api_key={TMDB_API_KEY}&page={page}"
            data = http.get(url).json()

            for s in data.get("results", []):
                try:
                    title = s.get("name")
                    if not title or exists(title, "show"):
                        continue
                    
                    show_id = s.get("id")
                    sources = []
                    if show_id:
                        prov_url = f"https://api.themoviedb.org/3/tv/{show_id}/watch/providers?api_key={TMDB_API_KEY}"
                        prov_res = http.get(prov_url).json()
                        us_prov = prov_res.get("results", {}).get("US", {})
                        prov_link = us_prov.get("link")
                        
                        added_provs = set()
                        for category in ["flatrate", "rent", "buy"]:
                            for p in us_prov.get(category, []):
                                prov_name = p.get("provider_name")
                                if prov_name and prov_name not in added_provs:
                                    search_url = get_provider_search_url(prov_name, title)
                                    sources.append({
                                        "platform": prov_name, 
                                        "url": search_url if search_url else (prov_link if prov_link else f"https://www.themoviedb.org/tv/{show_id}"), 
                                        "availability": category
                                    })
                                    added_provs.add(prov_name)
                    
                    doc = {
                        "title": title,
                        "type": "show",
                        "tmdb_id": show_id,
                        "genres": [TMDB_GENRES.get(gid, "Other") for gid in s.get("genre_ids", [])][:3],
                        "release_date": normalize_date(s.get("first_air_date")),
                        "release_year": int(normalize_date(s.get("first_air_date"))[:4]),
                        "view_count": int(s.get("popularity", 0) * 100),
                        "thumbnail": f"https://image.tmdb.org/t/p/w500{s.get('poster_path')}",
                        "added_at": datetime.now(UTC),
                        "sources": sources
                    }
                    media_col.update_one({'title': title, 'type': doc['type']}, {'$set': doc}, upsert=True)
                except Exception as e:
                    print(f"Error parsing show: {e}")

        except Exception as e:
            print(f"Error fetching shows page {page}: {e}")


def fetch_games():
    print("[Games] Fetching...")
    random_start = random.randint(1, 100)
    pages = range(random_start, random_start + 5)
    for page in pages:
        try:
            url = f"https://api.rawg.io/api/games?key={RAWG_API_KEY}&page={page}"
            main_res = http.get(url)
            if main_res.status_code != 200:
                print(f"RAWG API limits hit (Code {main_res.status_code}). Backing off...")
                time.sleep(3)
                continue
            data = main_res.json()

            for g in data.get("results", []):
                try:
                    title = g.get("name")
                    if not title or exists(title, "game"):
                        continue
                        
                    slug = g.get("slug")
                    sources = []
                    if slug:
                        time.sleep(0.3)  # Anti-rate limit delay for secondary API fetch
                        stores_url = f"https://api.rawg.io/api/games/{slug}/stores?key={RAWG_API_KEY}"
                        stores_req = http.get(stores_url)
                        stores_res = stores_req.json() if stores_req.status_code == 200 else {}
                        
                        store_mapping = {s["store"]["id"]: s["store"]["name"] for s in g.get("stores", [])}
                        
                        for s in stores_res.get("results", []):
                            store_url = s.get("url")
                            if store_url:
                                store_name = store_mapping.get(s.get("store_id"), "Store")
                                sources.append({"platform": store_name, "url": store_url, "availability": "buy"})
                                
                        if not sources:
                            sources.append({"platform": "RAWG", "url": f"https://rawg.io/games/{slug}", "availability": "info"})

                    doc = {
                        "title": title,
                        "type": "game",
                        "genres": [gen.get("name") for gen in g.get("genres", [])][:3],
                        "release_date": normalize_date(g.get("released")),
                        "release_year": int(normalize_date(g.get("released"))[:4]),
                        "view_count": int(g.get("ratings_count", 0) * 100),
                        "thumbnail": g.get("background_image"),
                        "added_at": datetime.now(UTC),
                        "sources": sources
                    }
                    media_col.update_one({'title': title, 'type': doc['type']}, {'$set': doc}, upsert=True)
                except Exception as e:
                    print(f"Error parsing game: {e}")

        except Exception as e:
            print(f"Error fetching games page {page}: {e}")


def fetch_books():
    print("[Books] Fetching...")
    # Use OpenLibrary Subjects API to avoid Google Books 429 Quota Limits
    queries = ["fiction", "fantasy", "science", "history"]

    for q in queries:
        try:
            offset = random.randint(0, 500)
            url = f"https://openlibrary.org/subjects/{q}.json?limit=40&offset={offset}"
            data = http.get(url).json()

            for b in data.get("works", []):
                try:
                    title = b.get("title")

                    if not title or exists(title, "book"):
                        continue

                    sources = []
                    key = b.get("key")
                    if key:
                        sources.append({"platform": "Open Library", "url": f"https://openlibrary.org{key}", "availability": "free"})

                    cover_id = b.get("cover_id")
                    thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None
                    
                    publish_year = b.get("first_publish_year")
                    release_date = f"{publish_year}-01-01" if publish_year else "1900-01-01"

                    doc = {
                        "title": title,
                        "type": "book",
                        "genres": b.get("subject", [q.title()])[:3] if isinstance(b.get("subject"), list) else [q.title()],
                        "release_date": release_date,
                        "release_year": publish_year if publish_year else 1900,
                        "view_count": int(b.get("edition_count", 0) * 100),
                        "thumbnail": thumbnail,
                        "added_at": datetime.now(UTC),
                        "sources": sources
                    }
                    media_col.update_one({'title': title, 'type': doc['type']}, {'$set': doc}, upsert=True)
                except Exception as e:
                    print(f"Error parsing book: {e}")

        except Exception as e:
            print(f"Error fetching books for query '{q}': {e}")


def fetch_comics():
    print("[Comics] Fetching...")
    # Use OpenLibrary to strictly filter subjects and avoid quotas
    queries = ["comic_books_strips_etc", "manga", "graphic_novels"]

    for q in queries:
        try:
            offset = random.randint(0, 500)
            url = f"https://openlibrary.org/subjects/{q}.json?limit=40&offset={offset}"
            data = http.get(url).json()

            for b in data.get("works", []):
                try:
                    title = b.get("title")

                    if not title or exists(title, "comic"):
                        continue

                    sources = []
                    key = b.get("key")
                    if key:
                        sources.append({"platform": "Open Library", "url": f"https://openlibrary.org{key}", "availability": "free"})

                    cover_id = b.get("cover_id")
                    thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None
                    
                    publish_year = b.get("first_publish_year")
                    release_date = f"{publish_year}-01-01" if publish_year else "1900-01-01"

                    doc = {
                        "title": title,
                        "type": "comic",
                        "genres": b.get("subject", [q.replace('_', ' ').title()])[:3] if isinstance(b.get("subject"), list) else [q.replace('_', ' ').title()],
                        "release_date": release_date,
                        "release_year": publish_year if publish_year else 1900,
                        "view_count": int(b.get("edition_count", 0) * 100),
                        "thumbnail": thumbnail,
                        "added_at": datetime.now(UTC),
                        "sources": sources
                    }
                    media_col.update_one({'title': title, 'type': doc['type']}, {'$set': doc}, upsert=True)
                except Exception as e:
                    print(f"Error parsing comic: {e}")

        except Exception as e:
            print(f"Error fetching comics for query '{q}': {e}")


def fetch_songs():
    print("[Songs] Fetching...")
    try:
        auth = base64.b64encode(
            f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
        ).decode()

        token_req = http.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {auth}"},
            data={"grant_type": "client_credentials"}
        )
        token = token_req.json().get("access_token")

        if not token:
            print("Failed to get Spotify token")
            return

        headers = {"Authorization": f"Bearer {token}"}

        for q in ["pop", "rock", "hip hop", "jazz", "classical"]:
            try:
                offset = random.randint(0, 900)
                res = http.get(
                    "https://api.spotify.com/v1/search",
                    headers=headers,
                    params={"q": q, "type": "track", "limit": 10, "offset": offset}
                )

                for t in res.json().get("tracks", {}).get("items", []):
                    try:
                        title = t.get("name")
                        if not title or exists(title, "song"):
                            continue

                        images = t.get("album", {}).get("images", [])
                        thumbnail = images[0]["url"] if images else None

                        sources = []
                        spotify_url = t.get("external_urls", {}).get("spotify")
                        if spotify_url:
                            sources.append({"platform": "Spotify", "url": spotify_url, "availability": "free"})

                        doc = {
                            "title": title,
                            "type": "song",
                            "genres": [q.title()],
                            "release_date": normalize_date(t.get("album", {}).get("release_date")),
                            "release_year": int(normalize_date(t.get("album", {}).get("release_date"))[:4]),
                            "view_count": int(t.get("popularity", 0) * 100),
                            "thumbnail": thumbnail,
                            "added_at": datetime.now(UTC),
                            "sources": sources
                        }
                        media_col.update_one({'title': title, 'type': doc['type']}, {'$set': doc}, upsert=True)
                    except Exception as e:
                        print(f"Error parsing song: {e}")
            except Exception as e:
                print(f"Error fetching songs for query '{q}': {e}")

    except Exception as e:
        print(f"Failed to fetch songs (Spotify API error): {e}")


def fetch_videos():
    print("[Videos] Fetching...")
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=documentary&type=video&maxResults=25&key={YOUTUBE_API_KEY}"
        data = http.get(url).json()

        for v in data.get("items", []):
            try:
                snippet = v.get("snippet", {})
                title = snippet.get("title")

                if not title or exists(title, "video"):
                    continue

                video_id = v.get("id", {}).get("videoId")
                sources = []
                if video_id:
                    sources.append({"platform": "YouTube", "url": f"https://www.youtube.com/watch?v={video_id}", "availability": "free"})

                thumbnails = snippet.get("thumbnails", {})
                high_res = thumbnails.get("high", {}).get("url")

                doc = {
                    "title": title,
                    "type": "video",
                    "genres": ["Documentary"],
                    "release_date": normalize_date(snippet.get("publishedAt")),
                    "release_year": int(normalize_date(snippet.get("publishedAt"))[:4]),
                    "view_count": random.randint(100, 5000),
                    "thumbnail": high_res,
                    "added_at": datetime.now(UTC),
                    "sources": sources
                }
                media_col.update_one({'title': title, 'type': doc['type']}, {'$set': doc}, upsert=True)
            except Exception as e:
                print(f"Error parsing video: {e}")

    except Exception as e:
        print(f"Error fetching videos: {e}")


# ─── SYNC ───
def sync_all():
    print("[System] Sync started...")
    fetch_movies()
    fetch_shows()
    fetch_games()
    fetch_books()
    fetch_comics()
    fetch_songs()
    fetch_videos()
    print("[System] Sync complete")


def worker():
    while True:
        sync_all()
        gc.collect()
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    while True:
        time.sleep(1)
