from app.core.supervisor_agent.supervisor_prompts import supervisor_system_prompt
from app.core.state import SellState
from typing import Literal, TypedDict
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from langgraph.graph import END
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.model import init_model
from langgraph.graph.message import add_messages


MEMBERS = ["product_agent", "cart_agent", "order_agent", "customer_agent"]
OPTIONS = MEMBERS + ["FINISH"]

class SupervisorNodes:
    class Router(TypedDict):
        next: str

    def __init__(self):
        self.members = MEMBERS
        self.options = OPTIONS
        self.llm = init_model()

    def supervisor_agent(
        self, state: SellState
    ) -> Command[Literal["product_agent", "cart_agent", "order_agent", "customer_agent", "__end__"]]:
        user_input = state["user_input"]
        state["messages"] = add_messages(state["messages"], [HumanMessage(content=user_input)])
        
        messages = [
            {"role": "system", "content": supervisor_system_prompt(members=self.members)},
        ] + state["messages"]

        response = self.llm.with_structured_output(self.Router).invoke(messages)

        goto = response["next"]
        if goto == "FINISH":
            goto = END

        return Command(
            update={
                "messages": state["messages"],
                "next_node": goto
            },
            goto=goto
        )
