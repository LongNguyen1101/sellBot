from langgraph.types import Command
from app.core.customer_service_agent.customer_service_promtps import customer_service_system_prompt
from app.core.customer_service_agent.customer_service_tools import get_common_situation_tool, get_qna_tool
from app.core.state import SellState
from langchain_core.messages import AIMessage
from app.core.utils.class_parser import AgentToolResponse
from app.core.utils.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent
from app.core.model import init_model
from typing import Literal

from app.core.utils.helper_function import get_chat_his

class CustomerServiceNodes:
    def __init__(self):
        self.graph_function = GraphFunction()
        
        self.llm = init_model()
        self.create_customer_service_agent = create_react_agent(
            model=self.llm,
            tools=[get_qna_tool, get_common_situation_tool],
            prompt = customer_service_system_prompt(),
            state_schema=SellState
        )
        
    def customer_service_agent(self, 
                               state: SellState
    ) -> Command[Literal["__end__", "supervisor"]]:
        state["messages"] = get_chat_his(
            state["messages"],
            start_offset=-10
        )
        tasks = state["tasks"]
        next_node = "__end__"
        update = {}
        
        response = self.create_cart_agent.invoke(state)
        content = response["messages"][-1].content
        status = response["status"]
        
        if status == "asking":
            next_node = "__end__"
            tasks = []
        elif status == "finish":
            if len(tasks) > 0:
                next_node = "supervisor"
                content = None
            else:
                next_node = "__end__"
        else:
            next_node = "__end__"
            tasks = []
        
        if content:
            update["messages"] = [AIMessage(content=content, name="customer_service_agent")]
        update["next_node"] = next_node
        update["tasks"] = tasks
            
        for key in ["cart", "name", "phone_number", "address"]:
           if response.get(key, None) is not None:
               update[key] = response[key]
        
        return Command(
            update=update,
            goto=next_node
        )