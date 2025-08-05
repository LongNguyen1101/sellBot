import json
from langchain_core.tools import tool, InjectedToolCallId
from pydantic import BaseModel
from app.core.utils.graph_function import GraphFunction
from app.core.model import init_model
from app.core.state import SellState
from typing import Annotated, TypedDict, Optional, Literal, Tuple, List
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from app.core.utils.class_parser import AgentToolResponse

graph_function = GraphFunction()
llm = init_model()

    
def _get_products(keyword: str,
                 user_input: str
) -> Tuple[AgentToolResponse, List[dict]]:
    try:
        tool_response: AgentToolResponse = {}
        products_found = graph_function.get_products_by_keyword(keyword)[:5]
        seen_products = products_found
        products_quantity = len(products_found)
        
        if products_quantity == 1:
            print(">>>> Sử dụng SQL")
            
            tool_response = {
                "status": "finish",
                "content": (
                    "Thông báo tìm thấy một sản phẩm phù hợp với khách:\n"
                    f"{products_found}.\n"
                )
            }
            
        elif products_quantity > 1:
            print(">>>> Sử dụng SQL")
            
            tool_response = {
                "status": "asking",
                "content": (
                    f"Thông báo tìm thấy nhiều sản phẩm phù hợp với khách, tổng cộng có {products_quantity} sản phẩm tìm được:\n"
                    f"{products_found}.\n"
                    "Hỏi khách muốn mua sản phẩm nào.\n"
                )
            }
                
        elif products_quantity == 0:
            print(">>>> Sử dụng embedding")
            
            alternate_products = graph_function.get_product_embedding_info(user_input, match_count=5)
            
            if alternate_products:
                tool_response = {
                    "status": "asking",
                    "content": (
                        "Đây là các sản phẩm, dựa vào yêu cầu của khách để chọn ra sản phẩm phù hợp nhất.\n"
                        f"{alternate_products}\n"
                        "Đây là các sản phẩm tương tự, và hỏi khách có muốn không.\n"
                    )
                }
                
                seen_products = alternate_products
            else:
                tool_response = {
                    "status": "asking",
                    "content": (
                        "Xin lỗi khách vì không tìm thấy bất kỳ sản phẩm nào "
                        "phù hợp với yêu cầu của khách.\n"
                    )
                }
                
                seen_products = alternate_products
                
        return tool_response, seen_products
    except Exception as e:
        raise Exception(e)

def _check_customer(customer_id: Optional[int], 
                   chat_id: int, 
                   tool_response: ToolMessage
) -> Tuple[ToolMessage, dict]:
    try:
        update = {}
        
        if customer_id:
            return tool_response, update
        
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
            update.update({
                "name": customer.name,
                "phone_number":customer.phone_number,
                "address":customer.address,
                "customer_id":customer.customer_id
                
            })
            
            tool_response["content"] += (
                "Đã tìm thấy thông tin khách hàng.\n"
                "Nếu chỉ có một sản phẩm trả về thì hãy hỏi khách muốn lên đơn luôn không.\n"
                "Nếu có nhiều sản phẩm trả về thì hỏi khách chọn sản phẩm nào.\n"
            )
        else:
            tool_response["content"] += (
                "Không có thông tin khách hàng.\n"
                "Nếu chỉ có một sản phẩm trả về thì hỏi khách số điện thoại để tư vấn và lên đơn.\n"
                "Nếu có nhiều sản phẩm trả về thì hỏi khách chọn sản phẩm và cho số điện thoại để liên hệ tư vấn.\n"
            )
            
        return tool_response, update
    except Exception as e:
        raise Exception(e)
    
    
    
@tool
def get_products_tool(
    keyword: Annotated[str, "The keyword of products"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to get products from database follow by the keyword of customer"""
    try:
        update = {}
        
        tool_response, seen_products = _get_products(
            keyword=keyword,
            user_input=state["user_input"]
        )
        
        update["seen_products"] = seen_products
        
        tool_response, new_update = _check_customer(
            customer_id=state["customer_id"],
            chat_id=state["chat_id"],
            tool_response=tool_response
        )
               
        update["messages"] = [
            ToolMessage
            (
                content=json.dumps(tool_response, ensure_ascii=False),
                tool_call_id=tool_call_id
            )
        ]
        
        update.update(new_update)
        
        print(f">>>> Upadate tool: {update}")
        
        return Command(
            update=update
        )
        
    except Exception as e:
        raise Exception(e)