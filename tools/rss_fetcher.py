from attr import s
import httpx
import feedparser
import logging
from typing import List
import html2text
from dataclasses import dataclass

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
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r = await client.get(url)
        if r.status_code != 200:
            logger.error(f"Error fetching {url}  feed: {r.status_code}")
            return []
        feed = feedparser.parse(r.text)
        return [
            RSSArticle(
                title=entry.title,
                link=entry.link,
                description=parser.handle(entry.description),
                publication_date=entry.published,
                source_name=source_name,
            )
            for entry in feed.entries
        ]


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
