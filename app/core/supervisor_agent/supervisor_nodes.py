from app.core.supervisor_agent.supervisor_prompts import supervisor_system_prompt
from app.core.state import SellState
from typing import Literal, TypedDict
from langgraph.types import Command
from app.core.model import init_model


MEMBERS = ["product_agent", "cart_agent", "order_agent", "customer_agent", "customer_service_agent", "__end__"]
OPTIONS = MEMBERS + ["FINISH"]

class SupervisorNodes:
    class Router(TypedDict):
        next: Literal["product_agent", "cart_agent", "order_agent", "customer_agent", "customer_service_agent", "__end__"]

    def __init__(self):
        self.members = MEMBERS
        self.options = OPTIONS
        self.llm = init_model()

    def supervisor_agent(self, state: SellState) -> Command:
        cart = state["cart"]
        orders = state["orders"]
        chat_his = [
            {
                "type": chat.type,
                "content": chat.content
            }
            for chat in state["messages"][-5:]
        ]
        
        messages = [
            {"role": "system", "content": supervisor_system_prompt(members=self.members)},
            {"role": "human", "content": (
                f"Lịch sử chat: {chat_his}\n"
                f"Giỏ hàng của khách: {cart}.\n"
                f"Đơn hàng của khách: {orders}\n"
            )}
        ]
        
        response = self.llm.with_structured_output(self.Router).invoke(messages)
        
        next_node = response["next"]

        return Command(
            update={
                "next_node": next_node
            },
            goto=next_node
        )
