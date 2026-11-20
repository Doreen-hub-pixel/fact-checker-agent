from typing import TypedDict, List, Optional, Annotated
import operator

class ResearchState(TypedDict):
    topic: str
    document_name: str
    document_context: str
    research_questions: List[str]
    search_results: Annotated[List[dict], operator.add]
    search_errors: List[str]
    conflicts: Optional[List[dict]]
    research_draft: Optional[str]
    critic_score: Optional[float]
    critic_feedback: Optional[str]
    research_iterations: int
    max_research_iterations: int
    fact_check_report: Optional[dict]
    sources: Annotated[List[str], operator.add]