from app.core.supervisor_agent.supervisor_prompts import supervisor_system_prompt
from app.core.state import SellState
from typing import Literal, TypedDict
from langgraph.types import Command
from app.core.model import init_model


MEMBERS = (["product_agent", "cart_agent", "order_agent", "customer_agent",
            "customer_service_agent", "irrelevant_agent", "store_info_agent", "__end__"])
OPTIONS = MEMBERS + ["FINISH"]

class SupervisorNodes:
    class Router(TypedDict):
        next: (Literal["product_agent", "cart_agent", "order_agent", "customer_agent",
                       "customer_service_agent", "irrelevant_agent", "store_info_agent", "__end__"])

    def __init__(self):
        self.members = MEMBERS
        self.options = OPTIONS
        self.llm = init_model()

    def supervisor_agent(self, state: SellState) -> Command:
        chat_his = [
            {
                "type": chat.type,
                "content": chat.content
            }
            for chat in state["messages"][-20:]
        ]
        current_state = state.copy()
        current_state.pop("messages", None)
        user_input = state["user_input"]
        
        messages = [
            {"role": "system", "content": supervisor_system_prompt(members=self.members)},
            {"role": "human", "content": (
                f"Yêu cầu của khách: {user_input}.\n"
                f"Lịch sử chat: {chat_his}\n"
                f"Các thông tin thu thập được (state của chatbot): {current_state}"
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
