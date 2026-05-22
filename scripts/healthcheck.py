from __future__ import annotations

import os
import sys
from urllib.error import URLError
from urllib.request import urlopen


def main() -> int:
    port = os.getenv("PORT", "8000")
    url = f"http://127.0.0.1:{port}/health"
    try:
        with urlopen(url, timeout=5) as response:
            return 0 if response.status == 200 else 1
    except URLError:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
