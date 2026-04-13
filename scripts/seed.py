"""
seed.py — Populates the universal_media_archive MongoDB database with sample data.
Run:  python seed.py
"""

from pymongo import MongoClient, TEXT
from datetime import datetime
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "universal_media_archive")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

media_col = db["media"]
users_col = db["users"]
reviews_col = db["reviews"]

# Clear existing data
media_col.drop()
users_col.drop()
reviews_col.drop()

# Re-create indexes
try:
    media_col.drop_index("title_text_genres_text_tags_text_description_text")
except Exception:
    pass
media_col.create_index([("title", TEXT), ("genres", TEXT), ("tags", TEXT), ("description", TEXT)])
media_col.create_index("type")
media_col.create_index("release_year")

print("Collections cleared and indexes created.")

MEDIA = [
    # ─── MOVIES ───
    {
        "title": "Inception",
        "type": "movie",
        "genres": ["Sci-Fi", "Thriller", "Action"],
        "release_year": 2010,
        "creators": ["Christopher Nolan"],
        "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
        "description": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
        "thumbnail": "https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@._V1_SX300.jpg",
        "ratings": {"imdb": 8.8, "user": None},
        "sources": [
            {"platform": "Netflix", "url": "https://www.netflix.com/title/70131314", "availability": "subscription"},
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=YoHD9XEInc0", "availability": "trailer"}
        ],
        "tags": ["mind-bending", "heist", "dreams", "blockbuster"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 842,
    },
    {
        "title": "2001: A Space Odyssey",
        "type": "movie",
        "genres": ["Sci-Fi", "Mystery", "Drama"],
        "release_year": 1968,
        "creators": ["Stanley Kubrick"],
        "cast": ["Keir Dullea", "Gary Lockwood"],
        "description": "After discovering a mysterious artifact buried beneath the Lunar surface, mankind sets off on a quest to find its origins with help from intelligent supercomputer H.A.L. 9000.",
        "thumbnail": "https://m.media-amazon.com/images/M/MV5BMmNlYzRiNDctZWNhMi00MzI4LThkZTctMTUzMmZkMmFmNThmXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX300.jpg",
        "ratings": {"imdb": 8.3, "user": None},
        "sources": [
            {"platform": "HBO Max", "url": "https://www.hbomax.com", "availability": "subscription"},
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=oR_e9y-bka0", "availability": "trailer"}
        ],
        "tags": ["classic", "space", "AI", "philosophical", "Kubrick"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 621,
    },
    {
        "title": "Parasite",
        "type": "movie",
        "genres": ["Thriller", "Drama", "Dark Comedy"],
        "release_year": 2019,
        "creators": ["Bong Joon-ho"],
        "cast": ["Song Kang-ho", "Lee Sun-kyun", "Cho Yeo-jeong"],
        "description": "Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.",
        "thumbnail": "https://m.media-amazon.com/images/M/MV5BYWZjMjk3ZTItODQ2ZC00NTY5LWE0ZDYtZTI3MjcwN2Q5NTVkXkEyXkFqcGdeQXVyODk4OTc3MTY@._V1_SX300.jpg",
        "ratings": {"imdb": 8.5, "user": None},
        "sources": [
            {"platform": "Hulu", "url": "https://www.hulu.com", "availability": "subscription"},
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=5xH0HfJHsaY", "availability": "trailer"}
        ],
        "tags": ["Korean", "class-struggle", "Oscar-winner", "social-commentary"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 733,
    },

    # ─── SHOWS ───
    {
        "title": "Breaking Bad",
        "type": "show",
        "genres": ["Crime", "Drama", "Thriller"],
        "release_year": 2008,
        "creators": ["Vince Gilligan"],
        "cast": ["Bryan Cranston", "Aaron Paul", "Anna Gunn"],
        "description": "A chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine with a former student to secure his family's future.",
        "thumbnail": "https://m.media-amazon.com/images/M/MV5BYmQ4YWMxYjUtNjZmYi00MDdmLWJjOTUtYjc2OGUzOTVhZWY4XkEyXkFqcGdeQXVyMTMzNDExODE5._V1_SX300.jpg",
        "ratings": {"imdb": 9.5, "user": None},
        "sources": [
            {"platform": "Netflix", "url": "https://www.netflix.com/title/70143836", "availability": "subscription"},
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=HhesaQXLuRY", "availability": "trailer"}
        ],
        "tags": ["chemistry", "crime", "transformation", "New-Mexico", "cult-classic"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 1120,
    },
    {
        "title": "Chernobyl",
        "type": "show",
        "genres": ["Drama", "History", "Thriller"],
        "release_year": 2019,
        "creators": ["Craig Mazin"],
        "cast": ["Jared Harris", "Stellan Skarsgård", "Emily Watson"],
        "description": "In April 1986, an explosion at the Chernobyl nuclear power plant in the USSR becomes one of the world's worst man-made catastrophes.",
        "thumbnail": "https://m.media-amazon.com/images/M/MV5BNGUyYmZlZDctNWQ1Yy00YWNkLWFhN2QtMmZlOWFlODMwMzQyXkEyXkFqcGdeQXVyMTkxNjUyNQ@@._V1_SX300.jpg",
        "ratings": {"imdb": 9.4, "user": None},
        "sources": [
            {"platform": "HBO Max", "url": "https://www.hbomax.com", "availability": "subscription"},
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=s9APLXM9Ei8", "availability": "trailer"}
        ],
        "tags": ["nuclear", "USSR", "historical", "miniseries", "tragedy"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 688,
    },

    # ─── BOOKS ───
    {
        "title": "Dune",
        "type": "book",
        "genres": ["Sci-Fi", "Epic", "Political"],
        "release_year": 1965,
        "creators": ["Frank Herbert"],
        "cast": [],
        "description": "Set in the distant future, Dune tells the story of young Paul Atreides, whose family accepts stewardship of the desert planet Arrakis—the only source of the galaxy's most precious substance, the spice mélange.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/d/de/Dune-Frank_Herbert_%281965%29_First_edition.jpg",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "Project Gutenberg", "url": "https://www.gutenberg.org", "availability": "free"},
            {"platform": "Open Library", "url": "https://openlibrary.org/works/OL102749W/Dune", "availability": "free"},
            {"platform": "Goodreads", "url": "https://www.goodreads.com/book/show/44767458-dune", "availability": "info"}
        ],
        "tags": ["space-opera", "ecology", "politics", "religion", "classic-SF"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 540,
    },
    {
        "title": "1984",
        "type": "book",
        "genres": ["Dystopia", "Political Fiction", "Sci-Fi"],
        "release_year": 1949,
        "creators": ["George Orwell"],
        "cast": [],
        "description": "A dystopian social science fiction novel and cautionary tale set in a totalitarian society ruled by Big Brother.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/commons/c/c3/1984first.jpg",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "Project Gutenberg", "url": "https://gutenberg.net.au/ebooks01/0100021.txt", "availability": "free"},
            {"platform": "Open Library", "url": "https://openlibrary.org/works/OL1168007W", "availability": "free"}
        ],
        "tags": ["surveillance", "totalitarianism", "classic", "dystopia", "political"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 480,
    },
    {
        "title": "Neuromancer",
        "type": "book",
        "genres": ["Cyberpunk", "Sci-Fi", "Thriller"],
        "release_year": 1984,
        "creators": ["William Gibson"],
        "cast": [],
        "description": "A washed-up hacker is hired for one last job, a heist targeting a powerful AI. The novel that defined cyberpunk.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/4/4b/Neuromancer_%28Book%29.jpg",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "Open Library", "url": "https://openlibrary.org/works/OL27258W/Neuromancer", "availability": "free"},
            {"platform": "Goodreads", "url": "https://www.goodreads.com/book/show/22328.Neuromancer", "availability": "info"}
        ],
        "tags": ["cyberpunk", "AI", "hacker", "matrix", "genre-defining"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 312,
    },

    # ─── SONGS ───
    {
        "title": "Bohemian Rhapsody",
        "type": "song",
        "genres": ["Rock", "Progressive Rock", "Opera Rock"],
        "release_year": 1975,
        "creators": ["Freddie Mercury", "Queen"],
        "cast": [],
        "description": "A six-minute suite with no chorus, consisting of several sections: a ballad, a guitar solo, an opera section, and a rock section. One of the greatest songs ever recorded.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/9/9f/Bohemian_Rhapsody.png",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "Spotify", "url": "https://open.spotify.com/track/7tFiyTwD0nx5a1eklYtX2J", "availability": "free/premium"},
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=fJ9rUzIMcZQ", "availability": "free"},
            {"platform": "Apple Music", "url": "https://music.apple.com/us/album/bohemian-rhapsody/1440650428?i=1440650501", "availability": "subscription"}
        ],
        "tags": ["classic-rock", "Queen", "opera", "anthem", "legendary"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 990,
    },
    {
        "title": "Kind of Blue",
        "type": "song",
        "genres": ["Jazz", "Modal Jazz"],
        "release_year": 1959,
        "creators": ["Miles Davis"],
        "cast": [],
        "description": "The best-selling jazz album of all time, recorded in two sessions in 1959. A landmark of modal jazz featuring tracks like So What and All Blues.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/3/3a/Kind_of_blue.jpg",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "Spotify", "url": "https://open.spotify.com/album/1weenld61qoidwYuZ1GESA", "availability": "free/premium"},
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=ylXk1LBvIqU", "availability": "free"}
        ],
        "tags": ["jazz", "Miles-Davis", "classic", "instrumental", "modal"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 320,
    },

    # ─── GAMES ───
    {
        "title": "The Legend of Zelda: Breath of the Wild",
        "type": "game",
        "genres": ["Action-Adventure", "Open World", "RPG"],
        "release_year": 2017,
        "creators": ["Nintendo", "Shigeru Miyamoto"],
        "cast": [],
        "description": "An open-world action-adventure game set in a post-apocalyptic Hyrule where Link must defeat Calamity Ganon.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/c/c6/Breath_of_the_Wild_cover_artwork.jpg",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "Nintendo eShop", "url": "https://www.nintendo.com/games/detail/the-legend-of-zelda-breath-of-the-wild-switch/", "availability": "purchase"},
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=1rPxiXXxftE", "availability": "trailer"}
        ],
        "tags": ["Nintendo", "Switch", "open-world", "Zelda", "GOTY"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 760,
    },
    {
        "title": "Disco Elysium",
        "type": "game",
        "genres": ["RPG", "Detective", "Political"],
        "release_year": 2019,
        "creators": ["ZA/UM"],
        "cast": [],
        "description": "A groundbreaking open-world role-playing game where you play a detective with a unique skill system and no combat.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/3/35/Disco_Elysium_cover_art.jpg",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "Steam", "url": "https://store.steampowered.com/app/632470/Disco_Elysium__The_Final_Cut/", "availability": "purchase"},
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=zyuMhBzFHKQ", "availability": "trailer"}
        ],
        "tags": ["indie", "detective", "philosophical", "PC", "narrative"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 430,
    },

    # ─── COMICS ───
    {
        "title": "Watchmen",
        "type": "comic",
        "genres": ["Superhero", "Dystopia", "Mystery"],
        "release_year": 1986,
        "creators": ["Alan Moore", "Dave Gibbons"],
        "cast": [],
        "description": "A landmark 12-issue comic book series set in an alternate history America where superheroes are real. Often cited as the greatest graphic novel ever written.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/a/a2/Watchmen%2C_issue_1.jpg",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "DC Universe", "url": "https://www.dcuniverseinfinite.com", "availability": "subscription"},
            {"platform": "Comixology", "url": "https://www.amazon.com/Kindle-Comics/b?node=2245645011", "availability": "purchase"}
        ],
        "tags": ["Alan-Moore", "graphic-novel", "DC", "alternate-history", "mature"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 380,
    },

    # ─── PODCASTS ───
    {
        "title": "Serial",
        "type": "podcast",
        "genres": ["True Crime", "Journalism", "Investigation"],
        "release_year": 2014,
        "creators": ["Sarah Koenig", "Julie Snyder"],
        "cast": [],
        "description": "Serial unfolds one story — a true story — over the course of a whole season. The first season investigates the 1999 murder of Hae Min Lee.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/en/e/ea/Serial_Podcast_Logo.png",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "Spotify", "url": "https://open.spotify.com/show/3y1tNjrcR2BIfWbBr6hGm7", "availability": "free"},
            {"platform": "Apple Podcasts", "url": "https://podcasts.apple.com/us/podcast/serial/id917918570", "availability": "free"},
            {"platform": "Serial Website", "url": "https://serialpodcast.org", "availability": "free"}
        ],
        "tags": ["true-crime", "journalism", "mystery", "podcast-pioneer"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 265,
    },

    # ─── VIDEOS ───
    {
        "title": "The Scale of the Universe",
        "type": "video",
        "genres": ["Science", "Educational", "Space"],
        "release_year": 2012,
        "creators": ["Cary Huang", "Michael Huang"],
        "cast": [],
        "description": "An interactive animation that lets users explore the scale of objects in our universe, from quantum foam to the observable universe.",
        "thumbnail": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Earth_Eastern_Hemisphere.jpg/480px-Earth_Eastern_Hemisphere.jpg",
        "ratings": {"imdb": None, "user": None},
        "sources": [
            {"platform": "YouTube", "url": "https://www.youtube.com/watch?v=uaGEjrADGPA", "availability": "free"},
            {"platform": "HTwins.net", "url": "https://htwins.net/scale2/", "availability": "free"}
        ],
        "tags": ["science", "scale", "universe", "educational", "interactive"],
        "related": [],
        "added_at": datetime.utcnow(),
        "view_count": 190,
    },
]

