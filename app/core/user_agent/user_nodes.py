from typing import Literal, Optional, Tuple
from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import HumanMessage, AIMessage
from app.core.model import llm
from app.core.user_agent.user_prompts import split_and_rewrite_prompt
from app.core.utils.class_parser import SplitRequestOutput
from app.core.utils.helper_function import get_chat_his
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.core.utils.class_parser import AgentToolResponse
from app.core.utils.graph_function import graph_function
from app.log.logger_config import setup_logging

logger = setup_logging(__name__)

def _get_or_create_customer(chat_id: int) ->dict:
    with session_scope() as sess:
        public_crud = PublicCRUD(sess)
        update = {}
        
        customer, note = graph_function.get_or_create_customer(
            chat_id=chat_id, 
            public_crud=public_crud,
            parse_object=False
        )
        
        if note == "found":
            log = (
                "Tìm thấy thông tin của khách:",
                f"Tên: {customer["name"]}. "
                f"Số điện thoại: {customer["phone_number"]}. "
                f"Địa chỉ: {customer["address"]}. "
                f"ID khách: {customer["customer_id"]}."
            )
            
            logger.info(log)
            update.update({
                "name": customer["name"],
                "phone_number":customer["phone_number"],
                "address":customer["address"],
                "customer_id":customer["customer_id"]
            })
        else:
            update.update({
                "customer_id": customer["customer_id"]
            })
            
            logger.info("Không có thông tin khách hàng, tạo mới khách.\n")
            
        return update

class UserNodes:
    def __init__(self):
        self.llm = llm
        
    def user_input_node(self, state: SellState) -> Command[Literal["planner_node"]]:
        user_input = state["user_input"]
        chat_id = state["chat_id"]
        customer_id = state["customer_id"]
        update = {}
        
        if not customer_id:
            new_update = _get_or_create_customer(chat_id=chat_id)
            update.update(new_update)
                
        update["messages"] = [HumanMessage(content=user_input, name="user_input_node")]
        
        return Command(
            update=update,
            goto="planner_node"
        )
        
    def planner_node(self, state: SellState) -> Command:
        update = {}
        user_input = state["user_input"]
        chat_his = get_chat_his(
            messages=state["messages"],
            start_offset=-10
        )
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
        logger.info(f"Tasks: {response["tasks"]}")
        
        if len(response["tasks"]) > 1:
            content = "Dạ khách vui lòng đợi em một chút để em xử lý ạ.\n"
            update["messages"] = [AIMessage(content=content, name="split_request_node")]
        
        update["tasks"] = response["tasks"] 
        
        return Command(
            update=update,
            goto="router_node"
        )
        
        