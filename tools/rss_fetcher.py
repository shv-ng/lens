import httpx
import feedparser
import logging
from typing import List
import html2text
from dataclasses import dataclass, asdict
from tools.cache import get_cached, set_cache
from typing import cast

import asyncio

logger = logging.getLogger(__name__)

parser = html2text.HTML2Text()
parser.ignore_links = True


@dataclass
class RSSArticle:
    title: str
    link: str
    description: str
    publication_date: str
    source_name: str


headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}


async def fetch_rss_feed(url: str, source_name: str) -> List[RSSArticle]:
    cached_articles = await get_cached(url)

    if cached_articles:
        logger.info(f"RSS feed cache hit: {url}")
        return [RSSArticle(**article) for article in cached_articles]

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
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
                source_name=source_name,
            )
            for entry in feed.entries
        ]

        await set_cache(url, [asdict(article) for article in articles])

        return articles


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


if __name__ == "__main__":
    import asyncio

    data = asyncio.run(
        fetch_rss_feed(
            "https://reddit.com/r/programming/.rss",
            source_name="reddit",
        )
    )
    if data:
        data = data[0]
        print("title:", data.title)
        print()
        print("link:", data.link)
        print()
        print("description:", data.description)
        print()
        print("publication_date:", data.publication_date)
        print()
        print("source_name:", data.source_name)
