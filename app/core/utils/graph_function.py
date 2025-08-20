from operator import sub
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
    def search_products_by_keyword(self, 
                                   keyword: str,
                                   public_crud: PublicCRUD,
                                   limit: int = 5
    ):
        
        products = public_crud.search_products_by_keyword(
            keyword=keyword, 
            limit=limit
        )
        extract_products = []
        show_products = []
        
        if products:
            for product in products:
                extract_products.append({
                    "product_id": product["product_id"],
                    "sku": product["sku"],
                    "product_name": product["product_name"],
                    "variance_description": product["variance_description"],
                    "price": product["price"],
                    "inventory": product["inventory"]
                })
                
                show_products.append({
                    "product_name": product["product_name"],
                    "variance_description": product["variance_description"],
                    "brief_description": product["brief_description"],
                    "price": product["price"],
                    "inventory": product["inventory"]
                })
        
        return extract_products, show_products
    
    def create_or_update_customer(self,
                                  public_crud: PublicCRUD,
                                  name: Optional[str] = None, 
                                  phone_number: Optional[str] = None,
                                  address: Optional[str] = None,
                                  chat_id: Optional[str] = None,
                                  parse_object: bool = True
    ) -> Customer | dict[str, Any] | None:
        
        check_customer_exist = public_crud.get_customer_by_chat_id(
            chat_id=chat_id, 
            parse_object=parse_object
        )
        
        if check_customer_exist:
            customer = public_crud.update_customer_info(
                customer_id=check_customer_exist["customer_id"],
                name=name,
                phone_number=phone_number,
                address=address,
                parse_object=parse_object
            )
        else:
            customer = public_crud.create_customer(
                name=name,
                phone_number=phone_number,
                address=address,
                chat_id=chat_id,
                parse_object=parse_object
            )
        return customer
            
    def get_or_create_customer(self,
                               chat_id: str,
                               public_crud: PublicCRUD,
                               parse_object: bool = False
    ):
        customer =  public_crud.get_or_create_customer(
            chat_id=chat_id, 
            parse_object=parse_object
        )
        
        return customer
        
            
    def update_customer(self,
                        public_crud: PublicCRUD,
                        customer_id: str,
                        name: Optional[str] = None, 
                        phone_number: Optional[str] = None,
                        address: Optional[str] = None,
                        parse_object: bool = True
    ) -> Customer | dict[str, Any] | None:
        
        return public_crud.update_customer_info(
            customer_id=customer_id,
            name=name,
            phone_number=phone_number,
            address=address,
            parse_object=parse_object
        )
        
    def add_cart_item_to_order(self,
                               cart_items: dict,
                               order_id: int,
                               public_crud: PublicCRUD,
                               parse_object: bool = True
    ):
        if not cart_items:
            return None
            
        order_items = []
        for item_data in cart_items.values():
            order_items.append({
                "order_id": order_id,
                "product_id": item_data["Mã sản phẩm"],
                "sku": item_data["Mã phân loại"],
                "quantity": item_data["Số lượng"],
                "price": item_data["Giá sản phẩm"],
                "subtotal": item_data["Giá cuối cùng"]
            })
            
        created_order_items = public_crud.create_order_items_bulk(
            order_items, 
            parse_object=parse_object
        )
        
        updated_order = public_crud.update_order(
            order_id=order_id,
            status="created",
            parse_object=parse_object
        )
                
        return created_order_items, updated_order
    
    def get_order_items_detail(self, order_id: int, public_crud: PublicCRUD) -> List[dict]:
        return public_crud.get_order_items_with_details(order_id)
            
    def update_customer_info(self, 
                             public_crud: PublicCRUD,
                             customer_id: int,
                             name: Optional[str] = None,
                             phone_number: Optional[str] = None,
                             address: Optional[str] = None,
                             parse_object: bool = True
    ) -> Customer | dict[str, Any] | None:
        
        return public_crud.update_customer_info(
            customer_id=customer_id,
            name=name,
            phone_number=phone_number,
            address=address,
            parse_object=parse_object
        )
            
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
    ) -> int | None:
        
        return public_crud.create_order(
            customer_id=customer_id,
            receiver_name=receiver_name,
            receiver_phone_number=receiver_phone_number,
            receiver_address=receiver_address,
            shipping_fee=shipping_fee
        )
            
    def get_editable_orders(self, 
                            customer_id: int, 
                            public_crud: PublicCRUD,
    ):
        return public_crud.get_editable_orders(
            customer_id=customer_id,
        )
            
    def retrieve_product_descriptions(
        self,
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
            
    def get_product_embedding_info(
        self, 
        public_crud: PublicCRUD,
        user_input: str,
        match_count: int = 5,
        number_of_products: int = 5,
    ):
        product_id_list = []
        product_raw = self.retrieve_product_descriptions(
            public_crud=public_crud,
            user_input=user_input, 
            match_count=match_count,
        )
        
        # get the list of product_id
        for data in product_raw:
            match = re.search(r"mã sản phẩm:\s*(\d+)", data['content'])
            if match:
                product_code = match.group(1)
                product_id_list.append(int(product_code))
                
        
        # query by ids
        products = public_crud.search_products_by_product_ids(
            product_ids=product_id_list[:number_of_products]
        )
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

        
    def get_customer_by_chat_id(self, 
                                chat_id: str, 
                                public_crud: PublicCRUD,
                                parse_object: bool = True
    ):
        return public_crud.get_customer_by_chat_id(
            chat_id=chat_id, 
            parse_object=parse_object
        )
            
    def get_order_by_id(self, order_id: int, public_crud: PublicCRUD) -> Optional[Order]:
        return public_crud.get_order_by_id(order_id)
            
    def get_order_detail(self, order_id: int, public_crud: PublicCRUD):
        order_info = self.get_order_by_id(order_id, public_crud)
        order_items = self.get_order_items_detail(order_id, public_crud)
        return order_info, order_items
    
    def get_order_with_items(self, order_id: int, public_crud: PublicCRUD):
        return public_crud.get_order_with_items(order_id=order_id)
        
        
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
                     parse_object: bool = True
    ):
        
        return public_crud.update_order(
            order_id=order_id,
            payment=payment,
            order_total=order_total,
            shipping_fee=shipping_fee,
            grand_total=grand_total,
            receiver_name=receiver_name,
            receiver_phone_number=receiver_phone_number,
            receiver_address=receiver_address,
            status=status,
            parse_object=parse_object
        )
            
    def delete_item(self,
                    item_id: int,
                    public_crud: PublicCRUD
    ) -> bool:
        return public_crud.delete_order_item(item_id=item_id)
            
    def update_order_item_quantity(self,
                                   item_id: int,
                                   new_quantity: int,
                                   public_crud: PublicCRUD,
                                   parse_object: bool = True
    ):
        if new_quantity == 0:
            deleted_item = self.delete_item(item_id=item_id, public_crud=public_crud)
            return deleted_item
        
        new_item = public_crud.update_order_item_quantity(
            item_id=item_id,
            new_quantity=new_quantity,
            parse_object=parse_object
        )
        
        return True if new_item else False
    
    def delete_order(self,
                     order_id: int,
                     public_crud: PublicCRUD,
    ):
        return public_crud.delete_order(order_id=order_id)
    
    def create_order_item(self,
                          order_id: int, 
                          product_id: int, 
                          sku: str,
                          public_crud: PublicCRUD,
                          quantity: Optional[int] = None,
                          price: Optional[int] = None,
                          subtotal: Optional[int] = None,
                          parse_object: bool = True
    ):
        return public_crud.create_order_item(
            order_id=order_id,
            product_id=product_id,
            sku=sku,
            quantity=quantity,
            price=price,
            subtotal=subtotal,
            parse_object=parse_object
        )
        
        
# init
graph_function = GraphFunction()