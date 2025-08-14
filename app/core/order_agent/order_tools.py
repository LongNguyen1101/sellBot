from langchain_core.tools import tool, InjectedToolCallId
from app.core.utils.graph_function import graph_function
from app.core.utils.graph_function import GraphFunction
from app.core.model import llm_tools
from app.core.order_agent.order_prompts import choose_order_prompt
from app.core.state import SellState
from typing import Annotated, Any, Optional, Tuple, List
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.utils.helper_function import return_order
from datetime import date
from app.core.utils.class_parser import AgentToolResponse, OrderChosen, SplitRequestOutput, SubQuery
from app.models.normal_models import Order
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.log.logger_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)

def _check_customer(
    chat_id: int, 
    graph_function: GraphFunction,
    public_crud: PublicCRUD
) -> dict[str, Any]:
    update = {}
    customer = graph_function.get_customer_by_chat_id(
        chat_id, 
        public_crud=public_crud,
        parse_object=False
    )
    
    if customer:
        logger.info(
            ">>>> Tìm thấy thông tin của khách:",
            f"Tên: {customer["name"]}. "
            f"Số điện thoại: {customer["phone_number"]}. "
            f"Địa chỉ: {customer["address"]}. "
            f"ID khách: {customer["customer_id"]}."
        )
        
        update.update({
            "name": customer["name"],
            "phone_number":customer["phone_number"],
            "address":customer["address"],
            "customer_id":customer["customer_id"]
        })
        
    return update

def _extract_order(order_info: dict, 
                   order_items: List[dict]
) -> dict:
    if not order_info:
        return None
    
    order_info["created_at"] = order_info["created_at"].strftime('%d-%m-%Y')
    order_info["updated_at"] = order_info["updated_at"].strftime('%d-%m-%Y')
    order_info["order_items"] = order_items
    
    return order_info

@tool
def create_order_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to create order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            
            update = {}
            tool_response: AgentToolResponse = {}
            
            customer_id = state["customer_id"]
            receiver_name = state["name"]
            receiver_phone_number = state["phone_number"]
            receiver_address = state["address"]
            shipping_fee = 50000
            
            if not receiver_phone_number or not receiver_name or not receiver_address:
                logger.info("Không đủ thông tin của người nhận")
                tool_response = {
                        "status": "incomplete_info",
                        "content": (
                            "Không có thông tin tên người nhận và địa chỉ "
                            "người nhận, hỏi khách hàng cung cấp thông tin.\n"
                        )
                    }
            else:
                logger.info("Đủ thông tin của người nhận")
                cart_items = state["cart"].copy()
                cart_items.pop("place_holder", None)
                
                if cart_items:
                    logger.info(f"Thông tin giỏ hàng: {cart_items}")

                    new_order_id = graph_function.create_order(
                        public_crud=public_crud,
                        customer_id=customer_id,
                        receiver_name=receiver_name,
                        receiver_phone_number=receiver_phone_number,
                        receiver_address=receiver_address,
                        shipping_fee=shipping_fee
                    )
                    
                    created_order_items, updated_order = graph_function.add_cart_item_to_order(
                        cart_items=cart_items, 
                        order_id=new_order_id,
                        public_crud=public_crud,
                        parse_object=False
                    )

                    if not created_order_items:
                        logger.error("Lỗi không thể thêm các sản phẩm vào đơn hàng")
                        tool_response = {
                            "status": "error",
                            "content": "Lỗi không thể thêm các sản phẩm vào đơn hàng, vui lòng thử lại"
                        }
                    else:
                        logger.info("Thêm các sản phẩm vào đơn hàng thành công")
                        order_detail = return_order(
                            order_info=updated_order, 
                            order_items=created_order_items, 
                            order_id=new_order_id
                        )

                        tool_response = {
                            "status": "finish",
                            "content": (
                                "Tạo đơn hàng thành công.\n"
                                "Trả về đơn hàng y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
                                f"{order_detail}\n"
                                "Lưu ý không được bỏ bớt thông tin, liệt kê chi tiết cho khách.\n"
                                "Nói khách đơn hàng sẽ được vận chuyển trong 3-5 ngày, khách để ý điện thoại "
                                "để nhân viên giao hàng gọi.\n"
                            )
                        }

                        # Save to state
                        update["orders"] = [_extract_order(
                            order_info=updated_order,
                            order_items=created_order_items
                        )]
                        
                        # Delete cart
                        update["cart"] = {"place_holder": "None"}
                else:
                    tool_response = {
                        "status": "incomplete_info",
                        "content": (
                            "Khách chưa chọn sản phẩm nào.\n"
                            "Dựa vào lịch sử để hỏi khách có muốn chọn sản phẩm đã xem không, "
                            "nếu không có thông tin thì hỏi khách muốn mua gì.\n"
                        )
                    }
            
            update["messages"] = [
                ToolMessage
                (
                    content=tool_response["content"],
                    tool_call_id=tool_call_id
                )
            ]
            update["status"] = tool_response["status"]
            
            return Command(update=update)
            
    except Exception as e:
        raise 
    
    
