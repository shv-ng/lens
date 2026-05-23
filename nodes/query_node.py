from typing import cast
import logging
import dotenv
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from llm.client import get_llm
from .state import LensState
from llm.schemas.query import QueriesOutput
from llm.prompts.query import SYSTEM_PROMPT

dotenv.load_dotenv()

logger = logging.getLogger(__name__)


llm = get_llm(QueriesOutput)

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(""" {raw_input} """),
    ]
)

chain = prompt | llm


async def query_extractor_node(state: LensState):
    raw_input = state["raw_input"]

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
        logger.info(f"Query extracted: {len(queries)}")

        return {
            "queries": queries,
        }

    except Exception as e:
        logger.exception("Error in query_extractor_node")

        return {
            "queries": [],
            "error": str(e),
        }


if __name__ == "__main__":
    import asyncio
    from .state import get_initial_state
    import json

    init_state = get_initial_state()
    init_state["raw_input"] = "What is the best way to learn Python?"

    data = asyncio.run(query_extractor_node(init_state))
    print(json.dumps(data, indent=4))
