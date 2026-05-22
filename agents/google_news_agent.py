import logging
from urllib.parse import quote_plus

from .state import LensState,get_initial_state
from tools.cache import get_cached, set_cache
from tools.rss_fetcher import fetch_rss_feed

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
)


async def google_news_agent(state: LensState) -> dict:
    queries = state["queries"]

    all_articles = []
    seen_links = set()

    try:
        for query in queries:
            encoded_query = quote_plus(query)

            rss_url = GOOGLE_NEWS_RSS.format(query=encoded_query)

            cached_articles = await get_cached(rss_url)

            if cached_articles:
                logger.info(
                    "Google News cache hit: %s",
                    query,
                )

                articles = cached_articles

            else:
                logger.info(
                    "Fetching Google News: %s",
                    query,
                )

                articles = await fetch_rss_feed(rss_url)

                await set_cache(
                    rss_url,
                    articles,
                )

            for article in articles:
                link = str(article.link)

                if link in seen_links:
                    continue

                seen_links.add(link)

                all_articles.append(article.model_dump())

        logger.info(
            "Collected %s Google News articles",
            len(all_articles),
        )

        return {
            "google_articles": all_articles,
        }

    except Exception as e:
        logger.exception("Google News agent failed")

        return {
            "google_articles": [],
            "error": [str(e)],
        }

if __name__ == "__main__":
    import asyncio
    import json
    
    init_state = get_initial_state()
    init_state["queries"] = ["What is the best way to learn Python?"]

    data = asyncio.run(google_news_agent(init_state))
    print(json.dumps(data, indent=4))