@tool
def get_all_editable_orders_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to get order based on request of customer"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            
            update = {}
            tool_response: AgentToolResponse = {}
            
            customer_id = state["customer_id"]
            
            if not customer_id:
                logger.info("Không thấy customer_id -> tìm customer")
                customer = graph_function.get_customer_by_chat_id(
                    state["chat_id"], 
                    public_crud=public_crud,
                    parse_object=False
                )
                
                if customer:
                    logger.info(f"Tìm thấy customer có id: {customer["customer_id"]}")
                    customer_id = customer["customer_id"]
                    
                    update["name"] = customer["name"]
                    update["address"] = customer["address"]
                    update["phone_number"] = customer["phone_number"]
                    update["customer_id"] = customer["customer_id"]
                else:
                    logger.info("Khách chưa đăng ký trên hệ thống")
                    tool_response = {
                        "status": "asking",
                        "content": (
                            "Khách hàng chưa đăng ký trên hệ thống nên sẽ không có thông tin "
                            "các đơn hàng, hỏi khách số điện thoại để đăng ký vào hệ thống, "
                            "ngoài ra nếu tiện khách có thể cho tên và địa chỉ.\b"
                        )
                    }
            
            if customer_id:
                logger.info("Khách có id -> thực hiện lấy các orders")
                all_orders = graph_function.get_editable_orders(
                    customer_id, 
                    public_crud=public_crud,
                )

                if all_orders:
                    logger.info(f"Lấy các orders của khách thành công: {all_orders}")
                    update["orders"] = all_orders
                    
                    messages = [
                        {'role': 'system', 'content': choose_order_prompt()},
                        {'role': 'human', 'content': (
                            f"Danh sách các đơn đặt hàng của khách: {all_orders}\n"
                            f"Yêu cầu của khách: {state['current_task']}\n"
                            f"Ngày hôm nay: {date.today().strftime('%d-%m-%Y')}"
                        )}
                    ]
                    
                    found_order = llm_tools.with_structured_output(OrderChosen).invoke(messages)
                    
                    if not found_order["order_id"]:
                        logger.info(f"Không thể xác định được order mà khách muốn")
                        tool_response = {
                            "status": "incomplete_info",
                            "content": (
                                "Không xác định được đơn hàng khách muốn.\n"
                                "Trả về tất cả các đơn hàng đã đặt của khách, "
                                "phải tóm gọn nhưng vẫn giữ lại thông tin quan trọng "
                                "là order_id, tên các sản phẩm trong giỏ hàng, thông tin "
                                "người nhận, thời gian đặt, tiền ship và tổng tiền (có tính ship).\n"
                                "Đây là thông tin các đơn hàng:\n"
                                f"{all_orders}\n"
                            )
                        }
                    else:
                        get_order = {}
                        for order in all_orders:
                            if order["order_id"] == found_order["order_id"]:
                                get_order = order
                                break
                                
                        logger.info(f"Xác định được order mà khách muốn: {get_order}")
                                
                        tool_response = {
                            "status": "asking",
                            "content": (
                                "Đây là thông tin đơn hàng theo yêu cầu của khách.\n"
                                f"{get_order}\n"
                                "Hiện các đơn hàng dưới dạng liệt kê, tóm tắt các đơn hàng nhưng phải có thông "
                                "tin của các sản phẩm trong đơn đó để khách nắm được.\n"
                                "Và hãy dịch các thông tin từ tiếng anh sang tiếng Việt để khách dễ hiểu.\n"
                                "Hãy hỏi khách có đúng đơn này không và có muốn thực hiện yêu cầu của khách không.\n"
                                "Lưu ý product_id là mã sản phẩm, sku là mã phân loại sản phẩm.\n"
                            )
                        }
                            
                else:
                    logger.info("Khách không có đơn hàng nào")
                    tool_response = {
                        "status": "asking",
                        "content": (
                            "Hiện tại khách hàng chưa có đơn hàng nào đã được "
                            "giao cho khách hoặc khách chưa đặt đơn hàng nào.\n"
                        )
                    }

            update["messages"] = [
                ToolMessage
                (
                    content=tool_response["content"],
                    tool_call_id=tool_call_id
                )
            ]
            update["status"] = tool_response["status"]
            
            return Command(update=update)
        
    except Exception as e:
        raise
    
