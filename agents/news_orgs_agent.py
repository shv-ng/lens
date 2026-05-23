from dataclasses import asdict
import logging
from urllib.parse import quote_plus
from typing import cast

from .state import LensState, get_initial_state
from tools.cache import get_cached, set_cache
from tools.rss_fetcher import fetch_rss_feed, RSSArticle
import asyncio

logger = logging.getLogger(__name__)

THE_HINDU_URLS = [
    "https://www.thehindu.com/feeder/default.rss",
    "https://www.thehindu.com/news/feeder/default.rss",
    "https://www.thehindu.com/news/national/feeder/default.rss",
    "https://www.thehindu.com/news/international/feeder/default.rss",
    "https://www.thehindu.com/opinion/feeder/default.rss",
    "https://www.thehindu.com/business/feeder/default.rss",
    "https://www.thehindu.com/sport/feeder/default.rss",
]

INDIAN_EXPRESS_URLS = [
    "https://indianexpress.com/section/india/feed/",
    "https://indianexpress.com/section/world/feed/",
    "https://indianexpress.com/section/politics/feed/",
    "https://indianexpress.com/section/business/feed/",
    "https://indianexpress.com/section/explained/feed/",
    "https://indianexpress.com/section/technology/feed/",
    "https://indianexpress.com/section/health-wellness/feed/",
]

ANI_NEWS_URLS = [
    "https://aninews.in/rss/feed/category/national.xml",
    "https://aninews.in/rss/feed/category/world.xml",
    "https://aninews.in/videos-rss-feed/videos/business/",
    "https://aninews.in/rss/feed/category/health.xml",
    "https://aninews.in/rss/feed/category/tech.xml",
]

BBC_NEWS_URLS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
    "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
]


async def fetch_all_feeds(urls, source):
    results = await asyncio.gather(
        *(fetch_rss_feed(url, source) for url in urls),
        return_exceptions=True,
    )

    articles = []

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"RSS fetch err: {result}")
            continue

        articles.extend(cast(list[RSSArticle], result))

    return articles


async def get_all_feeds():
    results = await asyncio.gather(
        fetch_all_feeds(THE_HINDU_URLS, source="the_hindu"),
        fetch_all_feeds(INDIAN_EXPRESS_URLS, source="indian_express"),
        fetch_all_feeds(ANI_NEWS_URLS, source="ani_news"),
        fetch_all_feeds(BBC_NEWS_URLS, source="bbc_news"),
        return_exceptions=True,
    )
    return results


async def news_orgs_agent(_state: LensState) -> dict:
    all_articles = []
    seen_links = set()

    try:
        cache_key = "news_orgs_feeds"

        cached_articles = await get_cached(cache_key)

        if cached_articles:
            logger.info("News orgs cache hit")

            return {
                "news_org_articles": cached_articles,
            }

        logger.info("Fetching news org feeds")

        results: list[
            list[RSSArticle] | BaseException
        ] = await get_all_feeds()

        for result in results:
            if isinstance(result, BaseException):
                logger.error(
                    "News org fetch failed: %s",
                    result,
                )
                continue

            for article in result:
                link = str(article.link)

                if link in seen_links:
                    continue

                seen_links.add(link)

                all_articles.append(asdict(article))

        logger.info(
            "Collected %s news org articles",
            len(all_articles),
        )

        await set_cache(
            cache_key,
            all_articles,
        )

        return {
            "news_org_articles": all_articles,
        }

    except Exception as e:
        logger.exception("News org agent failed")

        return {
            "news_org_articles": [],
            "error": [str(e)],
        }


if __name__ == "__main__":
    import asyncio
    import json

    init_state = get_initial_state()

    data = asyncio.run(news_orgs_agent(init_state))
    print(json.dumps(data, indent=4))
