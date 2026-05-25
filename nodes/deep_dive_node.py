import asyncio
import logging
from typing import cast

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from core.decorators import logit
from llm.client import get_llm
from llm.prompts.deep_dive import SYSTEM_PROMPT
from llm.schemas.query import QueriesOutput

from .google_news_node import fetch_for_query
from .state import LensState

logger = logging.getLogger(__name__)


@logit
async def deep_dive_node(state: LensState) -> dict:
    current_dive_count = state.get("deep_dive_count", 0)

    if not state.get("has_conflict"):
        return {"deep_dive_count": current_dive_count}

    conflicting = state.get("conflicting_articles", [])
    queries = state.get("queries", [])

    if not conflicting:
        return {"deep_dive_count": current_dive_count}

    # Build compact conflict summary for the prompt.
    # Use "source" — matches the RSSArticle dataclass field name.
    compact = [
        {
            "title": a.get("title"),
            "source": a.get("source"),
        }
        for a in conflicting[:10]
    ]

    try:
        llm = get_llm().with_structured_output(QueriesOutput)
    except Exception as e:
        logger.exception(f"Error initializing LLM for deep dive node, {e}")
        return {
            "top_articles": state.get("top_articles", []),
            "deep_dive_count": current_dive_count,
            "error": [str(e)],
        }
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(
                "original_queries: {original_queries}\nconflicts: {conflicts}"
            ),
        ]
    )
    chain = prompt | llm

    try:
        result = await chain.ainvoke(
            {
                "original_queries": queries,
                "conflicts": compact,
            }
        )
    except Exception as e:
        logger.exception(f"Error invoking LLM for deep dive node, {e}")
        return {
            "top_articles": state.get("top_articles", []),
            "deep_dive_count": current_dive_count,
            "error": [str(e)],
        }

    new_queries = result.queries[:3]
    logger.info("Deep dive queries generated: %s", new_queries)

    # Use fetch_for_query — same multi-locale, dual-variant logic as the main
    # google_news_node. No reason to nerf the deep dive with single-locale fetches.
    new_batches = await asyncio.gather(
        *(fetch_for_query(q) for q in new_queries),
        return_exceptions=True,
    )

    new_articles: list[dict] = []
    for batch in new_batches:
        if isinstance(batch, Exception):
            logger.warning("Deep dive fetch failed for one query: %s", batch)
            continue
        # fetch_for_query already returns list[dict] (asdict applied inside)
        new_articles.extend(cast(list[dict], batch))

    existing = state.get("top_articles", [])
    seen = {a.get("link") for a in existing if a.get("link")}
    merged = list(existing)

    added = 0
    for article in new_articles:
        link = article.get("link")
        if not link or link in seen:
            continue
        seen.add(link)
        merged.append(article)
        added += 1

    logger.info(
        "Deep dive round %s complete — added %s new articles, total pool: %s",
        current_dive_count + 1,
        added,
        len(merged),
    )

    return {
        "top_articles": merged,
        "deep_dive_count": current_dive_count + 1,
    }
