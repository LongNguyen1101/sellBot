from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import AIMessage
from app.core.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent
from app.core.product_agent.product_tools import (
    get_products
)
from app.core.product_agent.product_prompts import product_agent_system_prompt
from app.core.model import init_model
from typing import Literal

class ProductNodes:
    def __init__(self):
        self.graph_function = GraphFunction()
        
        self.llm = init_model()
        self.create_product_agent = create_react_agent(
            model=self.llm,
            tools=[get_products],
            prompt = product_agent_system_prompt(),
            state_schema=SellState
        )
        
    def product_agent(self, state: SellState) -> Command[Literal["__end__"]]:
        result = self.create_product_agent.invoke(state)
        
        update = {
            "messages": [
                AIMessage(content=result["messages"][-1].content, name="product_agent")
            ]
        }
        
        if result.get("cart", None):
            update["cart"] = result["cart"]
        
        if result.get("seen_products", None):
            update["seen_products"] = result["seen_products"]
            
        if result.get("name", None):
            update["name"] = result["name"]
            
        if result.get("phone_number", None):
            update["phone_number"] = result["phone_number"]
            
        if result.get("address", None):
            update["address"] = result["address"]
            
        if result.get("customer_id", None):
            update["customer_id"] = result["customer_id"]
        
        
        return Command(
            update=update,
            goto="__end__"
        )
    