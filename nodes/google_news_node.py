import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from urllib.parse import quote

from core.decorators import cached, logit
from tools.rss_fetcher import fetch_rss_feed

from .state import LensState

logger = logging.getLogger(__name__)

LOCALES = [
    {"hl": "en-US", "gl": "US", "ceid": "US:en"},
    {"hl": "en-GB", "gl": "GB", "ceid": "GB:en"},
    {"hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
]

BASE = "https://news.google.com/rss/search"


@logit
def _current_year_start() -> str:
    return f"{datetime.now(timezone.utc).year}-01-01"


@logit
def build_urls(query: str, locale: dict) -> list[str]:
    params = f"hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
    encoded = quote(query, safe="")

    recency_url = f"{BASE}?q={encoded}+when:7d&{params}"
    breadth_url = f"{BASE}?q={encoded}+after:{_current_year_start()}&{params}"

    return [recency_url, breadth_url]


@logit
@cached()
async def fetch_for_query(query: str) -> list[dict]:
    urls = []
    for locale in LOCALES:
        urls.extend(build_urls(query, locale))

    results = await asyncio.gather(
        *(fetch_rss_feed(url, "google_news") for url in urls),
        return_exceptions=True,
    )

    seen = set()
    articles = []

    for result in results:
        if not isinstance(result, list):
            logger.warning("Google News fetch failed for one URL: %s", result)
            continue

        for article in result:
            link = str(article.link)
            if link in seen:
                continue
            seen.add(link)
            articles.append(asdict(article))

    return articles


@logit
async def google_news_node(state: LensState) -> dict:
    queries = state["queries"]

    try:
        query_results = await asyncio.gather(
            *(fetch_for_query(q) for q in queries),
            return_exceptions=True,
        )
    except Exception as e:
        logger.exception("Google News node failed")
        return {
            "google_articles": [],
            "google_meta": {
                "article_count": 0,
            },
            "error": [str(e)],
        }

    all_articles = []
    seen_links = set()

    for result in query_results:
        if not isinstance(result, list):
            logger.error("Google News query batch failed: %s", result)
            continue

        for article in result:
            link = article.get("link", "")
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            all_articles.append(article)

    logger.info("Collected %s Google News articles", len(all_articles))

    return {
        "google_articles": all_articles,
        "google_meta": {
            "article_count": len(all_articles),
        },
    }
