from langchain_core.tools import tool, InjectedToolCallId
from app.core.graph_function import GraphFunction
from app.core.model import init_model
from app.core.state import SellState
from typing import Annotated, List, Literal, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage, AIMessage
from app.core.helper_function import _return_order

graph_function = GraphFunction()
llm = init_model()
    
    
@tool
def create_order(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to create order"""
    try:
        customer_id = state["customer_id"]
        if customer_id is not None:
            cart_items = state["cart"]
            shipping_fee = 50000
            payment = "COD"

            new_order = graph_function.create_order(customer_id)
            order_items, order_total = graph_function.add_cart_item_to_order(cart_items, new_order.order_id)

            grand_total = order_total + shipping_fee
            update_order = graph_function.add_total_to_order(
                new_order.order_id,
                payment,
                order_total,
                shipping_fee,
                grand_total
            )

            return_order = _return_order(new_order.order_id)

            content = (
                "Create order successfully.\n"
                "Return order to customer:\n"
                f"{return_order}"
            )
        else:
            content = "Customer does not provide phone_number, ask customer to provide"
        
        return Command(
            update={
                "messages": [
                    ToolMessage
                    (
                        content=content,
                        tool_call_id=tool_call_id
                    )
                ],
                "next_node": "__end__"
            }
        )
    except Exception as e:
        raise 
    