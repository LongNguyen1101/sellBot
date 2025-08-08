from asyncio import tasks
import json
from langchain_core.tools import tool, InjectedToolCallId
from sqlalchemy import Subquery
from app.core.utils.graph_function import GraphFunction
from app.core.model import llm
from app.core.order_agent.order_prompts import choose_order_prompt
from app.core.state import SellState
from typing import Annotated, Optional, Tuple, List
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.utils.helper_function import return_order
from datetime import date
from app.core.utils.class_parser import AgentToolResponse, UpdateOrder, UpdateReceiverInfo
from app.models.normal_models import Order
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD



def _check_customer(
    chat_id: int, 
    tool_response: ToolMessage,
    graph_function: GraphFunction,
    public_crud: PublicCRUD
) -> Tuple[ToolMessage, dict]:
    update = {}
    customer = graph_function.get_customer_by_chat_id(chat_id, public_crud=public_crud)
    
    if customer:
        log = (
            ">>>> Tìm thấy thông tin của khách:\n",
            f"Tên: {customer.name}\n"
            f"Số điện thoại: {customer.phone_number}\n"
            f"Địa chỉ: {customer.address}\n"
            f"ID khách: {customer.customer_id}.\n"
        )
        
        print(log)
        update.update({
            "name": customer.name,
            "phone_number":customer.phone_number,
            "address":customer.address,
            "customer_id":customer.customer_id
        })
        
        tool_response["content"] += (
            "Đã tìm thấy thông tin khách hàng.\n"
        )
    else:
        tool_response["content"] += (
            "Không có thông tin khách hàng.\n"
        )
        
    return tool_response, update

def _extract_order(order_info: Optional[Order], 
                   order_items: List[dict]
) -> dict:
    if not order_info:
        return None
    order = {
        k: v for k, v in order_info.__dict__.items()
        if not k.startswith("_")
    }
    order["created_at"] = order["created_at"].strftime('%d-%m-%Y')
    order["updated_at"] = order["updated_at"].strftime('%d-%m-%Y')
    order["items"] = order_items
    
    return order

def _map_orders(all_orders: List[Order], graph_function: GraphFunction, public_crud: PublicCRUD) -> list:
    orders = []
    for order in all_orders:
        data = {
            k: v for k, v in order.__dict__.items()
            if not k.startswith("_")
        }
        
        items = graph_function.get_order_items_detail(data["order_id"], public_crud=public_crud)
        
        data["items"] = items
        data["created_at"] = data["created_at"].strftime('%d-%m-%Y')
        data["updated_at"] = data["updated_at"].strftime('%d-%m-%Y')
        
        orders.append(data)
    return orders
    
