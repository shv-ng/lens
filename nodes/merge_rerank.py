import logging
import math
from datetime import datetime, timezone

import numpy as np

from tools.embedder import get_embeddings

from .state import LensState

logger = logging.getLogger(__name__)


def parse_date(x):
    try:
        # RSS often RFC822; adjust if needed
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(x)
    except Exception:
        return None


def recency_score(dt):
    if not dt:
        return 0.0

    age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600

    return math.exp(-age_hours / 48)


def cosine_sim(q, D):
    q = np.array(q)
    D = np.array(D)

    q = q / np.linalg.norm(q)
    D = D / np.linalg.norm(D, axis=1, keepdims=True)

    return D @ q


async def merge_rerank_node(state: LensState) -> dict:
    queries = state["queries"]

    articles = (
        state.get("google_articles", [])
        + state.get("news_org_articles", [])
        + state.get("reddit_articles", [])
    )

    # dedupe
    seen = set()
    deduped = []

    for a in articles:
        link = a.get("link")
        if not link or link in seen:
            continue
        seen.add(link)
        deduped.append(a)

    if not deduped:
        return {"top_articles": []}

    query_vec = get_embeddings([" ".join(queries)])[0]

    texts = [f"{a.get('title', '')}\n{a.get('description', '')}" for a in deduped]

    doc_vecs = get_embeddings(texts)

    cos_scores = cosine_sim(query_vec, doc_vecs)

    scored = []

    for a, c in zip(deduped, cos_scores):
        dt = parse_date(a.get("publication_date"))

        r = recency_score(dt)

        score = 0.7 * float(c) + 0.3 * r

        scored.append((score, a))

    scored.sort(reverse=True, key=lambda x: x[0])

    top = [{**a, "score": s} for s, a in scored[:10]]

    return {
        "top_articles": top,
        "merge_meta": {
            "merged_count": len(deduped),
            "top_count": len(top),
        },
    }


if __name__ == "__main__":
    import asyncio
    import json

    from .google_news_node import google_news_node
    from .news_orgs_node import news_orgs_node
    from .query_node import query_extractor_node
    from .reddit_node import reddit_node
    from .state import get_initial_state

    init_state = get_initial_state()
    logger.info(f"Initial state: {init_state}")
    init_state["raw_input"] = "Is the Indian government corrupt?"
    logger.info(f"Raw input: {init_state['raw_input']}")

    init_state["queries"] = asyncio.run(query_extractor_node(init_state))["queries"]
    logger.info(f"Queries: {init_state['queries']}")

    init_state["google_articles"] = asyncio.run(google_news_node(init_state))[
        "google_articles"
    ]
    logger.info(f"Google articles: {init_state['google_articles']}")

    init_state["news_org_articles"] = asyncio.run(news_orgs_node(init_state))[
        "news_org_articles"
    ]
    logger.info(f"News org articles: {init_state['news_org_articles']}")

    init_state["reddit_articles"] = asyncio.run(reddit_node(init_state))[
        "reddit_articles"
    ]
    logger.info(f"Reddit articles: {init_state['reddit_articles']}")

    data = asyncio.run(merge_rerank_node(init_state))
    print(json.dumps(data, indent=4))
