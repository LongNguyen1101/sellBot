from math import prod
from click import Option
from fastapi import FastAPI
from httpx import delete
from openai import chat
from sqlalchemy.orm import Session
from app.core.model import init_model
from app.db.database import get_db
from app.models.normal_models import Customer, Order, OrderItem
from app.services.crud_public import PublicCRUD
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date, time as dtime, timedelta
from app.core.state import SellState
from typing import List, Optional, Tuple
import json
from dotenv import load_dotenv
import os
from langchain_openai import OpenAIEmbeddings
import re

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_KEY")

def get_public_crud():
    """Generator function to provide a PublicCRUD instance with a database session."""
    db: Session = next(get_db())
    try:
        yield PublicCRUD(db)
    finally:
        db.close()

class GraphFunction:
    def __init__(self):
        self.llm = init_model()
        
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
                                public_crud: PublicCRUD = next(get_public_crud())
    ) -> List[dict]:
        try:
            products = public_crud.search_products_by_keyword(keyword=keyword)
            extract_products = [
                {
                    "product_id": product["product_id"],
                    "sku": product["sku"],
                    "product_name": product["product_name"],
                    "variance_description": product["variance_description"],
                    "brief_description": product["brief_description"],
                    "price": product["price"]
                }
                for product in products
            ]
            
            return extract_products
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
        
    def get_product_info_in_cart(self, product_id: int, sku: str, public_crud: PublicCRUD = next(get_public_crud())) -> dict:
        try:
            product = public_crud.get_product_by_product_id_and_sku(product_id, sku)
            return product
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
        
    def get_product_by_sql(self, command: str, public_crud: PublicCRUD = next(get_public_crud())) -> List[dict]:
        try:
            products = public_crud.execute_command(command=command)
            return products
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
        
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
    
    def update_or_create_customer(self,
                                  name: Optional[str] = None, 
                                  phone_number: Optional[str] = None,
                                  address: Optional[str] = None,
                                  chat_id: Optional[str] = None,
                                  public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[Customer]:
        try:
            check_customer_exist = public_crud.get_customer_by_chat_id(chat_id)
            if check_customer_exist:
                update_customer = public_crud.update_customer_info(
                    customer_id=check_customer_exist.customer_id,
                    name=name,
                    phone_number=phone_number,
                    address=address
                )
                return update_customer
            else:
                customer = public_crud.create_customer(
                    name=name,
                    phone_number=phone_number,
                    address=address,
                    chat_id=chat_id
                )
                return customer
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise 
        finally:
            public_crud.db.close()
    
    def find_customer_by_phone_number(self, phone_number: str, 
                      public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[Customer]:
        try:
            customer = public_crud.get_customer_by_phone_number(phone_number)
            return customer
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise 
        finally:
            public_crud.db.close()
        
    def add_total_to_order(self,
                           order_id: int,
                           payment: str,
                           order_total: int,
                           shipping_fee: int,
                           grand_total: int,
                           public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[Order]:
        try:
            
            order = public_crud.update_order(order_id,
                                             payment,
                                             order_total,
                                             shipping_fee,
                                             grand_total)
            return order
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
        
    def add_cart_item_to_order(self,
                               cart_items: dict,
                               order_id: int,
                               public_crud: PublicCRUD = next(get_public_crud())
    ):
        if not cart_items:
            return None
        
        order_items: List[OrderItem] = []
        try:
            note = ""
            for item_data in cart_items.values():
                product_id_from_cart = item_data["Mã sản phẩm"]
                sku_from_cart = item_data["Mã phân loại"]
                quantity_to_add = item_data["Số lượng"]
                product_name = item_data["Tên sản phẩm"]
                sku_name = item_data["Tên phân loại"] if item_data["Tên phân loại"] != '' else "Không có"
                
                existing_order_item = public_crud.get_items_by_order_id_sku_product_id(order_id,
                                                                                       product_id_from_cart,
                                                                                       sku_from_cart)

                if existing_order_item:
                    new_quantity = existing_order_item.quantity + quantity_to_add
                    updated_item = public_crud.update_order_item_quantity(existing_order_item.id,
                                                                          new_quantity)
                    
                    note += (
                        f"Sản phẩm: {product_name} với tên phân loại: {sku_name} "
                        "đã có trong đơn hàng bạn đặt trước đó. Tăng số lượng của sản phẩm này trong đơn hàng thành "
                        f"{new_quantity}.\n\n"
                    )
                    
                    if not updated_item:
                        raise SQLAlchemyError("Cannot update quantity of order item")
                
                else:
                    order_item = OrderItem(
                        order_id = order_id,
                        product_id = item_data["Mã sản phẩm"],
                        sku = item_data["Mã phân loại"],
                        quantity = item_data["Số lượng"],
                        price = item_data["Giá sản phẩm"],
                        subtotal = item_data["Giá cuối cùng"]
                    )
                    order_items.append(order_item)
                    
                    note += (
                        f"Sản phẩm: {product_name} với tên phân loại: {sku_name} "
                        "chưa có trong giỏ hàng. Thêm sản phẩm này vào trong giỏ hàng có sẵn."
                    )
                
            created_order_items = public_crud.create_order_items_bulk(order_items)
            updated_order = public_crud.update_order(
                order_id=order_id,
                status="created"
            )
                    
            return created_order_items, note
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        except ValueError as e:
            raise ValueError(e)
        finally:
            public_crud.db.close()
    
    def get_order_items_detail(self, order_id: int, public_crud: PublicCRUD = next(get_public_crud())) -> List[dict]:
        try:
            return public_crud.get_order_items_with_details(order_id)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
        
    def get_order_info(self, order_id: int, public_crud: PublicCRUD = next(get_public_crud())) -> dict:
        try:
            return public_crud.get_order_summary_by_id(order_id)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
            
    def get_order_by_command(self, 
                  command: str,
                  public_crud: PublicCRUD = next(get_public_crud())) -> List[dict]:
        try:
            return public_crud.execute_command(command)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def get_order_items(self,
                       order_id: int,
                       public_crud: PublicCRUD = next(get_public_crud())) ->  List[dict]:
        
        try:
            order_items = public_crud.get_items_by_order_id(order_id)

        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def update_order_by_command(self, 
                                command: str,
                                public_crud: PublicCRUD = next(get_public_crud())) -> List[dict]:
        try:
            return public_crud.execute_command(command)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def update_customer_info(self, 
                             customer_id: int,
                             name: Optional[str] = None,
                             phone_number: Optional[str] = None,
                             address: Optional[str] = None,
                             public_crud: PublicCRUD = next(get_public_crud())) -> Optional[Customer]:
        try:
            return public_crud.update_customer_info(customer_id=customer_id,
                                                    name=name,
                                                    phone_number=phone_number,
                                                    address=address)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def update_receiver_info_order(self, 
                                   order_id: int,
                                   name: Optional[str] = None,
                                   phone_number: Optional[str] = None,
                                   address: Optional[str] = None,
                                   public_crud: PublicCRUD = next(get_public_crud())) -> Optional[Order]:

        try:
            return public_crud.update_order(order_id=order_id,
                                            receiver_name=name,
                                            receiver_phone_number=phone_number,
                                            receiver_address=address)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def retrieve_qna(self, 
                     user_input: str, 
                     match_count: int = 5,
                     public_crud: PublicCRUD = next(get_public_crud())):
        
        try:
            embedding_model = OpenAIEmbeddings(
                model="text-embedding-3-small",  # hoặc text-embedding-ada-002
                openai_api_key=OPENAI_KEY
            )
            embedding_vector = embedding_model.embed_query(user_input)
            
            return public_crud.call_match_qna(embedding_vector,
                                              match_count)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def retrieve_common_situation(self, 
                                  user_input: str, 
                                  match_count: int = 5,
                                  public_crud: PublicCRUD = next(get_public_crud())):
        
        try:
            embedding_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=OPENAI_KEY
            )
            embedding_vector = embedding_model.embed_query(user_input)
            
            return public_crud.call_match_common_situation(embedding_vector,
                                                           match_count)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def get_or_create_order(self,
                            customer_id: int,
                            receiver_name: str,
                            receiver_phone_number: str,
                            receiver_address: str,
                            shipping_fee: int,
                            public_crud: PublicCRUD = next(get_public_crud())) -> Order:
        try:
            unshipped_order = public_crud.get_unshipped_order(customer_id=customer_id)
            
            if unshipped_order is None:
                return public_crud.create_order(customer_id=customer_id,
                                                receiver_name=receiver_name,
                                                receiver_phone_number=receiver_phone_number,
                                                receiver_address=receiver_address,
                                                shipping_fee=shipping_fee)
            
            return unshipped_order
                
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def get_unshipped_order(self,
                              customer_id: int,
                              public_crud: PublicCRUD = next(get_public_crud())) -> Optional[Order]:
        
        try:
            return public_crud.get_unshipped_order(customer_id=customer_id)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def get_shipped_order(self,
                              customer_id: int,
                              public_crud: PublicCRUD = next(get_public_crud())) -> Optional[List[Order]]:
        
        try:
            return public_crud.get_shipped_order(customer_id=customer_id)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def get_editable_orders(self,
                                   customer_id: int,
                                   public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[List[Order]]:
        try:
            return public_crud.get_editable_orders(customer_id=customer_id)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def retrieve_product_descriptions(self,
                                      user_input: str, 
                                      match_count: int = 5,
                                      public_crud: PublicCRUD = next(get_public_crud())):
        
        try:
            embedding_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=OPENAI_KEY
            )
            embedding_vector = embedding_model.embed_query(user_input)
            
            return public_crud.call_match_product_descriptions(embedding_vector,
                                                               match_count)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def get_product_embedding_info(self, 
                                    user_input: str,
                                    match_count: int = 5,
                                    number_of_products: int = 5,
                                    public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[List[dict]]:
        try:
            product_id_list = []
            product_raw = self.retrieve_product_descriptions(user_input, match_count, public_crud)

            # get the list of product_id
            for data in product_raw:
                match = re.search(r"mã sản phẩm:\s*(\d+)", data['content'])
                if match:
                    product_code = match.group(1)
                    product_id_list.append(int(product_code))
                    
            
            # query by ids
            products = public_crud.search_products_by_product_ids(product_id_list)
            return products[:number_of_products]

        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
        
    def get_customer_by_chat_id(self,
                                chat_id: str,
                                public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[Customer]:
        try:
            return public_crud.get_customer_by_chat_id(chat_id)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def get_order_by_id(self,
                        order_id: int,
                        public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[Order]:
        try:
            return public_crud.get_order_by_id(order_id)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def get_order_detail(self,
                         order_id: int,
                         public_crud: PublicCRUD = next(get_public_crud())
    ):
        try:
            order_items = self.get_order_items_detail(order_id)
            order_info = self.get_order_by_id(order_id)
            return order_info, order_items
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
        
        
    def update_order(self,
                     order_id: int, 
                     payment: Optional[str] = None,
                     order_total: Optional[int] = None,
                     shipping_fee: Optional[int] = None,
                     grand_total: Optional[int] = None,
                     receiver_name: Optional[str] = None,
                     receiver_phone_number: Optional[str] = None,
                     receiver_address: Optional[str] = None,
                     status: Optional[str] = None,
                     public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[Order]:
        try:
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
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def delete_item(self,
                    item_id: int,
                    public_crud: PublicCRUD = next(get_public_crud())
    ) -> bool:
        try:
            return public_crud.delete_items_item_id(
                item_id=item_id
            )
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
            
    def update_order_item_quantity(self,
                                   item_id: int,
                                   new_quantity: int,
                                   public_crud: PublicCRUD = next(get_public_crud())
    ) -> bool:
        try:
            new_item = public_crud.update_order_item_quantity(
                item_id=item_id,
                new_quantity=new_quantity
            )
            
            if new_item:
                if new_item.quantity == 0:
                    delete_item = self.delete_item(item_id=item_id)
                    if delete_item:
                        return True
                    else:
                        return False
                return True 
            return False
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()