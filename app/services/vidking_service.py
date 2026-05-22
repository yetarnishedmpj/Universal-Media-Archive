from __future__ import annotations

import logging
from typing import Any

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)


def get_vidking_sources(title: str) -> list[dict[str, Any]]:
    if not HAS_PLAYWRIGHT:
        logger.warning("Playwright not installed. Skipping VidKing search.")
        return []

    try:
        logger.info("Searching VidKing for: %s", title)

        with sync_playwright() as p:
            # We use a simple browser launch. In a real production env, 
            # you might want to reuse browsers or use a pool.
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            # Search page
            search_url = f"https://www.vidking.net/search?q={title.replace(' ', '+')}"
            page.goto(search_url, timeout=30000)

            # Wait for results
            try:
                page.wait_for_selector("a[href*='/watch/']", timeout=10000)
            except Exception:
                logger.info("No watch link found for '%s'", title)
                browser.close()
                return []

            link = page.query_selector("a[href*='/watch/']")
            if not link:
                browser.close()
                return []

            href = link.get_attribute("href")
            if not href:
                browser.close()
                return []

            # Open watch page
            page.goto(f"https://www.vidking.net{href}", timeout=30000)

            # Wait for iframe
            try:
                page.wait_for_selector("iframe", timeout=10000)
            except Exception:
                logger.info("No iframe found on watch page for '%s'", title)
                browser.close()
                return []

            iframe = page.query_selector("iframe")
            if not iframe:
                browser.close()
                return []

            src = iframe.get_attribute("src")
            browser.close()

            if src:
                logger.info("Found stream source: %s", src)
                return [{"platform": "vidking", "url": src, "availability": "free"}]

            return []

    except Exception as exc:
        logger.error("VidKing scraping error for '%s': %s", title, exc)
        return []
