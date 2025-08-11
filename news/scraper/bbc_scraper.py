import datetime
import json
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class BBCNewsArticles():
    """Class to scrape BBC News articles."""
    def __init__(self):
        """Initialize the scraper with the BBC News URL and headers."""
        self.BBC_NEWS_URL = "https://www.bbc.com/innovation/technology"
        self.HEADERS = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://www.google.com/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    # ------------------------
    # Helpers
    # ------------------------
    def _get(self, url: str, *, timeout: int = 12, retries: int = 2, backoff_sec: float = 0.75):
        """HTTP GET with small retry/backoff. Returns Response or None."""
        for attempt in range(retries + 1):
            try:
                resp = self.session.get(url, timeout=timeout)
                resp.raise_for_status()
                return resp
            except Exception as e:
                if attempt < retries:
                    print(f"[WARN] GET failed (attempt {attempt+1}/{retries+1}) for {url}: {e}")
                    try:
                        import time
                        time.sleep(backoff_sec * (attempt + 1))
                    except Exception:
                        pass
                else:
                    print(f"[ERROR] GET failed for {url}: {e}")
        return None

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def _text(self, node) -> str:
        return node.get_text(strip=True) if node else ""

    def _join(self, href: str) -> str:
        return urljoin("https://www.bbc.com", href) if href else ""

    def _parse_iso_date_to_date(self, s: str):
        if not s:
            return None
        try:
            # Handle trailing Z
            if s.endswith("Z"):
                s = s.replace("Z", "+00:00")
            dt = datetime.datetime.fromisoformat(s)
            if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
                # Already date
                return dt
            return dt.date()
        except Exception:
            return None


    def scrape_bbc_article(self, NEWS_ARTICLE_URL):
        """Scrape a BBC News article page; robust to layout changes."""
        resp = self._get(NEWS_ARTICLE_URL)
        if not resp:
            return {}

        soup = self._soup(resp.text)

        title = None
        publication_date = None
        summary_glob = ""

        # Primary: Next.js data blob
        data = None
        try:
            script = soup.find("script", id="__NEXT_DATA__")
            if script and script.string:
                data = json.loads(script.string)
        except Exception as e:
            print(f"[WARN] Failed to parse __NEXT_DATA__: {e}")

        if data:
            try:
                page = data.get("props", {}).get("pageProps", {}).get("page", {})
                page_data = next(iter(page.values()), {}) if isinstance(page, dict) else {}
            except Exception:
                page_data = {}

            # Extract from contents if present
            for block in page_data.get("contents", []) if isinstance(page_data, dict) else []:
                btype = block.get("type")
                if btype == "headline" and not title:
                    try:
                        title = (
                            block["model"]["blocks"][0]["model"]["blocks"][0]["model"]["text"]
                        )
                    except Exception:
                        pass
                if btype == "timestamp" and not publication_date:
                    try:
                        ts = block["model"]["timestamp"]
                        publication_date = datetime.datetime.fromtimestamp(ts / 1000, datetime.timezone.utc)
                    except Exception:
                        pass
                if btype == "text" and len(summary_glob) < 200:
                    try:
                        for s in block["model"].get("blocks", []):
                            if s.get("type") == "paragraph":
                                summary = s.get("model", {}).get("text", "")
                                if summary:
                                    if summary_glob:
                                        summary_glob += " "
                                    summary_glob += summary
                                    if len(summary_glob) > 220:
                                        summary_glob = summary_glob.strip()[:197] + "..."
                                        break
                    except Exception:
                        pass

        # Fallbacks: JSON-LD, meta tags
        if not title or not publication_date or not summary_glob:
            # JSON-LD
            try:
                for ld in soup.find_all("script", type="application/ld+json"):
                    ld_text = ld.string
                    if not ld_text:
                        continue
                    data_ld = json.loads(ld_text)
                    if isinstance(data_ld, dict):
                        maybe_headline = data_ld.get("headline") or data_ld.get("name")
                        maybe_desc = data_ld.get("description")
                        maybe_date = data_ld.get("datePublished") or data_ld.get("dateCreated")
                        title = title or maybe_headline
                        if maybe_desc and not summary_glob:
                            summary_glob = maybe_desc
                        if not publication_date:
                            publication_date = self._parse_iso_date_to_date(maybe_date)
                    elif isinstance(data_ld, list):
                        for item in data_ld:
                            if not isinstance(item, dict):
                                continue
                            title = title or item.get("headline") or item.get("name")
                            if not summary_glob and item.get("description"):
                                summary_glob = item["description"]
                            if not publication_date:
                                publication_date = self._parse_iso_date_to_date(
                                    item.get("datePublished") or item.get("dateCreated")
                                )
                            if title and summary_glob and publication_date:
                                break
                    if title and summary_glob and publication_date:
                        break
            except Exception as e:
                print(f"[WARN] JSON-LD parse failed: {e}")

            # Meta fallbacks
            if not title:
                og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
                if og_title and og_title.get("content"):
                    title = og_title["content"].strip()
            if not summary_glob:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    summary_glob = meta_desc["content"].strip()
            if not publication_date:
                meta_dt = soup.find("meta", property="article:published_time")
                if meta_dt and meta_dt.get("content"):
                    publication_date = self._parse_iso_date_to_date(meta_dt["content"].strip())

        to_return = {
            "title": (title or "Untitled").strip(),
            "publication_date": publication_date or datetime.datetime.now(datetime.timezone.utc).date(),
            "summary": (summary_glob or "").strip(),
            "source_url": NEWS_ARTICLE_URL or "",
        }
        return to_return

    
    def scrape_headlines(self):
        """Scrape the latest BBC News articles."""
        resp = self._get(self.BBC_NEWS_URL)
        if not resp:
            return []

        soup = self._soup(resp.text)
        articles = []
        
        # Preferred structure: "Latest headlines" section
        latest_section = soup.find("section", attrs={"data-analytics_group_name": "Latest headlines"})
        cards = []
        if latest_section:
            cards = latest_section.find_all("div", attrs={"data-testid": "dundee-card"})
        
        # Fallback 1: any dundee-card on page
        if not cards:
            cards = soup.find_all("div", attrs={"data-testid": "dundee-card"})

        # Fallback 2: generic anchor blocks to /news/ with headings
        if not cards:
            for a in soup.select('a[href^="/news/"]'):
                parent = a if a.name == "div" else a.parent
                if not parent:
                    continue
                cards.append(parent)

        for c in cards:
            try:
                h = c.find(["h2", "h3"]) or c.find("span", attrs={"aria-hidden": "true"})
                title = self._text(h)
                if not title:
                    continue
                a = c.find("a")
                href = a.get("href") if a else ""
                link = self._join(href)
                # Summary can be in p or span
                p = c.find("p") or c.find("span", class_=lambda x: x and "summary" in x)
                summary = self._text(p)
                img = c.find("img")
                image_url = img.get("src") if img and img.get("src") else (img.get("data-src") if img else None)

                if not link:
                    continue
                articles.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "image_url": image_url,
                })
            except Exception as e:
                print(f"[WARN] Failed to parse a headline card: {e}")
            
        return articles
    
    def run_scraper(self):
        """Run the scraper and return the latest articles."""
        articles = self.scrape_headlines()
        if not articles:
            print("[ERROR] No articles found.")
            return []

        news_articles = []
        for article in articles:
            print(f"[INFO] Scraping article: {article['title']}")
            if not article.get("link"):
                continue

            scraped = self.scrape_bbc_article(article["link"]) or {}
            if not scraped:
                print(f"[WARN] Skipping article due to scrape failure: {article['link']}")
                continue
            news_articles.append({
                "title": scraped.get("title") or article.get("title") or "Untitled",
                "publication_date": scraped.get("publication_date") or datetime.datetime.now(datetime.timezone.utc).date(),
                "summary": scraped.get("summary") or article.get("summary") or "",
                "source_url": article["link"],
            })

        return news_articles

    def __del__(self):
        """Close the session when the scraper is deleted."""
        self.session.close()


if __name__ == "__main__":
    scraper = BBCNewsArticles()
    articles = scraper.run_scraper()
    for article in articles:
        print(f"Title: {article['title']}")
        print(f"Publication Date: {article['publication_date']}")
        print(f"Summary: {article['summary']}")
        print(f"Source URL: {article['source_url']}\n")
        print("-" * 80)