@tool
def create_order_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to create order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            graph_function = GraphFunction()
            update = {}
            tool_response: AgentToolResponse = {}
            
            customer_id = state["customer_id"]
            receiver_name = state["name"]
            receiver_phone_number = state["phone_number"]
            receiver_address = state["address"]
            shipping_fee = 50000
            
            if not receiver_phone_number or not receiver_name or not receiver_address:
                tool_response = {
                        "status": "incomplete_info",
                        "content": (
                            "Không có thông tin tên người nhận và địa chỉ "
                            "người nhận, hỏi khách hàng cung cấp thông tin.\n"
                        )
                    }
            else:
                cart_items = state["cart"].copy()
                cart_items.pop("place_holder", None)
                if cart_items:
                    print(f">>>> Thông tin giỏ hàng: {cart_items}")

                    new_order = graph_function.create_order(
                        public_crud=public_crud,
                        customer_id=customer_id,
                        receiver_name=receiver_name,
                        receiver_phone_number=receiver_phone_number,
                        receiver_address=receiver_address,
                        shipping_fee=shipping_fee
                    )
                    created_order_items = graph_function.add_cart_item_to_order(
                        cart_items, 
                        new_order.order_id, 
                        public_crud=public_crud
                    )

                    if created_order_items is None:
                        tool_response = {
                            "status": "error",
                            "content": "Lỗi không thể thêm các sản phẩm vào đơn hàng, vui lòng thử lại"
                        }
                    else:
                        order_info, order_items = graph_function.get_order_detail(
                            new_order.order_id, 
                            public_crud=public_crud
                        )
                        order_detail = return_order(order_info, order_items, new_order.order_id)

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
                            order_info=order_info,
                            order_items=order_items
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
def get_all_orders_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to get order based on request of customer"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            graph_function = GraphFunction()
            update = {}
            tool_response: AgentToolResponse = {}
            customer_id = state["customer_id"]
            
            if not customer_id:
                customer = graph_function.get_customer_by_chat_id(
                    state["chat_id"], 
                    public_crud=public_crud
                )
                
                if customer:
                    customer_id = customer.customer_id
                    
                    update["name"] = customer.name
                    update["address"] = customer.address
                    update["phone_number"] = customer.phone_number
                    update["customer_id"] = customer.customer_id
                else:
                    tool_response = {
                        "status": "asking",
                        "content": (
                            "Khách hàng chưa đăng ký trên hệ thống nên sẽ không có thông tin "
                            "các đơn hàng, hỏi khách số điện thoại để đăng ký vào hệ thống.\n"
                        )
                    }
            
            if customer_id: 
                all_orders = graph_function.get_editable_orders(
                    customer_id, 
                    public_crud=public_crud
                )[-5:]

                if all_orders:
                    orders = _map_orders(
                        all_orders=all_orders, 
                        graph_function=graph_function, 
                        public_crud=public_crud
                    )
                    update["orders"] = orders
                    
                    messages = [
                        {'role': 'system', 'content': choose_order_prompt()},
                        {'role': 'human', 'content': (
                            f"Danh sách các đơn đặt hàng của khách: {orders}\n"
                            f"Yêu cầu của khách: {state['user_input']}\n"
                            f"Ngày hôm nay: {date.today().strftime('%d-%m-%Y')}"
                        )}
                    ]
                    
                    found_order = llm.invoke(messages).content
                    
                    tool_response = {
                        "status": "asking",
                        "content": (
                            "Đây là thông tin đơn hàng theo yêu cầu của khách.\n"
                            "Hãy tóm gọn nhưng vẫn đủ thông tin và trả về cho khách.\n"
                            "Khi tóm gọn bắt buộc phải có thông tin order_id và item_id của các sản phẩm.\n"
                            "Hãy hỏi khách có đúng đơn này không và có muốn thực hiện yêu cầu của khách không.\n"
                            f"{found_order}"
                        )
                    }
                else:
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
    order_id: Annotated[Optional[int], "ID of order chosen by customer"],
    item_id: Annotated[Optional[int], "ID of the product in order_item"],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to remove product out of specify order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            graph_function = GraphFunction()
            tool_response: AgentToolResponse = {}
            update = {}
            print(f">>>> ID of item: {item_id}")
            
            if not order_id:
                tool_response = {
                    "status": "incomplete_info",
                    "content": (
                        "Không xác định được đơn hàng khách muốn, "
                        "hỏi lại khách để xác định được.\n"
                    )
                }
            else:
                if not item_id:
                    tool_response = {
                        "status": "incomplete_info",
                        "content": (
                            "Không xác định được sản phẩm khách muốn xoá, "
                            "hỏi lại khách để xác định được.\n"
                        )
                    }
                else:
                    delete_item = graph_function.delete_item(item_id=item_id, public_crud=public_crud)
                    
                    if delete_item:
                        tool_response["content"] = "Đã xoá thành công sản phẩm <bạn hãy điền vào> khỏi đơn hàng của khách.\n"
                        
                        order_info, order_items = graph_function.get_order_detail(
                            order_id, 
                            public_crud=public_crud
                        )
                        order_detail = return_order(order_info, order_items, order_id)

                        tool_response["status"] = "finish"
                        tool_response["content"] += (
                            "Trả về đơn hàng sau khi cập nhật y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
                            f"{order_detail}"
                        )

                        # Save to state
                        update["orders"] = [_extract_order(
                            order_info=order_info,
                            order_items=order_items
                        )]
                    else:
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
    order_id: Annotated[Optional[int], "ID of order chosen by customer"],
    item_id: Annotated[Optional[int], "ID of the product in order_item"],
    quantity: Annotated[Optional[int], "New quantity of the product which customer want to update"],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to update quantity of specify product in order"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            graph_function = GraphFunction()
            tool_response: AgentToolResponse = {}
            update = {}
            
            if not order_id:
                tool_response = {
                    "status": "incomplete_info",
                    "content": (
                        "Không xác định được đơn hàng khách muốn, "
                        "hỏi lại khách để xác định được.\n"
                    )
                }
            else:
                if not item_id:
                    tool_response = {
                        "status": "incomplete_info",
                        "content": (
                            "Không xác định được sản phẩm khách muốn cập nhật, "
                            "hỏi lại khách để xác định được.\n"
                        )
                    }
                else:
                    if not quantity:
                        tool_response = {
                            "status": "incomplete_info",
                            "content": (
                                "Không xác định được số lượng sản phẩm khách "
                                "muốn cập nhật, hỏi lại khách.\n"
                            )
                        }
                    else:
                        new_item = graph_function.update_order_item_quantity(
                            item_id=item_id,
                            new_quantity=quantity,
                            public_crud=public_crud
                        )

                        if new_item:
                            
                            order_info, order_items = graph_function.get_order_detail(
                                order_id, 
                                public_crud=public_crud
                            )
                            order_detail = return_order(order_info, order_items, order_id)
                            
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
                            update["orders"] = [_extract_order(
                                order_info=order_info,
                                order_items=order_items
                            )]
                        else:
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
def update_receiver_info_tool(
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
            graph_function = GraphFunction()
            tool_response: AgentToolResponse = {}
            update = {}
            customer_id = state["customer_id"]
            
            if not order_id:
                tool_response = {
                    "status": "incomplete_info",
                    "content": (
                        "Không xác định được mã đơn hàng mà khách chọn.\n"
                        "Xin khách cung cấp thông tin rõ hơn.\n"
                    )
                }
            else:
                if not customer_id:
                    tool_response, new_update = _check_customer(
                        chat_id=state["chat_id"],
                        tool_response=tool_response,
                        graph_function=graph_function,
                        public_crud=public_crud
                    )
                    
                    if new_update.get("customer_id", None) is not None:
                        print(f">>>> Tìm thấy thông tin khách hàng trong hệ thống.")
                        update.update(new_update)
                        
                        tool_response = {
                            "status": "finish",
                            "content": (
                                "Tìm thấy thông tin khách hàng trong hệ thống.\n"
                            )
                        }
                        
                        tasks = state["tasks"]
                        tasks.append(Subquery(
                            id=tasks[-1]["id"] + 1,
                            sub_query="Lấy tất cả đơn hàng cho khách."
                        ))
                        update["tasks"] = tasks
                    else:
                        print(f">>>> Không tìm thấy thông tin khách hàng trong hệ thống.")
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
                    orders = state["orders"]
                    for order in orders:
                        if order["order_id"] == order_id:
                            if name:
                                order["receiver_name"] = name
                            if phone_number:
                                order["receiver_phone_number"] = phone_number
                            if address:
                                order["receiver_address"] = address
                            break

                    new_order = graph_function.update_order(
                        public_crud=public_crud,
                        order_id=order_id,
                        receiver_name=name,
                        receiver_address=address,
                        receiver_phone_number=phone_number
                    )
                    
                    if new_order:
                        tool_response = {
                            "status": "finish",
                            "content": (
                                "Đã cập nhật đơn hàng thành công cho khách."
                            )
                        }
                    else:
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