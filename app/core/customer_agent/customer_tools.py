from operator import add
from venv import create
from langchain_core.tools import tool, InjectedToolCallId
from langsmith import expect
from app.core import graph
from app.core.graph_function import GraphFunction
from app.core.model import init_model
from app.core.state import SellState
from typing import Annotated, List, Literal, LiteralString, Optional, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage, AIMessage
from app.core.helper_function import _get_cart, _return_order


graph_function = GraphFunction()
llm = init_model()

@tool
def add_phone_number(
    phone_number: Annotated[str, "Phone number of customer"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to add phone number to customer in database"""
    try:
        content = ""
        update = {}
        chat_id = state["chat_id"]
        cart = state["cart"]
        
        customer = graph_function.update_or_create_customer(
            phone_number=phone_number,
            chat_id=chat_id
        )
        
        if customer:
            update["phone_number"] = phone_number
            update["customer_id"] = customer.customer_id
            
            if cart:
                get_cart = _get_cart(cart, "Không có thông tin", phone_number, "Không có thông tin")
                content += (
                    "Đây là giỏ hàng của khách, trả về đúng y giỏ hàng để khách kiểm tra, không được tóm gọn, không được viết lại:\n"
                    f"{get_cart}.\n"
                    "Hỏi khách muốn lên đơn luôn không.\n"
                )
            else:
                seen_products = state["seen_products"]
                if seen_products:
                    content += (
                        "Đây là các sản phẩm khách vừa xem:\n"
                        f"{seen_products}\n\n"
                        "Hỏi khách muốn mua sản phẩm nào"
                    )
                else:
                    content += (
                        "Dựa vào yêu cầu trước đó của khách để:\n"
                        "- Nếu khách có yêu cầu trước đó, hỏi khách có muốn tiếp tục thực hiện không.\n"
                        "- Nếu khách không có yêu cầu trước đó, giới thiệu về các mặt hàng cửa "
                        "hàng đang bán (đồ điện tử thông minh như camera, cảm biến, đèn led, ...).\n"
                    )
        else:
            content += "Lỗi trong lúc đăng ký khách hàng, thông báo khách vui lòng thử lại."
        
        update["messages"] = [
            ToolMessage 
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]
        update["next_node"] = "__end__"

        return Command(
            update=update,
        )

    except Exception as e:
        raise Exception(e)

@tool
def add_name_address(
    name: Annotated[Optional[str], "Name of customer"],
    address: Annotated[Optional[str], "Address of customer"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to add name and address to customer in database"""
    try:
        content = ""
        update = {}
        missing_info = []
        cart = state["cart"]
        
        if name is None:
            missing_info.append("name")
        if address is None:
            missing_info.append("address")
            
        if len(missing_info) > 0:
            content += f"Thiếu những thông tin sau để đăng ký cho khách hàng: {missing_info}"
        else:
            updated_customer = graph_function.update_customer_info(
                customer_id=state["customer_id"],
                name=name,
                address=address
            )

            if updated_customer:                
                content += (
                    "Thêm tên và địa chỉ của khách hàng thành công.\n"
                )
                update["name"] = name
                update["address"] = address
                
                if cart:
                    update["next_node"] = "order_agent"
                    content += (
                        "Đã có đầy đủ thông tin, lên đơn cho khách.\n"
                        "Không được đề cập đến bất kỳ nhân viên nào, "
                        "chỉ được thông báo khách chờ trong giây lát để "
                        "lên đơn."
                    )
                else:
                    seen_products = state["seen_products"]
                    if seen_products:
                        content += (
                            "Đây là các sản phẩm khách vừa xem:\n"
                            f"{seen_products}\n\n"
                            "Hỏi khách muốn mua sản phẩm nào"
                        )
                    else:
                        content += (
                            "Dựa vào yêu cầu trước đó của khách để:\n"
                            "- Nếu khách có yêu cầu trước đó, hỏi khách có muốn tiếp tục thực hiện không.\n"
                            "- Nếu khách không có yêu cầu trước đó, giới thiệu về các mặt hàng cửa "
                            "hàng đang bán (đồ điện tử thông minh như camera, cảm biến, đèn led, ...).\n"
                        )
            else:
                content += "Lỗi trong thêm tên và địa chỉ của khách hàng. Nói khách vui lòng thử lại."
        
        update["messages"] = [
            ToolMessage 
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]
            
        return Command(
            update=update
        )
        
    except Exception as e:
        raise Exception(e)
    
@tool
def add_phone_name_address(
    phone_number: Annotated[str, "Phone number of customer"],
    name: Annotated[Optional[str], "Name of customer"],
    address: Annotated[Optional[str], "Address of customer"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Only use this tool when customer give all three information phone number, name and address"""
    try:
        content = ""
        update = {}
        chat_id = state["chat_id"]
        cart = state["cart"]
        
        customer = graph_function.update_or_create_customer(
            name=name,
            phone_number=phone_number,
            address=address,
            chat_id=chat_id
        )
        
        if customer:
            update["phone_number"] = phone_number
            update["name"] = name
            update["address"] = address
            update["customer_id"] = customer.customer_id
            
            if cart:
                update["next_node"] = "order_agent"
                content += (
                    "Đã có đầy đủ thông tin, lên đơn cho khách.\n"
                    "Không được đề cập đến bất kỳ nhân viên nào, "
                    "chỉ được thông báo khách chờ trong giây lát để "
                    "lên đơn."
                )
            else:
                seen_products = state["seen_products"]
                if seen_products:
                    content += (
                        "Đây là các sản phẩm khách vừa xem:\n"
                        f"{seen_products}\n\n"
                        "Hỏi khách muốn mua sản phẩm nào"
                    )
                else:
                    content += (
                        "Dựa vào yêu cầu trước đó của khách để:\n"
                        "- Nếu khách có yêu cầu trước đó, hỏi khách có muốn tiếp tục thực hiện không.\n"
                        "- Nếu khách không có yêu cầu trước đó, giới thiệu về các mặt hàng cửa "
                        "hàng đang bán (đồ điện tử thông minh như camera, cảm biến, đèn led, ...).\n"
                    )
        else:
            content += "Lỗi trong lúc thêm thông tin khách hàng, thông báo khách vui lòng thử lại."
        
        update["messages"] = [
            ToolMessage 
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]

        return Command(
            update=update,
        )

    except Exception as e:
        raise Exception(e)