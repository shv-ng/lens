from pydantic import BaseModel
import httpx
import feedparser
import logging
from typing import List

logger = logging.getLogger(__name__)

class RSSArticle(BaseModel):
    title: str
    link: str
    description: str
    pubDate: str
    source_name: str

async def fetch_rss_feed(url: str) -> list[RSSArticle]:
    """
    Fetch + parse RSS feed.

    Returns:
        List[RSSArticle]
    """
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        parsed = feedparser.parse(resp.text)

        source_name = parsed.feed.get("title", "Unknown Source")

        articles: List[RSSArticle] = []

        for entry in parsed.entries:
            article = RSSArticle(
                title=entry.get("title", "No title"),
                link=entry.get("link", ""),
                description=entry.get("description", ""),
                pubDate=entry.get("published"),
                source=source_name,
            )

            articles.append(article)

        logger.info(
            "Fetched %s articles from %s",
            len(articles),
            source_name,
        )

        return articles

    except Exception as e:
        logger.exception("Failed fetching RSS feed: %s", url)
        raise RuntimeError(f"RSS fetch failed: {e}") from e
