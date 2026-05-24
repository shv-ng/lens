import asyncio
import json
import logging
import os
import tempfile
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from core.decorators import logit
from nodes.graph import build_graph
from nodes.state import get_initial_state
from tools.ocr import extract_text_from_image
from tools.pdf import extract_text_from_pdf

router = APIRouter()
graph = build_graph()
logger = logging.getLogger(__name__)

TRACKED_NODES = {
    "query",
    "google_news",
    "news_orgs",
    "reddit",
    "merge_rerank",
    "conflict",
    "deep_dive",
    "verdict",
}


@logit
def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@logit
def format_node_message(node: str, output: dict) -> str:
    def meta(key):
        return output.get(key, {})

    if node == "query":
        return f"Extracted {meta('query_meta').get('query_count', 0)} search queries"
    if node == "google_news":
        return f"Fetched {meta('google_meta').get('article_count', 0)} Google News articles"
    if node == "news_orgs":
        return f"Fetched {meta('news_orgs_meta').get('article_count', 0)} news organization articles"
    if node == "reddit":
        r_meta = meta("reddit_meta")
        return f"Found {r_meta.get('subreddit_count', 0)} relevant subreddits, Fetched {r_meta.get('article_count', 0)} Reddit posts"
    if node == "merge_rerank":
        m_meta = meta("merge_meta")
        return f"Merged {m_meta.get('merged_count', 0)} articles, reranked top {m_meta.get('top_count', 0)}"
    if node == "conflict":
        if meta("conflict_meta").get("conflict"):
            return f"Detected conflict across {meta('conflict_meta').get('conflicting_count', 0)} articles"
        return "No major conflict detected"
    if node == "deep_dive":
        return "Running targeted deep-dive retrieval"
    if node == "verdict":
        return "Generated final analytical verdict"
    return node


@logit
async def process_file_input(file_bytes: bytes, input_type: str) -> str:
    """Saves file bytes to disk and passes the path directly to your tool functions."""
    loop = asyncio.get_running_loop()

    def run_tool_pipeline():
        suffix = ".pdf" if input_type == "pdf" else ".img"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            if input_type == "pdf":
                extracted_text = extract_text_from_pdf(tmp_path)
            else:
                extracted_text = extract_text_from_image(tmp_path)

            if not extracted_text or not extracted_text.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Could not extract any text from the provided {input_type} file.",
                )
            return extracted_text.strip()
        except Exception as e:
            logger.exception("Error running tool pipeline")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Error running tool pipeline: {e}",
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return await loop.run_in_executor(None, run_tool_pipeline)


@logit
async def stream_graph_events(
    raw_input: str, input_type: str, request: Request
) -> AsyncGenerator[str, None]:
    state = get_initial_state()
    state["raw_input"] = raw_input
    state["input_type"] = input_type

    final_result = None
    graph_stream = graph.astream_events(state, version="v2")

    try:
        next_event_task = asyncio.create_task(anext(graph_stream))

        while True:
            if await request.is_disconnected():
                logger.info("Client disconnected, Aborting stream")
                break

            done, _ = await asyncio.wait([next_event_task], timeout=0.25)
            if not done:
                continue

            try:
                event = next_event_task.result()
            except StopAsyncIteration:
                logger.info("No more events from LangGraph")
                break

            next_event_task = asyncio.create_task(anext(graph_stream))

            if event.get("event") != "on_chain_end":
                continue

            name = event.get("name")
            if name == "LangGraph":
                final_result = event.get("data", {}).get("output", {})
                continue

            if name not in TRACKED_NODES:
                continue

            output = event.get("data", {}).get("output", {})
            yield format_sse(
                "progress",
                {
                    "node": name,
                    "message": format_node_message(name, output),
                },
            )

        if final_result and not await request.is_disconnected():
            yield format_sse(
                "final",
                {
                    "verdict_label": final_result.get("verdict_label"),
                    "verdict_explanation": final_result.get("verdict_explanation"),
                    "framing_notes": final_result.get("framing_notes"),
                    "top_articles": final_result.get("top_articles", []),
                },
            )

        yield format_sse("done", {"ok": True})

    except asyncio.CancelledError:
        logger.info("SSE stream pipeline cancelled")
        raise
    except Exception as e:
        logger.exception("Error inside event generator stream workflow")
        yield format_sse("error", {"error": str(e)})
    finally:
        try:
            await graph_stream.aclose()
        except Exception as e:
            logger.debug(f"Error closing graph stream iterator: {e}")


@logit
@router.post("/verify/stream")
async def verify_stream(
    request: Request,
    input_type: Optional[str] = Form(None),
    file: Optional[UploadFile] = None,
):
    content_type = request.headers.get("content-type", "")

    # Multipart Form Routing
    if "multipart/form-data" in content_type:
        if not input_type:
            raise HTTPException(
                status_code=400, detail="Missing form parameter field: 'input_type'"
            )
        if not file:
            raise HTTPException(status_code=400, detail="Missing upload file payload.")

        if input_type not in {"pdf", "image"}:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file type flag: {input_type}"
            )

        resolved_type = input_type
        file_bytes = await file.read()
        raw_input = await process_file_input(file_bytes, resolved_type)

    # application/json Processing
    elif "application/json" in content_type:
        try:
            body = await request.json()
            raw_input = body.get("raw_input", "").strip()
            resolved_type = body.get("input_type", "text")
        except Exception:
            raise HTTPException(
                status_code=400, detail="Malformed JSON request payload structure."
            )

        if not raw_input:
            raise HTTPException(
                status_code=400, detail="Missing required field key: 'raw_input'"
            )

    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported media header. Must use application/json or multipart/form-data.",
        )

    return StreamingResponse(
        stream_graph_events(
            raw_input=raw_input, input_type=resolved_type, request=request
        ),
        media_type="text/event-stream",
    )
