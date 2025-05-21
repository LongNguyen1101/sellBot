# BOOKINGTABLE/bot/langgraph/state.py
from typing import TypedDict, Optional, Dict, Any, List, Annotated
from langgraph.graph.message import add_messages
import datetime

class SellState(TypedDict):
    user_input: str
    messages: Annotated[list, add_messages]
    next_node: str
    intent: str
    state_flow: List[str]
    
def init_state() -> SellState:
    return SellState(
        user_input = "",
        messages = [],
        next_node = "",
        intent="",
        state_flow=[],
        
    )