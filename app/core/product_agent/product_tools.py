from itertools import product
from langchain_core.tools import tool, InjectedToolCallId
from app.core.graph_function import GraphFunction
from app.chain.sell_chain import SellChain
from app.core.model import init_model
from app.core.product_agent.product_prompts import choose_product_prompt
from app.core.state import SellState
from typing import Annotated, List, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from typing import Optional

graph_function = GraphFunction()
llm = init_model()

class ProductChosen(TypedDict):
    product_id: Optional[int]
    sku: Optional[str]
    product_name: Optional[str]
    variance_description: Optional[str]
    price: Optional[int]
    

@tool
def get_products(
    keyword: Annotated[str, "The keyword of products"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to get products from database follow by the keyword of customer"""
    try:
        products = graph_function.get_products_by_keyword(keyword=keyword)
        extract_products = [
            {
                "product_id": product["product_id"],
                "sku": product["sku"],
                "product_name": product["product_name"],
                "variance_description": product["variance_description"],
                "price": product["price"]
            }
            for product in products
        ]
        
        products_length = len(extract_products)
        product_chosen = extract_products[0] if products_length == 1 else None

        content = (
            f"Số lượng sản phẩm khớp với từ khoá: {products_length}\n"
            "Dưới đây là danh sách các sản phẩm:\n"
            f"{products}"
        )
        
        return Command(
            update={
                "seen_products": extract_products,
                "product_chosen": product_chosen,
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
        raise Exception(e)

@tool
def choose_product(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to identify product which chosen by customer"""
    seen_products = state["seen_products"]
    chat_history = state["messages"]
    user_input = state["user_input"]
    content = ""
    next_node = "__end__"
    product_chosen = None
    phone_number = state["phone_number"]
    
    messages = [
        {"role": "system", "content": choose_product_prompt()},
        {"role": "human", "content": (
            f"Danh sách các sản phẩm khách đã xem: {seen_products}\n"
            f"Lịch sử chat: {chat_history}\n"
            f"Tin nhắn của khách: {user_input}\n"
            "Bạn hãy xác định sản phẩm mà khách chọn."
        )}
    ]
    
    response = llm.with_structured_output(ProductChosen).invoke(messages)
    
    if response["product_id"] is not None:
        content = "Product identified."
        product_chosen = response
        if phone_number is None:
            content += "\nContinue add product to cart."
            next_node = "cart_agent"
        else:
            content += "\nAsk customer provide phone number."
            next_node = "__end__"
    else:
        content = "Can not identify product. Ask again customer."
        product_chosen = None
        next_node =  "__end__"
    
    return Command(
        update={
            "messages": [
                ToolMessage
                (
                    content=content,
                    tool_call_id=tool_call_id
                ),
            ],
            "next_node": next_node,
            "product_chosen": product_chosen
        }
    )