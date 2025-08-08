from typing import Literal
from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import HumanMessage, AIMessage
from app.core.model import llm
from app.core.user_agent.user_prompts import split_and_rewrite_prompt
from app.core.utils.class_parser import SplitRequestOutput

class UserNodes:
    def __init__(self):
        self.llm = llm
        
    def user_input_node(self, 
                        state: SellState
    ) -> Command[Literal["split_request_node"]]:
        user_input = state["user_input"]
        
        return Command(
            update={
                "messages": [HumanMessage(content=user_input, name="user_input_node")],
            },
            goto="split_request_node"
        )
        
    def split_request_node(self, state: SellState) -> Command:
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
            goto="supervisor"
        )
        
        