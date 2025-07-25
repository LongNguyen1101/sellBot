from langgraph.types import Command, interrupt
from app.core.customer_agent.customer_prompts import customer_agent_system_prompt
from app.core.customer_agent.customer_tools import add_phone_number, add_name_address, add_phone_name_address
from app.core.state import SellState
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import add_messages
from app.chain.sell_chain import SellChain
from app.core.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent

from app.core.model import init_model
from typing import Literal, TypedDict

class CustomerNodes:
    def __init__(self):
        self.chain = SellChain()
        self.graph_function = GraphFunction()
        
        self.llm = init_model()
        self.create_customer_agent = create_react_agent(
            model=self.llm,
            tools=[add_phone_number, add_name_address, add_phone_name_address],
            prompt = customer_agent_system_prompt(),
            state_schema=SellState
        )
        
    def customer_agent(self, state: SellState) -> Command:
        response = self.create_customer_agent.invoke(state)
        content = response["messages"][-1].content
        update = {}
        update["next_node"] = "__end__"
        
        if response.get("customer_id", None):
            update["customer_id"] = response["customer_id"]
            
        if response.get("next_node", None):
            update["next_node"] = response["next_node"]
        
        if response.get("name", None):
            update["name"] = response["name"]
        
        if response.get("phone_number", None):
            update["phone_number"] = response["phone_number"]
        
        if response.get("address", None):
            update["address"] = response["address"]
        
        update["messages"] = [AIMessage(content=content, name="customer_agent")]
        
        return Command(
            update=update,
            goto=update["next_node"]
        )