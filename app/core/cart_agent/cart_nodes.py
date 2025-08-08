from langgraph.types import  Command
from app.core.utils.class_parser import AgentToolResponse
from app.core.utils.helper_function import get_chat_his
from app.core.state import SellState
from langchain_core.messages import AIMessage
from app.core.utils.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent
from app.core.cart_agent.cart_tools import (
    add_cart_tool,
    get_cart_tool,
    change_quantity_cart_tool,
    update_receiver_info_in_cart_tool
)
from app.core.cart_agent.cart_prompts import cart_agent_system_prompt
from app.core.model import llm_agent
from typing import Literal

class CarttNodes:
    def __init__(self):
        self.create_cart_agent = create_react_agent(
            model=llm_agent,
            tools=[add_cart_tool, get_cart_tool, change_quantity_cart_tool, update_receiver_info_in_cart_tool],
            prompt = cart_agent_system_prompt(),
            state_schema=SellState
        )
        
    def cart_agent(self, 
                   state: SellState
    ) -> Command[Literal["__end__", "router_node"]]:
        state["messages"] = get_chat_his(
            state["messages"],
            start_offset=-10
        )
        tasks = state["tasks"]
        next_node = "__end__"
        update = {}
        
        response = self.create_cart_agent.invoke(state)
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
            update["messages"] = [
                AIMessage(content=content, name="cart_agent")
            ]
        update["next_node"] = next_node
        update["tasks"] = tasks
            
        for key in ["cart", "name", "phone_number", "address"]:
           if response.get(key, None) is not None:
               update[key] = response[key]
        
        return Command(
            update=update,
            goto=next_node
        )
    