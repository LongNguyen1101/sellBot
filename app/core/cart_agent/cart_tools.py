import json
from aiohttp import content_disposition_filename
from langchain_core.tools import tool, InjectedToolCallId
from app.core.cart_agent.cart_prompts import add_cart_prompt
from app.core.graph_function import GraphFunction
from app.core.model import init_model
from app.core.state import SellState
from typing import Annotated, List, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.helper_function import _get_cart


graph_function = GraphFunction()
llm = init_model()

class AddCart(TypedDict):
    product_id: int
    sku: str
    product_name: str
    variance_description: str
    quantity: int
    price: int

@tool
def add_cart(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
    
) -> Command:
    """Use this tool to add product into cart"""
    try:
        cart = []
        content = ""
        next_node = "__end__"
        product_chosen = state["product_chosen"]
        
        if product_chosen is not None:
            cart = [
                {
                    "product_id": product_chosen["product_id"],
                    "sku": product_chosen["sku"],
                    "product_name": product_chosen["product_name"],
                    "variance_description": product_chosen["variance_description"],
                    "quantity": 1,
                    "price": product_chosen["price"],
                    "subtotal": product_chosen["price"]
                }
            ]
            
            old_cart = state["cart"]
            new_cart = old_cart + cart
            get_cart = _get_cart(new_cart)
            
            content = (
                "Add product successfully.\n"
                "Here is cart of customer, return this to customer:\n"
                f"{get_cart}"
            )
            next_node = "__end__"
        else:
            seen_products = state["seen_products"]
            content = (
                "Customer has not chosen product, ask customer to choose.\n"
                "Here are the previous product searched by customer, suggest customer with these products:\n"
                f"{seen_products}"
            )
            next_node = "product_agent"
            
        return_json = json.dumps(cart)
        
        return Command(
            update={
                "next_node": next_node,
                "return_json": return_json,
                "messages": [
                    ToolMessage
                    (
                        content=content,
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
    except Exception as e:
        raise Exception(e)
    
@tool
def get_cart(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to return th item in cart to customer"""
    try:
        cart = state["cart"]
        cart_item = ""
        index = 1
        total = 0

        for item in cart:
            cart_item += (
                f"STT: {index}\n"
                f"Tên sản phẩm: {item["product_name"]}\n"
                f"Tên phân loại: {item["variance_description"]}\n"
                f"Mã sản phẩm: {item["product_id"]}\n"
                f"Mã phân loại: {item["sku"]}\n"
                f"Giá: {item["price"]} VNĐ\n"
                f"Số lượng: {item["quantity"]} cái\n"
                f"Tổng giá sản phẩm: {item["subtotal"]} VNĐ\n\n"
            )
            total += item["subtotal"]
            index += 1
            
        cart_item += f"Tổng giá trị của giỏ hàng: {total}"
        
        return Command(
            update={
                "next_node": "__end__",
                "messages": [
                    ToolMessage
                    (
                        content=cart_item,
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
    except Exception as e:
        raise Exception(e)
    
@tool
def update_quantity(
    tate: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to update quanity of the chosen product in cart"""
    pass

@tool
def remove_item(
    tate: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to remove a product in cart"""
    pass