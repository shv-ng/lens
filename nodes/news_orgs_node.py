import asyncio
import logging
from dataclasses import asdict

from core.decorators import cached, logit
from tools.rss_fetcher import RSSArticle, fetch_all_feeds

from .state import LensState

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


@logit
async def get_all_feeds():
    results = await asyncio.gather(
        fetch_all_feeds(THE_HINDU_URLS, source="the_hindu"),
        fetch_all_feeds(INDIAN_EXPRESS_URLS, source="indian_express"),
        fetch_all_feeds(ANI_NEWS_URLS, source="ani_news"),
        fetch_all_feeds(BBC_NEWS_URLS, source="bbc_news"),
        return_exceptions=True,
    )
    return results


@logit
async def news_orgs_node(state: LensState):
    all_articles = []
    seen_links = set()

    try:
        results: list[list[RSSArticle] | BaseException] = await get_all_feeds()

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

        return {
            "news_org_articles": all_articles,
            "news_orgs_meta": {
                "article_count": len(all_articles),
            },
        }

    except Exception as e:
        logger.exception("News org node failed")

        return {
            "news_org_articles": [],
            "error": [str(e)],
        }
