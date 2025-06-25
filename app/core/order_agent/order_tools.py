import comm
from langchain_core.tools import tool, InjectedToolCallId
from app.core.graph_function import GraphFunction
from app.core.model import init_model
from app.core.order_agent.order_prompts import find_order_prompt, update_order_prompt
from app.core.state import SellState
from typing import Annotated, List, Literal, Optional, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage, AIMessage
from app.core.helper_function import _return_order

graph_function = GraphFunction()
llm = init_model()

class UpdateOrder(TypedDict):
    command: str
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
        if customer_id is not None:
            cart_items = state["cart"]
            shipping_fee = 50000
            payment = "COD"
            receiver_name = state["name"]
            receiver_phone_number = state["phone_number"]
            receiver_address = state["address"]

            new_order = graph_function.create_order(customer_id,
                                                    receiver_name=receiver_name,
                                                    receiver_phone_number=receiver_phone_number,
                                                    receiver_address=receiver_address)
            
            order_items, order_total = graph_function.add_cart_item_to_order(cart_items, new_order.order_id)

            grand_total = order_total + shipping_fee
            update_order = graph_function.add_total_to_order(
                new_order.order_id,
                payment,
                order_total,
                shipping_fee,
                grand_total
            )

            return_order, order_items = _return_order(new_order.order_id)

            content = (
                "Create order successfully.\n"
                "Return order to customer:\n"
                f"{return_order}"
            )
            
            order_list = {
                f"order_id: {new_order.order_id}": order_items
            }
            update["order_list"] = order_list
        else:
            content = "Không thấy số điện thoại của khách, hỏi khách số điện thoại để kiểm tra các đơn đặt hàng"
        
        update["messages"] = [
            ToolMessage
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]
        update["next_node"] = "__end__"
        
        return Command(
            update=update
        )
    except Exception as e:
        raise 
    
    
@tool
def get_order(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to get order which is relevance to requirement of client request"""
    try:
        update = {}
        customer_id = state["customer_id"]
        if customer_id is not None:
            user_input = state["user_input"]
            msg = [
                {"role": "system", "content": find_order_prompt()},
                {"role": "human", "content": (
                    f"Đây là yêu cầu của khách: {user_input}\n"
                    f"Mã khách hàng (customer_id): {customer_id}"
                )}
            ]
            result = llm.invoke(msg).content
            command = result.replace("```sql", "").replace("```", "").replace("\n", " ").strip()
            print(f">>>> command: {command}")
            
            orders = graph_function.get_order_by_command(command)
            
            order_items = {}
            for order in orders:
                order_id = order["order_id"]
                items = graph_function.get_order_items_detail(order_id)
                order_items[f"order_id: {order_id}"] = items
            
            print(f">>>> order_items: {order_items}")
            
            if order_items.__len__() == 0:
                content = "Không có đơn đặt hàng nào thoã yêu cầu của khách. Hỏi lại khách."
            else:
                content = (
                    f"Tìm thấy {order_items.__len__()} đơn hàng thoã yêu cầu của khách.\n"
                    "Đây là thông tin chi tiết đơn hàng của khách:\n"
                    f"{order_items}.\n"
                    "Nếu số lượng đơn hàng lớn hơn 3 thì tóm tắt chi tiết đơn hàng để khách dễ đọc.\n"
                    "Sau cùng hỏi khách đây có phải là đơn khách cần không hoặc trong các đơn trên, đơn nào là đơn khách cần.\n"
                    "Lưu ý trả về cả mã đơn hàng để khách dễ sửa đổi.\n"
                )
                
                update["order_list"] = order_items
        else:
            content = "Không thấy số điện thoại của khách, hỏi khách số điện thoại để kiểm tra các đơn đặt hàng."
        
        update["messages"] = [
            ToolMessage
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]
        update["next_node"] = "__end__"
        
        return Command(
            update=update
        )
        
    except Exception as e:
        raise 
    
@tool
def update_product_in_order(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to udpate, add, or delete product in order"""
    try:
        update = {}
        customer_id = state["customer_id"]
        if customer_id is not None:
            chat_histories = [
                {
                    "type": chat.type,
                    "content": chat.content
                } for chat in state["messages"][-5:]]
            
            print(f">>>> user_input: {chat_histories}")
            order_list = state["order_list"]
            msg = [
                {"role": "system", "content": update_order_prompt()},
                {"role": "human", "content": (
                    f"Đây là lịch sử chat của khách và chatbot: {chat_histories}\n"
                    f"Đây là dictionary đơn hàng liên quan đến yêu cầu của khách: {order_list}"
                )}
            ]
            result = llm.with_structured_output(UpdateOrder).invoke(msg)
            command = result["command"].replace("```sql", "").replace("```", "").replace("\n", " ").strip()
            order_id = int(result["order_id"])
            print(f">>>> command and order_id: {command}, {order_id}")
            
            update_order = graph_function.update_order_by_command(command)
            return_order, _ = _return_order(order_id)
            
            print(f">>>> return order: {return_order}")
            
            content = (
                "Cập nhật đơn hàng thành công.\n"
                "Trả lại đơn hàng sau khi đã cập nhật cho khách:\n"
                f"{return_order}"
            )
            
        else:
            content = "Không thấy số điện thoại của khách, hỏi khách số điện thoại để kiểm tra các đơn đặt hàng."
        
        update["messages"] = [
            ToolMessage
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]
        update["next_node"] = "__end__"
        
        return Command(
            update=update
        )
        
            
    except Exception as e:
        raise