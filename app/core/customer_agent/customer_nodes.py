from langgraph.types import Command
from app.core.customer_agent.customer_prompts import customer_agent_system_prompt
from app.core.customer_agent.customer_tools import add_phone_name_address_tool
from app.core.state import SellState
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from app.core.model import llm_agent
from app.core.utils.helper_function import get_chat_his
from typing import Literal

class CustomerNodes:
    def __init__(self):
        self.create_customer_agent = create_react_agent(
            model=llm_agent,
            tools=[add_phone_name_address_tool],
            prompt = customer_agent_system_prompt(),
            state_schema=SellState
        )
        
    def customer_agent(self, 
                       state: SellState
    ) -> Command[Literal["__end__", "router_node"]]:
        state["messages"] = get_chat_his(
            state["messages"],
            start_offset=-10
        )
        tasks = state["tasks"]
        next_node = "__end__"
        update = {}
        
        response = self.create_customer_agent.invoke(state)
        content = response["messages"][-1].content
        status = response["status"]
        
        if response.get("tasks", None):
            tasks = response["tasks"]
            update["tasks"] = tasks
            print(f">>>> Tasks sau khi được cập nhật: {tasks}")
        
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
            
        for key in ["customer_id", "name", "phone_number", "address"]:
           if response.get(key, None) is not None:
               update[key] = response[key]
        
        return Command(
            update=update,
            goto=next_node
        )