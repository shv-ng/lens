import asyncio
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from nodes.graph import build_graph
from nodes.state import get_initial_state

router = APIRouter()

graph = build_graph()

logger = logging.getLogger(__name__)


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
    request: Request,
):
    async def event_generator():
        try:
            state = get_initial_state()

            state["raw_input"] = req.raw_input
            state["input_type"] = req.input_type

            final_result = None

            graph_stream = graph.astream_events(
                state,
                version="v2",
            )

            next_event_task = asyncio.create_task(anext(graph_stream))
            while True:
                if await request.is_disconnected():
                    logger.info("Client disconnected, Aborting stream")
                    break

                done, _ = await asyncio.wait(
                    [next_event_task],
                    timeout=0.25,
                )

                if not done:
                    continue

                try:
                    event = next_event_task.result()
                except StopAsyncIteration:
                    logger.info("No more events")
                    break

                next_event_task = asyncio.create_task(anext(graph_stream))

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

            if final_result and not await request.is_disconnected():
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
        except asyncio.CancelledError:
            logger.info("SSE cancelled")
            raise
        except Exception as e:
            logger.exception("Error in event generator")
            yield sse_event(
                "error",
                {"error": str(e)},
            )
        finally:
            try:
                await graph_stream.aclose()
                logger.info("LangGraph stream iterator closed successfully.")
            except Exception as e:
                logger.debug(f"Error closing graph stream iterator: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
