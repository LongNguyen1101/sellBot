from httpx import ConnectError
from langgraph.types import interrupt, Command
from app.core.state import SellState
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from app.chain.sell_chain import SellChain
from app.core.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent
from app.core.product_agent.product_tools import (
    get_products
)
from app.core.product_agent.product_prompts import product_agent_system_prompt
from app.core.model import init_model
from typing import Literal

class UserNodes:
    def __init__(self):
        self.chain = SellChain()
        self.graph_function = GraphFunction()
        
    def greeting_user_node(self, state: SellState) -> Command[Literal["user_input_node"]]:
        hello_msg = (
            "Kính chào quý khách"
        )
        
        return Command(
            update={
                "messages": [AIMessage(content=hello_msg)]
            },
            goto="user_input_node"
        )
        
    
    def user_input_node(self, state: SellState) -> Command[Literal["supervisor"]]:
        user_input = interrupt(None)
        
        return Command(
            update={
                "messages": [HumanMessage(content=user_input)],
                "user_input": user_input
            },
            goto="supervisor"
        )