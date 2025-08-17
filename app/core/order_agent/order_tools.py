from click import Option
from langchain_core.tools import tool, InjectedToolCallId
from app.core.cart_agent.cart_prompts import choose_product_prompt
from app.core.utils.graph_function import graph_function
from app.core.utils.graph_function import GraphFunction
from app.core.model import llm_tools
from app.core.order_agent.order_prompts import choose_order_prompt
from app.core.state import SellState
from typing import Annotated, Any, Optional, Tuple, List
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.utils.helper_function import get_chat_his, return_order
from datetime import date
from app.core.utils.class_parser import AgentToolResponse, OrderChosen, ProductChosen, SplitRequestOutput, SubQuery
from app.models.normal_models import Order
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.log.logger_config import logger

def _extract_order(order_info: dict, 
                   order_items: List[dict]
) -> dict:
    if not order_info:
        return None
    
    order_info["created_at"] = order_info["created_at"].strftime('%d-%m-%Y')
    order_info["updated_at"] = order_info["updated_at"].strftime('%d-%m-%Y')
    order_info["order_items"] = order_items
    
    return order_info
    
def build_update(
    content: str,
    status: str,
    tool_call_id: Any,
    **kwargs
) -> dict:
    return {
        "messages": [
            ToolMessage
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ],
        "status": status,
        **kwargs
    }
    
def _find_order(
    all_orders: List[dict],
    current_task: str
):
    messages = [
        {'role': 'system', 'content': choose_order_prompt()},
        {'role': 'human', 'content': (
            f"Danh sách các đơn đặt hàng của khách: {all_orders}\n"
            f"Yêu cầu của khách: {current_task}\n"
            f"Ngày hôm nay: {date.today().strftime('%d-%m-%Y')}"
        )}
    ]

    return llm_tools.with_structured_output(OrderChosen).invoke(messages)
    
def _check_full_info(
    all_orders: List[dict],
    current_task: str,
    tool_call_id: str,
    need_item_id: bool = True,
    need_quantity: bool = True
):
    found_order = {}
    
    if not all_orders:
        logger.info("Không thấy đơn hàng trong orders state -> tìm")
        add_tasks = [
            {
                "id": 1,
                "agent": "order_agent",
                "sub_query": "Lấy tất cả các đơn hàng để khách chọn."
            }
        ]
        return {}, found_order, build_update(
            content="Không tạo phản hồi",
            status="finish",
            tool_call_id=tool_call_id,
            tasks=add_tasks
        )
        
    logger.info("Thấy đơn hàng trong orders state")
    found_order = _find_order(
        all_orders=all_orders,
        current_task=current_task
    )
    
    if not found_order["order_id"]:
        logger.info(f"Không thể xác định được order mà khách muốn")
        return {}, found_order, build_update(
            content=(
                "Không xác định được đơn hàng khách muốn.\n"
                "Hỏi lại khách để xác định.\n"
            ),
            status="incomplete_info",
            tool_call_id=tool_call_id,
        )
    
    if need_item_id and not found_order["item_id"]:
        logger.info(f"Không thể xác định được item_id mà khách muốn")
        return {}, found_order, build_update(
            content=(
                "Không xác định được sản phẩm mà khách muốn thay đổi.\n"
                "Hỏi lại khách để xác định.\n"
            ),
            status="incomplete_info",
            tool_call_id=tool_call_id,
        )
        
    if need_quantity and not found_order["quantity"]:
            logger.info(f"Không thể xác định được số lượng mà khách muốn cập nhật")
            return {}, found_order, build_update(
                content=(
                    "Không xác định được số lượng sản phẩm khách "
                    "muốn cập nhật, hỏi lại khách.\n"
                ),
                status="incomplete_info",
                tool_call_id=tool_call_id,
            )
    
    get_order = {}
    for order in all_orders:
        if order["order_id"] == found_order["order_id"]:
            get_order = order
            break
    
    logger.info(f"Xác định được order mà khách muốn: {get_order}")

    return get_order, found_order, {}

