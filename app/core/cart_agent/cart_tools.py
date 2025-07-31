from langchain_core.tools import tool, InjectedToolCallId
from app.core.cart_agent.cart_prompts import update_cart_prompt, choose_product_prompt
from app.core.graph_function import GraphFunction
from app.core.model import init_model
from app.core.state import SellState
from typing import Annotated, List, Literal, Optional, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.helper_function import _get_cart, _add_cart, _return_order


graph_function = GraphFunction()
llm = init_model()

class ProductChosen(TypedDict):
    product_id: Optional[int]
    sku: Optional[str]
    product_name: Optional[str]
    variance_description: Optional[str]
    price: Optional[int]

class AddCart(TypedDict):
    product_id: int
    sku: str
    product_name: str
    variance_description: str
    quantity: int
    price: int
    
class UpdateCart(TypedDict):
    key: Optional[str]
    update_quantity: Optional[int]

class RemoveProduct(TypedDict):
    product_id: Optional[int]
    sku: Optional[str]

@tool
def add_cart(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
    
) -> Command:
    """Use this tool to add product into cart"""
    try:
        seen_products = state["seen_products"]
        user_input = state["user_input"]
        cart = state["cart"]
        
        phone_number = state["phone_number"]
        name = state["name"]
        address = state["address"]

        content = ""
        update = {}

        messages = state["messages"][-5:]
        chat_histories = [
            {
                "type": chat.type,
                "content": chat.content
            } for chat in messages
        ]

        messages = [
            {"role": "system", "content": choose_product_prompt()},
            {"role": "human", "content": (
                f"Danh sách các sản phẩm khách đã xem: {seen_products}\n"
                f"Lịch sử chat: {chat_histories}\n"
                f"Tin nhắn của khách: {user_input}\n"
                "Bạn hãy xác định sản phẩm mà khách chọn."
            )}
        ]

        response = llm.with_structured_output(ProductChosen).invoke(messages)

        if response["product_id"] is None:
            content += (
                "Không xác định được sản phẩm khách muốn hoặc không có sản phẩm nào đúng ý khách, "
                "hãy dựa vào câu nói của khách để trả lời cho phù hợp."
            )
        else:
            key, value = _add_cart(response)
            cart.pop("place_holder", None)
            cart[key] = value
            update["cart"] = cart
            
            get_cart = _get_cart(cart, name, phone_number, address)

            content += (
                "Nói xác nhận với khách đã chọn sản phẩm <bạn hãy tự điền>\n"
                "Không được nói đã thêm sản phẩm vào giỏ hàng hay đơn hàng.\n"
                "Hãy nói xác nhận khách đã chọn sản phẩm <bạn hãy tự điền>.\n"
                "Sau đó liệt kê thông tin dưới đây đầy đủ, không được bỏ bớt hay tóm gọn thông tin nào.\n"
                f"Đây là các sản phẩm của khách, hãy trả về y nguyên để khách kiểm tra:\n"
                f"{get_cart}\n\n"
                "Nếu thiếu thông tin (tên, địa chỉ, số điện thoại) nào thì nói khách cung cấp thông tin đó.\n"
            )
            
            # if phone_number is None:
            #     content += (
            #         "Chưa có thông tin số điện thoại của khách.\n"
            #         f"Đây là các sản phẩm của khách, hãy trả về y nguyên để khách kiểm tra:\n"
            #         f"{get_cart}\n\n"
            #         "Nhờ khách kiểm tra lại và xin các thông tin còn thiếu để tiến hành lên đơn cho khách."
            #     )
            # else:
            #     if not name:
            #         content += "Không có thông tin tên người nhận, hỏi khách tên người nhận.\n"
            #     if not phone_number:
            #         content += "Không có thông tin địa chỉ người nhận, hỏi khách địa chỉ người nhận.\n"
                
            #     content += (
            #         "Đã có thông tin số điện thoại của khách.\n"
            #         f"Đây là các sản phẩm của khách, hãy trả về y nguyên để khách kiểm tra:\n"
            #         f"{get_cart}\n\n"
            #         "Nhờ khách kiểm tra lại thông tin trên.\n"
            #         "Nếu đã có đủ tên và địa chỉ người nhận thì hỏi khách muốn lên đơn luôn không.\n"
            #         "Nếu thiếu một trong hai hoặc cả hai thông tin tên và địa chỉ người nhận thì hỏi khách.\n"
            #     )


        update["messages"] = [
            ToolMessage
            (
                content=content,
                tool_call_id=tool_call_id
            ),
        ]

        return Command(
            update=update
        )
    except Exception as e:
        raise Exception(e)
    
