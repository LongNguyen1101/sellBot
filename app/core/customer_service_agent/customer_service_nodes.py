from langgraph.types import Command
from app.core.customer_service_agent.customer_service_promtps import customer_service_system_prompt
from app.core.customer_service_agent.customer_service_tools import get_common_situation, get_qna
from app.core.state import SellState
from langchain_core.messages import AIMessage
from app.core.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent
from app.core.model import init_model
from typing import Literal

class CustomerServiceNodes:
    def __init__(self):
        self.graph_function = GraphFunction()
        
        self.llm = init_model()
        self.create_customer_service_agent = create_react_agent(
            model=self.llm,
            tools=[get_qna, get_common_situation],
            prompt = customer_service_system_prompt(),
            state_schema=SellState
        )
        
    def customer_service_agent(self, state: SellState) -> Command[Literal["__end__"]]:
        result = self.create_customer_service_agent.invoke(state)
        
        update = {
            "messages": [
                AIMessage(content=result["messages"][-1].content, name="customer_service_agent")
            ],
        }
        
        return Command(
            update=update,
            goto="__end__"
        )       