def _handle_remove_order(
    order_id: int,
    tool_call_id: str,
    public_crud: PublicCRUD
):
    delete_order = graph_function.delete_order(
        order_id=order_id,
        public_crud=public_crud
    )
    
    if delete_order:
        logger.info("Xoá order thành công")
        return build_update(
            content=(
                "Vì đơn hàng chỉ có 1 sản phẩm nên khi xoá sản phẩm thì tự động "
                "huỷ đơn hàng của khách.\n"
                "Huỷ đơn hàng của khách thành công.\n"
            ),
            status="finish",
            tool_call_id=tool_call_id,
        )
        
    logger.error("Xoá order không thành công")
    return build_update(
        content=(
            "Vì đơn hàng chỉ có 1 sản phẩm nên khi xoá sản phẩm thì tự động "
            "huỷ đơn hàng của khách.\n"
            "Nhưng đã sảy ra lỗi trong lúc huỷ đơn, xin lỗi khách "
            "và cửa hàng tìm cách và thông báo lại cho khách sau.\n"
        ),
        status="error",
        tool_call_id=tool_call_id,
    )

def _get_order(
    order_id: int,
    public_crud: PublicCRUD
):
    order_info = graph_function.get_order_with_items(
        order_id=order_id,
        public_crud=public_crud
    )
    
    order_detail = return_order(
        order_info=order_info, 
        order_items=order_info["order_items"], 
        order_id=order_id
    )
    
    return order_info, order_detail
    

def _handle_remove_item(
    get_order: dict, 
    found_order: dict,
    tool_call_id:str,
    public_crud: PublicCRUD
):  
    if len(get_order["order_items"]) == 1:
        logger.info("Đơn hàng chỉ có 1 sản phẩm -> xoá đơn hàng")
        return _handle_remove_order(
            order_id=found_order["order_id"],
            tool_call_id=tool_call_id,
            public_crud=public_crud
        )
    
    logger.info("Đơn hàng có nhiều hơn 1 sản phẩm -> xoá sản phẩm đó")
    
    delete_item = graph_function.delete_item(
        item_id=found_order["item_id"], 
        public_crud=public_crud
    )
    
    if not delete_item:
        logger.error("Xoá sản phẩm không thành công")
        return build_update(
            content=(
                "Đã có lỗi trong lúc xoá sản phẩm <bạn hãy điền vào>, "
                "nói khách vui lòng thử lại.\n"
            ),
            status="error",
            tool_call_id=tool_call_id,
        )
    
    logger.info("Xoá sản phẩm thành công")
    
    order_info, order_detail = _get_order(
        order_id=found_order["order_id"],
        public_crud=public_crud
    )
    
    return build_update(
        content= (
            "Xoá sản phẩm thành công.\n"
            "Trả về đơn hàng sau khi cập nhật y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
            f"{order_detail}"
        ),
        status="finish",
        tool_call_id=tool_call_id,
        orders=[order_info]
    )
    
def _handle_update_item_quantity(
    get_order: dict, 
    found_order: dict,
    tool_call_id: str,
    public_crud: PublicCRUD
):
    if len(get_order["order_items"]) == 1 and found_order["quantity"] == 0:
        logger.info("Đơn hàng chỉ có 1 sản phẩm -> số lượng khách muốn cập nhật là 0 -> xoá đơn hàng")
        return _handle_remove_order(
            order_id=found_order["order_id"],
            public_crud=public_crud
        )
        
    logger.info("Đơn hàng có nhiều hơn 1 sản phẩm -> thoải mái cập nhật")
    
    new_item = graph_function.update_order_item_quantity(
        item_id=found_order["item_id"],
        new_quantity=found_order["quantity"],
        public_crud=public_crud,
        parse_object=False
    )
    
    if not new_item:
        logger.error("Cập nhật sản phẩm không thành công")
        return build_update(
            content=(
                "Đã có lỗi trong lúc cập nhật đơn hàng có mã là "
                "<bạn hãy điền vào>, nói khách vui lòng thử lại.\n"
            ),
            status="error"
        )
        
    logger.info(f"Cập nhật sản phẩm thành công")
    
    order_info, order_detail = _get_order(
        order_id=found_order["order_id"],
        public_crud=public_crud
    )
    
    return build_update(
        content= (
            "Cập sản phẩm thành công.\n"
            "Trả về đơn hàng sau khi cập nhật y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
            f"{order_detail}"
        ),
        status="finish",
        tool_call_id=tool_call_id,
        orders=[order_info]
    )
    

