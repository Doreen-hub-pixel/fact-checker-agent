import os
import asyncio
import logging

from tavily import AsyncTavilyClient

from core.state import ResearchState

logger = logging.getLogger(__name__)


async def search_node(state: ResearchState) -> dict:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is required to search for sources.")

    tavily = AsyncTavilyClient(api_key=api_key)
    queries = list(state["research_questions"])
    feedback = state.get("critic_feedback")
    if state.get("research_iterations", 0) > 0 and feedback:
        queries.append(f"{state['topic']}: {feedback[:300]}")

    async def search_one(q: str):
        return await tavily.search(
            q,
            max_results=3,
            search_depth="advanced",
            include_answer=False,
        )
    
    responses = await asyncio.gather(
        *(search_one(q) for q in queries),
        return_exceptions=True,
    )

    results = []
    errors = []
    known_urls = {
        result.get("url")
        for result in state.get("search_results", [])
        if result.get("url")
    }
    for query, resp in zip(queries, responses):
        if isinstance(resp, Exception):
            logger.warning("Tavily search failed (%s): %s", type(resp).__name__, resp)
            errors.append(f"{type(resp).__name__}: {resp}")
            continue
        for result in resp.get("results", []):
            url = result.get("url")
            if url and result.get("content") and url not in known_urls:
                results.append({**result, "query": query})
                known_urls.add(url)

    if errors and not results and all(isinstance(response, Exception) for response in responses):
        raise RuntimeError(f"All Tavily searches failed: {'; '.join(errors)}")

    return {
        "search_results": results,
        "search_errors": list(dict.fromkeys(state.get("search_errors", []) + errors)),
    }