result = media_col.insert_many(MEDIA)
media_ids = [str(mid) for mid in result.inserted_ids]
print(f"Inserted {len(media_ids)} media items.")

# ─── USERS ───
USERS = [
    {
        "username": "archiver_jane",
        "email": "jane@example.com",
        "watchlist": [media_ids[0], media_ids[3]],
        "history": [media_ids[1], media_ids[5]],
        "preferences": ["Sci-Fi", "Thriller", "Drama"],
        "created_at": datetime.utcnow(),
    },
    {
        "username": "cinephile_mark",
        "email": "mark@example.com",
        "watchlist": [media_ids[2], media_ids[4]],
        "history": [media_ids[0], media_ids[2]],
        "preferences": ["Drama", "History", "Dark Comedy"],
        "created_at": datetime.utcnow(),
    },
    {
        "username": "bookworm_alice",
        "email": "alice@example.com",
        "watchlist": [media_ids[5], media_ids[6]],
        "history": [media_ids[7]],
        "preferences": ["Sci-Fi", "Dystopia", "Cyberpunk"],
        "created_at": datetime.utcnow(),
    },
]

user_result = users_col.insert_many(USERS)
user_ids = [str(uid) for uid in user_result.inserted_ids]
print(f"Inserted {len(user_ids)} users.")

