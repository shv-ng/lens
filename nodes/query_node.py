import logging
from typing import cast

from langchain_core.prompts import (ChatPromptTemplate,
                                    HumanMessagePromptTemplate,
                                    SystemMessagePromptTemplate)

from llm.client import get_llm
from llm.prompts.query import SYSTEM_PROMPT
from llm.schemas.query import QueriesOutput

from .state import LensState

logger = logging.getLogger(__name__)


async def query_extractor_node(state: LensState):
    llm = get_llm().with_structured_output(QueriesOutput)
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
            "error": "No input provided",
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
            "error": str(e),
        }


if __name__ == "__main__":
    import asyncio
    import json

    from .state import get_initial_state

    init_state = get_initial_state()
    init_state["raw_input"] = "What is the best way to learn Python?"

    data = asyncio.run(query_extractor_node(init_state))
    print(json.dumps(data, indent=4))
