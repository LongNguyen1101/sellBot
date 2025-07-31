from langchain_core.tools import tool, InjectedToolCallId
from app.core.graph_function import GraphFunction
from app.core.model import init_model
from app.core.product_agent.product_prompts import create_response_rag
from app.core.state import SellState
from typing import Annotated, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from typing import Optional
from app.core.helper_function import _add_cart

graph_function = GraphFunction()
llm = init_model()

class ProductChosen(TypedDict):
    product_id: Optional[int]
    sku: Optional[str]
    product_name: Optional[str]
    variance_description: Optional[str]
    price: Optional[int]
    

@tool
def get_products(
    keyword: Annotated[str, "The keyword of products"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to get products from database follow by the keyword of customer"""
    try:
        cart = state["cart"]
        seen_products = state["seen_products"]
        chat_id = state["chat_id"]
        customer_id = state["customer_id"]
        content = ""
        update = {}
        
        extract_products = graph_function.get_products_by_keyword(keyword)[:5]
        seen_products = extract_products
        
        if len(extract_products) == 1:
            print(">>>> Sử dụng SQL")
            key, value = _add_cart(extract_products[0])
            
            cart[key] = value
            update["cart"] = cart
            update["product_chosen"] = extract_products[0] 
            
            content += (
                "Thông báo tìm thấy một sản phẩm phù hợp với khách:\n"
                f"{extract_products}.\n"
                "Hãy trả về sản phẩm trong giỏ hàng hiện tại để khách kiểm tra.\n"
                "Đây là thông tin giỏ hàng.\n"
                f"{cart}."
            )
            
        elif len(extract_products) > 1:
            print(">>>> Sử dụng SQL")
            content += (
                f"Thông báo tìm thấy nhiều sản phẩm phù hợp với khách, tổng cộng có {len(extract_products)} sản phẩm tìm được:\n"
                f"{extract_products}.\n"
                "Hỏi khách muốn mua sản phẩm nào.\n"
            )
                
        elif len(extract_products) == 0:
            print(">>>> Sử dụng embedding")
            content += "Thông báo tìm thấy nhiều sản phẩm phù hợp với yêu cầu khách.\n"
            user_input = state["user_input"]
            alternate_products = graph_function.get_product_embedding_info(user_input, match_count=5)
            
            if alternate_products:
                content += (
                    "Đây là các sản phẩm, dựa vào yêu cầu của khách để chọn ra sản phẩm phù hợp nhất.\n"
                    f"{alternate_products}\n"
                    "Lưu ý nếu không có sản phẩm nào phù hợp, hãy nói là không tìm "
                    "thấy sản phẩm theo yêu cầu của khách, "
                    "đây là các sản phẩm tương tự, và hỏi khách có muốn không.\n"
                )
                
                seen_products = alternate_products
        
        if not customer_id:
            customer = graph_function.get_customer_by_chat_id(chat_id)
            
            if customer:
                log = (
                    ">>>> Tìm thấy thông tin của khách:\n",
                    f"Tên: {customer.name}\n"
                    f"Số điện thoại: {customer.phone_number}\n"
                    f"Địa chỉ: {customer.address}\n"
                    f"ID khách: {customer.customer_id}.\n"
                )
                print(log)

                update["name"] = customer.name
                update["phone_number"] = customer.phone_number
                update["address"] = customer.address
                update["customer_id"] = customer.customer_id

                content += (
                    "Đã tìm thấy thông tin khách hàng.\n"
                    "Nếu chỉ có một sản phẩm trả về thì hãy hỏi khách muốn lên đơn luôn không.\n"
                    "Nếu có nhiều sản phẩm trả về thì hỏi khách chọn sản phẩm nào.\n"
                )
            else:
                content += (
                    "Không có thông tin khách hàng trong CSDL, tức là khách chưa đăng ký.\n"
                    "Nếu chỉ có một sản phẩm trả về thì hỏi khách số điện thoại để tư vấn và lên đơn.\n"
                    "Nếu có nhiều sản phẩm trả về thì hỏi khách chọn sản phẩm và cho số điện thoại để liên hệ tư vấn.\n"
                )
            
            
        update["messages"] = [
            ToolMessage
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]
        
        update["seen_products"] = seen_products
        
        return Command(
            update=update
        )
        
    except Exception as e:
        raise Exception(e)