import os
import sys
import random
import threading
import time
import logging
import base64
from datetime import datetime, timezone
from typing import Any

import requests
from pymongo import MongoClient

# Add root to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ─── CONFIG (From env or settings) ───
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

SYNC_INTERVAL = 3600  # 1 hour

client = MongoClient(settings.mongodb_uri)
db = client[settings.mongodb_db_name]
media_col = db["media"]

http = requests.Session()

# ─── HELPERS ───
def normalize_date(date_str: str | None) -> str:
    if not date_str:
        return "1900-01-01"
    return str(date_str)[:10]

def exists(title: str, media_type: str) -> bool:
    return media_col.find_one({"title": title, "type": media_type}) is not None

def get_provider_search_url(provider: str, title: str) -> str | None:
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

# ─── FETCH FUNCTIONS ───

def fetch_movies():
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY missing. Skipping movies.")
        return
    
    logger.info("[Movies] Syncing...")
    random_start = random.randint(1, 100)
    TMDB_GENRES = {28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime', 99: 'Documentary', 18: 'Drama', 10751: 'Family', 14: 'Fantasy', 36: 'History', 27: 'Horror', 10402: 'Music', 9648: 'Mystery', 10749: 'Romance', 878: 'Sci-Fi', 10770: 'TV Movie', 53: 'Thriller', 10752: 'War', 37: 'Western'}
    
    try:
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&page={random_start}"
        data = http.get(url).json()

        for m in data.get("results", []):
            title = m.get("title")
            if not title or exists(title, "movie"):
                continue

            movie_id = m.get("id")
            sources = []
            if movie_id:
                try:
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
                except Exception:
                    pass

            release_date = normalize_date(m.get("release_date"))
            doc = {
                "title": title,
                "type": "movie",
                "genres": [TMDB_GENRES.get(gid, "Other") for gid in m.get("genre_ids", [])][:3],        
                "release_year": int(release_date[:4]) if release_date != "1900-01-01" else 1900,
                "popularity_score": int(m.get("popularity", 0)),
                "thumbnail": f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}" if m.get("poster_path") else None,
                "description": m.get("overview", ""),
                "ratings": {"imdb": m.get("vote_average"), "user": None},
                "added_at": datetime.now(timezone.utc),
                "sources": sources,
                "analytics": {"views": 0, "watchlisted": 0, "search_hits": 0}
            }
            media_col.insert_one(doc)
    except Exception as e:
        logger.error("Error fetching movies: %s", e)

def fetch_games():
    if not RAWG_API_KEY:
        logger.warning("RAWG_API_KEY missing. Skipping games.")
        return
    
    logger.info("[Games] Syncing...")
    try:
        page = random.randint(1, 20)
        url = f"https://api.rawg.io/api/games?key={RAWG_API_KEY}&page={page}"
        data = http.get(url).json()

        for g in data.get("results", []):
            title = g.get("name")
            if not title or exists(title, "game"):
                continue

            slug = g.get("slug")
            sources = []
            if slug:
                stores_url = f"https://api.rawg.io/api/games/{slug}/stores?key={RAWG_API_KEY}"
                stores_res = http.get(stores_url).json() if http.get(stores_url).status_code == 200 else {}
                store_mapping = {s["store"]["id"]: s["store"]["name"] for s in g.get("stores", [])}     

                for s in stores_res.get("results", []):
                    store_url = s.get("url")
                    if store_url:
                        store_name = store_mapping.get(s.get("store_id"), "Store")
                        sources.append({"platform": store_name, "url": store_url, "availability": "buy"})

            release_date = normalize_date(g.get("released"))
            doc = {
                "title": title,
                "type": "game",
                "genres": [gen.get("name") for gen in g.get("genres", [])][:3],
                "release_year": int(release_date[:4]) if release_date != "1900-01-01" else 1900,
                "popularity_score": int(g.get("ratings_count", 0)),
                "thumbnail": g.get("background_image"),
                "description": "", # RAWG overview is separate call
                "ratings": {"imdb": g.get("rating") * 2 if g.get("rating") else None, "user": None},
                "added_at": datetime.now(timezone.utc),
                "sources": sources,
                "analytics": {"views": 0, "watchlisted": 0, "search_hits": 0}
            }
            media_col.insert_one(doc)
    except Exception as e:
        logger.error("Error fetching games: %s", e)

def sync_all():
    logger.info("Starting global data sync...")
    fetch_movies()
    fetch_games()
    # Others omitted for brevity in this task, but can be added similarly
    logger.info("Global data sync complete.")

def run_sync_loop():
    while True:
        sync_all()
        time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        sync_all()
    else:
        run_sync_loop()
