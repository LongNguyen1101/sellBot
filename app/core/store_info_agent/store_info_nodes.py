from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import AIMessage
from app.core.graph_function import GraphFunction

from app.core.model import init_model
from app.core.store_info_agent.store_info_prompts import store_info_agent_prompt

class StoreInfoNodes:
    def __init__(self):
        self.graph_function = GraphFunction()
        self.llm = init_model()
        
    def store_info_agent(self, state: SellState) -> Command:
        user_input = state["user_input"]
        chat_his = [
            {
                "type": chat.type,
                "content": chat.content
            }
            for chat in state["messages"][-5:]
        ]
        
        messages = [
            {"role": "system", "content": store_info_agent_prompt()},
            {"role": "human", "content": (
                f"Yêu cầu của khách: {user_input}.\n"
                f"Lịch sử chat: {chat_his}\n"
            )}
        ]
        
        response = self.llm.invoke(messages)
        
        next_node = "__end__"
        content = response.content
        
        update = {}
        update["messages"] = [AIMessage(content=content, name="store_info_agent")]
        update["next_node"] = next_node
        
        return Command(
            update=update,
            goto=next_node
        )
    