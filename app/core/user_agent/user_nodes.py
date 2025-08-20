from typing import Any, Literal, Optional, Tuple
from langgraph.types import Command
from app.core.state import SellState
from langchain_core.messages import HumanMessage, AIMessage
from app.core.model import llm
from app.core.user_agent.user_prompts import split_and_rewrite_prompt
from app.core.utils.class_parser import SplitRequestOutput
from app.core.utils.helper_function import build_update, get_chat_his
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.core.utils.graph_function import graph_function
from app.log.logger_config import setup_logging
import random


logger = setup_logging(__name__)

def _get_or_create_customer(chat_id: int) ->dict:
    with session_scope() as sess:
        public_crud = PublicCRUD(sess)
        
        # Find customer or create a new one
        customer = graph_function.get_or_create_customer(
            chat_id=chat_id, 
            public_crud=public_crud,
            parse_object=False
        )
        
        logger.info(
            "Tìm thấy thông tin của khách: "
            f"Tên: {customer["name"]} | "
            f"Số điện thoại: {customer["phone_number"]} | "
            f"Địa chỉ: {customer["address"]} | "
            f"ID khách: {customer["customer_id"]}.", 
            color="green"
        )
        
        return customer
    
def _split_task(
    llm: Any,
    user_input: str,
    messages: list,
    orders: list,
    cart: dict,
    seen_products: list
):
    chat_his = get_chat_his(
        messages=messages,
        start_offset=-10
    )
    
    messages = [
        {"role": "system", "content": split_and_rewrite_prompt()},
        {"role": "human", "content": (
            f"Yêu cầu của khách: {user_input}.\n"
            f"Lịch sử chat: {chat_his}.\n"
            f"Danh sách đơn hàng của khách (orders): {orders}.\n"
            f"Danh sách các sản phẩm khách muốn mua (cart): {cart}.\n"
            f"Danh sách các sản phẩm khách đã xem (seen_products): {seen_products}.\n"
        )}
    ]
    
    response = llm.with_structured_output(SplitRequestOutput).invoke(messages)
    return response["tasks"]

class UserNodes:
    def __init__(self):
        self.llm = llm
        
    def user_input_node(self, state: SellState) -> Command[Literal["planner_node"]]:
        user_input = state["user_input"]
        update = {}
        
        if not state["customer_id"]:
            logger.info("Chưa có thông tin khách hàng -> tìm hoặc tạo mới")
            customer = _get_or_create_customer(chat_id=state["chat_id"])
            
            update.update({
                "customer_id": customer["customer_id"],
                "name": customer["name"],
                "address": customer["address"],
                "phone_number": customer["phone_number"]
            })

        logger.info("Đã có thông tin khách hàng")     
        update["messages"] = [HumanMessage(content=user_input, name="user_input_node")]
        
        return Command(
            update=update,
            goto="planner_node"
        )
        
    def planner_node(self, state: SellState) -> Command:
        update = {}
        
        tasks = _split_task(
            llm=self.llm,
            user_input=state["user_input"],
            messages=state["messages"],
            orders=state.get("orders", []),
            cart=state.get("cart", {}),
            seen_products=state.get("seen_products", [])
        )
        logger.info(f"Danh sách tasks: {tasks}", color="green")
        
        if len(tasks) > 1:
            waiting_messages = [
                "Dạ khách cứ thong thả, khách pha thêm ly trà thơm thơm rồi chờ em trả kết quả nè ☕🍃😊.",
                "Dạ khách ăn miếng bánh, uống miếng trà đợi em một chút nhe 🍰☕😉.",
                "Khách chờ máy một chút, em pha ly cafe cho tỉnh táo rồi quay lại ngay ☕😎💨.",
                "Dạ khách đợi xíu, em vắt óc suy nghĩ cho vừa vị 🤔🧠✨.",
                "Em đang đói nên khách chờ em ăn xíu nhenn, cám ơn khách nhìu 🍔😋🙏.",
                "Khách thong thả tí nha, em đang tập yoga cho trí não tỉnh táo xíu 🧘‍♀️💭😊.",
                "Em mới tới công ty nên khách chờ em pha cà phê xíu nhenn ☕🏢😄.",
                "Em đang cãi nhau với sếp, khách đợi em xíu em xử lý sếp em xong rồi qua với khách ạ 😅👩‍💼🔥.",
                "Hôm nay trời đẹp nhưng em không có hứng làm việc lắm, khách đợi mấy giây để em tìm cảm hứng nhe 🌞😌🎨.",
                "Nay sếp la em quá trời nên khách chờ em xíu em lau nước mắt rồi nhắn khách nhenn 😢🧻😂🙏.",
                "Nay sếp em vui nên mua trà sữa đãi nhân viên, khách đợi em húp xong ly trà sữa trân châu x3 phô mai này rồi nhắn lại khách nhenn 🥤😋🧀✨😊."
            ]

            idx = random.randint(0, len(waiting_messages) - 1)
            content = waiting_messages[idx]

            update["messages"] = [AIMessage(content=content, name="split_request_node")]
        
        update["tasks"] = tasks
        
        return Command(
            update=update,
            goto="router_node"
        )
        
        