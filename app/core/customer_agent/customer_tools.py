from langchain_core.tools import tool, InjectedToolCallId
from app.core.utils.graph_function import graph_function
from app.core.state import SellState
from typing import Annotated, Optional
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from app.core.utils.helper_function import build_update
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.log.logger_config import setup_logging

logger = setup_logging(__name__)

def _handle_update_customer(
    customer_id: int,
    chat_id: int,
    name: Optional[str],
    phone_number: Optional[str],
    address: Optional[str],
    public_crud: PublicCRUD
    
):
    if not customer_id:
        logger.info("Không thấy id khách -> đi tìm hoặc tạo mới")
        customer = graph_function.create_or_update_customer(
            public_crud=public_crud,
            chat_id=chat_id,
            name=name,
            phone_number=phone_number,
            address=address,
            parse_object=False
        )
        
        logger.info("Đã tạo mới hoặc cập nhật khách có sẵn.")
        
    else:
        logger.info("Đã có id khách -> cập nhật")
        customer = graph_function.update_customer(
            public_crud=public_crud,
            customer_id=customer_id,
            name=name,
            phone_number=phone_number,
            address=address,
            parse_object=False
        )
        
        logger.info("Đã cập nhật thông tin khách.")
    
    logger.info(
        f"ID khách: {customer["customer_id"]} | "
        f"Tên: {customer["name"]} | "
        f"SĐT: {customer["phone_number"]} | "
        f"Địa chỉ: {customer["address"]}."
    )
    
    return customer
    
def _handle_cart_available(
    customer: dict,
    tool_call_id: str,
    update_dict: Optional[dict] = None
):
    if all([customer["customer_id"], customer["name"], customer["phone_number"], customer["address"]]):
        logger.info("Khách có có đầy đủ thông tin -> lên đơn")
        tasks = [
            {
                "id": 1,
                "agent": "order_agent",
                "sub_query": "Lên đơn cho khách."
            }
        ]

        return build_update(
            content=(
                "Đã có đầy đủ thông tin, lên đơn cho khách.\n"
                "Không được đề cập đến bất kỳ nhân viên nào, "
                "chỉ được thông báo khách chờ trong giây lát để "
                "lên đơn."
            ),
            status="finish",
            tool_call_id=tool_call_id,
            tasks=tasks,
            **update_dict
        )

    logger.info("Thiếu thông tin khách -> hỏi khách")
    return build_update(
        content=(
            "Thiếu thông tin khách hàng để lên đơn.\n"
            "Đây là các thông tin của khách:\n"
            f"Tên: {customer["name"]}\n"
            f"SĐT: {customer["phone_number"]}\n"
            f"Địa chỉ: {customer["address"]}\n"
            "Xác nhận với khách các thông tin đã có "
            "và hỏi khách các thông tin còn thiếu.\n"
        ),
        status="incomplete_info",
        tool_call_id=tool_call_id,
        **update_dict
    )
    
def _handle_cart_not_available(
    seen_products: list,
    tool_call_id: str,
    update_dict: Optional[dict] = None
):
    if len(seen_products) == 1:
        logger.info("Khách đã xem 1 sản phẩm -> thêm vào giỏ hàng")
        tasks = [
            {
                "id": 1,
                "agent": "cart_agent",
                "sub_query": f"Thêm vào giỏ hàng sản phẩm {seen_products[0]["product_name"]}"
            }
        ]
        return build_update(
            content="Không tạo phản hồi",
            status="finish",
            tool_call_id=tool_call_id,
            tasks=tasks,
            **update_dict
        )
    elif len(seen_products) > 1:
        logger.info("Khách đã xem nhiều sản phẩm -> hỏi khách")
        return build_update(
            content=(
                "Đây là các sản phẩm khách đã xem:\n"
                f"{seen_products}\n"
                "Hỏi khách muốn mua sản phẩm nào.\n"
            ),
            status="finish",
            tool_call_id=tool_call_id,
            **update_dict
        )
        
    logger.info("Khách chưa xem nhiều sản phẩm -> hỏi khách")
    return build_update(
            content=(
                "Dựa vào yêu cầu trước đó của khách để:\n"
                "- Nếu khách có yêu cầu trước đó, hỏi khách có muốn tiếp tục thực hiện không.\n"
                "- Nếu khách không có yêu cầu trước đó, giới thiệu về các mặt hàng cửa "
                "hàng đang bán (đồ điện tử thông minh như camera, cảm biến, đèn led, ...).\n"
            ),
            status="asking",
            tool_call_id=tool_call_id,
        )

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
        logger.info("Đang gọi add_phone_name_address_tool")
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            
            cart = state["cart"]
            customer_id = state["customer_id"]
            
            customer = _handle_update_customer(
                customer_id=customer_id,
                chat_id=state["chat_id"],
                name=name,
                address=address,
                phone_number=phone_number,
                public_crud=public_crud
            )
                
            customer_info = {
                "customer_id": customer["customer_id"],
                "name": customer["name"],
                "phone_number": customer["phone_number"],
                "address": customer["address"]
            }
            logger.info("Thêm tên | số điện thoại | địa chỉ khách thành công", color="green")
            
            if cart and "place_holder" not in cart:
                logger.info("Khách có hàng trong giỏ")
                update = _handle_cart_available(
                    customer=customer,
                    tool_call_id=tool_call_id,
                    update_dict=customer_info
                )
                return Command(update=update)
                
            logger.info("Khách chưa có hàng trong giỏ")
            update = _handle_cart_not_available(
                seen_products=state["seen_products"],
                tool_call_id=tool_call_id,
                update_dict=customer_info
            )
            
            return Command(update=update)
            
    except Exception as e:
        logger.error(f"Lỗi: {e}")
        raise