from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import HumanMessage
from typing import Literal

class UserNodes:
    def user_input_node(self, state: SellState) -> Command[Literal["supervisor"]]:
        user_input = state["user_input"]
        
        return Command(
            update={
                "messages": [HumanMessage(content=user_input, name="user_input_node")],
            },
            goto="supervisor"
        )