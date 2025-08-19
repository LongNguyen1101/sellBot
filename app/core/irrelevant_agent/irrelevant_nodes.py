from langgraph.types import Command
from app.core.irrelevant_agent.irrelevant_prompts import irrelevant_agent_prompt
from app.core.state import SellState
from langchain_core.messages import AIMessage, HumanMessage
from typing import Literal
from app.core.model import llm_agent
from app.core.utils.helper_function import get_chat_his
from app.log.logger_config import setup_logging

logger = setup_logging(__name__)

class IrrelevantNodes:
    def __init__(self):
        self.llm = llm_agent
        
    def irrelevant_agent(self, 
                         state: SellState
    ) -> Command[Literal["__end__", "router_node"]]:
        chat_his = get_chat_his(
            state["messages"],
            start_offset=-10
        )
        state["messages"].append(
            HumanMessage(content=state["current_task"])
        )
        user_input = state["user_input"]
        tasks = state["tasks"]
        next_node = "__end__"
        
        messages = [
            {"role": "system", "content": irrelevant_agent_prompt()},
            {"role": "human", "content": (
                f"Yêu cầu của khách: {user_input}.\n"
                f"Lịch sử chat: {chat_his}\n"
            )}
        ]
        
        response = self.llm.invoke(messages)
        content = response.content[0]["text"]
        
        if len(tasks) > 0:
            next_node = "router_node"
        else:
            next_node = "__end__"
        
        update = {
            "messages": [AIMessage(content=content, name="irrelevant_agent")],
            "next_node": next_node
        }
        
        return Command(
            update=update,
            goto=next_node
        )
    