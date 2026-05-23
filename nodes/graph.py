from langgraph.graph import END, START, StateGraph

from .conflict_detector import conflict_detector_node
from .deep_dive_node import deep_dive_node
from .google_news_node import google_news_node
from .merge_rerank import merge_rerank_node
from .news_orgs_node import news_orgs_node
from .query_node import query_extractor_node
from .reddit_node import reddit_node
from .state import LensState
from .verdict_node import verdict_node


def conflict_router(state: LensState):
    if state.get("has_conflict") and state.get("deep_dive_count", 0) < 2:
        return "deep_dive"
    return "verdict"


def build_graph():
    graph = StateGraph(LensState)

    # entry
    graph.add_node("query", query_extractor_node)

    graph.add_node("google_news", google_news_node)
    graph.add_node("news_orgs", news_orgs_node)
    graph.add_node("reddit", reddit_node)

    graph.add_node("merge_rerank", merge_rerank_node)
    graph.add_node("conflict", conflict_detector_node)
    graph.add_node("deep_dive", deep_dive_node)
    graph.add_node("verdict", verdict_node)

    # start
    graph.add_edge(START, "query")

    # fan-out
    graph.add_edge("query", "google_news")
    graph.add_edge("query", "news_orgs")
    graph.add_edge("query", "reddit")

    # merge barrier
    graph.add_edge("google_news", "merge_rerank")
    graph.add_edge("news_orgs", "merge_rerank")
    graph.add_edge("reddit", "merge_rerank")

    # reasoning pipeline
    graph.add_edge("merge_rerank", "conflict")

    # conditional loop
    graph.add_conditional_edges(
        "conflict",
        conflict_router,
        {
            "deep_dive": "deep_dive",
            "verdict": "verdict",
        },
    )

    # loop back
    graph.add_edge("deep_dive", "conflict")

    # end
    graph.add_edge("verdict", END)

    return graph.compile()


if __name__ == "__main__":
    import asyncio

    from .conflict_detector import conflict_detector_node
    from .deep_dive_node import deep_dive_node
    from .google_news_node import google_news_node
    from .merge_rerank import merge_rerank_node
    from .news_orgs_node import news_orgs_node
    from .query_node import query_extractor_node
    from .reddit_node import reddit_node
    from .state import LensState, get_initial_state

    init_state = get_initial_state()
    init_state["raw_input"] = "Is the Indian government corrupt?"

    graph = build_graph()
    result = asyncio.run(graph.ainvoke(init_state))
    print(result)
