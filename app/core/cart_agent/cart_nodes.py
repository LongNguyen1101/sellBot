from turtle import update
from langgraph.types import interrupt, Command
from app.core import state
from app.core.state import SellState
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from app.chain.sell_chain import SellChain
from app.core.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent
from app.core.cart_agent.cart_tools import (
    add_cart,
    get_cart
)
from app.core.cart_agent.cart_prompts import cart_agent_system_prompt
from app.core.model import init_model
from typing import Literal

class CarttNodes:
    def __init__(self):
        self.chain = SellChain()
        self.graph_function = GraphFunction()
        
        self.llm = init_model()
        self.create_cart_agent = create_react_agent(
            model=self.llm,
            tools=[add_cart, get_cart],
            prompt = cart_agent_system_prompt(),
            state_schema=SellState
        )
        
    def cart_agent(self, state: SellState) -> Command[Literal["customer_agent"]]:
        result = self.create_cart_agent.invoke(state)
        
        update = {
            "messages": [
                AIMessage(content=result["messages"][-1].content, name="cart_agent")
            ],
        }
        next_node = result["next_node"]
        
        if result.get("cart", None) is not None:
            update["cart"] = result["cart"]
        
        return Command(
            update=update,
            goto=next_node
        )
    