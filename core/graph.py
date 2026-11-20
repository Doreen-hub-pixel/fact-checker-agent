from langgraph.graph import StateGraph, START, END
from core.state import ResearchState
from agents.planner import planner_node
from agents.searcher import search_node
from agents.conflict import conflict_node
from agents.critic import critic_node, route_after_critic
from agents.synthesizer import synthesis_node
from agents.fact_checker import fact_check_node

builder = StateGraph(ResearchState)

builder.add_node("planner", planner_node)
builder.add_node("searcher", search_node)
builder.add_node("conflict", conflict_node)
builder.add_node("critic", critic_node)
builder.add_node("synthesizer", synthesis_node)
builder.add_node("fact_checker", fact_check_node)

builder.add_edge(START, "planner")
builder.add_edge("planner", "searcher")
builder.add_edge("searcher", "conflict")
builder.add_edge("conflict", "critic")

builder.add_conditional_edges("critic", route_after_critic, {
    "research_more": "searcher",
    "synthesize": "synthesizer",
})

builder.add_edge("synthesizer", "fact_checker")
builder.add_edge("fact_checker", END)

graph = builder.compile()