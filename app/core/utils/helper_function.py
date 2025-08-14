from typing import Any, Optional, Literal
from app.core.utils.class_parser import ProductChosen
from app.core.utils.graph_function import GraphFunction
from app.core.state import SellState
from app.models.normal_models import Order
from pydantic import BaseModel

graph_function = GraphFunction()
    
def get_chat_his(messages: list, 
                 start_offset: int = -10, 
                 stop_offset: Optional[int] = None
) -> list:
    sliced = messages[start_offset:stop_offset]
    try:
        return [{"type": chat.type, "content": chat.content} for chat in sliced]
    finally:
        return sliced

def get_customer_info(state: SellState):
    try:
        missing_info = []
        content = ""
        
        phone_number = state.get("phone_number", None)
        name = state.get("name", None)
        address = state.get("address", None)
        
        if phone_number is None:
            missing_info.append("phone number")
        if name is None:
            missing_info.append("name")
        if address is None:
            missing_info.append("address")
            
        if len(missing_info) > 0:
            content = f"Mising these customer info: {missing_info}."
        else:
            content = "Have all of customer info"
        
        return content
            
    except Exception as e:
        raise Exception(e)
    
def return_order(order_info: dict, order_items: list, order_id: int):
    try:
        content = f"Mã đơn hàng: {order_id}\n\n"
        index = 1
        
        for item in order_items:
            content += (
                f"STT: {index}.\n"
                f"Tên sản phẩm: {item["product_name"]}\n"
                f"Tên phân loại sản phẩm: {item["variance_name"]}\n"
                f"Mã sản phẩm: {item["product_id"]}\n"
                f"Mã SKU: {item["sku"]}\n"
                f"Giá của sản phẩm: {item["price"]}\n"
                f"Số lượng: {item["quantity"]}\n"
                f"Giá cuối cùng: {item["subtotal"]}\n\n"
            )
            index += 1
        
        content += (
            "Thông tin người nhận:\n"
            f"Tên khách hàng: {order_info["receiver_name"]}\n"
            f"Số điện thoại khách hàng: {order_info["receiver_phone_number"]}\n"
            f"Địa chỉ khách hàng: {order_info["receiver_address"]}\n"
            f"Phương thức thanh toán: {order_info["payment"]}\n"
            f"Ngày tạo đơn: {order_info["created_at"]}.\n"
            f"Ngày cập nhật đơn: {order_info["updated_at"]}.\n\n"
            
            "Giá trị đơn hàng:\n"
            f"Tổng đơn hàng (chưa tính phí ship): {order_info["order_total"]} VNĐ\n"
            f"Phí ship: {order_info["shipping_fee"]} VNĐ\n"
            f"Tổng đơn hàng (đã bao gồm phí ship): {order_info["grand_total"]} VNĐ\n"
        )
        
        return content
        
    except Exception as e:
        raise
    
def get_cart(cart: dict, 
              name: Optional[str], 
              phone_number: Optional[str], 
              address: Optional[str]
    ) -> str:
    
    cart_item = ""
    index = 1
    total = 0
    
    if cart:
        for key, item in cart.items():
            if key == "place_holder":
                continue
            
            cart_item += (
                f"STT: {index}\n"
                f"Tên sản phẩm: {item["Tên sản phẩm"]}\n"
                f"Tên phân loại: {item["Tên phân loại"]}\n"
                f"Mã sản phẩm: {int(item["Mã sản phẩm"])}\n"
                f"Mã phân loại: {item["Mã phân loại"]}\n"
                f"Giá: {item["Giá sản phẩm"]} VNĐ\n"
                f"Số lượng: {item["Số lượng"]} cái\n"
                f"Tổng giá sản phẩm: {item["Giá cuối cùng"]} VNĐ\n\n"
            )
            total += item["Giá cuối cùng"]
            index += 1

        cart_item += f"Tổng giá trị của giỏ hàng: {total}.\n\n"
        cart_item += (
            "Thông tin người nhận:\n"
            f"- Tên người nhận: {name if name else "Không có thông tin"}.\n"
            f"- Số điện thoại người nhận: {phone_number if phone_number else "Không có thông tin"}.\n"
            f"- Địa chỉ người nhận: {address if address else "Không có thông tin"}.\n"
        )
    else:
        cart_item += (
            "Không còn sản phẩm nào mà khách muốn mua.\n"
        )
    
    return cart_item

def add_cart(product: ProductChosen):
    product_id = int(product["product_id"])
    sku = product["sku"]
    key = f"{product_id} - {sku}"
    
    value = {
        "Mã sản phẩm": product_id,
        "Mã phân loại": sku,
        "Tên sản phẩm": product["product_name"],
        "Tên phân loại": product["variance_description"],
        "Giá sản phẩm":  int(product["price"]),
        "Số lượng": int(product["quantity"]),
        "Giá cuối cùng": int(product["quantity"]) * int(product["price"]),
    }
    
    return key, value