# ─── REVIEWS ───
REVIEWS = [
    {"user_id": user_ids[0], "media_id": media_ids[0], "rating": 9.5, "comment": "Mind-blowing concept executed perfectly. Nolan at his best.", "created_at": datetime.utcnow()},
    {"user_id": user_ids[1], "media_id": media_ids[0], "rating": 8.5, "comment": "Visually stunning but slightly overrated. Still great.", "created_at": datetime.utcnow()},
    {"user_id": user_ids[0], "media_id": media_ids[3], "rating": 10.0, "comment": "The greatest TV show ever made. Period.", "created_at": datetime.utcnow()},
    {"user_id": user_ids[2], "media_id": media_ids[5], "rating": 9.0, "comment": "Herbert built an entire universe. The ecology and politics are unmatched.", "created_at": datetime.utcnow()},
    {"user_id": user_ids[1], "media_id": media_ids[2], "rating": 9.8, "comment": "Bong Joon-ho is a genius. This film is perfect.", "created_at": datetime.utcnow()},
    {"user_id": user_ids[0], "media_id": media_ids[8], "rating": 10.0, "comment": "Freddie Mercury was from another planet. This song proves it.", "created_at": datetime.utcnow()},
]

reviews_col.insert_many(REVIEWS)
print(f"Inserted {len(REVIEWS)} reviews.")

# Update user ratings on media
for media_id in [media_ids[0], media_ids[2], media_ids[3], media_ids[5], media_ids[8]]:
    all_reviews = list(reviews_col.find({"media_id": media_id}))
    if all_reviews:
        avg = sum(r["rating"] for r in all_reviews) / len(all_reviews)
        media_col.update_one(
            {"_id": result.inserted_ids[media_ids.index(media_id)]},
            {"$set": {"ratings.user": round(avg, 1), "ratings.review_count": len(all_reviews)}}
        )

print("\n✅ Seed complete!")
print(f"   Media:   {len(media_ids)} items")
print(f"   Users:   {len(user_ids)} users")
print(f"   Reviews: {len(REVIEWS)} reviews")
print(f"\nSample media IDs:")
for i, (media, mid) in enumerate(zip(MEDIA, media_ids)):
    print(f"   [{media['type']:8}] {media['title'][:40]:40} → {mid}")
