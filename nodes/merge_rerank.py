import asyncio
import logging
import math
from datetime import datetime, timezone

import numpy as np

from core.decorators import logit
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


@logit
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

    query_vec_res = await asyncio.to_thread(get_embeddings, [" ".join(queries)])
    query_vec = query_vec_res[0]

    texts = [f"{a.get('title', '')}\n{a.get('description', '')}" for a in deduped]

    doc_vecs = await asyncio.to_thread(get_embeddings, texts)

    cos_scores = cosine_sim(query_vec, doc_vecs)

    scored = []

    for a, c in zip(deduped, cos_scores):
        dt = parse_date(a.get("publication_date"))

        r = recency_score(dt)

        score = 0.5 * float(c) + 0.5 * r

        scored.append((score, a))

    scored.sort(reverse=True, key=lambda x: x[0])

    top = [{**a, "score": s} for s, a in scored[:20]]

    return {
        "top_articles": top,
        "merge_meta": {
            "merged_count": len(deduped),
            "top_count": len(top),
        },
    }
