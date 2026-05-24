import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from nodes.graph import build_graph
from nodes.state import get_initial_state

router = APIRouter()

graph = build_graph()


class VerifyStreamRequest(BaseModel):
    raw_input: str
    input_type: str = "text"


def sse_event(event: str, data: dict):
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


NODE_MESSAGES = {
    "query": "Extracted search queries",
    "google_news": "Fetched Google News articles",
    "news_orgs": "Fetched news organization articles",
    "reddit": "Fetched Reddit discussions",
    "merge_rerank": "Merged and reranked articles",
    "conflict": "Analyzed source conflicts",
    "deep_dive": "Performed deep-dive retrieval",
    "verdict": "Generated final verdict",
}


def build_message(node: str, output: dict):
    if node == "query":
        return f"Extracted {output.get('query_meta', {}).get('query_count', 0)} search queries"

    if node == "google_news":
        return f"Fetched {output.get('google_meta', {}).get('article_count', 0)} Google News articles"

    if node == "news_orgs":
        return f"Fetched {output.get('news_orgs_meta', {}).get('article_count', 0)} news organization articles"

    if node == "reddit":
        return (
            f"Found {output.get('reddit_meta', {}).get('subreddit_count', 0)} relevant subreddits, "
            f"Fetched {output.get('reddit_meta', {}).get('article_count', 0)} Reddit posts"
        )

    if node == "merge_rerank":
        return (
            f"Merged {output.get('merge_meta', {}).get('merged_count', 0)} articles, "
            f"reranked top {output.get('merge_meta', {}).get('top_count', 0)}"
        )

    if node == "conflict":
        if output.get("conflict_meta", {}).get("conflict"):
            return f"Detected conflict across {output.get('conflict_meta', {}).get('conflicting_count', 0)} articles"
        return "No major conflict detected"

    if node == "deep_dive":
        return "Running targeted deep-dive retrieval"

    if node == "verdict":
        return "Generated final analytical verdict"

    return node


@router.post("/verify/stream")
async def verify_stream(
    req: VerifyStreamRequest,
):
    async def event_generator():
        state = get_initial_state()

        state["raw_input"] = req.raw_input
        state["input_type"] = req.input_type

        final_result = None

        async for event in graph.astream_events(
            state,
            version="v2",
        ):
            if event.get("event") != "on_chain_end":
                continue

            name = event.get("name")

            if name == "LangGraph":
                final_result = event.get("data", {}).get("output", {})
                continue

            if name not in {
                "query",
                "google_news",
                "news_orgs",
                "reddit",
                "merge_rerank",
                "conflict",
                "deep_dive",
                "verdict",
            }:
                continue

            output = event.get("data", {}).get("output", {})

            yield sse_event(
                "progress",
                {
                    "node": name,
                    "message": build_message(name, output),
                },
            )

        if final_result:
            yield sse_event(
                "final",
                {
                    "verdict_label": final_result.get("verdict_label"),
                    "verdict_explanation": final_result.get("verdict_explanation"),
                    "framing_notes": final_result.get("framing_notes"),
                    "top_articles": final_result.get(
                        "top_articles",
                        [],
                    ),
                },
            )

        yield sse_event(
            "done",
            {"ok": True},
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
