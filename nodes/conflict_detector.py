from typing import cast
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from pydantic import BaseModel
from langchain_groq import ChatGroq
from .state import LensState
import logging

logger = logging.getLogger(__name__)


class ConflictOutput(BaseModel):
    has_conflict: bool
    conflicting_indices: list[int]
    reasoning: str


SYSTEM_PROMPT = """
You are a news synthesis and bias detection engine.

You receive a list of news articles, each with:
- index
- title
- source name

Your task:
Detect whether multiple sources describe the same underlying event differently.

Types of differences:
1. Factual conflict
   - contradictory claims about what happened, who did it, or outcomes
2. Framing divergence
   - same facts, but different emphasis, tone, or narrative angle
   - common between Indian vs Western outlets or ideological slants
3. No meaningful difference
   - same story cluster, same framing

Rules:
- Focus only on semantic differences implied by titles and source names.
- Do NOT assume external knowledge beyond what is implied.
- Prefer conservative conflict detection (avoid false positives).
- If uncertain, mark has_conflict = false.

Output requirements:
- has_conflict: true if any meaningful contradiction OR strong framing divergence exists
- conflicting_indices: list of indices that contribute to the divergence
- reasoning: short technical explanation (1–3 sentences max)
    """

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
)

structured_llm = llm.with_structured_output(ConflictOutput)

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(""" {raw_input} """),
    ]
)

chain = prompt | structured_llm


async def conflict_detector_node(state: LensState) -> dict:
    articles = state.get("top_articles", [])[:10]

    if not articles:
        return {
            "has_conflict": False,
            "conflicting_articles": [],
            "deep_dive_count": 0,
        }

    compact = [
        {"i": i, "title": a.get("title"), "source": a.get("source")}
        for i, a in enumerate(articles)
    ]

    result = cast(
        ConflictOutput,
        await chain.ainvoke(
            {
                "articles": compact,
            }
        ),
    )

    conflicting = [
        articles[i] for i in result.conflicting_indices if 0 <= i < len(articles)
    ]

    return {
        "has_conflict": result.has_conflict,
        "conflicting_articles": conflicting,
        "deep_dive_count": 0,
    }
