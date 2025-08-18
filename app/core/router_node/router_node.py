from app.core.state import SellState
from langgraph.types import Command
from app.core.model import llm
from app.log.logger_config import setup_logging

logger = setup_logging(__name__)

MEMBERS = (["product_agent", "cart_agent", "order_agent", "customer_agent",
            "customer_service_agent", "irrelevant_agent", "store_info_agent"])
OPTIONS = MEMBERS + ["FINISH"]

class RouterNodes:
    def __init__(self):
        self.members = MEMBERS
        self.options = OPTIONS
        self.llm = llm

    def router(self, 
               state: SellState
    ) -> Command:
        tasks = state["tasks"]
        current_task = None
        next_node = "__end__"
        
        if len(tasks) > 0:
            current_task = tasks[0]["sub_query"]
            next_node = tasks[0]["agent"]
            tasks.pop(0)
            logger.info(f"Đang xử lý tasks: {current_task}")
            
        return Command(
            update={
                "next_node": next_node,
                "tasks": tasks,
                "current_task": current_task
            },
            goto=next_node
        )
