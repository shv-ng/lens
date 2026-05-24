import logging

from langchain_core.prompts import (ChatPromptTemplate,
                                    HumanMessagePromptTemplate,
                                    SystemMessagePromptTemplate)

from llm.client import get_llm
from llm.prompts.verdict import SYSTEM_PROMPT
from llm.schemas.verdict import VerdictOutput

from .state import LensState

logger = logging.getLogger(__name__)


async def verdict_node(state: LensState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(VerdictOutput)

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

    result = await chain.ainvoke(
        {
            "queries": state.get("queries", []),
            "top_articles": state.get("top_articles", [])[:10],
            "has_conflict": state.get("has_conflict", False),
            "conflicting_articles": state.get("conflicting_articles", []),
        }
    )

    return {
        "verdict_label": result.verdict_label,
        "verdict_explanation": result.verdict_explanation,
        "framing_notes": result.framing_notes,
    }


if __name__ == "__main__":
    import asyncio

    from .conflict_detector import conflict_detector_node
    from .deep_dive_node import deep_dive_node
    from .google_news_node import google_news_node
    from .merge_rerank import merge_rerank_node
    from .news_orgs_node import news_orgs_node
    from .query_node import query_extractor_node
    from .reddit_node import reddit_node
    from .state import get_initial_state

    init_state = get_initial_state()
    init_state["raw_input"] = "Is the Indian government corrupt?"
    init_state["queries"] = asyncio.run(query_extractor_node(init_state))["queries"]
    init_state["google_articles"] = asyncio.run(google_news_node(init_state))[
        "google_articles"
    ]
    init_state["news_org_articles"] = asyncio.run(news_orgs_node(init_state))[
        "news_org_articles"
    ]
    init_state["reddit_articles"] = asyncio.run(reddit_node(init_state))[
        "reddit_articles"
    ]
    init_state["top_articles"] = asyncio.run(merge_rerank_node(init_state))[
        "top_articles"
    ]
    init_state["has_conflict"] = asyncio.run(conflict_detector_node(init_state))[
        "has_conflict"
    ]
    init_state["conflicting_articles"] = asyncio.run(
        conflict_detector_node(init_state)
    )["conflicting_articles"]
    init_state["deep_dive_count"] = asyncio.run(deep_dive_node(init_state))[
        "deep_dive_count"
    ]

    data = asyncio.run(verdict_node(init_state))
    init_state["verdict_label"] = data["verdict_label"]
    init_state["verdict_explanation"] = data["verdict_explanation"]
    init_state["framing_notes"] = data["framing_notes"]
    print(init_state)
