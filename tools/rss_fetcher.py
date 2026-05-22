from pydantic import BaseModel
import httpx
import feedparser
import logging
from typing import List
import html2text

logger = logging.getLogger(__name__)

parser = html2text.HTML2Text()
parser.ignore_links = True


class RSSArticle(BaseModel):
    title: str
    link: str
    description: str
    publication_date: str
    source_name: str


async def fetch_rss_feed(url: str) -> List[RSSArticle]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(url)
        if r.status_code != 200:
            logger.error(f"Error fetching Google News feed: {r.status_code}")
            return []
        feed = feedparser.parse(r.text)
        return [
            RSSArticle(
                title=entry.title,
                link=entry.link,
                description=parser.handle(entry.description),
                publication_date=entry.published,
                source_name="Google News",
            )
            for entry in feed.entries
        ]


async def fetch_reddit_feed(url: str) -> List[RSSArticle]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(url)
        if r.status_code != 200:
            logger.error(f"Error fetching Reddit feed: {r.status_code}")
            return []
        feed = feedparser.parse(r.text)
        return [
            RSSArticle(
                title=entry.title,
                link=entry.link,
                description=parser.handle(entry.description),
                publication_date=entry.published,
                source_name="Reddit",
            )
            for entry in feed.entries
        ]


if __name__ == "__main__":
    import asyncio

    data = asyncio.run(
        fetch_rss_feed(
            "https://reddit.com/r/programming/.rss",
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
