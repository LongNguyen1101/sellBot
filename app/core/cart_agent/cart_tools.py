from langchain_core.tools import tool, InjectedToolCallId
from app.core.cart_agent.cart_prompts import update_cart_prompt, choose_product_prompt
from app.core.utils.graph_function import graph_function
from app.core.model import llm_tools
from app.core.state import SellState
from typing import Annotated, List, Literal, Optional, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.utils.helper_function import build_update, get_cart, add_cart, get_chat_his
from app.core.utils.class_parser import (
    ProductChosen,
    UpdateCart,
)
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.log.logger_config import setup_logging

logger = setup_logging(__name__)

def _choose_product(
    seen_products: list,
    current_task: str,
    messages: list
):
    chat_histories = get_chat_his(
        messages=messages,
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
    
    return llm_tools.with_structured_output(ProductChosen).invoke(messages)

def _find_product_to_update(
    cart: dict,
    current_task: str,
    chat_histories: list
):
    msg = [
        {"role": "system", "content": update_cart_prompt()},
        {"role": "human", "content": (
            f"Yêu cầu hiện tại (current_task): {current_task}.\n"
            f"Đây là giỏ hàng (cart): {cart}.\n"
            f"Đây là lịch sử chat (chat_histories): {chat_histories}."
        )}
    ]
    
    result = llm_tools.with_structured_output(UpdateCart).invoke(msg)
    logger.info(f"Thông tin cập nhật số lượng trong giỏ hàng: {result}")
    
    key = str(result.get("key")) if result.get("key") else result.get("key")
    update_quantity = int(result.get("update_quantity")) if result.get("update_quantity") else result.get("update_quantity")
    
    return key, update_quantity

def _update_quantity(
    cart: dict,
    key: str,
    update_quantity: int
):  
    if key in cart:
        logger.info(f"{key} có trong giỏ hàng -> cập nhật")
        cart[key]["Số lượng"] = int(update_quantity)
        cart[key]["Giá cuối cùng"] = int(update_quantity) * cart[key]["Giá sản phẩm"]
        return cart
    
    return None

def _handle_exception(
    key: str,
    update_quantity: int,
    tool_call_id: str,
    need_quantity: bool = True,
) -> dict | None:
    if key is None:
        logger.info("Không xác định được sản phẩm")

        return build_update(
            content="Không xác định được sản phẩm khách muốn thay đổi, hỏi lại khách.",
            status="incomplete_info",
            tool_call_id=tool_call_id
        )
    
    if need_quantity and update_quantity is None:
        logger.info("Không xác định được số lượng khách muốn đổi")

        return build_update(
            content="Không xác định được số lượng sản phẩm khách muốn thay đổi, hỏi lại khách",
            status="incomplete_info",
            tool_call_id=tool_call_id
        )
    
    return None

def _handle_remove_item(
    cart: dict,
    key: str,
    name: str,
    phone_number: str,
    address: str,
    tool_call_id: str
):
    cart.pop(key, None)
    
    if not cart:
        logger.info("Giỏ hàng trống -> đặt place_holder")
        cart["place_holder"] = "None"
        return build_update(
            content="Xác nhận với khách đã xoá sản phẩm <bạn tự điền vào> thì giỏ hàng trống, hỏi khách có muốn mua gì tiếp không",
            status="finish",
            tool_call_id=tool_call_id,
            cart=cart
        )
    
    logger.info(f"Đã xoá sản phẩm {key} ra khỏi giỏ hàng")
    cart_info = get_cart(
        cart=cart,
        name=name,
        phone_number=phone_number,
        address=address
    )
    
    return build_update(
        content=(
            "Xác nhận với khách đã xoá sản phẩm <bạn tự điền vào>.\n"
            "Sau đó liệt kê các sản phẩm của khách dưới đây đầy đủ, không được bỏ bớt hay tóm gọn thông tin nào:\n"
            f"{cart_info}\n\n"
        ),
        status="finish",
        tool_call_id=tool_call_id,
        cart=cart
    )

@tool
def add_cart_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
    
) -> Command:
    """Use this tool to add product into cart"""
    try:
        seen_products = state["seen_products"]
        phone_number = state["phone_number"]
        cart = state["cart"]
        
        if not seen_products:
            logger.info("Seen products không có sản phẩm")
            return Command(
                update=build_update(
                    content=(
                        "Đây là số điện thoại của khách:\n"
                        f"{phone_number if phone_number else 'Không có số điện thoại'}.\n"
                        "Hãy thông báo và xin lỗi với khách là khách chưa xem sản phẩm nào nên không biết khách muốn "
                        "mua sản phẩm gì.\n"
                        "Thông báo cửa hàng bán các đồ điện tử thông minh trong nhà như "
                        "ổ cắm, công tắc, khóa cửa, đèn, rèm thông minh,..."
                        "Nếu không có thông tin số điện thoại của khách hàng thì hỏi khách để hỗ trợ tư vấn.\n"
                        "Nếu đã có số điện thoại của khách thì bỏ qua, không nói gì cả.\n"
                    ),
                    status="asking",
                    tool_call_id=tool_call_id
                )
            )
        
        logger.info("Seen products có sản phẩm")
        
        response = _choose_product(
            seen_products=seen_products,
            current_task=state["current_task"],
            messages=state["messages"],
        )
        logger.info(f"Sản phẩm trả về: {response}")
        
        if response.get("product_id") is None:
            logger.info("Không xác định được sản phẩm khách muốn thêm -> đi tìm sản phẩm đó trong product_agent")
            
            # Add task to query product in database if LLM cannot identify the product in seen_products
            tasks = state["tasks"].copy()
            tasks.insert(0, {
                "id": 1,
                "agent": "product_agent",
                "sub_query": (
                    "Lấy ra sản phẩm có trong yêu cầu sau: "
                    f"'{state["current_task"]}'"
                )
            })
            
            return Command(
                update=build_update(
                    content="Không cần tạo phản hồi",
                    status="finish",
                    tool_call_id=tool_call_id,
                    tasks=tasks
                )
            )
            
        logger.info(f"Xác định được sản phẩm {response["product_id"]} | {response["sku"]}")
        key, value = add_cart(response)
        cart.pop("place_holder", None)
        cart[key] = value
        cart_info = get_cart(
            cart, 
            state["name"], 
            phone_number, 
            state["address"]
        )
        
        return Command(
            update=build_update(
                content=(
                    "Nói xác nhận với khách đã chọn sản phẩm <bạn hãy tự điền>\n"
                    "Không được nói đã thêm sản phẩm vào giỏ hàng hay đơn hàng.\n"
                    "Sau đó liệt kê các sản phẩm của khách dưới đây đầy đủ, không được bỏ bớt hay tóm gọn thông tin nào:\n"
                    f"{cart_info}\n\n"
                    "Nếu thiếu thông tin (tên, địa chỉ, số điện thoại) nào thì nói khách cung cấp thông tin đó.\n"
                    "Nếu đả đủ cả 3 thông tin thì hỏi khách có muốn lên đơn luôn không.\n"
                ),
                status="finish",
                tool_call_id=tool_call_id,
                cart=cart
            )
        )
        
    except Exception as e:
        raise
    
