from langgraph.types import interrupt
from app.core.state import SellState
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from app.chain.sell_chain import SellChain

class GreetingDialogue:
    def __init__(self):
        self.chain = SellChain()
    
    def user_input_node(self, state: SellState) -> SellState:
        print(f"> Node: user_input_node")
        user_input = interrupt(None)

        state["user_input"] = user_input
        state["messages"] = add_messages(state["messages"], [HumanMessage(content=user_input)])
        state["state_flow"].append("user_input_node")
        return state
    
    
