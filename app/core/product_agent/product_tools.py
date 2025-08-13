from langchain_core.tools import tool, InjectedToolCallId
from app.core.utils.graph_function import graph_function
from app.core.state import SellState
from typing import Annotated
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
):
    tool_response: AgentToolResponse = {}
    products_found, show_products = graph_function.search_products_by_keyword(
        keyword=keyword, 
        public_crud=public_crud
    )
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
            public_crud=public_crud,
            user_input=user_input,
            match_count=5, 
        )
        
        if alternate_products:
            tool_response = {
                "status": "asking",
                "content": (
                    "Đây là các sản phẩm tương tự:\n"
                    f"{show_products}"
                    "Nếu có sản phẩm nào phù hợp với yêu cầu của khách, in chi tiết sản phẩm đó ra.\n"
                    "Nếu không có sản phẩm nào phù hợp với yêu cầu của khách, in chi tiết tất cả các sản phẩm ra để khách chọn.\n"
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

@tool
def get_products_tool(
    keyword: Annotated[str, "The keyword of products"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to get products from database follow by the keyword of customer"""
    try:
        with session_scope() as sess:
            public_crud = PublicCRUD(sess)
            update = {}
            phone_number = state["phone_number"]

            tool_response, seen_products = _get_products(
                keyword=keyword,
                user_input=state["user_input"],
                public_crud=public_crud
            )

            update["seen_products"] = seen_products

            if not phone_number:
                tool_response["content"] += (
                    "Khách chưa có số điện thoại.\n"
                    "Xin khách số điện thoại để liên hệ tư vấn.\n"
                )

            update.update({
                "messages": [
                    ToolMessage(
                        content=tool_response.get("content", ""),
                        tool_call_id=tool_call_id
                    )
                ],
                "status": tool_response.get("status", "error")
            })

            return Command(update=update)
            
    except Exception as e:
        # Log the exception for debugging
        print(f">>>> An error occurred in get_products_tool: {e}")
        raise
