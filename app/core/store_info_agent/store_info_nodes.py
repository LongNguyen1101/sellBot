from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import AIMessage
from app.core.utils.graph_function import graph_function
from typing import Literal
from app.core.model import llm_agent
from app.core.store_info_agent.store_info_prompts import store_info_agent_prompt
from app.core.utils.helper_function import get_chat_his

class StoreInfoNodes:
    def __init__(self):
        self.llm = llm_agent
        
    def store_info_agent(self, 
                         state: SellState
    ) -> Command[Literal["__end__", "supervisor"]]:
        chat_his = get_chat_his(
            state["messages"],
            start_offset=-10
        )
        user_input = state["user_input"]
        tasks = state["tasks"]
        next_node = "__end__"
        
        messages = [
            {"role": "system", "content": store_info_agent_prompt()},
            {"role": "human", "content": (
                f"Yêu cầu của khách: {user_input}.\n"
                f"Lịch sử chat: {chat_his}\n"
            )}
        ]
        
        response = self.llm.invoke(messages)
        content = response.content
        
        if len(tasks) > 0:
            next_node = "supervisor"
        else:
            next_node = "__end__"
        
        update = {
            "messages": [AIMessage(content=content, name="store_info_agent")],
            "next_node": next_node
        }
        
        return Command(
            update=update,
            goto=next_node
        )
    