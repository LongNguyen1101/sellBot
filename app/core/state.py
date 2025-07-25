from typing import NoReturn, TypedDict, Optional, Dict, Any, List, Annotated
import annotated_types
from httpcore import AnyIOBackend
from langgraph.graph.message import add_messages
from langgraph.prebuilt.chat_agent_executor import AgentState

def merge_lists(old, new):
    return old + new

def remain_value(old: Optional[Any], new: Optional[Any]) -> Optional[Any]:
    return new if new is not None else old

def remain_list(old, new):
    return old if len(new) == 0 else new
    
def remain_dict(old: dict, new: dict):
    return old if new.__len__() == 0 else new

class SellState(AgentState):
    user_input: Annotated[str, remain_value]
    messages: Annotated[list, add_messages]
    next_node: Annotated[str, remain_value]
    
    customer_id: Annotated[Optional[int], remain_value]
    name: Annotated[Optional[str], remain_value]
    phone_number: Annotated[Optional[str], remain_value]
    address: Annotated[Optional[str], remain_value]
    chat_id: Annotated[Optional[str], remain_value]
    
    cart: Annotated[Optional[dict], remain_dict]
    seen_products: Annotated[List[dict], remain_list]
    product_chosen: Annotated[Optional[dict], remain_value]
    
    orders: Annotated[list, remain_list]

def init_state() -> SellState:
    return SellState(
        user_input="",
        messages=[],
        next_node="",
    
        customer_id=None,
        name=None,
        phone_number=None,
        address=None,
        chat_id=None,

        cart={},
        seen_products=[],
        product_chosen=None,
        
        orders=[]
    )
