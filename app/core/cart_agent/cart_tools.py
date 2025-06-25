from ctypes import addressof
import json
from operator import add
from click import Option
from langchain_core.tools import tool, InjectedToolCallId
from platformdirs import user_data_dir
from app.core.cart_agent.cart_prompts import change_quantity_product_prompt, remove_product_prompt
from app.core.graph_function import GraphFunction
from app.core.model import init_model
from app.core.state import SellState
from typing import Annotated, List, Literal, Optional, TypedDict
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
    
class UpdateQuantity(TypedDict):
    product_id: Optional[int]
    sku: Optional[str]
    update_quantity: Optional[int]

class RemoveProduct(TypedDict):
    product_id: Optional[int]
    sku: Optional[str]

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
        
        name = state["name"] if state["name"] else "Không có thông tin"
        phone_number = state["phone_number"] if state["phone_number"] else "Không có thông tin"
        address = state["address"] if state["address"] else "Không có thông tin"
        
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
            get_cart = _get_cart(new_cart, name, phone_number, address)
            
            content = (
                "Thêm sản phẩm thành công.\n"
                "Đây là giỏ hàng của khách, hãy trả về cho khách:\n"
                f"{get_cart}"
            )
            next_node = "__end__"
        else:
            seen_products = state["seen_products"]
            content = (
                "Khách chưa chọn sản phẩm, hỏi lại khách muốn chọn sản phẩm nào.\n"
                "Đây là các sản phẩm khách đã xem lần trước, gợi ý cho khách các sản phẩm này:\n"
                f"{seen_products}"
            )
            next_node = "__end__"
            
        return_json = json.dumps(new_cart)
        
        return Command(
            update={
                "next_node": next_node,
                "cart": new_cart,
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
        name = state["name"] if state["name"] else "Không có thông tin"
        phone_number = state["phone_number"] if state["phone_number"] else "Không có thông tin"
        address = state["address"] if state["address"] else "Không có thông tin"
        cart_item = _get_cart(cart, name, phone_number, address)
        
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
def change_quantity_product(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to change quantity of a specify product"""
    content = ""
    cart = state["cart"]
    user_input = state["user_input"]
    chat_histories = state["messages"]
    update = {}
    
    name = state["name"] if state["name"] else "Không có thông tin"
    phone_number = state["phone_number"] if state["phone_number"] else "Không có thông tin"
    address = state["address"] if state["address"] else "Không có thông tin"
    
    msg = [
        {"role": "system", "content": change_quantity_product_prompt()},
        {"role": "human", "content": (
            f"Đây là cart: {cart}.\n"
            f"Đây là yêu cầu của người dùng: {user_input}.\n"
            f"Đây là lịch sử chat: {chat_histories}."
        )}
    ]
    
    result = llm.with_structured_output(UpdateQuantity).invoke(msg)
    
    if result["product_id"] is None:
        content = "Không xác định được sản phẩm khách muốn thay đổi, hỏi lại khách."
    else:
        update_quantity = result["update_quantity"]
        if update_quantity is None:
            content = "Không xác định được số lượng sản phẩm khách muốn thay đổi, hỏi lại khách."
        else:
            for item in cart:
                if item["product_id"] == result["product_id"] and item["sku"] == result["sku"]:
                    item["quantity"] = int(update_quantity)
            get_cart = _get_cart(cart, name, phone_number, address)
            
            content = (
                "Đã thay đổi số lượng thành công.\n"
                "Trả lại giỏ hàng cho khách:\n"
                f"{get_cart}"
            )
            
    update["cart"] = cart
    update["messages"] = [
        ToolMessage
        (
            content=content,
            tool_call_id=tool_call_id
        )
    ]
    
    print(f">>>> Update: {update}")
   
    return Command(
        update=update
    )
    
@tool
def remove_product(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to remove product in cart"""
    try:
        content = ""
        cart = state["cart"]
        user_input = state["user_input"]
        chat_histories = state["messages"]
        update = {}

        name = state["name"] if state["name"] else "Không có thông tin"
        phone_number = state["phone_number"] if state["phone_number"] else "Không có thông tin"
        address = state["address"] if state["address"] else "Không có thông tin"

        msg = [
            {"role": "system", "content": remove_product_prompt()},
            {"role": "human", "content": (
                f"Đây là cart: {cart}.\n"
                f"Đây là yêu cầu của người dùng: {user_input}.\n"
                f"Đây là lịch sử chat: {chat_histories}."
            )}
        ]

        result = llm.with_structured_output(RemoveProduct).invoke(msg)

        if result["product_id"] is None:
            content = "Không xác định được sản phẩm khách muốn thay đổi, hỏi lại khách."
        else:
            updated_cart = [item for item in cart if item["product_id"] != result["product_id"] and item["sku"] != result["sku"]]
            get_cart = _get_cart(updated_cart, name, phone_number, address)
            
            content = (
                "Đã thay đổi số lượng thành công.\n"
                "Trả lại giỏ hàng cho khách:\n"
                f"{get_cart}"
            )

        update["cart"] = updated_cart
        update["messages"] = [
            ToolMessage
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]

        print(f">>>> Update: {update}")
    except Exception as e:
        raise Exception(e)