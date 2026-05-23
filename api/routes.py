from fastapi import APIRouter
from pydantic import BaseModel

from nodes.graph import build_graph
from nodes.state import get_initial_state

router = APIRouter()

graph = build_graph()


class VerifyRequest(BaseModel):
    raw_input: str
    input_type: str = "text"


class VerifyResponse(BaseModel):
    verdict_label: str
    verdict_explanation: str
    framing_notes: str
    top_articles: list[dict]


@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest):
    state = get_initial_state()

    state["raw_input"] = req.raw_input
    state["input_type"] = req.input_type

    result = await graph.ainvoke(state)

    return {
        "verdict_label": result.get("verdict_label"),
        "verdict_explanation": result.get("verdict_explanation"),
        "framing_notes": result.get(
            "framing_notes",
            "",
        ),
        "top_articles": result.get(
            "top_articles",
            [],
        ),
    }
