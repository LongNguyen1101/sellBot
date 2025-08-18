from ast import Tuple
from langchain_core.tools import tool, InjectedToolCallId
from app.core.utils.graph_function import graph_function
from app.core.state import SellState
from typing import Annotated
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.utils.class_parser import AgentToolResponse
from app.core.utils.helper_function import build_update
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.log.logger_config import setup_logging

logger = setup_logging(__name__)

def _handle_sql_return(
    show_products: list,
    products_quantity: int,
    tool_call_id: str,
) -> dict | None:
    if products_quantity == 1:
        return build_update(
            content=(
                "Thông báo tìm thấy một sản phẩm phù hợp với khách:"
                f"{show_products}.\n"
                "Đây là số điện thoại của khách:\n"
            ),
            status="finish",
            tool_call_id=tool_call_id
        )
        
    if products_quantity > 1:
        return build_update(
            content=(
                f"Thông báo tìm thấy nhiều sản phẩm phù hợp với khách, tổng cộng có {products_quantity} sản phẩm tìm được:"
                f"{show_products}."
                "Hỏi khách muốn mua sản phẩm nào."
            ),
            status="asking",
            tool_call_id=tool_call_id
        )
        
    if products_quantity < 0:
        logger.error("Có lỗi trong quá trình truy xuất sản phẩm")
        return build_update(
            content=(
                "Lỗi trong lúc truy xuất sản phẩm, mong khách thử lại"
            ),
            status="error",
            tool_call_id=tool_call_id
        )
    
    return None


def _get_products(
    keyword: str,
    user_input: str,
    tool_call_id: str,
    public_crud: PublicCRUD,
):

    # First find product via SQL
    logger.info("Đầu tiên sử dụng SQL để tìm sản phẩm")
    products_found, show_products = graph_function.search_products_by_keyword(
        keyword=keyword, 
        public_crud=public_crud
    )
    products_quantity = len(products_found)
    logger.info(f"Số lượng sản phẩm trả về: {products_quantity}")
    
        
    handle_sql = _handle_sql_return(
        show_products=show_products,
        products_quantity=products_quantity,
        tool_call_id=tool_call_id
    )
    
    if handle_sql:
        return handle_sql, products_found
        
    logger.info("Sử dụng embedding để tìm sản phẩm")
    alternate_products, show_products = graph_function.get_product_embedding_info(
        public_crud=public_crud,
        user_input=user_input,
        match_count=5, 
    )
    
    if not alternate_products:
        logger.info("Không tìm thấy các sản phẩm tương tự bằng embedding")
        return build_update(
            content=(
                "Xin lỗi khách vì không tìm thấy bất kỳ sản phẩm nào "
                "phù hợp với yêu cầu của khách."
            ),
            status="asking",
            tool_call_id=tool_call_id
        ), []
    
    logger.info(f"Lấy được các sản phẩm tương tự bằng embedding: {alternate_products}")
    
    return build_update(
        content=(
            "Đây là các sản phẩm tương tự:\n"
            f"{show_products}\n"
            "Nếu có sản phẩm tương tự với yêu cầu của khách -> in ra chi tiết sản phẩm đó và tóm gọn các sản phẩm còn lại.\n"
            "Nếu không có sản phẩm tương tự với yêu cầu của khách -> in ra chi tiết các sản phẩm còn lại.\n"
        ),
        status="asking",
        tool_call_id=tool_call_id
    ), alternate_products


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
            
            update, seen_products = _get_products(
                keyword=keyword,
                user_input=state["user_input"],
                public_crud=public_crud,
                tool_call_id=tool_call_id
            )

            update["seen_products"] = seen_products if seen_products else update["seen_products"]

            if not state["phone_number"]:
                logger.info("Khách chưa có số điện thoại -> xin khách")
                
                update["messages"][0].content += (
                    "Khách chưa có số điện thoại.\n"
                    "Xin khách số điện thoại để liên hệ tư vấn.\n"
                )
            else:
                logger.info("Khách đã có số điện thoại")
                
                update["messages"][0].content += (
                    "Khách đã có số điện thoại, không xin nữa.\n"
                    "Đây là thông tin tên và địa chỉ của khách:\n"
                    f"- Tên: {state["name"]}\n"
                    f"- Địa chỉ: {state["address"]}\n"
                    "Nếu thiếu thông tin nào thì hỏi khách.\n"
                    "Nếu không thiếu thì nói khách có muốn mua không.\n"
                )
                
            return Command(update=update)
            
    except Exception as e:
        # Log the exception for debugging
        logger.error(f"Có lỗi sảy ra: {e}")
        raise
