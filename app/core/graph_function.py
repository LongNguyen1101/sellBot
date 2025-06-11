from sqlalchemy import Boolean
from sqlalchemy.orm import Session
from app.chain.sell_chain import SellChain
from app.db.database import get_db
from app.models.normal_models import Customer, Order, OrderItem
from app.services.crud_public import PublicCRUD
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date, time as dtime, timedelta
from app.core.state import SellState
from typing import List, Optional, Tuple
import json

def get_public_crud():
    """Generator function to provide a PublicCRUD instance with a database session."""
    db: Session = next(get_db())
    try:
        yield PublicCRUD(db)
    finally:
        db.close()

class GraphFunction:
    def __init__(self):
        self.chain = SellChain()
        
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
        
    def get_products_by_keyword(self, keyword: str, public_crud: PublicCRUD = next(get_public_crud())) -> List[dict]:
        try:
            product = public_crud.search_products_by_keyword(keyword=keyword)
            return product
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
    
    def add_customer(self,
                     name: str,
                     phone_number: str,
                     address: str,
                     public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[Customer]:
        try:
            customer = public_crud.create_customer(
                name=name,
                phone_number=phone_number,
                address=address
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
    
    def create_order(self,
                     customer_id: int,
                     public_crud: PublicCRUD = next(get_public_crud())
    ) -> Optional[Order]:
        try:
            
            order = public_crud.create_order(customer_id=customer_id)
            return order
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
                               cart_items: List[dict],
                               order_id: int,
                               public_crud: PublicCRUD = next(get_public_crud())
    ) -> Tuple[Optional[List[OrderItem]], int]:
        order_total = 0
        order_items: List[OrderItem] = []
        
        if cart_items is not None:
            for item in cart_items:
                order_item = OrderItem(
                    order_id = order_id,
                    product_id = item["product_id"],
                    sku = item["sku"],
                    quantity = item["quantity"],
                    price = item["price"],
                    subtotal = item["subtotal"]
                )
                order_total += item["subtotal"]
                order_items.append(order_item)
            
            try:
                created_order_items = public_crud.create_order_items_bulk(order_items)
                return created_order_items, order_total
            except SQLAlchemyError as e:
                public_crud.db.rollback()
                raise
            finally:
                public_crud.db.close()
        return None, 0
    
    def return_order(self, order_id: int, public_crud: PublicCRUD = next(get_public_crud())) -> List[dict]:
        try:
            return public_crud.get_order_items_with_details(order_id)
        except SQLAlchemyError as e:
            public_crud.db.rollback()
            raise
        finally:
            public_crud.db.close()
        
    def get_order_items(self, order_id: int, public_crud: PublicCRUD = next(get_public_crud())) -> List[dict]:
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
    