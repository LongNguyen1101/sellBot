from app.chain.sell_chain import SellChain
from app.core.state import SellState
from langgraph.graph import END
from typing import List
import json

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
        state["node_flow"].append("check_intent_user_router")
        return state
    
    def check_exists_product_router(self, state: SellState) -> SellState:
        print(f"> Node: check_exists_product_router")
        
        list_products = state["list_products"]
        next_node = "no"
        
        if len(list_products) > 0:
            next_node = "yes"
            
        state["next_node"] = next_node
        state["node_flow"].append("check_exists_product_router")
        return state
    
    def check_identify_product_router(self, state: SellState) -> SellState:
        print(f"> Node: check_exists_product_router")
        
        user_input = state["user_input"]
        products = state["list_products"]
        next_node = "identified"
        
        if len(products) > 5:
            products = products[:5]
        
        response = self.chain.check_identify_product().invoke({
            "products": products,
            "user_input": user_input
        })
        data = response.content.replace("```json\n", "").replace("\n```", "").replace("\n", "")
        data = json.loads(data)
        
        if data.get("product_id", None) is None or data.get("sku", None) is None or data.get("quantity", None) is None:
            next_node = "need_identify"
        else:
            state["cart"].append(data)
            
        print(F"> Identify product: {data}")
        
        state["next_node"] = next_node
        state["node_flow"].append("check_identify_product_router")
        return state
    
    def check_user_confirm_cart_router(self, state: SellState) -> SellState:
        print(f"> Node: check_user_confirm_router")
        
        intent_list = ["add_product", "confirm", "cancel"]
        next_node = "cancel"
        user_input = state["user_input"]
        result = self.chain.check_user_confirm_cart().invoke(user_input).content
        
        if result in intent_list:
            next_node = result
        print(f"> Check user confirm: {next_node}")
         
        state["next_node"] = next_node
        state["node_flow"].append("check_user_confirm_router")
        return state