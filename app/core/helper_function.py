from app.core.graph_function import GraphFunction
from app.core.state import SellState

graph_function = GraphFunction()

def _get_customer_info(state: SellState):
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
    
def _return_order(order_id: int):
    try:
        order_items = graph_function.get_order_items_detail(order_id)
        order_info = graph_function.get_order_info(order_id)
        
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
            f"Tên khách hàng: {order_info["customer_name"]}\n"
            f"Số điện thoại khách hàng: {order_info["customer_phone"]}\n"
            f"Địa chỉ khách hàng: {order_info["customer_address"]}\n"
            f"Phương thức thanh toán: {order_info["payment"]}\n"
            f"Tổng đơn hàng (chưa tính phí ship): {order_info["order_total"]}\n"
            f"Phí ship: {order_info["shipping_fee"]}\n"
            f"Tổng đơn hàng (đã bao gồm phí ship): {order_info["grand_total"]}\n"
        )
        
        return content, order_items
        
    except Exception as e:
        raise
    
def _get_cart(cart, name, phone_number, address) -> str:
    cart_item = ""
    index = 1
    total = 0
    
    for item in cart:
        cart_item += (
            f"STT: {index}\n"
            f"Tên sản phẩm: {item["product_name"]}\n"
            f"Tên phân loại: {item["variance_description"]}\n"
            f"Mã sản phẩm: {item["product_id"]}\n"
            f"Mã phân loại: {item["sku"]}\n"
            f"Giá: {item["price"]} VNĐ\n"
            f"Số lượng: {item["quantity"]} cái\n"
            f"Tổng giá sản phẩm: {item["subtotal"]} VNĐ\n\n"
        )
        total += item["subtotal"]
        index += 1
        
    cart_item += f"Tổng giá trị của giỏ hàng: {total}"
    cart_item += (
        "Thông tin người nhận:\n"
        f"- Tên người nhận: {name}.\n"
        f"- Số điện thoại người nhận: {phone_number}.\n"
        f"- Địa chỉ người nhận: {address}.\n"
    )
    
    return cart_item

def generate_sql(user_input: str, prompt: str) -> str:
        pass