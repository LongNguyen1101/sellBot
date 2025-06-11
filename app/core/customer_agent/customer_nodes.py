from langgraph.types import Command, interrupt
from app.core.customer_agent.customer_prompts import customer_agent_system_prompt
from app.core.customer_agent.customer_tools import find_customer, register_customer
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
            tools=[find_customer, register_customer],
            prompt = customer_agent_system_prompt(),
            state_schema=SellState
        )
        
    def customer_agent(self, state: SellState) -> Command[Literal["__end__", "cart_agent"]]:
        response = self.create_customer_agent.invoke(state)
        content = response["messages"][-1].content
        next_node = "__end__"
        update = {}
        
        
        if response.get("customer_id", None):
            update["customer_id"] = response["customer_id"]
            update["is_login"] = True
        
        if response.get("name", None):
            update["name"] = response["name"]
        
        if response.get("phone_number", None):
            update["phone_number"] = response["phone_number"]
        
        if response.get("address", None):
            update["address"] = response["address"]
        
        update["next_node"] = response["next_node"]
        next_node = response["next_node"]
        update["messages"] = [AIMessage(content=content, name="customer_agent")]
        
        
        return Command(
            update=update,
            goto=next_node
        )
    
    def user_input_customer_agent_node(self, state: SellState) -> Command[Literal["customer_agent"]]:
        user_input = interrupt(None)
        
        return Command(
            update={
                "messages": [HumanMessage(content=user_input)],
                "user_input": user_input
            },
            goto="customer_agent"
        )