@tool
def remove_item_from_order_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to remove product out of specify order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            tool_response: AgentToolResponse = {}
            update = {}
            orders = state["orders"]
            
            if not orders:
                logger.info("Không thấy đơn hàng trong orders state -> tìm")
                update["tasks"] = [
                    {
                        "id": 1,
                        "agent": "order_agent",
                        "sub_query": "Lấy tất cả các đơn hàng để khách chọn."
                    }
                ]
            else:
                logger.info("Thấy đơn hàng trong orders state")
                messages = [
                    {'role': 'system', 'content': choose_order_prompt()},
                    {'role': 'human', 'content': (
                        f"Danh sách các đơn đặt hàng của khách: {orders}\n"
                        f"Yêu cầu của khách: {state['current_task']}\n"
                        f"Ngày hôm nay: {date.today().strftime('%d-%m-%Y')}"
                    )}
                ]
                
                found_order = llm_tools.with_structured_output(OrderChosen).invoke(messages)

                if not found_order["order_id"]:
                    logger.info(f"Không thể xác định được order mà khách muốn")
                    tool_response = {
                        "status": "incomplete_info",
                        "content": (
                            "Không xác định được đơn hàng khách muốn.\n"
                            "Hỏi lại khách để xác định.\n"
                        )
                    }
                else:
                    get_order = {}
                    for order in orders:
                        if order["order_id"] == found_order["order_id"]:
                            get_order = order
                            break
                    
                    logger.info(f"Xác định được order mà khách muốn: {get_order}")
                                
                    if not found_order["item_id"]:
                        logger.info(f"Không thể xác định được item_id mà khách muốn")
                        tool_response = {
                            "status": "incomplete_info",
                            "content": (
                                "Không xác định được sản phẩm mà khách muốn thay đổi.\n"
                                "Hỏi lại khách để xác định.\n"
                            )
                        }
                        update["orders"] = get_order
                    else:
                        logger.info(f"Xác định được item_id mà khách muốn -> xoá")
                        delete_item = graph_function.delete_item(
                            item_id=found_order["item_id"], 
                            public_crud=public_crud
                        )
                        logger.info(f"Tiến hành xoá sản phẩm: {delete_item}")

                        if delete_item:
                            logger.info("Xoá sản phẩm thành công")
                            tool_response["content"] = "Đã xoá thành công sản phẩm <bạn hãy điền vào> khỏi đơn hàng của khách.\n"

                            order_info = graph_function.get_order_with_items(
                                order_id=found_order["order_id"],
                                public_crud=public_crud
                            )
                            
                            if order_info["order_total"] == 0:
                                logger.info("Phát hiện sau khi xoá thì order không có order_item nào -> xoá order")
                                delete_order = graph_function.delete_order(
                                    order_id=found_order["order_id"],
                                    public_crud=public_crud
                                )
                                
                                if delete_order:
                                    logger.info("Xoá order thành công")
                                    tool_response["status"] = "finish"
                                    tool_response["content"] += (
                                        "Vì đơn hàng chỉ có 1 sản phẩm nên khi xoá sản phẩm thì tự động "
                                        "huỷ đơn hàng của khách.\n"
                                        "Huỷ đơn hàng của khách thành công.\n"
                                    )
                                else:
                                    logger.erro("Xoá order không thành công")
                                    tool_response["status"] = "error"
                                    tool_response["content"] += (
                                        "Vì đơn hàng chỉ có 1 sản phẩm nên khi xoá sản phẩm thì tự động "
                                        "huỷ đơn hàng của khách.\n"
                                        "Nhưng đã sảy ra lỗi trong lúc huỷ đơn, xin lỗi khách "
                                        "và cửa hàng tìm cách và thông báo lại cho khách sau.\n"
                                    )
                            else:
                                logger.info("Sau khi xoá thì order vẫn còn order_items")
                                order_detail = return_order(
                                    order_info=order_info, 
                                    order_items=order_info["order_items"], 
                                    order_id=found_order["order_id"]
                                )

                                tool_response["status"] = "finish"
                                tool_response["content"] += (
                                    "Trả về đơn hàng sau khi cập nhật y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
                                    f"{order_detail}"
                                )

                                # Save to state
                                update["orders"] = [order_info]
                        else:
                            logger.error("Xoá sản phẩm không thành công")
                            tool_response = {
                                "status": "error",
                                "content": (
                                    "Đã có lỗi trong lúc xoá sản phẩm <bạn hãy điền vào>, "
                                    "nói khách vui lòng thử lại.\n"
                                )
                            }
            
            update["messages"] = [
                ToolMessage
                (
                    content=tool_response["content"],
                    tool_call_id=tool_call_id
                )
            ]
            update["status"] = tool_response["status"]
            
            return Command(update=update)
        
    except Exception as e:
        raise

