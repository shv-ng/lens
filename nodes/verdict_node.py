import logging
from typing import cast

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from core.decorators import cached, logit
from llm.client import get_llm
from llm.prompts.verdict import SYSTEM_PROMPT
from llm.schemas.verdict import VerdictOutput

from .state import LensState

logger = logging.getLogger(__name__)


@logit
async def verdict_node(state: LensState) -> dict:
    try:
        structured_llm = get_llm().with_structured_output(VerdictOutput)
    except Exception as e:
        logger.exception(f"Error initializing LLM for verdict node, {e}")
        return {
            "verdict_label": "",
            "verdict_explanation": "",
            "framing_notes": "",
            "error": [str(e)],
        }

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template("""
    queries: {queries}
    top_articles: {top_articles}
    has_conflict: {has_conflict}
    conflicting_articles: {conflicting_articles}
    """),
        ]
    )

    chain = prompt | structured_llm

    try:
        result = cast(
            VerdictOutput,
            await chain.ainvoke(
                {
                    "queries": state.get("queries", []),
                    "top_articles": state.get("top_articles", [])[:10],
                    "has_conflict": state.get("has_conflict", False),
                    "conflicting_articles": state.get("conflicting_articles", []),
                }
            ),
        )
    except Exception as e:
        logger.exception("Error invoking LLM for verdict node")
        return {
            "verdict_label": "",
            "verdict_explanation": "",
            "framing_notes": "",
            "error": [str(e)],
        }

    return {
        "verdict_label": result.verdict_label,
        "verdict_explanation": result.verdict_explanation,
        "framing_notes": result.framing_notes,
    }

