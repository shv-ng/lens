import logging
from typing import cast

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from core.decorators import cached, logit
from llm.client import get_llm
from llm.prompts.conflict import SYSTEM_PROMPT
from llm.schemas.conflict import ConflictOutput

from .state import LensState

logger = logging.getLogger(__name__)


@logit
async def conflict_detector_node(state: LensState) -> dict:
    try:
        llm = get_llm().with_structured_output(ConflictOutput)
    except Exception as e:
        logger.exception(f"Error initializing LLM for conflict detector node, {e}")
        return {
            "has_conflict": False,
            "conflicting_articles": [],
            "deep_dive_count": 0,
            "error": [str(e)],
        }

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(
                """ Raw input: {raw_input}\n\n Articles: {articles}"""
            ),
        ]
    )
    chain = prompt | llm

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

    try:
        result = cast(
            ConflictOutput,
            await chain.ainvoke(
                {
                    "raw_input": state["raw_input"],
                    "articles": compact,
                }
            ),
        )
    except Exception as e:
        logger.exception(f"Error invoking LLM for conflict detector node, {e}")
        return {
            "has_conflict": False,
            "conflicting_articles": [],
            "deep_dive_count": 0,
            "error": [str(e)],
        }

    conflicting = [
        articles[i] for i in result.conflicting_indices if 0 <= i < len(articles)
    ]

    return {
        "has_conflict": result.has_conflict,
        "conflicting_articles": conflicting,
        "deep_dive_count": state.get("deep_dive_count", 0),
        "conflict_meta": {
            "conflict": result.has_conflict,
            "conflicting_count": len(conflicting),
        },
    }
