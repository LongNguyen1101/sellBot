from langchain_core.tools import tool, InjectedToolCallId
from app.core.user_agent.user_nodes import _get_or_create_customer
from app.core.utils.class_parser import AgentToolResponse, SplitRequestOutput, SubQuery
from app.core.utils.graph_function import graph_function
from app.core.state import SellState
from typing import Annotated, Optional
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.log.logger_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)


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
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            tool_response: AgentToolResponse = {}
            
            chat_id = state["chat_id"]
            cart = state["cart"]
            customer_id = state["customer_id"]
            tasks = state["tasks"]
            
            if not customer_id:
                customer = graph_function.create_or_update_customer(
                    public_crud=public_crud,
                    chat_id=chat_id,
                    name=name,
                    phone_number=phone_number,
                    address=address,
                    parse_object=False
                )
                
                log = "Đã tạo mới hoặc cập nhật khách có sẵn."
                
            else:
                customer = graph_function.update_customer(
                    public_crud=public_crud,
                    customer_id=customer_id,
                    name=name,
                    phone_number=phone_number,
                    address=address,
                    parse_object=False
                )
                    
                log = "Cập nhật thông tin cho khách hàng đã có sẵn."
            
            logger.info(
                f">>>> {log}\n"
                f"ID khách: {customer["customer_id"]}\n"
                f"Tên: {customer["name"]}\n"
                f"SĐT: {customer["phone_number"]}\n"
                f"Địa chỉ: {customer["address"]}\n"
            )
                
            update = {
                "customer_id": customer["customer_id"],
                "name": customer["name"],
                "phone_number": customer["phone_number"],
                "address": customer["address"]
            }
            
            if cart and "place_holder" not in cart:
                logger.info(">>>> Khách có hàng trong giỏ")
                if all([customer["customer_id"], customer["name"], customer["phone_number"], customer["address"]]):
                    logger.info(">>>> Khách có có đầy đủ thông tin -> lên đơn")
                    tasks = [
                        {
                            "id": 1,
                            "agent": "order_agent",
                            "sub_query": "Lên đơn cho khách."
                        }
                    ]
                    
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
                    logger.info(">>>> Thiếu thông tin khách -> hỏi khách")
                    tool_response = {
                        "status": "incomplete_info",
                        "content": (
                            "Thiếu thông tin khách hàng để lên đơn.\n"
                            "Đây là các thông tin của khách:\n"
                            f"Tên: {customer["name"]}\n"
                            f"SĐT: {customer["phone_number"]}\n"
                            f"Địa chỉ: {customer["address"]}\n"
                            "Xác nhận với khách các thông tin đã có "
                            "và hỏi khách các thông tin còn thiếu.\n"
                        )
                    }
            else:
                logger.info("Khách chưa có hàng trong giỏ")
                seen_products = state["seen_products"]
                
                if len(seen_products) == 1:
                    logger.info("Khách đã xem 1 sản phẩm -> thêm vào giỏ hàng")
                    tasks = [
                        {
                            "id": 1,
                            "agent": "cart_agent",
                            "sub_query": f"Thêm vào giỏ hàng sản phẩm {seen_products[0]["product_name"]}"
                        }
                    ]
                elif len(seen_products) > 1:
                    logger.info("Khách đã xem nhiều sản phẩm -> hỏi khách")
                    tool_response = {
                        "status": "finish",
                        "content": (
                            "Đây là các sản phẩm khách đã xem:\n"
                            f"{seen_products}\n"
                            "Hỏi khách muốn mua sản phẩm nào.\n"
                        )
                    }
                else:
                    logger.info("Khách chưa xem nhiều sản phẩm -> hỏi khách")
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