@tool
def update_item_quantity_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to update quantity of specify product in order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            tool_response: AgentToolResponse = {}
            update = {}
            orders = state["orders"]
            
            if not orders:
                logger.info("Không thấy đơn hàng trong orders state -> tìm")
                update["tasks"] = [
                    {
                        "id": 1,
                        "agent": "order_agent",
                        "sub_query": "Lấy tất cả các đơn hàng để khách chọn."
                    }
                ]
            else:
                logger.info("Thấy đơn hàng trong orders state")
                messages = [
                    {'role': 'system', 'content': choose_order_prompt()},
                    {'role': 'human', 'content': (
                        f"Danh sách các đơn đặt hàng của khách: {orders}\n"
                        f"Yêu cầu của khách: {state['current_task']}\n"
                        f"Ngày hôm nay: {date.today().strftime('%d-%m-%Y')}"
                    )}
                ]
                
                found_order = llm_tools.with_structured_output(OrderChosen).invoke(messages)
                    
                if not found_order["order_id"]:
                    logger.info(f"Không thể xác định được order mà khách muốn")
                    tool_response = {
                        "status": "incomplete_info",
                        "content": (
                            "Không xác định được đơn hàng khách muốn.\n"
                            "Hỏi lại khách để xác định.\n"
                        )
                    }
                else:
                    get_order = {}
                    for order in orders:
                        if order["order_id"] == found_order["order_id"]:
                            get_order = order
                            break
                    
                    logger.info(f"Xác định được order mà khách muốn: {get_order}")
                                
                    if not found_order["item_id"]:
                        logger.info(f"Không thể xác định được item_id mà khách muốn")
                        
                        tool_response = {
                            "status": "incomplete_info",
                            "content": (
                                "Không xác định được sản phẩm mà khách muốn thay đổi.\n"
                                "Đây là đơn hàng mà khách muốn thay đổi:\n"
                                f"{get_order}\n"
                                "Hỏi lại khách để xác định được sản phẩm trong đơn đó.\n"
                            )
                        }
                        update["orders"] = get_order
                    else:
                        logger.info(f"Xác định được item_id mà khách muốn")
                        
                        if not found_order["quantity"]:
                            logger.info(f"Không thể xác định được số lượng mà khách muốn cập nhật")
                            tool_response = {
                                "status": "incomplete_info",
                                "content": (
                                    "Không xác định được số lượng sản phẩm khách "
                                    "muốn cập nhật, hỏi lại khách.\n"
                                )
                            }
                            update["orders"] = get_order
                        else:
                            logger.info(f"Xác định được số lượng mà khách muốn -> cập nhật")
                            
                            new_item = graph_function.update_order_item_quantity(
                                item_id=found_order["item_id"],
                                new_quantity=found_order["quantity"],
                                public_crud=public_crud,
                                parse_object=False
                            )

                            if new_item:
                                logger.info(f"Cập nhật thành công")
                                order_info = graph_function.get_order_with_items(
                                    order_id=found_order["order_id"],
                                    public_crud=public_crud
                                )
                                
                                if order_info["order_total"] == 0:
                                    logger.info("Phát hiện sau khi xoá thì order không có order_item nào -> xoá order")
                                    delete_order = graph_function.delete_order(
                                        order_id=found_order["order_id"],
                                        public_crud=public_crud
                                    )

                                    if delete_order:
                                        logger.info("Xoá order thành công")
                                        tool_response["status"] = "finish"
                                        tool_response["content"] += (
                                            "Vì đơn hàng chỉ có 1 sản phẩm nên khi xoá sản phẩm thì tự động "
                                            "huỷ đơn hàng của khách.\n"
                                            "Huỷ đơn hàng của khách thành công.\n"
                                        )
                                    else:
                                        logger.erro("Xoá order không thành công")
                                        tool_response["status"] = "error"
                                        tool_response["content"] += (
                                            "Vì đơn hàng chỉ có 1 sản phẩm nên khi xoá sản phẩm thì tự động "
                                            "huỷ đơn hàng của khách.\n"
                                            "Nhưng đã sảy ra lỗi trong lúc huỷ đơn, xin lỗi khách "
                                            "và cửa hàng tìm cách và thông báo lại cho khách sau.\n"
                                        )
                                else:
                                    logger.info("Sau khi xoá thì order vẫn còn order_items")
                                    order_detail = return_order(
                                        order_info=order_info, 
                                        order_items=order_info["order_items"], 
                                        order_id=found_order["order_id"]
                                    )

                                    tool_response = {
                                        "status": "finish",
                                        "content": (
                                            "Đã thay đổi thành công sản phẩm <bạn hãy điền vào> "
                                            "từ <bạn hãy điền vào> cái thành <bạn hãy điền vào> cái.\n"
                                            "Trả về đơn hàng sau khi cập nhật y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
                                            f"{order_detail}"
                                        )
                                    }

                                    # Save to state
                                    update["orders"] = [order_info]

                            else:
                                logger.error("Cập nhật sản phẩm không thành công")
                                tool_response = {
                                    "status": "error",
                                    "content": (
                                        "Đã có lỗi trong lúc cập nhật đơn hàng có mã là "
                                        "<bạn hãy điền vào>, nói khách vui lòng thử lại.\n"
                                    )
                                }
            
            update["messages"] = [
                ToolMessage
                (
                    content=tool_response["content"],
                    tool_call_id=tool_call_id
                )
            ]
            update["status"] = tool_response["status"]
            
            return Command(update=update)
        
    except Exception as e:
        raise Exception(e)

