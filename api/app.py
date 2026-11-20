from dotenv import load_dotenv

load_dotenv()

import json
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, StringConstraints
from api.auth import require_authenticated_user
from core.graph import graph

app = FastAPI(title="Multi-Agent Fact Checker API")
logger = logging.getLogger(__name__)
BLACKLIST = ["ignore previous instructions", "system prompt", "drop table"]

class ResearchRequest(BaseModel):
    topic: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    document_name: Annotated[str, StringConstraints(max_length=255)] = ""
    document_context: str = Field(default="", max_length=25_000)

@app.post("/research/stream")
async def research_stream(
    req: ResearchRequest,
    _user: dict = Depends(require_authenticated_user),
):
    if any(word in req.topic.lower() for word in BLACKLIST):
        raise HTTPException(status_code=400, detail="Invalid input. Prompt injection blocked.")
    
    async def event_generator():
        initial_state = {
            "topic": req.topic, "document_name": req.document_name,
            "document_context": req.document_context,
            "research_questions": [], "search_results": [],
            "search_errors": [],
            "conflicts": [], "research_draft": None, "critic_score": None,
            "critic_feedback": None, "research_iterations": 0, "max_research_iterations": 2,
            "fact_check_report": None, "sources": [],
        }
        try:
            async for chunk in graph.astream(initial_state, stream_mode="updates"):
                for node_name, update in chunk.items():
                    payload = json.dumps(
                        {"node": node_name, "data": update},
                        default=str,
                    )
                    yield f"data: {payload}\n\n"
        except Exception:
            logger.exception("LangGraph research stream failed")
            payload = json.dumps(
                {"error": "Research failed. Check the API server logs for details."}
            )
            yield f"event: error\ndata: {payload}\n\n"
        else:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/")
def health_check():
    return {"status": "healthy"}