from abc import update_abstractmethods
from turtle import update
from langgraph.types import interrupt, Command
from app.core import state
from app.core.state import SellState
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from app.chain.sell_chain import SellChain
from app.core.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent
from app.core.product_agent.product_tools import (
    choose_product,
    get_products
)
from app.core.product_agent.product_prompts import product_agent_system_prompt
from app.core.model import init_model
from typing import Literal

class ProductNodes:
    def __init__(self):
        self.chain = SellChain()
        self.graph_function = GraphFunction()
        
        self.llm = init_model()
        self.create_product_agent = create_react_agent(
            model=self.llm,
            tools=[get_products, choose_product],
            prompt = product_agent_system_prompt(),
            state_schema=SellState
        )
        
    def product_agent(self, state: SellState) -> Command[Literal["__end__", "cart_agent"]]:
        result = self.create_product_agent.invoke(state)
        next_node = "__end__"
        
        update = {
            "messages": [
                AIMessage(content=result["messages"][-1].content, name="product_agent")
            ]
        }
        
        if result.get("seen_products", None):
            update["seen_products"] = result["seen_products"]
            
        if result.get("product_chosen", None):
            update["product_chosen"] = result["product_chosen"]
        
        if result.get("next_node", None):
            next_node = result["next_node"]
            update["next_node"] = result["next_node"]
        
        return Command(
            update=update,
            goto=next_node
        )
    