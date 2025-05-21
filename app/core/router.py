from app.chain.sell_chain import SellChain
from app.core.state import SellState
from langgraph.graph import END
from typing import List

class GraphRouter():
    def __init__(self):
        self.chain = SellChain()
        
    def check_intent_user_router(self, state: SellState) -> SellState:
        print(f"> Node: check_intent_user_router")
        
        intent_list = ["information", "product", "qna", "order", "update_order", "other"]
        user_input = state["user_input"]
        result = self.chain.check_intent_user().invoke(user_input)
        intent = "other"
        
        if result.content in intent_list:
            intent = result.content
        
        print(f"> Intent of user: {intent}")
        
        state["next_node"] = intent
        state["intent"] = intent
        state["state_flow"].append("check_intent_user_router")
        return state