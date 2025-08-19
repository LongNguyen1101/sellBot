from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import AIMessage, HumanMessage
from typing import Any, Literal
from app.core.model import llm_agent
from app.core.store_info_agent.store_info_prompts import store_info_agent_prompt
from app.core.utils.helper_function import get_chat_his
from app.log.logger_config import setup_logging

logger = setup_logging(__name__)

def _get_store_info(
    llm: Any,
    messages: list,
    current_task: str
):
    chat_his = get_chat_his(
        messages=messages,
        start_offset=-10
    )
    
    messages = [
        {"role": "system", "content": store_info_agent_prompt()},
        {"role": "human", "content": (
            f"Yêu cầu của khách: {current_task}.\n"
            f"Lịch sử chat: {chat_his}\n"
        )}
    ]
    
    response = llm.invoke(messages)
    return response.content[0]["text"]

class StoreInfoNodes:
    def __init__(self):
        self.llm = llm_agent
        
    def store_info_agent(self, 
                         state: SellState
    ) -> Command[Literal["__end__", "router_node"]]:
        tasks = state["tasks"]
        next_node = "__end__"
        
        content = _get_store_info(
            llm=self.llm,
            messages=state["messages"],
            current_task=state["current_task"]
        )
        
        if len(tasks) > 0:
            next_node = "router_node"
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
    