@tool
def get_cart(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to return items in cart to customer"""
    try:
        cart = state["cart"]
        name = state["name"] if state["name"] else "Không có thông tin"
        phone_number = state["phone_number"]
        address = state["address"] if state["address"] else "Không có thông tin"
        customer_id = state["customer_id"]
        content = ""
        
        if cart:
            cart_item = _get_cart(cart, name, phone_number, address)
            content += (
                "Đây là thông tin các sản phẩm khách muốn mua:\n"
                f"{cart_item}"

                "Lưu ý:\n"
                "- Cần trả lời chính xác cho khách về thông tin trên.\n"
                "- Nếu có danh sách các sản phẩm thì trả về chính xác các sản phẩm đó.\n"
                "- Nếu không có sản phẩm nào thì thông báo khách chưa chọn sản phẩm nào.\n"
                "- Tuyệt đối không được tự đưa ra sản phẩm.\n"
            )

            if phone_number:
                content += "Đã có số điện thoại của khách.\n"
                unshipped_order = graph_function.get_unshipped_order(customer_id)

                if unshipped_order:
                    order_info, order_items = graph_function.get_order_detail(unshipped_order.order_id)
                    order_detail = _return_order(order_info, order_items, unshipped_order.order_id)
                    content += (
                        "Khách có đơn chưa vận chuyển:\n"
                        f"{order_detail}."
                        "Hiển thị đầy đủ đơn hàng khách đã đặt, thông báo nếu khách muốn lên đơn "
                        "thì sản phẩm của khách sẽ được gộp vào đơn hàng này của khách.\n"
                    )

                content += (
                    "Hỏi khách kiểm tra lại lại các sản phẩm, nếu đúng thì lên đơn.\n"
                )
            else:
                content += (
                    "Chưa có số điện thoại của khách.\n"
                    "Hỏi khách số điện thoại để dễ dàng tư vấn cho khách.\n"
                )
        else:
            content += (
                "Giỏ hàng của khách đang trống.\n"
                "Dựa vào seen_products hoặc lịch sử chat để hỏi khách có muốn mua gì không."
            )
            
        
        return Command(
            update={
                "messages": [
                    ToolMessage
                    (
                        content=content,
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
    except Exception as e:
        raise Exception(e)

@tool
def update_cart(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to change quantity of a specify product in cart"""
    content = ""
    cart = state["cart"]
    user_input = state["user_input"]
    chat_histories = state["messages"]
    update = {}
    
    name = state["name"]
    phone_number = state["phone_number"]
    address = state["address"]
    
    msg = [
        {"role": "system", "content": update_cart_prompt()},
        {"role": "human", "content": (
            f"Đây là cart: {cart}.\n"
            f"Đây là yêu cầu của người dùng: {user_input}.\n"
            f"Đây là lịch sử chat: {chat_histories}."
        )}
    ]
    
    result = llm.with_structured_output(UpdateCart).invoke(msg)
    key = result["key"]
    update_quantity = result["update_quantity"]
    
    if result["key"] is None:
        content = "Không xác định được sản phẩm khách muốn thay đổi, hỏi lại khách."
    else:
        print(f">>>> update_quantity: {update_quantity}")
        if update_quantity is None:
            content = "Không xác định được số lượng sản phẩm khách muốn thay đổi, hỏi lại khách."
        elif update_quantity == 0:
            # delete cart with key found
            del cart[key]
            print(f">>>> Đã xoá {key}")
        else:
            cart[key]["Số lượng"] = int(update_quantity)
            cart[key]["Giá cuối cùng"] = int(update_quantity) * cart[key]["Giá sản phẩm"]
        
        get_cart = _get_cart(cart, name, phone_number, address)
            
        content = (
            "Đã sửa lại thông tin cho khách, xác nhận lại với khách thông tin vừa sửa.\n"
            "Trả lại các sản phẩm cho khách:\n"
            f"{get_cart}"
        )
    
    if not cart:
        cart["place_holder"] = "None"
    
    update["cart"] = cart
    update["messages"] = [
        ToolMessage
        (
            content=content,
            tool_call_id=tool_call_id
        )
    ]
   
    return Command(
        update=update
    )
    
@tool
def update_receiver_information_in_cart(
    name: Annotated[Optional[str], "Receiver name"],
    phone_number: Annotated[Optional[str], "Receiver phone number"],
    address: Annotated[Optional[str], "Receiver address"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to update name or phone number or address of receiver in cart"""
    try:
        update = {}
        content = ""
        customer_id = state["customer_id"]
        cart = state["cart"]
        
        update["name"] = name
        update["phone_number"] = phone_number
        update["address"] = address
        
        update_receiver = graph_function.update_customer_info(
            customer_id=customer_id,
            name=name,
            phone_number=phone_number,
            address=address
        )
        
        if update_receiver is not None:
            if name is not None:
                content += f"Đã cập nhật tên của người nhận: {name}\n"
            if phone_number is not None:
                content += f"Đã cập nhật số điện thoại của người nhận: {phone_number}\n"
            if address is not None:
                content += f"Đã câp địa chỉ của người nhận: {address}.\n"
            
            get_cart = _get_cart(cart, name, phone_number, address)
                
            content += (
                "\nTrả lại các sản phẩm cho khách:\n"
                f"{get_cart}"
            )
        else:
            content += "Đã có lỗi xảy ra trong quá trình cập nhật thông tin khách hàng. Xin lỗi khách và xin quý khách thử lại."
            
        update["messages"] = [
            ToolMessage
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]
        
        return Command(
            update=update
        )
        
    except Exception as e:
        raise Exception(e)