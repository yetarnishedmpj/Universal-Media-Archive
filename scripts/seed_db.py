from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.mongo import close_mongo_connection, connect_to_mongo, seed_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed MongoDB with demo archive data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing media, users, and reviews before reseeding.",
    )
    args = parser.parse_args()

    database = connect_to_mongo()
    if database is None:
        raise SystemExit("MongoDB is unavailable. Start MongoDB and retry.")

    seed_database(database, force=args.reset)
    close_mongo_connection()
    print("Seed data applied successfully.")


if __name__ == "__main__":
    main()
