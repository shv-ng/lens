import logging
from dataclasses import asdict
from urllib.parse import quote_plus

from tools.rss_fetcher import fetch_rss_feed

from .state import LensState

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query} after:2026-01-01&hl=en-IN&gl=IN&ceid=IN:en"


async def google_news_node(state: LensState) -> dict:
    queries = state["queries"]

    all_articles = []
    seen_links = set()

    try:
        for query in queries:
            encoded_query = quote_plus(query)

            rss_url = GOOGLE_NEWS_RSS.format(query=encoded_query)

            articles = await fetch_rss_feed(rss_url, "google_news")

            for article in articles:
                link = str(article.link)

                if link in seen_links:
                    continue

                seen_links.add(link)

                all_articles.append(asdict(article))

        logger.info(
            "Collected %s Google News articles",
            len(all_articles),
        )

        return {
            "google_articles": all_articles,
            "google_meta": {
                "article_count": len(all_articles),
            },
        }

    except Exception as e:
        logger.exception("Google News node failed")

        return {
            "google_articles": [],
            "error": [str(e)],
        }


if __name__ == "__main__":
    import asyncio
    import json

    from .state import get_initial_state

    init_state = get_initial_state()
    init_state["queries"] = ["What is the best way to learn Python?"]

    data = asyncio.run(google_news_node(init_state))
    print(json.dumps(data, indent=4))
