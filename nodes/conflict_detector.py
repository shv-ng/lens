import logging
from typing import cast

from langchain_core.prompts import (ChatPromptTemplate,
                                    HumanMessagePromptTemplate,
                                    SystemMessagePromptTemplate)

from llm.client import get_llm
from llm.prompts.conflict import SYSTEM_PROMPT
from llm.schemas.conflict import ConflictOutput

from .state import LensState

logger = logging.getLogger(__name__)


async def conflict_detector_node(state: LensState) -> dict:
    llm = get_llm().with_structured_output(ConflictOutput)
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

    result = cast(
        ConflictOutput,
        await chain.ainvoke(
            {
                "raw_input": state["raw_input"],
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
        "deep_dive_count": state.get("deep_dive_count", 0),
        "conflict_meta": {
            "conflict": result.has_conflict,
            "conflicting_count": len(conflicting),
        },
    }


if __name__ == "__main__":
    import asyncio
    import json

    from .google_news_node import google_news_node
    from .merge_rerank import merge_rerank_node
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

    data = asyncio.run(conflict_detector_node(init_state))
    print(data)
