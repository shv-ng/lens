import operator
from typing import Annotated, TypedDict

from core.decorators import logit


class LensState(TypedDict, total=False):
    # Input
    raw_input: str
    input_type: str  # text or image

    # Query Node
    queries: list[str]

    # Fetch Nodes (each writes its own)
    google_articles: list[dict]
    reddit_articles: list[dict]
    news_org_articles: list[dict]

    # Merge + Rerank
    top_articles: list[dict]

    # Conflict Detector
    has_conflict: bool
    conflicting_articles: list[dict]
    deep_dive_count: int

    # Verdict
    verdict_label: str  # "Widely Corroborated" | "Contradicted" | etc.
    verdict_explanation: str
    framing_notes: str  # western vs Indian framing diff, if any

    error: Annotated[list[str], operator.add]


@logit
def get_initial_state() -> LensState:
    return {
        "raw_input": "",
        "input_type": "text",
        "queries": [],
        "google_articles": [],
        "reddit_articles": [],
        "news_org_articles": [],
        "top_articles": [],
        "has_conflict": False,
        "conflicting_articles": [],
        "deep_dive_count": 0,
        "verdict_label": "",
        "verdict_explanation": "",
        "framing_notes": "",
        "error": [],
    }
