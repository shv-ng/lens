import asyncio
import logging
from dataclasses import asdict
from typing import cast
from urllib.parse import quote_plus

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from llm.client import get_llm
from llm.prompts.deep_dive import SYSTEM_PROMPT
from llm.schemas.query import QueriesOutput
from tools.rss_fetcher import RSSArticle, fetch_rss_feed

from .google_news_node import GOOGLE_NEWS_RSS
from .state import LensState

logger = logging.getLogger(__name__)


async def deep_dive_node(state: LensState) -> dict:
    llm = get_llm().with_structured_output(QueriesOutput)
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(
                "original_queries: {original_queries}\nconflicts: {conflicts}"
            ),
        ]
    )

    chain = prompt | llm
    if not state.get("has_conflict"):
        return {
            "deep_dive_count": state.get("deep_dive_count", 0),
        }

    conflicting = state.get("conflicting_articles", [])
    queries = state.get("queries", [])

    if not conflicting:
        return {
            "deep_dive_count": state.get("deep_dive_count", 0),
        }

    compact = [
        {
            "title": a.get("title"),
            "source": a.get("source_name"),
        }
        for a in conflicting[:10]
    ]

    prompt_input = {
        "original_queries": queries,
        "conflicts": compact,
    }

    result = await chain.ainvoke(prompt_input)

    new_queries = result.queries[:3]

    tasks = [
        fetch_rss_feed(
            GOOGLE_NEWS_RSS.format(query=quote_plus(q)),
            "google_news",
        )
        for q in new_queries
    ]

    new_batches = await asyncio.gather(*tasks, return_exceptions=True)

    new_articles = []
    for batch in new_batches:
        if isinstance(batch, Exception):
            continue
        batch = cast(list[RSSArticle], batch)

        new_articles.extend([asdict(a) for a in batch])

    existing = state.get("top_articles", [])
    seen = {a.get("link") for a in existing if a.get("link")}

    merged = list(existing)

    for a in new_articles:
        link = a.get("link")
        if not link or link in seen:
            continue
        seen.add(link)
        merged.append(a)

    return {
        "top_articles": merged,
        "deep_dive_count": state.get("deep_dive_count", 0) + 1,
    }
