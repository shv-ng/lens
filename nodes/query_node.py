import logging
from typing import cast

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from core.decorators import cached, logit
from llm.client import get_llm
from llm.prompts.query import SYSTEM_PROMPT
from llm.schemas.query import QueriesOutput

from .state import LensState

logger = logging.getLogger(__name__)


@logit
async def query_extractor_node(state: LensState):
    try:
        llm = get_llm().with_structured_output(QueriesOutput)
    except Exception as e:
        logger.exception(f"Error initializing LLM for query extractor node, {e}")
        return {
            "queries": [],
            "error": [str(e)],
        }
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(""" {raw_input} """),
        ]
    )
    chain = prompt | llm
    raw_input = state["raw_input"]
    if not raw_input.strip():
        return {
            "queries": [],
            "query_meta": {
                "query_count": 0,
            },
            "error": ["No input provided"],
        }

    try:
        response = cast(
            QueriesOutput,
            await chain.ainvoke(
                {
                    "raw_input": raw_input,
                }
            ),
        )
        queries = [k.strip() for k in response.queries if k.strip()]
        logger.info(f"Query extracted: {queries}")

        return {
            "queries": queries,
            "query_meta": {
                "query_count": len(queries),
            },
        }

    except Exception as e:
        logger.exception("Error in query_extractor_node")

        return {
            "queries": [],
            "error": [str(e)],
        }
