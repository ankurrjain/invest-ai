"""
LangGraph StateGraph — wires supervisor → specialist agents → synthesizer.
"""
from langgraph.graph import StateGraph, START, END
from .state import ResearchState
from .supervisor import supervisor_node
from .technical import technical_node
from .fundamental import fundamental_node
from .news import news_node
from .synthesizer import synthesizer_node
from .comparison import comparison_node
from .dividend import dividend_node
from .moat import moat_node
from .screener import screener_node


def _route_after_supervisor(state: ResearchState) -> list[str]:
    """Fan out to all requested specialist agents in parallel."""
    mode = state.get("mode", "single")
    
    if mode == "compare":
        return ["comparison_agent"]
    elif mode == "screener":
        return ["screener_agent"]
        
    agents = state.get("agents_to_call", ["technical", "fundamental", "news"])
    mapping = {
        "technical": "technical_agent",
        "fundamental": "fundamental_agent",
        "news": "news_agent",
        "dividend": "dividend_agent",
        "moat": "moat_agent",
    }
    return [mapping[a] for a in agents if a in mapping]


def _route_to_synthesizer(state: ResearchState) -> str:
    return "synthesizer"


def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)

    # Nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("technical_agent", technical_node)
    graph.add_node("fundamental_agent", fundamental_node)
    graph.add_node("news_agent", news_node)
    graph.add_node("comparison_agent", comparison_node)
    graph.add_node("dividend_agent", dividend_node)
    graph.add_node("moat_agent", moat_node)
    graph.add_node("screener_agent", screener_node)
    graph.add_node("synthesizer", synthesizer_node)

    # Entry
    graph.add_edge(START, "supervisor")

    # Supervisor fans out to specialist agents
    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            "technical_agent": "technical_agent",
            "fundamental_agent": "fundamental_agent",
            "news_agent": "news_agent",
            "comparison_agent": "comparison_agent",
            "dividend_agent": "dividend_agent",
            "moat_agent": "moat_agent",
            "screener_agent": "screener_agent",
        },
    )

    # All specialists converge to synthesizer
    graph.add_edge("technical_agent", "synthesizer")
    graph.add_edge("fundamental_agent", "synthesizer")
    graph.add_edge("news_agent", "synthesizer")
    graph.add_edge("comparison_agent", "synthesizer")
    graph.add_edge("dividend_agent", "synthesizer")
    graph.add_edge("moat_agent", "synthesizer")
    graph.add_edge("screener_agent", "synthesizer")

    # End
    graph.add_edge("synthesizer", END)

    return graph.compile()


# Singleton compiled graph
research_graph = build_graph()


def run_research(ticker: str, market: str, query: str) -> dict:
    """
    Run the full research pipeline.
    Returns the final state dict with all analysis fields.
    """
    initial_state: ResearchState = {
        "messages": [],
        "ticker": ticker,
        "market": market,
        "query": query,
        "agents_to_call": [],
        "agents_called": [],
        "technical_analysis": None,
        "fundamental_analysis": None,
        "news_analysis": None,
        "final_report": None,
        "company_name": None,
        "current_price": None,
        "error": None,
    }
    return research_graph.invoke(initial_state)
