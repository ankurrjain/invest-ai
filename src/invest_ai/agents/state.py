from typing import TypedDict, Annotated, Optional, List
import operator
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ResearchState(TypedDict):
    """Shared state passed between all agents in the research graph."""
    messages: Annotated[List[BaseMessage], add_messages]
    mode: str                         # "single", "compare", "screener", "live_intel"
    ticker: str                       # comma-separated for comparison, theme string for screener
    market: str                       # "india" or "us"
    query: str
    agents_to_call: List[str]         # set by supervisor
    agents_called: Annotated[List[str], operator.add] 
    
    # Analysis outputs
    technical_analysis: Optional[str]
    fundamental_analysis: Optional[str]
    news_analysis: Optional[str]
    dividend_analysis: Optional[str]
    moat_analysis: Optional[str]
    comparison_analysis: Optional[str]
    screener_analysis: Optional[str]
    live_intel_analysis: Optional[str]
    live_news_analysis: Optional[str]
    
    final_report: Optional[str]
    company_name: Optional[str]
    current_price: Optional[float]
    error: Optional[str]
