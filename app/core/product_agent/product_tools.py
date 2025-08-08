import json
from langchain_core.tools import tool, InjectedToolCallId
from app.core.utils.graph_function import graph_function
from app.core.state import SellState
from typing import Annotated, TypedDict, Optional, Literal, Tuple, List
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.utils.class_parser import AgentToolResponse
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD



def _get_products(
    keyword: str,
    user_input: str,
    public_crud: PublicCRUD
) -> Tuple[AgentToolResponse, List[dict]]:
    tool_response: AgentToolResponse = {}
    products_found, show_products = graph_function.get_products_by_keyword(keyword, public_crud=public_crud)
    # Limit to 5 products
    products_found = products_found[:5]
    show_products = show_products[:5]
    
    seen_products = products_found
    products_quantity = len(products_found)
    
    if products_quantity == 1:
        print(">>>> Sử dụng SQL")
        tool_response = {
            "status": "finish",
            "content": (
                "Thông báo tìm thấy một sản phẩm phù hợp với khách:"
                f"{show_products}."
            )
        }
    elif products_quantity > 1:
        print(">>>> Sử dụng SQL")
        tool_response = {
            "status": "asking",
            "content": (
                f"Thông báo tìm thấy nhiều sản phẩm phù hợp với khách, tổng cộng có {products_quantity} sản phẩm tìm được:"
                f"{show_products}."
                "Hỏi khách muốn mua sản phẩm nào."
            )
        }
    elif products_quantity == 0:
        print(">>>> Sử dụng embedding")
        alternate_products, show_products = graph_function.get_product_embedding_info(
            user_input,
            match_count=5, 
            public_crud=public_crud
        )
        
        if alternate_products:
            tool_response = {
                "status": "asking",
                "content": (
                    "Đây là các sản phẩm, dựa vào yêu cầu của khách để chọn ra sản phẩm phù hợp nhất."
                    f"{show_products}"
                    "Đây là các sản phẩm tương tự, và hỏi khách có muốn không."
                )
            }
            seen_products = alternate_products
        else:
            tool_response = {
                "status": "asking",
                "content": (
                    "Xin lỗi khách vì không tìm thấy bất kỳ sản phẩm nào "
                    "phù hợp với yêu cầu của khách."
                )
            }
            
    return tool_response, seen_products

def _check_customer(
    customer_id: Optional[int], 
    chat_id: int, 
    tool_response: AgentToolResponse,
    public_crud: PublicCRUD
) -> Tuple[AgentToolResponse, dict]:
    update = {}
    
    if customer_id:
        return tool_response, update
    
    customer = graph_function.get_customer_by_chat_id(chat_id, public_crud=public_crud)
    
    if customer:
        log = (
            ">>>> Tìm thấy thông tin của khách:",
            f"Tên: {customer.name}. "
            f"Số điện thoại: {customer.phone_number}. "
            f"Địa chỉ: {customer.address}. "
            f"ID khách: {customer.customer_id}."
        )
        
        print(log)
        update.update({
            "name": customer.name,
            "phone_number":customer.phone_number,
            "address":customer.address,
            "customer_id":customer.customer_id
        })
        
        tool_response["content"] += (
            "Đã tìm thấy thông tin khách hàng.\n"
            "Nếu chỉ có một sản phẩm trả về thì hãy hỏi khách muốn lên đơn luôn không.\n"
            "Nếu có nhiều sản phẩm trả về thì hỏi khách chọn sản phẩm nào."
        )
    else:
        tool_response["content"] += (
            "Không có thông tin khách hàng.\n"
            "Nếu chỉ có một sản phẩm trả về thì hỏi khách số điện thoại để tư vấn và lên đơn.\n"
            "Nếu có nhiều sản phẩm trả về thì hỏi khách chọn sản phẩm và cho số điện thoại để liên hệ tư vấn."
        )
        
    return tool_response, update

@tool
def get_products_tool(
    keyword: Annotated[str, "The keyword of products"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to get products from database follow by the keyword of customer"""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            update = {}
            
            tool_response, seen_products = _get_products(
                keyword=keyword,
                user_input=state["user_input"],
                public_crud=public_crud
            )
            
            update["seen_products"] = seen_products
            
            tool_response, new_update = _check_customer(
                customer_id=state["customer_id"],
                chat_id=state["chat_id"],
                tool_response=tool_response,
                public_crud=public_crud
            )
                   
            update.update({
                "messages": [
                    ToolMessage(
                        content=tool_response["content"],
                        tool_call_id=tool_call_id
                    )
                ],
                "status": tool_response["status"]
            })
            update.update(new_update)
            
            print(f">>>> Upadate tool: {update}")
            
            return Command(
                update=update
            )
            
    except Exception as e:
        # Log the exception for debugging
        print(f"An error occurred in get_products_tool: {e}")
        # Optionally, return a ToolMessage indicating failure
        return Command(update={"messages": [ToolMessage(content=f"Lỗi: {e}", tool_call_id=tool_call_id)]})