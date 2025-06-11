# BOOKINGTABLE/bot/langgraph/state.py
from typing import TypedDict, Optional, Dict, Any, List, Annotated
from langgraph.graph.message import add_messages
from langgraph.prebuilt.chat_agent_executor import AgentState
import operator

def merge_lists(old, new):
    return old + new

def remain_value(old: Optional[Any], new: Optional[Any]) -> Optional[Any]:
    return new if new is not None else old

class SellState(AgentState):
    user_input: Annotated[str, remain_value]
    messages: Annotated[list, add_messages]
    next_node: Annotated[str, remain_value]
    
    check_customer_info: Optional[str]
    
    customer_id: Annotated[Optional[int], remain_value]
    name: Annotated[Optional[str], remain_value]
    phone_number: Annotated[Optional[str], remain_value]
    address: Annotated[Optional[str], remain_value]
    is_login: Annotated[bool, remain_value]
    
    cart: Annotated[List[dict], merge_lists]
    seen_products: Annotated[List[dict], merge_lists]
    product_chosen: Annotated[Optional[dict], remain_value]

def init_state() -> SellState:
    return SellState(
        user_input="",
        messages=[],
        next_node="",
        
        check_customer_info=None,
        
        customer_id=None,
        name=None,
        phone_number=None,
        address=None,
        is_login=False,

        cart=[],
        seen_products=[],
        product_chosen=None
    )
