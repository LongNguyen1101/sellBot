from app.models.normal_models import Customer, Order, OrderItem
from app.services.crud_public import PublicCRUD
from app.core.state import SellState
from typing import Any, List, Optional, Tuple, Dict
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
import json
import os
import re

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class GraphFunction:
    def extract_product_name(self, user_input: str) -> List[str]:
        result = self.chain.extract_product_name().invoke(user_input)
        data = result.content.replace("```json\n", "").replace("\n```", "").replace("\n", "")

        try:
            data = json.loads(data)
            if isinstance(data, list) and all(isinstance(item, str) for item in data):
                return data
            else:
                print("Not a valid list of string")
                return []
            
        except json.JSONDecodeError as e:
            print(f"Eror parsing json to list: {e}")
            return []
        
    def get_products_by_keyword(self, 
                                keyword: str,
                                public_crud: PublicCRUD,
                                limit: int = 5
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        products = public_crud.search_products_by_keyword(
            keyword=keyword, 
            limit=limit
        )
        extract_products = []
        show_products = []
        
        for product in products:
            extract_products.append({
                "product_id": product["product_id"],
                "sku": product["sku"],
                "product_name": product["product_name"],
                "variance_description": product["variance_description"],
                "price": product["price"]
            })
            
            show_products.append({
                "product_name": product["product_name"],
                "variance_description": product["variance_description"],
                "brief_description": product["brief_description"],
                "price": product["price"]
            })
        
        return extract_products, show_products
        
    def get_product_info_in_cart(self, product_id: int, sku: str, public_crud: PublicCRUD) -> dict:
        product = public_crud.get_product_by_product_id_and_sku(product_id, sku)
        return product
        
    def get_product_by_sql(self, command: str, public_crud: PublicCRUD) -> List[dict]:
        products = public_crud.execute_command(command=command)
        return products
        
    def get_chat_histories(self, state: SellState, number_of_messages: int) -> List[dict]:
        raw_chat_histories = state["messages"][-number_of_messages:]
        
        chat_histories = [
            {
                "type": chat.type,
                "content": chat.content
            }
            for chat in raw_chat_histories
        ]
        
        return chat_histories
    
    def create_or_update_customer(self,
                                  public_crud: PublicCRUD,
                                  name: Optional[str] = None, 
                                  phone_number: Optional[str] = None,
                                  address: Optional[str] = None,
                                  chat_id: Optional[str] = None,
    ) -> Optional[Customer]:
        check_customer_exist = public_crud.get_customer_by_chat_id(chat_id)
        if check_customer_exist:
            update_customer = public_crud.update_customer_info(
                customer_id=check_customer_exist.customer_id,
                name=name,
                phone_number=phone_number,
                address=address
            )
            return update_customer, "Tìm thấy và cập nhật thông tin khách hàng."
        else:
            customer = public_crud.create_customer(
                name=name,
                phone_number=phone_number,
                address=address,
                chat_id=chat_id
            )
            return customer, "Tạo khách hàng mới thành công."
            
    def get_customer(self,
                     chat_id: str,
                     public_crud: PublicCRUD
    ) -> Optional[Customer]:
        return public_crud.get_customer_by_chat_id(chat_id)
            
    def create_customer(self,
                        chat_id: str,
                        name: Optional[str] = None, 
                        phone_number: Optional[str] = None,
                        address: Optional[str] = None,
                        public_crud: PublicCRUD = None
    ) -> Customer:
        return public_crud.create_customer(
            chat_id=chat_id,
            name=name,
            phone_number=phone_number,
            address=address
        )
            
    def update_customer(self,
                        public_crud: PublicCRUD,
                        customer_id: str,
                        name: Optional[str] = None, 
                        phone_number: Optional[str] = None,
                        address: Optional[str] = None,
    ) -> Customer:
        return public_crud.update_customer_info(
            customer_id=customer_id,
            name=name,
            phone_number=phone_number,
            address=address
        )
    
    def find_customer_by_phone_number(self,phone_number: str, public_crud: PublicCRUD) -> Optional[Customer]:
        customer = public_crud.get_customer_by_phone_number(phone_number)
        return customer
        
    def add_total_to_order(self,
                           order_id: int,
                           payment: str,
                           order_total: int,
                           shipping_fee: int,
                           grand_total: int,
                           public_crud: PublicCRUD
    ) -> Optional[Order]:
        order = public_crud.update_order(order_id,
                                         payment,
                                         order_total,
                                         shipping_fee,
                                         grand_total)
        return order
        
    def add_cart_item_to_order(self,
                               cart_items: dict,
                               order_id: int,
                               public_crud: PublicCRUD
    ):
        if not cart_items:
            return None
        
        order_items: List[OrderItem] = []
        for item_data in cart_items.values():
            order_item = OrderItem(
                order_id = order_id,
                product_id = item_data["Mã sản phẩm"],
                sku = item_data["Mã phân loại"],
                quantity = item_data["Số lượng"],
                price = item_data["Giá sản phẩm"],
                subtotal = item_data["Giá cuối cùng"]
            )
            order_items.append(order_item)
            
        created_order_items = public_crud.create_order_items_bulk(order_items)
        
        updated_order = public_crud.update_order(
            order_id=order_id,
            status="created"
        )
                
        return created_order_items
    
    def get_order_items_detail(self, order_id: int, public_crud: PublicCRUD) -> List[dict]:
        return public_crud.get_order_items_with_details(order_id)
        
    def get_order_info(self, order_id: int, public_crud: PublicCRUD) -> dict:
        return public_crud.get_order_summary_by_id(order_id)
            
            
    def get_order_by_command(self, 
                             command: str,
                             public_crud: PublicCRUD
    ) -> List[dict]:
        return public_crud.execute_command(command)
            
    def get_order_items(self,
                       order_id: int,
                       public_crud: PublicCRUD) ->  List[dict]:
        
        order_items = public_crud.get_items_by_order_id(order_id)
            
    def update_order_by_command(self, 
                                command: str,
                                public_crud: PublicCRUD) -> List[dict]:
        return public_crud.execute_command(command)
            
    def update_customer_info(self, 
                             public_crud: PublicCRUD,
                             customer_id: int,
                             name: Optional[str] = None,
                             phone_number: Optional[str] = None,
                             address: Optional[str] = None,
    ) -> Optional[Customer]:
        return public_crud.update_customer_info(customer_id=customer_id,
                                                name=name,
                                                phone_number=phone_number,
                                                address=address)
            
    def update_receiver_info_order(self, 
                                   public_crud: PublicCRUD,
                                   order_id: int,
                                   name: Optional[str] = None,
                                   phone_number: Optional[str] = None,
                                   address: Optional[str] = None,
    ) -> Optional[Order]:

        return public_crud.update_order(order_id=order_id,
                                        receiver_name=name,
                                        receiver_phone_number=phone_number,
                                        receiver_address=address)
            
    def retrieve_qna(self, 
                     public_crud: PublicCRUD,
                     user_input: str, 
                     match_count: int = 5,
    ):
        
        embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",  # hoặc text-embedding-ada-002
            openai_api_key=OPENAI_API_KEY
        )
        embedding_vector = embedding_model.embed_query(user_input)
        
        return public_crud.call_match_qna(embedding_vector, match_count)
            
    def retrieve_common_situation(self, 
                                  public_crud: PublicCRUD,
                                  user_input: str, 
                                  match_count: int = 5,
    ):
        
        embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=OPENAI_API_KEY
        )
        embedding_vector = embedding_model.embed_query(user_input)
        
        return public_crud.call_match_common_situation(embedding_vector, match_count)
            
    def create_order(self,
                     customer_id: int,
                     receiver_name: str,
                     receiver_phone_number: str,
                     receiver_address: str,
                     shipping_fee: int,
                     public_crud: PublicCRUD
    ):
        return public_crud.create_order(
            customer_id=customer_id,
            receiver_name=receiver_name,
            receiver_phone_number=receiver_phone_number,
            receiver_address=receiver_address,
            shipping_fee=shipping_fee
        )
            
    def get_unshipped_order(self,
                            customer_id: int,
                            public_crud: PublicCRUD
    ) -> Optional[Order]:
        
        return public_crud.get_unshipped_order(customer_id=customer_id)
            
    def get_shipped_order(self,
                          customer_id: int,
                          public_crud: PublicCRUD
    ) -> Optional[List[Order]]:
        
        return public_crud.get_shipped_order(customer_id=customer_id)
            
    def get_editable_orders(self, customer_id: int, public_crud: PublicCRUD) -> Optional[List[Order]]:
        return public_crud.get_editable_orders(customer_id=customer_id)
            
    def retrieve_product_descriptions(self,
                                      public_crud: PublicCRUD,
                                      user_input: str, 
                                      match_count: int = 5,
    ):
        
        embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=OPENAI_API_KEY
        )
        embedding_vector = embedding_model.embed_query(user_input)
        
        return public_crud.call_match_product_descriptions(embedding_vector, match_count)
            
    def get_product_embedding_info(self, 
                                    public_crud: PublicCRUD,
                                    user_input: str,
                                    match_count: int = 5,
                                    number_of_products: int = 10,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        product_id_list = []
        product_raw = self.retrieve_product_descriptions(user_input, match_count, public_crud)

        print(f">>>> Product raw: {product_raw}")
        # get the list of product_id
        for data in product_raw:
            match = re.search(r"mã sản phẩm:\s*(\d+)", data['content'])
            if match:
                product_code = match.group(1)
                product_id_list.append(int(product_code))
                
        
        # query by ids
        products = public_crud.search_products_by_product_ids(product_id_list)[:number_of_products]
        show_products = []
        extract_products = []
        
        if products:
            for product in products:
                extract_products.append({
                    "product_id": product["product_id"],
                    "sku": product["sku"],
                    "product_name": product["product_name"],
                    "variance_description": product["variance_description"],
                    "price": product["price"]
                })

                show_products.append({
                    "product_name": product["product_name"],
                    "variance_description": product["variance_description"],
                    "brief_description": product["brief_description"],
                    "price": product["price"]
                })
        
        return extract_products, show_products

        
    def get_customer_by_chat_id(self, chat_id: str, public_crud: PublicCRUD) -> Optional[dict]:
        return public_crud.get_customer_by_chat_id(chat_id)
            
    def get_order_by_id(self, order_id: int, public_crud: PublicCRUD) -> Optional[Order]:
        return public_crud.get_order_by_id(order_id)
            
    def get_order_detail(self, order_id: int, public_crud: PublicCRUD):
        order_items = self.get_order_items_detail(order_id, public_crud)
        order_info = self.get_order_by_id(order_id, public_crud)
        return order_info, order_items
        
        
    def update_order(self,
                     public_crud: PublicCRUD,
                     order_id: int, 
                     payment: Optional[str] = None,
                     order_total: Optional[int] = None,
                     shipping_fee: Optional[int] = None,
                     grand_total: Optional[int] = None,
                     receiver_name: Optional[str] = None,
                     receiver_phone_number: Optional[str] = None,
                     receiver_address: Optional[str] = None,
                     status: Optional[str] = None,
    ) -> Optional[Order]:
        
        return public_crud.update_order(
            order_id,
            payment,
            order_total,
            shipping_fee,
            grand_total,
            receiver_name,
            receiver_phone_number,
            receiver_address,
            status
        )
            
    def delete_item(self,
                    item_id: int,
                    public_crud: PublicCRUD
    ) -> bool:
        return public_crud.delete_items_item_id(
            item_id=item_id
        )
            
    def update_order_item_quantity(
                                   self,
                                   item_id: int,
                                   new_quantity: int,
                                   public_crud: PublicCRUD
    ) -> bool:
        new_item = public_crud.update_order_item_quantity(
            item_id=item_id,
            new_quantity=new_quantity
        )
        
        if new_item:
            if new_item.quantity == 0:
                delete_item = self.delete_item(item_id=item_id, public_crud=public_crud)
                if delete_item:
                    return True
                else:
                    return False
            return True 
        return False

graph_function = GraphFunction()