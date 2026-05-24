import asyncio
import logging
from dataclasses import dataclass
from typing import List, cast

import feedparser
import html2text
import httpx

from core.decorators import logit
from core.decorators.cache import build_cache_key, get_cached, set_cache
from core.decorators.retry import retry

logger = logging.getLogger(__name__)

parser = html2text.HTML2Text()
parser.ignore_links = True


@dataclass
class RSSArticle:
    title: str
    link: str
    description: str
    publication_date: str
    source: str


headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}


@logit
@retry()
async def fetch_rss_feed(url: str, source: str) -> List[RSSArticle]:
    cached_result = await get_cached(
        build_cache_key("fetch_rss_feed", (url, source), {})
    )
    if cached_result:
        return [
            RSSArticle(**item) if isinstance(item, dict) else item
            for item in cached_result
        ]
    async with httpx.AsyncClient(
        headers=headers, follow_redirects=True, timeout=10
    ) as client:
        r = await client.get(url)

        if r.status_code != 200:
            logger.error(f"Error fetching {url}  feed: {r.status_code}")
            return []

        feed = feedparser.parse(r.text)

        articles = [
            RSSArticle(
                title=getattr(entry, "title", ""),
                link=getattr(entry, "link", ""),
                description=parser.handle(getattr(entry, "description", "")),
                publication_date=getattr(
                    entry,
                    "published",
                    getattr(entry, "updated", ""),
                ),
                source=source,
            )
            for entry in feed.entries
        ]

        await set_cache(
            build_cache_key("fetch_rss_feed", (url, source), {}),
            articles,
            ttl=3600,
        )
        return articles


@logit
async def fetch_all_feeds(urls, source):
    results = await asyncio.gather(
        *(fetch_rss_feed(url, source) for url in urls),
        return_exceptions=True,
    )

    articles = []

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"RSS fetch err: {result}, source: {source}")
            continue

        articles.extend(cast(list[RSSArticle], result))

    return articles
