from app.core.supervisor_agent.supervisor_prompts import supervisor_system_prompt
from app.core.state import SellState
from typing import Literal, TypedDict
from langgraph.types import Command
from app.core.model import init_model
from app.core.utils.class_parser import Router
from app.core.utils.helper_function import get_chat_his


MEMBERS = (["product_agent", "cart_agent", "order_agent", "customer_agent",
            "customer_service_agent", "irrelevant_agent", "store_info_agent"])
OPTIONS = MEMBERS + ["FINISH"]

class SupervisorNodes:
    def __init__(self):
        self.members = MEMBERS
        self.options = OPTIONS
        self.llm = init_model()

    def supervisor_agent(self, 
                         state: SellState
    ) -> Command:
        tasks = state["tasks"]
        next_node = "__end__"
        
        if len(tasks) > 0:
            chat_his = get_chat_his(
                messages=state["messages"],
                start_offset=-10,
            )
            
            current_task = tasks[0]["sub_query"]
            tasks.pop(0)
            
            customer_id = state["customer_id"]
            cart = state["cart"]
            seen_products = state["seen_products"]
            orders = state["orders"]
            
            print(f">>>> Đang xử lý tasks: {current_task}")

            messages = [
                {"role": "system", "content": supervisor_system_prompt(members=self.members)},
                {"role": "human", "content": (
                    f"Yêu cầu hiện tại: {current_task}.\n"
                    # f"Lịch sử chat: {chat_his}\n"
                    f"customer_id: {customer_id}\n"
                    f"cart {cart}\n"
                    f"seen_products: {seen_products}\n"
                    f"orders: {orders}\n"
                )}
            ]

            response = self.llm.with_structured_output(Router).invoke(messages)
            next_node = response["next"]
            

        return Command(
            update={
                "next_node": next_node,
                "tasks": tasks
            },
            goto=next_node
        )
