import json
from langchain_core.tools import tool, InjectedToolCallId
from sqlalchemy import Subquery
from app.core.utils.class_parser import AgentToolResponse, SubQuery
from app.core.utils.graph_function import GraphFunction
from app.core.model import init_model
from app.core.state import SellState
from typing import Annotated, Optional
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage, AIMessage
from app.core.utils.helper_function import get_cart

graph_function = GraphFunction()
llm = init_model()
    
@tool
def add_phone_name_address_tool(
    phone_number: Annotated[Optional[str], "Phone number of customer"],
    name: Annotated[Optional[str], "Name of customer"],
    address: Annotated[Optional[str], "Address of customer"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool when customer give phone number or name or address"""
    try:
        tool_response: AgentToolResponse = {}
        
        chat_id = state["chat_id"]
        cart = state["cart"]
        customer_id = state["customer_id"]
        tasks = state["tasks"]
        
        if not customer_id:
            customer, log = graph_function.create_or_update_customer(
                chat_id=chat_id,
                name=name,
                phone_number=phone_number,
                address=address
            )
        else:
            customer = graph_function.update_customer(
                customer_id=customer_id,
                name=name,
                phone_number=phone_number,
                address=address
            )
                
            log = "Cập nhật thông tin cho khách hàng đã có sẵn."
        
        print(f">>>> {log}\n"
              f"ID khách: {customer.customer_id}\n"
              f"Tên: {customer.name}\n"
              f"SĐT: {customer.phone_number}\n"
              f"Địa chỉ: {customer.address}\n")
            
        update = {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "phone_number": customer.phone_number,
            "address": customer.address
        }
        
        if cart:
            print(">>>> Khách có hàng trong giỏ -> lên đơn")
            if all([customer.customer_id, customer.name, customer.phone_number, customer.address]):
                tasks.append(Subquery(
                    id=tasks[-1]["id"] + 1,
                    sub_query="Lên đơn cho khách."
                ))
                tool_response = {
                    "status": "finish",
                    "content": (
                        "Đã có đầy đủ thông tin, lên đơn cho khách.\n"
                        "Không được đề cập đến bất kỳ nhân viên nào, "
                        "chỉ được thông báo khách chờ trong giây lát để "
                        "lên đơn."
                    )
                }
            else:
                tool_response = {
                    "status": "incomplete_info",
                    "content": (
                        "Thiếu thông tin khách hàng để lên đơn.\n"
                        "Đây là các thông tin của khách:\n"
                        f"Tên: {customer.name}\n"
                        f"SĐT: {customer.phone_number}\n"
                        f"Địa chỉ: {customer.address}\n"
                        "Xác nhận với khách các thông tin đã có "
                        "và hỏi khách các thông tin còn thiếu.\n"
                    )
                }
        else:
            print(">>>> Khách chưa có hàng trong giỏ -> hỏi khách")
            seen_products = state["seen_products"]
            if seen_products:
                tool_response = {
                    "status": "asking",
                    "content": (
                        "Đây là các sản phẩm khách vừa xem:\n"
                        f"{seen_products}\n\n"
                        "Hỏi khách muốn mua sản phẩm nào"
                    )
                }
            else:
                tool_response = {
                    "status": "asking",
                    "content":(
                        "Dựa vào yêu cầu trước đó của khách để:\n"
                        "- Nếu khách có yêu cầu trước đó, hỏi khách có muốn tiếp tục thực hiện không.\n"
                        "- Nếu khách không có yêu cầu trước đó, giới thiệu về các mặt hàng cửa "
                        "hàng đang bán (đồ điện tử thông minh như camera, cảm biến, đèn led, ...).\n"
                    )
                }
        
        update.update({
            "messages": [
                ToolMessage 
                (
                    content=tool_response["content"],
                    tool_call_id=tool_call_id
                )
            ],
            "tasks": tasks,
            "status": tool_response["status"]
        })

        return Command(update=update)
        
    except Exception as e:
        raise Exception(e)