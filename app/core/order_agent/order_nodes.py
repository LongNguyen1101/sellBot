from typing import Literal
from langgraph.types import Command
from app.core.order_agent.order_prompts import order_agent_system_prompt
from app.core.order_agent.order_tools import (
    create_order_tool,
    get_all_orders_tool,
    update_item_quantity_tool,
    remove_item_from_order_tool,
    update_receiver_info_tool
)
from app.core.state import SellState
from langchain_core.messages import AIMessage
from app.core.utils.class_parser import AgentToolResponse
from app.core.utils.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent

from app.core.model import init_model
from app.core.utils.helper_function import get_chat_his

class OrderNodes:
    def __init__(self):
        self.graph_function = GraphFunction()
        self.llm = init_model()
        self.create_order_agent = create_react_agent(
            model=self.llm,
            tools=([create_order_tool, get_all_orders_tool, update_item_quantity_tool, 
                    remove_item_from_order_tool, update_receiver_info_tool]),
            prompt = order_agent_system_prompt(),
            state_schema=SellState
        )
        
    def order_agent(self, 
                    state: SellState
    ) -> Command[Literal["__end__", "supervisor"]]:
        state["messages"] = get_chat_his(
            state["messages"],
            start_offset=-10
        )
        tasks = state["tasks"]
        next_node = "__end__"
        update = {}
        
        response = self.create_order_agent.invoke(state)
        content = response["messages"][-1].content
        status = response["status"]
        
        if response.get("tasks", None):
            if len(response["tasks"]) > 0:
                tasks = response["tasks"]
                update["tasks"] = tasks
                print(f">>>> Tasks sau khi được cập nhật: {tasks}")
        
        if status == "asking":
            next_node = "__end__"
            tasks = []
        elif status == "finish":
            if len(tasks) > 0:
                next_node = "supervisor"
                content = None
            else:
                next_node = "__end__"
                tasks = []
        else:
            next_node = "__end__"
            tasks = []
        
        if content:
            update["messages"] = [
                AIMessage(content=content, name="order_agent")
            ]
        update["next_node"] = next_node
        update["tasks"] = tasks
            
        for key in ["orders", "cart", "name", "phone_number", "address", "customer_id"]:
           if response.get(key, None) is not None:
               update[key] = response[key]
               
        print(f">>>> Update: {update}")
        
        return Command(
            update=update,
            goto=next_node
        )
    