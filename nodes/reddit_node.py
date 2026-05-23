from dataclasses import asdict
from .state import LensState
from tools.embedder import get_embeddings
import logging
from db.queries.subreddits import get_subreddits
from tools.rss_fetcher import fetch_all_feeds

logger = logging.getLogger(__name__)


async def reddit_node(state: LensState) -> dict:
    queries = state["queries"]
    REDDIT_URLS = set()
    REDDIT_URLS.add("https://www.reddit.com/r/skeptic/.rss")

    for query in queries:
        embeddings = get_embeddings([query])

        subs = await get_subreddits(embeddings[0])
        if not subs:
            logger.error(f"No subreddits found for query: {query}")
            continue

        subs = [sub["subreddit"] for sub in subs]
        REDDIT_URLS.update([f"https://www.reddit.com/{sub}/.rss" for sub in subs])

    try:
        logger.info(f"Fetching {len(REDDIT_URLS)} reddit feeds")
        results = await fetch_all_feeds(REDDIT_URLS, source="reddit")

        articles = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Reddit fetch err: {result}")
                continue
            articles.append(result)

        logger.info(
            "Collected %s reddit articles",
            len(articles),
        )

        return {
            "reddit_articles": [asdict(article) for article in articles],
        }

    except Exception as e:
        logger.exception("Reddit node failed")

        return {
            "reddit_articles": [],
            "error": [str(e)],
        }


if __name__ == "__main__":
    import asyncio
    from .state import get_initial_state

    init_state = get_initial_state()
    init_state["queries"] = ["What is the best way to learn Python?"]

    data = asyncio.run(reddit_node(init_state))
    print(len(data["reddit_articles"]))
    print(data["reddit_articles"][0])
