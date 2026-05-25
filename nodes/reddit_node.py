import asyncio
import logging
from dataclasses import asdict

from core.decorators import logit
from db.queries.subreddits import get_subreddits
from tools.embedder import get_embeddings
from tools.rss_fetcher import fetch_all_feeds

from .state import LensState

logger = logging.getLogger(__name__)


@logit
async def reddit_node(state: LensState) -> dict:
    queries = state["queries"]
    REDDIT_URLS = {"https://www.reddit.com/r/skeptic/.rss"}

    for query in queries:
        embeddings = await asyncio.to_thread(get_embeddings, [query])

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
            "reddit_meta": {
                "article_count": len(articles),
                "subreddit_count": len(subs),
            },
        }

    except Exception as e:
        logger.exception("Reddit node failed")

        return {
            "reddit_articles": [],
            "error": [str(e)],
        }
