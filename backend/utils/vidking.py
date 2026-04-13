from playwright.sync_api import sync_playwright


def get_vidking_source(title):
    try:
        print("🔍 Searching:", title)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 🔍 SEARCH PAGE
            search_url = f"https://www.vidking.net/search?q={title.replace(' ', '+')}"
            page.goto(search_url, timeout=60000)

            # ✅ WAIT for actual results
            page.wait_for_selector("a[href*='/watch/']", timeout=10000)

            link = page.query_selector("a[href*='/watch/']")

            if not link:
                print("❌ No watch link found")
                browser.close()
                return []

            href = link.get_attribute("href")
            print("🎯 Found:", href)

            # 🎬 OPEN WATCH PAGE
            page.goto(f"https://www.vidking.net{href}", timeout=60000)

            # ✅ WAIT for iframe properly
            page.wait_for_selector("iframe", timeout=10000)

            iframe = page.query_selector("iframe")

            if not iframe:
                print("❌ No iframe found")
                browser.close()
                return []

            src = iframe.get_attribute("src")
            print("🎬 Stream:", src)

            browser.close()

            if src:
                return [{
                    "platform": "vidking",
                    "url": src
                }]

            return []

    except Exception as e:
        print("VidKing error:", e)
        return []