@tool
def get_cart_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to return items in cart to customer"""
    try:
        cart = state["cart"]
        
        if cart and "place_holder" not in cart:
            logger.info("Giỏ hàng có sản phẩm")
            
            cart_item = get_cart(
                cart, 
                state["name"], 
                state["phone_number"], 
                state["address"]
            )
            
            return Command(
                update=build_update(
                    content=(
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
                    ),
                    status="finish",
                    tool_call_id=tool_call_id
                )
            )
            
            
        logger.info("Giỏ hàng không có sản phẩm")
        
        seen_products = state["seen_products"]
        return Command(
            update=build_update(
                content=(
                    "Giỏ hàng của khách đang trống.\n"
                    "Đây là thông tin các sản phẩm khách mới xem:\n"
                    f"{seen_products if seen_products else 'Không có sản phẩm nào'}.\n"
                    "Dựa vào thông tin trên hoặc lịch sử chat để hỏi khách có muốn mua gì không."
                ),
                status="asking",
                tool_call_id=tool_call_id
            )
        )
    except Exception as e:
        raise

@tool
def change_quantity_cart_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to change quantity of a specify product in cart"""
    cart = state["cart"]
    
    key, update_quantity = _find_product_to_update(
        cart=cart,
        current_task=state["current_task"],
        chat_histories=get_chat_his(
            messages=state["messages"],
            start_offset=-10
        )
    )
    
    # Handel exception
    update_unvalid = _handle_exception(
        key=key,
        update_quantity=update_quantity,
        tool_call_id=tool_call_id
    )
    
    if update_unvalid:
        return Command(update=update_unvalid)
    
    # Key and update_quantity are determined
    logger.info("Đã có đầy đủ thông tin sản phẩm và số lượng muốn cập nhật")
    logger.info(f"Cập nhật số lượng thành: {update_quantity}")
    
    if update_quantity == 0:
        logger.info("Sau khi cập nhật thì số lượng sản phẩm = 0")
        
        update = _handle_remove_item(
            cart=cart,
            key=key,
            name=state["name"], 
            phone_number=state["phone_number"], 
            address=state["address"],
            tool_call_id=tool_call_id
        )
        
        return Command(update=update)
    
    logger.info("Sau khi cập nhật thì số lượng sản phẩm > 0")
    new_cart = _update_quantity(
        cart=cart.copy(),
        key=key,
        update_quantity=update_quantity
    )
    
    if not new_cart:
        logger.error(f"Lỗi: {key} không có trong giỏ hàng")
        return Command(
            update=build_update(
                content="Đã có lỗi trong lúc xác định sản phẩm mà khách muốn cập nhật.",
                status="error",
                tool_call_id=tool_call_id
            )
        )
    
    logger.info("Đã Thay đổi số lượng sản phẩm trong giỏ hàng thành công")
    cart_info = get_cart(
        cart=new_cart, 
        name=state["name"], 
        phone_number=state["phone_number"], 
        address=state["address"]
    )
    
    return Command(
        update=build_update(
            content=(
                "Đã sửa lại thông tin cho khách, xác nhận lại với khách thông tin vừa sửa.\n"
                "Trả lại đầy đủ thông tin các sản phẩm cho khách, không được rút gọn:\n"
                f"{cart_info}\n"
                "Nếu danh sách trên rỗng thì nói khách hiện tại không có sản phẩm nào khách "
                "muốn mua.\n"
            ),
            status="finish",
            tool_call_id=tool_call_id,
            cart=new_cart
        )
    )
    

