from typing import Optional, Any, List, Annotated
from langgraph.graph.message import add_messages
from langgraph.prebuilt.chat_agent_executor import AgentState

def merge_lists(old, new):
    return old + new

def remain_value(old: Optional[Any], new: Optional[Any]) -> Optional[Any]:
    return new if new is not None else old

def remain_list(old, new):
    return old if len(new) == 0 else new
    
def remain_dict(old: dict, new: dict):
    return old if not new else new

def remain_tasks(old: Optional[List[dict]], new: Optional[List[dict]]) -> List[dict]:
    return old if new is None else new

class SellState(AgentState):
    user_input: Annotated[str, remain_value]
    messages: Annotated[list, add_messages]
    next_node: Annotated[str, remain_value]
    
    tasks: Annotated[Optional[List[dict]], remain_tasks]
    status: Annotated[str, remain_value]
    
    customer_id: Annotated[Optional[int], remain_value]
    name: Annotated[Optional[str], remain_value]
    phone_number: Annotated[Optional[str], remain_value]
    address: Annotated[Optional[str], remain_value]
    chat_id: Annotated[Optional[str], remain_value]
    
    cart: Annotated[Optional[dict], remain_dict]
    seen_products: Annotated[List[dict], remain_list]
    
    orders: Annotated[list, remain_list]

def init_state() -> SellState:
    return SellState(
        user_input="",
        messages=[],
        next_node="",
        
        tasks=None,
        status="",
    
        customer_id=None,
        name=None,
        phone_number=None,
        address=None,
        chat_id=None,

        cart={},
        seen_products=[],
        
        orders=[],
    )
