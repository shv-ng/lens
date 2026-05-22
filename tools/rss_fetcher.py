from pydantic import BaseModel
import httpx
import feedparser
import logging
from typing import List
import enum

logger = logging.getLogger(__name__)


class RSSArticle(BaseModel):
    title: str
    link: str
    description: str
    publication_date: str
    source_name: str


class SourceType(enum.Enum):
    GOOGLE_NEWS = "google_news"
    REDDIT = "reddit"
    HACKER_NEWS = "hacker_news"
    BBC_NEWS = "bbc_news"
    THE_HINDU = "the_hindu"
    ANI = "ani"
    INDIAN_EXPRESS = "indian_express"


async def fetch_rss_feed(url: str, source_type: SourceType) -> List[RSSArticle]:
    match source_type:
        case SourceType.GOOGLE_NEWS:
            return await fetch_google_news_feed(url)
        case SourceType.REDDIT:
            return await fetch_reddit_feed(url)
        case SourceType.HACKER_NEWS:
            return await fetch_hacker_news_feed(url)
        case SourceType.BBC_NEWS:
            return await fetch_bbc_news_feed(url)
        case SourceType.THE_HINDU:
            return await fetch_the_hindu_feed(url)
        case SourceType.ANI:
            return await fetch_ani_feed(url)
        case SourceType.INDIAN_EXPRESS:
            return await fetch_indian_express_feed(url)


async def fetch_google_news_feed(url: str) -> List[RSSArticle]:
async def fetch_reddit_feed(url: str) -> List[RSSArticle]: ...
async def fetch_hacker_news_feed(url: str) -> List[RSSArticle]: ...
async def fetch_bbc_news_feed(url: str) -> List[RSSArticle]: ...
async def fetch_the_hindu_feed(url: str) -> List[RSSArticle]: ...
async def fetch_ani_feed(url: str) -> List[RSSArticle]: ...
async def fetch_indian_express_feed(url: str) -> List[RSSArticle]: ...


if __name__ == "__main__":
    import asyncio, pprint

    data = asyncio.run(
        fetch_rss_feed("https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en")
    )
    pprint.pprint(data[0])
