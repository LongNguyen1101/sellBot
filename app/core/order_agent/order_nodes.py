import json
from langgraph.types import Command
from pydantic import BaseModel
from zmq import RouterNotify
from app.core.order_agent.order_prompts import order_agent_system_prompt
from app.core.order_agent.order_tools import (
    create_order,
    get_all_orders,
    update_item_quantity,
    remove_item_from_order,
    update_receiver_info
)
from app.core.state import SellState
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import add_messages
from app.core.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent

from app.core.model import init_model
from typing import Literal, TypedDict

class OrderNodes:
    class OrderResponse(BaseModel):
        next: str 
        content: str
        
    def __init__(self):
        self.graph_function = GraphFunction()
        self.llm = init_model()
        self.create_order_agent = create_react_agent(
            model=self.llm,
            tools=[create_order, get_all_orders, update_receiver_info, update_item_quantity, remove_item_from_order],
            prompt = order_agent_system_prompt(),
            state_schema=SellState
        )
        
    def order_agent(self, state: SellState) -> Command:
        response = self.create_order_agent.invoke(state)
        
        next_node = "__end__"
        content = response["messages"][-1].content
        
        update = {}
        update["messages"] = [AIMessage(content=content, name="order_agent")]
        update["next_node"] = next_node
            
        if response.get("orders", None):
            update["orders"] = response["orders"]
        
        if response.get("name", None):
            update["name"] = response["name"]
            
        if response.get("phone_number", None):
            update["phone_number"] = response["phone_number"]
            
        if response.get("address", None):
            update["address"] = response["address"]
            
        if response.get("customer_id", None):
            update["customer_id"] = response["customer_id"]
        
        return Command(
            update=update,
            goto=next_node
        )
    