from langgraph.types import Command
from pydantic import BaseModel
from app.core.utils.helper_function import get_chat_his
from app.core.state import SellState
from langchain_core.messages import AIMessage
from app.core.utils.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent
from app.core.product_agent.product_tools import (
    get_products_tool
)
from app.core.product_agent.product_prompts import product_agent_system_prompt
from app.core.model import init_model
from typing import Literal
from app.core.utils.class_parser import AgentToolResponse

class ProductNodes:
    def __init__(self):
        self.graph_function = GraphFunction()
        
        self.llm = init_model()
        self.create_product_agent = create_react_agent(
            model=self.llm,
            tools=[get_products_tool],
            prompt = product_agent_system_prompt(),
            state_schema=SellState,
        )
        
    def product_agent(self, 
                      state: SellState
    ) -> Command[Literal["__end__", "supervisor"]]:
        state["messages"] = get_chat_his(
            state["messages"],
            start_offset=-10
        )
        tasks = state["tasks"]
        next_node = "__end__"
        update = {}
        
        response = self.create_product_agent.invoke(state)
        parse_response = AgentToolResponse.model_validate_json(response["messages"][-1].content)
        status = parse_response.status
        content = parse_response.content
        
        if status == "asking":
            next_node = "__end__"
            # Must ask the customer first, then create new subtasks depending on their answer
            tasks = []
        elif status == "finish":
            if len(tasks) > 0:
                next_node = "supervisor"
                content = None
            else:
                next_node = "__end__"
        else:
            next_node = "__end__"
            
        if content:
            update["messages"] = [
                AIMessage(content=content, name="product_agent")
            ]
        update.update({
            "next_node": next_node,
            "tasks": tasks
        })
        
        for key in ["cart", "seen_products", "name", "phone_number", "address", "customer_id"]:
           if response.get(key, None) is not None:
               update[key] = response[key]
        
        return Command(
            update=update,
            goto=next_node
        )
    