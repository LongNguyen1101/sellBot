from langchain_core.tools import tool, InjectedToolCallId
from app.core.graph_function import GraphFunction
from app.core.model import init_model
from app.core.order_agent.order_prompts import choose_order_prompt
from app.core.state import SellState
from typing import Annotated, Optional, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.helper_function import _return_order
from datetime import date

graph_function = GraphFunction()
llm = init_model()

class UpdateOrder(TypedDict):
    command: str
    order_id: int
    
class UpdateReceiverInfo(TypedDict):
    order_id: int
    
@tool
def create_order(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to create order"""
    try:
        update = {}
        customer_id = state["customer_id"]
        receiver_name = state["name"]
        receiver_phone_number = state["phone_number"]
        receiver_address = state["address"]
        shipping_fee = 50000
        payment = "COD"
        
        content = ""
        
        if not receiver_name or not receiver_address:
            content += "Không có thông tin tên người nhận và địa chỉ người nhận, hỏi khách hàng cung cấp thông tin.\n"
        else:
            cart_items = state["cart"]
            cart_items.pop("place_holder", None)
            if cart_items:
                print(f">>>> Thông tin giỏ hàng: {cart_items}")

                new_order = graph_function.get_or_create_order(
                    customer_id,
                    receiver_name=receiver_name,
                    receiver_phone_number=receiver_phone_number,
                    receiver_address=receiver_address,
                    shipping_fee=shipping_fee
                )

                created_order_items, note = graph_function.add_cart_item_to_order(cart_items, new_order.order_id)

                if created_order_items is None:
                    content += "Lỗi không thể thêm các sản phẩm vào đơn hàng, vui lòng thử lại"
                else:
                    order_info, order_items = graph_function.get_order_detail(new_order.order_id)
                    order_detail = _return_order(order_info, order_items, new_order.order_id)

                    content += (
                        "Tạo đơn hàng thành công.\n"
                        "Đây là thông tin về việc gộp đơn hay không:\n"
                        f"{note}.\n"
                        "- Nếu thông tin trên đề cập sản phẩm được thêm mới thì bỏ qua, không thông báo cho khách.\n"
                        "- Nếu thông tin trên đề cập sản phẩm đã có sẵn trong đơn hàng, gộp đơn thì thông báo cho khách.\n"
                        "Trả về đơn hàng y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
                        f"{order_detail}\n"
                        "Lưu ý không được bỏ bớt thông tin, liệt kê chi tiết cho khách.\n"
                        "Nói khách đơn hàng sẽ được vận chuyển trong 3-5 ngày, khách để ý điện thoại "
                        "để nhân viên giao hàng gọi.\n"
                    )

                    # Save to state
                    order = {
                        k: v for k, v in order_info.__dict__.items()
                        if not k.startswith("_")
                    }
                    order["created_at"] = order["created_at"].strftime('%d-%m-%Y')
                    order["updated_at"] = order["updated_at"].strftime('%d-%m-%Y')
                    order["items"] = order_items
                    update["orders"] = [order]
            else:
                content += (
                    "Khách chưa chọn sản phẩm nào.\n"
                    "Dựa vào lịch sử để hỏi khách có muốn chọn sản phẩm đã xem không, "
                    "nêu không có thông tin thì hỏi khách muốn mua gì.\n"
                )
        
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
        raise 
    
    
@tool
def get_all_orders(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to get order based on request of customer"""
    try:
        update = {}
        content = ""
        customer_id = state["customer_id"]
        name = state["name"]
        address = state["address"]
        phone_number = state["phone_number"]
        
        if not customer_id:
            chat_id = state["chat_id"]
            customer = graph_function.get_customer_by_chat_id(chat_id)
            
            if customer:
                name = customer.name
                address = customer.address
                phone_number = customer.phone_number
                customer_id = customer.customer_id
                
                update["name"] = name
                update["phone_number"] = phone_number
                update["address"] = address
                update["customer_id"] = customer_id
            else:
                content += "Khách hàng chưa đăng ký trên hệ thống nên sẽ không có thông tin các đơn hàng, hỏi khách số điện thoại để đăng ký vào hệ thống.\n"
        else:
            all_orders = graph_function.get_editable_orders(customer_id)[-5:]

            if all_orders:
                orders = []
                for order in all_orders:
                    data = {
                        k: v for k, v in order.__dict__.items()
                        if not k.startswith("_")
                    }
                    items = graph_function.get_order_items_detail(data["order_id"])
                    data["items"] = items
                    data["created_at"] = data["created_at"].strftime('%d-%m-%Y')
                    data["updated_at"] = data["updated_at"].strftime('%d-%m-%Y')

                    orders.append(data)

                update["orders"] = orders
                
                messages = [
                    {'role': 'system', 'content': choose_order_prompt()},
                    {'role': 'human', 'content': (
                        f"Danh sách các đơn đặt hàng của khách: {orders}\n"
                        f"Yêu cầu của khách: {state["user_input"]}\n"
                        f"Ngày hôm nay: {date.today().strftime('%d-%m-%Y')}"
                    )}
                ]
                
                found_order = llm.invoke(messages).content
                content += (
                    "Đây là thông tin đơn hàng theo yêu cầu của khách.\n"
                    "Hãy tóm gọn nhưng vẫn đủ thông tin và trả về cho khách.\n"
                    "Khi tóm gọn bắt buộc phải có thông tin order_id và item_id của các sản phẩm.\n"
                    "Hãy hỏi khách có đúng đơn này không và có muốn thực hiện yêu cầu của khách không.\n"
                    f"{found_order}"
                )
            else:
                content += (
                    "Hiện tại khách hàng chưa có đơn hàng nào đã được giao cho khách hoặc khách chưa đặt đơn hàng nào.\n"
                )

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
        raise
    
@tool
def remove_item_from_order(
    order_id: Annotated[Optional[int], "ID of order chosen by customer"],
    item_id: Annotated[Optional[int], "ID of the product in order_item"],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to remove product out of specify order"""
    try:
        update = {}
        content = ""
        print(f">>>> item_id: {item_id}")
        
        if not order_id:
            content += "Không xác định được đơn hàng khách muốn, hỏi lại khách để xác định được.\n"
        else:
            if not item_id:
                content += "Không xác định được sản phẩm khách muốn xoá, hỏi lại khách để xác định được.\n"
            else:
                delete_item = graph_function.delete_item(
                    item_id=item_id
                )
                
                if delete_item:
                    content += "Đã xoá thành công sản phẩm <bạn hãy điền vào> khỏi đơn hàng của khách.\n"
                    
                    order_info, order_items = graph_function.get_order_detail(order_id)
                    order_detail = _return_order(order_info, order_items, order_id)

                    content += (
                        "Trả về đơn hàng sau khi cập nhật y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
                        f"{order_detail}"
                    )

                    # Save to state
                    order = {
                        k: v for k, v in order_info.__dict__.items()
                        if not k.startswith("_")
                    }
                    order["created_at"] = order["created_at"].strftime('%d-%m-%Y')
                    order["updated_at"] = order["updated_at"].strftime('%d-%m-%Y')
                    order["items"] = order_items
                    update["orders"] = [order]
                else:
                    content += "Đã có lỗi trong lúc xoá sản phẩm <bạn hãy điền vào>, nói khách vui lòng thử lại.\n"
        
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
        raise

@tool
def update_item_quantity(
    order_id: Annotated[Optional[int], "ID of order chosen by customer"],
    item_id: Annotated[Optional[int], "ID of the product in order_item"],
    quantity: Annotated[Optional[int], "New quantity of the product which customer want to update"],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to update quantity of specify product in order"""
    try:
        update = {}
        content = ""
        
        if not order_id:
            content += "Không xác định được đơn hàng khách muốn, hỏi lại khách để xác định được.\n"
        else:
            if not item_id:
                content += "Không xác định được sản phẩm khách muốn cập nhật, hỏi lại khách để xác định được.\n"
            else:
                if not quantity:
                    content += "Không xác định được số lượng sản phẩm khách muốn cập nhật, hỏi lại khách.\n"
                else:
                    new_item = graph_function.update_order_item_quantity(
                        item_id=item_id,
                        new_quantity=quantity
                    )

                    if new_item:
                        content += (
                            "Đã thay đổi thành công sản phẩm <bạn hãy điền vào> "
                            "từ <bạn hãy điền vào> cái thành <bạn hãy điền vào> cái.\n"
                        )

                        order_info, order_items = graph_function.get_order_detail(order_id)
                        order_detail = _return_order(order_info, order_items, order_id)

                        content += (
                            "Trả về đơn hàng sau khi cập nhật y nguyên cho khách (không được bớt thông tin sản phẩm):\n"
                            f"{order_detail}"
                        )

                        # Save to state
                        order = {
                            k: v for k, v in order_info.__dict__.items()
                            if not k.startswith("_")
                        }
                        order["created_at"] = order["created_at"].strftime('%d-%m-%Y')
                        order["updated_at"] = order["updated_at"].strftime('%d-%m-%Y')
                        order["items"] = order_items
                        
                        update["orders"] = [order]
                    else:
                        content += "Đã có lỗi trong lúc cập nhật đơn hàng có mã là <bạn hãy điền vào>, nói khách vui lòng thử lại.\n"
        
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
        raise

@tool
def update_receiver_info(
    name: Annotated[Optional[str], "Receiver name, None if human not mention"],
    phone_number: Annotated[Optional[str], "Receiver phone number, None if human not mention"],
    address: Annotated[Optional[str], "Receiver address, None if human not mention"],
    order_id: Annotated[Optional[int], "ID of order"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to update name or phone number or address of receiver in order"""
    try:
        update = {}
        content = ""
        customer_id = state["customer_id"]
        
        if not order_id:
            content += "Không xác định được order_id mà khách chọn.\n"
        else:
            if not customer_id:
                content += "Chưa có thông tin khách hàng nên không thể cập nhật được.\n"
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
                    order_id=order_id,
                    receiver_name=name,
                    receiver_address=address,
                    receiver_phone_number=phone_number
                )
                
                if new_order:
                    content += "Đã cập nhật đơn hàng thành công cho khách."
                else:
                    content += "Đã sảy ra lỗi trong quá trình cập nhật, xin khách vui lòng thử lại."
            
            
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