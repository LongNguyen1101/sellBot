from typing import Literal, Optional, Tuple
from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import HumanMessage, AIMessage
from app.core.model import llm
from app.core.user_agent.user_prompts import split_and_rewrite_prompt
from app.core.utils.class_parser import SplitRequestOutput
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.core.utils.class_parser import AgentToolResponse
from app.core.utils.graph_function import graph_function

def _get_or_create_customer(chat_id: int) -> Tuple[AgentToolResponse, dict]:
    with session_scope() as sess:
        public_crud = PublicCRUD(sess)
        tool_response: AgentToolResponse = {}
        update = {}
        
        customer, note = graph_function.get_or_create_customer(chat_id, public_crud=public_crud)
        
        if note == "found":
            log = (
                ">>>> Tìm thấy thông tin của khách:",
                f"Tên: {customer["name"]}. "
                f"Số điện thoại: {customer["phone_number"]}. "
                f"Địa chỉ: {customer["address"]}. "
                f"ID khách: {customer["customer_id"]}."
            )
            
            print(log)
            update.update({
                "name": customer["name"],
                "phone_number":customer["phone_number"],
                "address":customer["address"],
                "customer_id":customer["customer_id"]
            })
            
            tool_response["content"] = (
                "Đã tìm thấy thông tin khách hàng.\n"
            )
        else:
            update.update({
                "customer_id": customer["customer_id"]
            })
            
            tool_response["content"] = (
                "Không có thông tin khách hàng, tạo mới khách.\n"
            )
            
        return tool_response, update

class UserNodes:
    def __init__(self):
        self.llm = llm
        
    def user_input_node(self, state: SellState) -> Command[Literal["planner_node"]]:
        user_input = state["user_input"]
        chat_id = state["chat_id"]
        customer_id = state["customer_id"]
        update = {}
        
        tool_response: AgentToolResponse = {}
        
        if not customer_id:
            tool_response, new_update = _get_or_create_customer(chat_id=chat_id)
            update.update(new_update)
            print(f">>>> {tool_response["content"]}")
                
        update["messages"] = [HumanMessage(content=user_input, name="user_input_node")]
        
        return Command(
            update=update,
            goto="planner_node"
        )
        
    def planner_node(self, state: SellState) -> Command:
        update = {}
        user_input = state["user_input"]
        chat_his = [
            {
                "type": chat.type,
                "content": chat.content
            }
            for chat in state["messages"][-10:]
        ]
        orders = state.get("orders", [])
        cart = state.get("cart", [])
        seen_products = state.get("seen_products", [])
        
        messages = [
            {"role": "system", "content": split_and_rewrite_prompt()},
            {"role": "human", "content": (
                f"Yêu cầu của khách: {user_input}.\n"
                f"Lịch sử chat: {chat_his}.\n"
                f"Danh sách đơn hàng của khách (orders): {orders}.\n"
                f"Danh sách các sản phẩm khách muốn mua (cart): {cart}.\n"
                f"Danh sách các sản phẩm khách đã xem (seen_products): {seen_products}.\n"
            )}
        ]
        
        response = self.llm.with_structured_output(SplitRequestOutput).invoke(messages)
        print(f">>>> Tasks: {response["tasks"]}")
        
        if len(response["tasks"]) > 1:
            content = "Dạ khách vui lòng đợi em một chút để em xử lý ạ.\n"
            update["messages"] = [AIMessage(content=content, name="split_request_node")]
        
        update["tasks"] = response["tasks"] 
        
        return Command(
            update=update,
            goto="router_node"
        )
        
        