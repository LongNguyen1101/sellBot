from langchain_core.tools import tool, InjectedToolCallId
from app.core.cart_agent.cart_prompts import update_cart_prompt, choose_product_prompt
from app.core.utils.graph_function import graph_function
from app.core.model import llm_tools
from app.core.state import SellState
from typing import Annotated, List, Literal, Optional, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.utils.helper_function import get_cart, add_cart, get_chat_his, return_order
from app.core.utils.class_parser import (
    AgentToolResponse,
    ProductChosen,
    UpdateCart,
)
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.log.logger_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)

@tool
def add_cart_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
    
) -> Command:
    """Use this tool to add product into cart"""
    try:
        update = {}
        tool_response: AgentToolResponse = {}
        
        seen_products = state["seen_products"]
        current_task = state["current_task"]
        phone_number = state["phone_number"]
        name = state["name"]
        address = state["address"]
        cart = state["cart"]
        
        if seen_products:
            logger.info("Seen products có sản phẩm")
            chat_histories = get_chat_his(
                messages=state["messages"],
                start_offset=-5
            )
            
            messages = [
                {"role": "system", "content": choose_product_prompt()},
                {"role": "human", "content": (
                    f"Danh sách các sản phẩm khách đã xem: {seen_products}\n"
                    f"Lịch sử chat: {chat_histories}\n"
                    f"Yêu cầu hiện tại: {current_task}.\n"
                    "Bạn hãy xác định sản phẩm mà khách chọn."
                )}
            ]
            
            response = llm_tools.with_structured_output(ProductChosen).invoke(messages)
            logger.info(f"Sản phẩm trả về: {response}")
            
            if response.get("product_id") is None:
                logger.info(f"Không xác định được product_id")
                tool_response = {
                    "status": "asking",
                    "content": (
                        "Không xác định được sản phẩm khách muốn hoặc không có sản phẩm nào đúng ý khách, "
                        "hãy dựa vào câu nói của khách để trả lời cho phù hợp."
                    )
                }
            else:
                logger.info(f"Xác định được product_id: {response["product_id"]}")
                key, value = add_cart(response)
                cart.pop("place_holder", None)
                cart[key] = value
                update["cart"] = cart
                cart_info = get_cart(cart, name, phone_number, address)
                
                tool_response = {
                    "status": "finish",
                    "content": (
                        "Nói xác nhận với khách đã chọn sản phẩm <bạn hãy tự điền>\n"
                        "Không được nói đã thêm sản phẩm vào giỏ hàng hay đơn hàng.\n"
                        "Sau đó liệt kê các sản phẩm của khách dưới đây đầy đủ, không được bỏ bớt hay tóm gọn thông tin nào:\n"
                        f"{cart_info}\n\n"
                        "Nếu thiếu thông tin (tên, địa chỉ, số điện thoại) nào thì nói khách cung cấp thông tin đó.\n"
                        "Nếu đả đủ cả 3 thông tin thì hỏi khách có muốn lên đơn luôn không.\n"
                    )
                }
        else:
            logger.info("Seen products không có sản phẩm")
            tool_response = {
                "status": "asking",
                "content": (
                    "Đây là số điện thoại của khách:\n"
                    f"{phone_number if phone_number else 'Không có số điện thoại'}.\n"
                    "Hãy thông báo và xin lỗi với khách là khách chưa xem sản phẩm nào nên không biết khách muốn "
                    "mua sản phẩm gì.\n"
                    "Thông báo cửa hàng bán các đồ điện tử thông minh trong nhà như "
                    "ổ cắm, công tắc, khóa cửa, đèn, rèm thông minh,..."
                    "Nếu không có thông tin số điện thoại của khách hàng thì hỏi khách để hỗ trợ tư vấn.\n"
                    "Nếu đã có số điện thoại của khách thì bỏ qua, không nói gì cả.\n"
                )
            }
        
        update.update({
            "messages": [
                ToolMessage
                (
                    content=tool_response["content"],
                    tool_call_id=tool_call_id
                )
            ],
            "status": tool_response["status"]
        })

        return Command(
            update=update
        )
    except Exception as e:
        raise Exception(e)
    
