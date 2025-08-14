from langgraph.types import Command
from app.core.customer_service_agent.customer_service_promtps import customer_service_system_prompt
from app.core.customer_service_agent.customer_service_tools import get_common_situation_tool, get_qna_tool
from app.core.state import SellState
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from app.core.model import llm_agent
from typing import Literal
from app.core.utils.helper_function import get_chat_his
from app.log.logger_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)

class CustomerServiceNodes:
    def __init__(self):
        self.create_customer_service_agent = create_react_agent(
            model=llm_agent,
            tools=[get_qna_tool, get_common_situation_tool],
            prompt = customer_service_system_prompt(),
            state_schema=SellState
        )
        
    def customer_service_agent(self, 
                               state: SellState
    ) -> Command[Literal["__end__", "router_node"]]:
        state["messages"] = get_chat_his(
            state["messages"],
            start_offset=-10
        )
        state["messages"].append(
            HumanMessage(content=state["current_task"])
        )
        tasks = state["tasks"]
        next_node = "__end__"
        update = {}
        
        response = self.create_cart_agent.invoke(state)[0]["text"]
        content = response["messages"][-1].content
        status = response["status"]
        
        if status == "asking":
            next_node = "__end__"
            tasks = []
        elif status == "finish":
            if len(tasks) > 0:
                next_node = "router_node"
                content = None
            else:
                next_node = "__end__"
                tasks = []
        else:
            next_node = "__end__"
            tasks = []
        
        if content:
            update["messages"] = [AIMessage(content=content, name="customer_service_agent")]
        
        update["next_node"] = next_node
        update["tasks"] = tasks
            
        for key in ["cart", "name", "phone_number", "address"]:
           if response.get(key, None) is not None:
               update[key] = response[key]
               
        logger.info(f"Thông tin cập nhật: {update}")
        
        return Command(
            update=update,
            goto=next_node
        )