@tool
def remove_item_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to remove product in cart"""
    cart = state["cart"]
    
    key, update_quantity = _find_product_to_update(
        cart=cart,
        current_task=state["current_task"],
        chat_histories=get_chat_his(
            messages=state["messages"],
            start_offset=-10
        )
    )
    
    # Handel exception
    update_unvalid = _handle_exception(
        key=key,
        update_quantity=update_quantity,
        need_quantity=False,
        tool_call_id=tool_call_id
    )
    
    if update_unvalid:
        return Command(update=update_unvalid)
    
    # Key are determined
    logger.info(f"Xác định được key trong giỏ hàng: {key}")
    
    update = _handle_remove_item(
        cart=cart,
        key=key,
        name=state["name"], 
        phone_number=state["phone_number"], 
        address=state["address"],
        tool_call_id=tool_call_id
    )
    
    return Command(update=update)

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
            
            logger.info(
                "Các thông tin của khách cần cập nhật: "
                f"Tên: {name} | "
                f"Số điện thoại {phone_number} | "
                f"Địa chỉ {address}"
            )
            
            update_receiver = graph_function.update_customer_info(
                public_crud=public_crud,
                customer_id=state["customer_id"],
                name=name,
                phone_number=phone_number,
                address=address,
                parse_object=False
            )
            
            if not update_receiver:
                logger.error("Đã xảy ra lỗi trong quá trình cập nhật thông tin người nhận")
                return Command(
                    update=build_update(
                        content="Đã có lỗi xảy ra trong quá trình cập nhật thông tin khách hàng. Xin lỗi khách và xin quý khách thử lại.",
                        status="error",
                        tool_call_id=tool_call_id
                    )
                )
            
            logger.info("Có thông tin trả về khi cập nhật khách")
            log = ""
            log += f"Đã cập nhật tên của người nhận: {name}. " if name is not None else ""
            log += f"Đã cập nhật số điện thoại của người nhận: {phone_number}. " if phone_number is not None else ""
            log += f"Đã cập nhật địa chỉ của người nhận: {address}." if address is not None else ""

            logger.info(f"Các thông tin cập nhật: {log}")
            
            cart_info = get_cart(
                state["cart"], 
                name if name else state["name"],
                phone_number if phone_number else state["phone_number"], 
                address if address else state["address"],
            )
            
            return Command(
                update=build_update(
                    content=(
                        "Các thông tin đã cập nhật của khách, hãy thông báo cho khách:\n"
                        f"{log}\n\n"
                        "Trả lại các sản phẩm cho khách, không được rút gọn, bỏ bớt hay tự bịa đặt thông tin:\n"
                        f"{cart_info}"
                    ),
                    status="finish",
                    tool_call_id=tool_call_id,
                    name=update_receiver["name"],
                    phone_number=update_receiver["phone_number"],
                    address=update_receiver["address"]
                )
            )
            
    except Exception as e:
        raise