@tool
def get_cart_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to return items in cart to customer"""
    try:
        cart = state["cart"]
        name = state["name"]
        phone_number = state["phone_number"]
        address = state["address"]
        tool_response: AgentToolResponse = {}
        
        if cart and "place_holder" not in cart:
            logger.info("Giỏ hàng có sản phẩm")
            
            cart_item = get_cart(cart, name, phone_number, address)
            tool_response = {
                "status": "finish",
                "content": (
                    "Đây là thông tin các sản phẩm khách muốn mua:\n"
                    f"{cart_item}"

                    "Lưu ý:\n"
                    "- Xem các thông tin người nhận như tên, địa chỉ, số điện thoại "
                    "nếu thiếu thông tin nào thì hỏi khách cung cấp thông tin đó, "
                    "nếu đã đủ cả 3 thông tin thì hỏi khách muốn lên đơn luôn không.\n"
                    "- Cần trả lời chính xác cho khách về thông tin trên.\n"
                    "- Nếu có danh sách các sản phẩm thì trả về chính xác các sản phẩm đó.\n"
                    "- Nếu không có sản phẩm nào thì thông báo khách chưa chọn sản phẩm nào.\n"
                    "- Tuyệt đối không được tự đưa ra sản phẩm.\n"
                )
            }
        else:
            logger.info("Giỏ hàng không có sản phẩm")
            
            seen_products = state["seen_products"]
            tool_response = {
                "status": "asking",
                "content": (
                    "Giỏ hàng của khách đang trống.\n"
                    "Đây là thông tin các sản phẩm khách mới xem:\n"
                    f"{seen_products if seen_products else 'Không có sản phẩm nào'}.\n"
                    "Dựa vào thông tin trên hoặc lịch sử chat để hỏi khách có muốn mua gì không."
                )
            }
            
        
        return Command(
            update={
                "messages": [
                    ToolMessage
                    (
                        content=tool_response["content"],
                        tool_call_id=tool_call_id
                    )
                ],
                "status": tool_response["status"]
            }
        )
    except Exception as e:
        raise Exception(e)

@tool
def change_quantity_cart_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to change quantity of a specify product in cart"""
    cart = state["cart"].copy()
    current_task = state["current_task"]
    chat_histories = state["messages"]
    name = state["name"]
    phone_number = state["phone_number"]
    address = state["address"]
    
    msg = [
        {"role": "system", "content": update_cart_prompt()},
        {"role": "human", "content": (
            f"Đây là cart: {cart}.\n"
            f"Yêu cầu hiện tại: {current_task}.\n"
            f"Đây là lịch sử chat: {chat_histories}."
        )}
    ]
    
    result = llm_tools.with_structured_output(UpdateCart).invoke(msg)
    logger.info(f"Thông tin cập nhật số lượng trong giỏ hàng: {result}")
    
    key = result.get("key")
    update_quantity = int(result.get("update_quantity"))

    tool_response: AgentToolResponse = {}
    
    if key is None:
        logger.info("Không xác định được sản phẩm")
        tool_response = {
            "status": "incomplete_info",
            "content": "Không xác định được sản phẩm khách muốn thay đổi, hỏi lại khách."
        }
        
    elif update_quantity is None:
        logger.info("Không xác định được số lượng khách muốn đổi")
        tool_response = {
            "status": "incomplete_info",
            "content": "Không xác định được số lượng sản phẩm khách muốn thay đổi, hỏi lại khách."
        }
        
    elif update_quantity >= 0:
        logger.debug(f">>>> Update quantity: {update_quantity}")
        if update_quantity == 0:
            logger.info("Số lượng cập nhật = 0 -> xoá sản phẩm")
            cart.pop(key, None)
            logger.debug(f">>>> Đã xoá sản phẩm {key}")
            
        elif update_quantity > 0:
            logger.info("Số lượng cập nhật > 0 -> cập nhật sản phẩm")
            if key in cart:
                cart[key]["Số lượng"] = int(update_quantity)
                cart[key]["Giá cuối cùng"] = int(update_quantity) * cart[key]["Giá sản phẩm"]
            else:
                logger.error(f"Lỗi: {key} không có trong giỏ hàng")
                raise KeyError()
        
        cart_info = get_cart(cart, name, phone_number, address)
        tool_response = {
            "status": "finish",
            "content": (
                "Đã sửa lại thông tin cho khách, xác nhận lại với khách thông tin vừa sửa.\n"
                "Trả lại đầy đủ thông tin các sản phẩm cho khách, không được rút gọn:\n"
                f"{cart_info}\n"
                "Nếu danh sách trên rỗng thì nói khách hiện tại không có sản phẩm nào khách "
                "muốn mua.\n"
            )
        }
    
    if not cart:
        cart["place_holder"] = "None"
    
    update = {
        "cart": cart,
        "messages": [
            ToolMessage
            (
                content=tool_response["content"],
                tool_call_id=tool_call_id
            )
        ],
        "status": tool_response["status"]
    }
   
    return Command(
        update=update
    )
    
@tool
def update_receiver_info_in_cart_tool(
    name: Annotated[Optional[str], "Receiver name"],
    phone_number: Annotated[Optional[str], "Receiver phone number"],
    address: Annotated[Optional[str], "Receiver address"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to update name or phone number or address of receiver in cart"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            
            customer_id = state["customer_id"]
            cart = state["cart"]
            tool_response: AgentToolResponse = {}
            
            logger.info(
                "Các thông tin của khách cần cập nhật: "
                f"Tên: {name} | "
                f"Số điện thoại {phone_number} | "
                f"Địa chỉ {address}"
            )
            update_receiver = graph_function.update_customer_info(
                public_crud=public_crud,
                customer_id=customer_id,
                name=name,
                phone_number=phone_number,
                address=address,
                parse_object=False
            )
            
            if update_receiver:
                logger.info("Có thông tin trả về khi cập nhật khách")
                tool_response["content"] = ""
                if name is not None:
                    tool_response["content"] += f"Đã cập nhật tên của người nhận: {name}\n"
                if phone_number is not None:
                    tool_response["content"] += f"Đã cập nhật số điện thoại của người nhận: {phone_number}\n"
                if address is not None:
                    tool_response["content"] += f"Đã cập nhật địa chỉ của người nhận: {address}.\n"
                
                cart_info = get_cart(
                    cart, 
                    name if name else state["name"],
                    phone_number if phone_number else state["phone_number"], 
                    address if address else state["address"],
                )
                
                tool_response["status"] = "finish"
                tool_response["content"] += (
                    "Trả lại các sản phẩm cho khách, không được rút gọn, bỏ bớt hay tự bịa đặt thông tin:\n"
                    f"{cart_info}"
                )
            else:
                logger.error("Không có thông tin trả về khi cập nhật khách")
                tool_response = {
                    "status": "error",
                    "content": "Đã có lỗi xảy ra trong quá trình cập nhật thông tin khách hàng. Xin lỗi khách và xin quý khách thử lại."
                }
            
            update = {
                "name": update_receiver["name"],
                "phone_number": update_receiver["phone_number"],
                "address": update_receiver["address"],
                "messages": [
                    ToolMessage(
                        content=tool_response["content"],
                        tool_call_id=tool_call_id
                    )
                ],
                "status": tool_response["status"]
            }
            
            return Command(
                update=update
            )
            
    except Exception as e:
        raise Exception(e)