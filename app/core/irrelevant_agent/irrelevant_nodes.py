from langgraph.types import Command
from pydantic import BaseModel
from app.core.irrelevant_agent.irrelevant_prompts import irrelevant_agent_prompt
from app.core.order_agent.order_prompts import order_agent_system_prompt
from app.core.state import SellState
from langchain_core.messages import AIMessage
from app.core.graph_function import GraphFunction
from langgraph.prebuilt import create_react_agent

from app.core.model import init_model

class IrrelevantNodes:
    def __init__(self):
        self.graph_function = GraphFunction()
        self.llm = init_model()
        
    def irrelevant_agent(self, state: SellState) -> Command:
        user_input = state["user_input"]
        chat_his = [
            {
                "type": chat.type,
                "content": chat.content
            }
            for chat in state["messages"][-5:]
        ]
        
        messages = [
            {"role": "system", "content": irrelevant_agent_prompt()},
            {"role": "human", "content": (
                f"Yêu cầu của khách: {user_input}.\n"
                f"Lịch sử chat: {chat_his}\n"
            )}
        ]
        
        response = self.llm.invoke(messages)
        
        next_node = "__end__"
        content = response.content
        
        update = {}
        update["messages"] = [AIMessage(content=content, name="irrelevant_agent")]
        update["next_node"] = next_node
        
        return Command(
            update=update,
            goto=next_node
        )
    