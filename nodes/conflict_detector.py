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
from llm.schemas.conflict import ConflictOutput
from llm.prompts.conflict import SYSTEM_PROMPT
from llm.client import get_llm

logger = logging.getLogger(__name__)


llm = get_llm(ConflictOutput)

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(""" {raw_input} """),
    ]
)

chain = prompt | llm


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