def _handle_update_receiver(
    name: Optional[str],
    phone_number: Optional[str],
    address: Optional[str],
    get_order: dict,
    tool_call_id: str,
    public_crud: PublicCRUD
):
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
        order_id=get_order["order_id"],
        receiver_name=name,
        receiver_address=address,
        receiver_phone_number=phone_number,
        parse_object=False
    )
    
    if not new_order:
        logger.error("Cập nhật thông tin người nhận không thành công")
        return build_update(
            content="Đã sảy ra lỗi trong quá trình cập nhật, xin khách vui lòng thử lại.",
            status="error"
        )
    
    logger.info("Cập nhật thông tin người nhận thành công")
    order_detail = return_order(
        order_info=get_order,
        order_items=get_order["order_items"],
        order_id=get_order["order_id"]
    )
    
    return build_update(
        content= (
            "Cập sản phẩm thành công.\n"
            "Trả về đơn hàng sau khi cập nhật y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
            f"{order_detail}"
        ),
        status="finish",
        orders=[get_order],
        name=name,
        phone_number=phone_number,
        address=address,
        tool_call_id=tool_call_id,
    )


def _add_item_into_order(
    get_order: dict,
    seen_products: List[dict],
    current_task: str,
    messages: list,
    tool_call_id: str,
    public_crud: PublicCRUD
):
    if not seen_products:
        logger.info("Không sản phẩm nào trong seen products")
        add_tasks = [
            {
                "id": 1,
                "agent": "product_agent",
                "sub_query": (
                    "Lấy sản phẩm xuất hiện trong câu sau: "
                    f"({current_task})"
                )
            }
        ]
        return build_update(
            content="Không tạo phản hồi",
            status="finish",
            tool_call_id=tool_call_id,
            tasks=add_tasks
        )
        
    logger.info("Có sản phẩm nào trong seen products") 
    chat_histories = get_chat_his(
        messages=messages,
        start_offset=-5
    )

    messages = [
        {"role": "system", "content": choose_product_prompt()},
        {"role": "human", "content": (
            f"Danh sách các sản phẩm khách đã xem: {seen_products}\n"
            f"Lịch sử chat: {chat_histories}\n"
            f"Yêu cầu hiện tại: {current_task}.\n"
            "Bạn hãy xác định sản phẩm mà khách chọn."
        )}
    ]

    response = llm_tools.with_structured_output(ProductChosen).invoke(messages)
    logger.info(f"Sản phẩm trả về: {response}")
    
    if response.get("product_id") is None:
        logger.info(f"Không xác định được product_id -> tìm sản phẩm trong product_agent")
        add_tasks = [
            {
                "id": 1,
                "agent": "product_agent",
                "sub_query": (
                    "Lấy sản phẩm xuất hiện trong câu sau: "
                    f"({current_task})"
                )
            }
        ]
        
        return build_update(
            content="Không tạo phản hồi",
            status="finish",
            tool_call_id=tool_call_id,
            tasks=add_tasks
        )
        
    logger.info(f"Xác định được sản phẩm: {response} -> thêm sản phẩm vào đơn hàng")
    new_item = graph_function.create_order_item(
        order_id=get_order["order_id"],
        product_id=response["product_id"],
        sku=response["sku"],
        public_crud=public_crud,
        quantity=response["quantity"],
        price=response["price"]
    )
    
    if not new_item:
        logger.error(f"Thêm sản phẩm có mã là {response["product_id"]} vào đơn hàng không thành công")
        return build_update(
            content=(
                f"Không thể thêm sản phẩm có mã là {response["product_id"]} "
                "vào đơn hàng thành công."
            ),
            status="error",
            tool_call_id=tool_call_id,
        )
        
    logger.info(f"Thêm sản phẩm có mã là {response["product_id"]} vào đơn hàng thành công")
    
    order_info, order_detail = _get_order(
        order_id=get_order["order_id"],
        public_crud=public_crud
    )
    
    return build_update(
        content= (
            "Thêm sản phẩm vào đơn hàng thành công.\n"
            "Trả về đơn hàng sau khi cập nhật y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
            f"{order_detail}"
        ),
        status="finish",
        tool_call_id=tool_call_id,
        orders=[order_info]
    )
        
    
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
            
            get_order, found_order, update = _check_full_info(
                all_orders=state["orders"],
                current_task=state["current_task"],
                tool_call_id=tool_call_id,
                need_quantity=False
            )
            
            if not get_order:
                logger.info("Không tìm thấy đơn hàng thoã yêu cầu của khách")
                return Command(update=update)

            update = _handle_remove_item(
                get_order=get_order,
                found_order=found_order,
                public_crud=public_crud,
                tool_call_id=tool_call_id,
            )
            
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
            
            get_order, found_order, update = _check_full_info(
                all_orders=state["orders"],
                current_task=state["current_task"],
                tool_call_id=tool_call_id,
            )
            
            if not get_order:
                logger.info("Không tìm thấy đơn hàng thoã yêu cầu của khách")
                return Command(update=update)

            update = _handle_update_item_quantity(
                get_order=get_order,
                found_order=found_order,
                public_crud=public_crud,
                tool_call_id=tool_call_id,
            )
            
            return Command(update=update)
        
    except Exception as e:
        raise Exception(e)

