from typing import Literal
from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import HumanMessage
from app.core.model import init_model
from app.core.user_agent.user_prompts import split_and_rewrite_prompt
from app.core.utils.class_parser import SplitRequestOutput

class UserNodes:
    def __init__(self):
        self.llm = init_model()
        
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
                f"Danh sách đơn hàng của khách: {orders}.\n"
                f"Danh sách các sản phẩm khách muốn mua: {cart}.\n"
                f"Danh sách các sản phẩm khách đã xem {seen_products}.\n"
            )}
        ]
        
        response = self.llm.with_structured_output(SplitRequestOutput).invoke(messages)
        print(f">>>> Tasks: {response["tasks"]}")
        
        return Command(
            update={
                "tasks": response["tasks"],
            },
            goto="supervisor"
        )
        
        