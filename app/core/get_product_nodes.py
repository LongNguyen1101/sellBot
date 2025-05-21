from langgraph.types import interrupt
from app.core.state import SellState
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from app.chain.sell_chain import SellChain

class GetProductDialogue:
    def __init__(self):
        self.chain = SellChain()
        
    def get_product_node(self, state: SellState) -> SellState:
        pass