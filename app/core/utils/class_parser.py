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
    quantity: Optional[int]

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
    
class OrderChosen(TypedDict):
    order_id: Optional[int] = Field(
        description=(
            "Mã đơn hàng.\n"
            "Nếu không thể xác định được đơn hàng mà khách chọn -> trả về None."
        )
    )
    item_id: Optional[int] = Field(
        description=(
            "Mã sản phẩm của các sản phẩm trong đơn hàng tương ứng.\n"
            "Trường order_items trong các đơn hàng chứa một danh sách các sản phẩm trong đơn hàng đó.\n"
            "Mỗi sản phẩm đại diện bởi id, id đó chính là item_id cần tìm.\n"
            "Nếu trường order_items của đơn hàng có order_id đó duy nhất 1 sản phẩm "
            "thì mặc định item_id của sản phẩm đó.\n"
            "Nếu không thể xác định được sản phẩm mà khách chọn -> trả về None."
        )
    )
    quantity: Optional[int] = Field(
        description=(
            "Số lượng khách muốn thay đổi đối với sản phẩm có item_id và "
            "trong đơn hàng có order_id tìm được ở trên.\n"
            "Nếu không thể xác định được sản phẩm hoặc đơn hàng mà khách chọn -> trả về None.\n"
            "Nếu không thể xác định được số lượng khách muốn thay đổi -> trả về None."
        )
    )
    