@tool
def update_receiver_info_in_order_tool(
    name: Annotated[Optional[str], "Receiver name, None if human not mention"],
    phone_number: Annotated[Optional[str], "Receiver phone number, None if human not mention"],
    address: Annotated[Optional[str], "Receiver address, None if human not mention"],
    order_id: Annotated[Optional[int], "ID of order"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to update name or phone number or address of receiver in order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            tool_response: AgentToolResponse = {}
            update = {}
            customer_id = state["customer_id"]
            orders = state["orders"]
            
            if not orders:
                logger.info("Không thấy đơn hàng trong orders state -> tìm")
                update["tasks"] = [
                    {
                        "id": 1,
                        "agent": "order_agent",
                        "sub_query": "Lấy tất cả các đơn hàng để khách chọn."
                    }
                ]
            else:
                logger.info("Thấy đơn hàng trong orders state")
                if not customer_id:
                    logger.info("Không thấy thông tin khách -> tìm")
                    customer = _check_customer(
                        chat_id=state["chat_id"],
                        graph_function=graph_function,
                        public_crud=public_crud
                    )
                    
                    if customer.get("customer_id", None) is not None:
                        logger.info(f"Tìm thấy thông tin khách hàng trong hệ thống: {customer["customer_id"]}")
                        update.update(customer)
                        
                        tool_response = {
                            "status": "finish",
                            "content": (
                                "Tìm thấy thông tin khách hàng trong hệ thống.\n"
                            )
                        }
                        
                        update["tasks"] = [
                            {
                                "id": 1,
                                "agent": "order_agent",
                                "sub_query": "Lấy tất cả các đơn hàng để khách chọn."
                            }
                        ]
                    else:
                        logger.info(f"Không tìm thấy thông tin khách hàng trong hệ thống")
                        tool_response = {
                            "status": "finish",
                            "content": (
                                "Không có thông tin khách hàng trong hệ thống.\n"
                                "Thông báo với khách có lẽ khách đã nhầm.\n"
                                "Xin khách số điện thoại để tiện hỗ trợ, và "
                                "nếu có thể thì xin cả tên và địa chỉ của khách.\n"
                            )
                        }
                else:
                    logger.info("Tìm thấy thông tin khách trong hệ thống")
                    
                    messages = [
                        {'role': 'system', 'content': choose_order_prompt()},
                        {'role': 'human', 'content': (
                            f"Danh sách các đơn đặt hàng của khách: {orders}\n"
                            f"Yêu cầu của khách: {state['current_task']}\n"
                            f"Ngày hôm nay: {date.today().strftime('%d-%m-%Y')}"
                        )}
                    ]
                
                    found_order = llm_tools.with_structured_output(OrderChosen).invoke(messages)
                    
                    if found_order.get("order_id", None) is None:
                        logger.info(f"Không thể xác định được order mà khách muốn")
                        tool_response = {
                            "status": "incomplete_info",
                            "content": (
                                "Không xác định được đơn hàng khách muốn.\n"
                                "Hỏi lại khách để xác định.\n"
                            )
                        }
                    else:
                        get_order = {}
                        for order in orders:
                            if order["order_id"] == found_order["order_id"]:
                                get_order = order
                                break
                        
                        logger.info(f"Xác định được order mà khách muốn: {get_order}")
                                
                        if name:
                            get_order["receiver_name"] = name
                        if phone_number:
                            get_order["receiver_phone_number"] = phone_number
                        if address:
                            get_order["receiver_address"] = address
                            
                        logger.info(
                            "Các thông tin cập nhật: "
                            f"Tên: {name} | "
                            f"Số điện thoại: {phone_number} | "
                            f"Địa chỉ: {address}"
                        )

                        new_order = graph_function.update_order(
                            public_crud=public_crud,
                            order_id=found_order["order_id"],
                            receiver_name=name,
                            receiver_address=address,
                            receiver_phone_number=phone_number,
                            parse_object=False
                        )

                        if new_order:
                            logger.info("Cập nhật thông tin người nhận thành công")
                            get_order = return_order(
                                order_info=get_order,
                                order_items=get_order["order_items"],
                                order_id=found_order["order_id"]
                            )
                            
                            tool_response = {
                                "status": "finish",
                                "content": (
                                    "Đã cập nhật đơn hàng thành công cho khách.\n"
                                    "Trả lại đơn hàng sau khi chỉnh sửa cho khách, không được tóm gọn:\n"
                                    f"{get_order}\n"
                                    "Sau đó hỏi khách có cần hỗ trợ gì nữa không.\n"
                                )
                            }
                        else:
                            logger.error("Cập nhật thông tin người nhận không thành công")
                            tool_response = {
                                "status": "error",
                                "content": (
                                    "Đã sảy ra lỗi trong quá trình cập nhật, xin khách vui lòng thử lại."
                                )
                            }
                            
            update["messages"] = [
                ToolMessage
                (
                    content=tool_response["content"],
                    tool_call_id=tool_call_id
                )
            ]
            update["status"] = tool_response["status"]
            
            return Command(update=update)
            
    except Exception as e:
        raise Exception(e)