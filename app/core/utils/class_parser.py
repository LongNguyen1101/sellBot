from pydantic import BaseModel, Field
from typing import Literal, Optional, TypedDict, List



class SubQuery(TypedDict):
        id: int = Field(
            description="Số nguyên (bắt đầu từ 1)"
        )
        agent: (Literal["product_agent", 
                        "cart_agent", 
                        "order_agent", 
                        "customer_agent",
                        "customer_service_agent", 
                        "irrelevant_agent", 
                        "store_info_agent"]
        ) = Field(
            description="Tên của agent cần trả về"
        )
        sub_query: str = Field(
            description="sub_query được tách ra dựa vào query ban đầu của khách hàng."
        )

class SplitRequestOutput(TypedDict):
    tasks: List[SubQuery]

class Router(TypedDict):
    next: (Literal["product_agent", "cart_agent", "order_agent", "customer_agent",
                   "customer_service_agent", "irrelevant_agent", "store_info_agent"])

class AgentToolResponse(BaseModel):
    status: Literal["asking", "finish", "incomplete_info", "error"]
    content: Optional[str]
    
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
    
class UpdateOrder(TypedDict):
    command: str
    order_id: int
    
class UpdateReceiverInfo(TypedDict):
    order_id: int