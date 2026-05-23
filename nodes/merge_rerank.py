from datetime import datetime, timezone
import numpy as np
import math

from tools.embedder import get_embeddings
from .state import LensState


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

    age_hours = (
        datetime.now(timezone.utc) - dt
    ).total_seconds() / 3600

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

    texts = [
        f"{a.get('title','')}\n{a.get('description','')}"
        for a in deduped
    ]

    doc_vecs = get_embeddings(texts)

    cos_scores = cosine_sim(query_vec, doc_vecs)

    scored = []

    for a, c in zip(deduped, cos_scores):
        dt = parse_date(a.get("publication_date"))

        r = recency_score(dt)

        score = 0.7 * float(c) + 0.3 * r

        scored.append((score, a))

    scored.sort(reverse=True, key=lambda x: x[0])

    top = [
        {**a, "score": s}
        for s, a in scored[:10]
    ]

    return {"top_articles": top}

if __name__ == "__main__":
    import asyncio
    import json
    from .google_news_node import google_news_node

    init_state = get_initial_state()
    init_state["queries"] = ["What is the best way to learn Python?"]
    init_state["google_articles"] = google_news_node(init_state)["google_articles"]