@tool
def update_receiver_info_in_order_tool(
    name: Annotated[Optional[str], "Receiver name, None if human not mention"],
    phone_number: Annotated[Optional[str], "Receiver phone number, None if human not mention"],
    address: Annotated[Optional[str], "Receiver address, None if human not mention"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to update name or phone number or address of receiver in order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            
            get_order, found_order, update = _check_full_info(
                all_orders=state["orders"],
                current_task=state["current_task"],
                tool_call_id=tool_call_id,
            )
            
            if not get_order:
                logger.info("Không tìm thấy đơn hàng thoã yêu cầu của khách")
                return Command(update=update)
                            
            update = _handle_update_receiver(
                name=name if name else state["name"],
                phone_number=phone_number if phone_number else state["phone_number"],
                address=address if address else state["address"],
                get_order=get_order,
                found_order=found_order,
                public_crud=public_crud,
                tool_call_id=tool_call_id
            )
            
            return Command(update=update)
            
    except Exception as e:
        raise Exception(e)
    
@tool
def remove_order(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to remove | delete order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            
            get_order, found_order, update = _check_full_info(
                all_orders=state["orders"],
                current_task=state["current_task"],
                tool_call_id=tool_call_id,
                need_item_id=False,
                need_quantity=False
            )
            
            if not get_order:
                logger.info("Không tìm thấy đơn hàng thoã yêu cầu của khách")
                return Command(update=update)
                            
            delete_order = graph_function.delete_order(
                order_id=get_order["order_id"],
                public_crud=public_crud
            )
            
            if delete_order:
                logger.info("Xoá order thành công")
                return Command(
                    update=build_update(
                        content=f"Xoá đơn hàng {get_order["order_id"]} thành công",
                        status="finish",
                        tool_call_id=tool_call_id,
                    )
                )
            
            logger.error("Xoá order không thành công")
            return Command(
                update=build_update(
                    content="Có lỗi lúc xoá đơn hàng, cửa hàng sẽ khắc phục sớm nhất có thể",
                    status="error",
                    tool_call_id=tool_call_id,
                )
            )
            
    except Exception as e:
        raise Exception(e)
    

def add_item_into_order_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to add product into specify order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            
            get_order, found_order, update = _check_full_info(
                all_orders=state["orders"],
                current_task=state["current_task"],
                tool_call_id=tool_call_id,
                need_item_id=False,
                need_quantity=False
            )
            
            if not get_order:
                logger.info("Không tìm thấy đơn hàng thoã yêu cầu của khách")
                return Command(update=update)
            
                    
            logger.info(f"Xác định được order mà khách muốn: {get_order}")
            logger.info(f"Lấy danh sách các sản phẩm khách xem để biết được sản phẩm nào để thêm vào đơn hàng")
            
            update = _add_item_into_order(
                get_order=get_order,
                seen_products=state["seen_products"],
                current_task=state["current_task"],
                messages=state["messages"],
                tool_call_id=tool_call_id,
                public_crud=public_crud
            )
            
            return Command(update=update)
        
    except Exception as e:
        raise