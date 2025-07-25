from json import JSONDecodeError
from math import prod
from os import PRIO_USER
from click import Option
from sqlalchemy.orm import Session
from app.core.state import SellState
from app.models.normal_models import (
    ProductDescription, Pricing, Inventory, Cart,
    Order, OrderItem, Customer
)
from datetime import datetime
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.exc import ResourceClosedError, SQLAlchemyError


class PublicCRUD:
    def __init__(self, db: Session):
        self.db = db
        
    # ------------------ EMBEDDING QUERY ------------------ #
    
    def call_match_qna(self, embedding_vector: list[float], match_count: int = 5):
        sql = text("""
            SELECT * FROM match_qna(:query_embedding, :match_count)
        """)

        result = self.db.execute(sql, {
            "query_embedding": embedding_vector,
            "match_count": match_count
        }).fetchall()

        return [dict(r._mapping) for r in result]
    
    def call_match_common_situation(self, embedding_vector: list[float], match_count: int = 5):
        sql = text("""
            SELECT * FROM match_common_situations(:query_embedding, :match_count)
        """)

        result = self.db.execute(sql, {
            "query_embedding": embedding_vector,
            "match_count": match_count
        }).fetchall()

        return [dict(r._mapping) for r in result]
    
    def call_match_product_descriptions(self, embedding_vector: list[float], match_count: int = 5):
        sql = text("""
            SELECT * FROM match_product_descriptions(:query_embedding, :match_count)
        """)

        result = self.db.execute(sql, {
            "query_embedding": embedding_vector,
            "match_count": match_count
        }).fetchall()

        return [dict(r._mapping) for r in result]
        
    # ------------------ OTHER QUERY ------------------ #
    
    def get_order_summary_by_id(self, order_id: int) -> Optional[dict]:
        result = (
            self.db.query(
                Customer.name.label("customer_name"),
                Customer.phone_number.label("customer_phone"),
                Customer.address.label("customer_address"),

                Order.payment,
                Order.order_total,
                Order.shipping_fee,
                Order.grand_total
            )
            .join(Customer, Order.customer_id == Customer.customer_id)
            .filter(Order.order_id == order_id)
            .first()
        )

        return dict(result._mapping) if result else None
    
    def get_order_items_with_details(self, order_id: int) -> List[dict]:
        results = (
            self.db.query(
                OrderItem.id.label("item_id"),
                OrderItem.product_id,
                OrderItem.sku,
                ProductDescription.product_name,
                Pricing.variance_description.label("variance_name"),
                OrderItem.quantity,
                OrderItem.price,
                OrderItem.subtotal,
            )
            .join(ProductDescription, OrderItem.product_id == ProductDescription.product_id)
            .join(Pricing, OrderItem.sku == Pricing.sku)
            .filter(OrderItem.order_id == order_id)
            .all()
        )
    
        return [dict(row._mapping) for row in results]
    
    def execute_command(self, command: str) -> List[dict]:
        sql = text(command.strip())
        try:
            result = self.db.execute(sql)
            # Kiểm tra có trả về dòng không (SELECT, RETURNING, ...)
            if result.returns_rows:
                return [dict(row._mapping) for row in result.fetchall()]
            else:
                self.db.commit()  # Câu UPDATE, INSERT, DELETE cần commit
                return []
        except ResourceClosedError:
            self.db.commit()
            return []
    
    def search_products_by_keyword(self, keyword: str) -> List[dict]:
        results = (
            self.db.query(
                ProductDescription.product_id,
                Pricing.sku,
                ProductDescription.product_name,
                Pricing.variance_description,
                ProductDescription.brief_description,
                Pricing.price,
                Pricing.inventory
            )
            .join(Pricing, ProductDescription.product_id == Pricing.product_id)
            .filter(
                ProductDescription.product_name.ilike(f"%{keyword}%"),
                Pricing.price != 0
            )
            .all()
        )

        return [dict(row._mapping) for row in results]  # chuyển kết quả thành list of dict
    
    def get_product_by_product_id_and_sku(self, product_id: int, sku: str) -> dict:
        results = (
            self.db.query(
                ProductDescription.product_name,
                Pricing.price
            )
            .join(Pricing, ProductDescription.product_id == Pricing.product_id)
            .join(Inventory, Pricing.sku == Inventory.sku)
            .filter(
                ProductDescription.product_id == product_id,
                Pricing.sku == sku
            )
            .first()
        )
        
        return dict(results._mapping) # chuyển kết quả thành list of dict
    
    def search_products_by_product_ids(self, product_ids: List[int]) -> List[dict]:
        results = (
            self.db.query(
                ProductDescription.product_id,
                Pricing.sku,
                ProductDescription.product_name,
                Pricing.variance_description,
                ProductDescription.brief_description,
                Pricing.price,
                Pricing.inventory
            )
            .join(Pricing, ProductDescription.product_id == Pricing.product_id)
            .filter(
                ProductDescription.product_id.in_(product_ids),
                Pricing.inventory != 0,
                Pricing.price != 0
            )
            .all()
        )

        return [dict(row._mapping) for row in results]
    
    # ------------------ CUSTOMER ------------------ #
    
    def create_customer(self, 
                        name: Optional[str] = None,
                        phone_number: Optional[str] = None, 
                        address: Optional[str] = None,
                        chat_id: str = None,
    ) -> Customer:
        customer = Customer(
            name=name,
            phone_number=phone_number,
            address=address,
            chat_id=chat_id,
            created_at=datetime.now()
        )
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.customer_id == customer_id).first()
    
    def get_customer_by_phone_number(self, phone_number: str) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.phone_number == phone_number).first()
    
    def get_customer_by_chat_id(self, chat_id: str) -> Optional[Customer]:
        return self.db.query(Customer).filter(Customer.chat_id == chat_id).first()

    def get_all_customers(self) -> List[Customer]:
        return self.db.query(Customer).all()

    def update_customer_info(self, 
                             customer_id: int,
                             name: Optional[str] = None,
                             phone_number: Optional[str] = None,
                             address: Optional[str] = None
    ) -> Optional[Customer]:
        customer = self.get_customer_by_id(customer_id)
        if customer:
            if name is not None:
                customer.name = name
            if phone_number is not None:
                customer.phone_number = phone_number
            if address is not None:
                customer.address = address
            self.db.commit()
            self.db.refresh(customer)
            return customer
        return None
    
    def update_customer_state_by_chat_id(db: Session, chat_id: str, new_state: dict) -> Optional[Customer]:
        customer = db.query(Customer).filter(Customer.chat_id == chat_id).one()
        customer.state = new_state
        db.commit()
        db.refresh(customer)
        return customer

    def delete_customer(self, customer_id: int) -> bool:
        customer = self.get_customer_by_id(customer_id)
        if customer:
            self.db.delete(customer)
            self.db.commit()
            return True
        return False
    
    # ------------------ ORDER ------------------ #
    
    def create_order(self,
                     customer_id: Optional[int] = None,
                     status: Optional[str] = 'pending',
                     order_total: Optional[int] = 0,
                     shipping_fee: Optional[int] = 0,
                     grand_total: Optional[int] = None,
                     payment: Optional[str] = 'COD',
                     receiver_name: Optional[str] = "Không có",
                     receiver_phone_number: Optional[str] = "Không có",
                     receiver_address: Optional[str] = "Không có",
                 
    ) -> Order:
    
        if grand_total is None:
            grand_total = order_total + shipping_fee

        order = Order(
            customer_id=customer_id,
            status=status,
            order_total=order_total,
            shipping_fee=shipping_fee,
            grand_total=grand_total,
            payment=payment,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            receiver_name=receiver_name,
            receiver_phone_number=receiver_phone_number,
            receiver_address=receiver_address
        )

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def get_unshipped_order(self, customer_id: int) -> Optional[Order]:
        unshipped_statuses = ['pending', 'created', 'awaiting_payment', 'confirmed', 'processing']
        return self.db.query(Order)\
            .filter(Order.customer_id == customer_id)\
            .filter(Order.status.in_(unshipped_statuses))\
            .first()
            
    def get_shipped_order(self, customer_id: int) -> Optional[List[Order]]:
        shipped_statuses = ['shipped', 'in_transit', 'delivered', 'cancelled', 'returned', 'refunded']
        return self.db.query(Order)\
            .filter(Order.customer_id == customer_id)\
            .filter(Order.status.in_(shipped_statuses))\
            .all()
            
    def get_editable_orders(self, customer_id: int) -> Optional[List[Order]]:
        shipped_statuses = ['delivered', 'cancelled', 'returned', 'refunded']
        return (
            self.db.query(Order)
            .filter(Order.customer_id == customer_id)
            .filter(Order.status.notin_(shipped_statuses))
            .all()
        )

    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        return self.db.query(Order).filter(Order.order_id == order_id).first()

    def get_all_orders(self) -> List[Order]:
        return self.db.query(Order).all()

    def update_order_status(self, order_id: int, new_status: str) -> Optional[Order]:
        order = self.get_order_by_id(order_id)
        if order:
            order.status = new_status
            order.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(order)
            return order
        return None
    
    def update_order(self, 
                     order_id: int, 
                     payment: Optional[str] = None,
                     order_total: Optional[int] = None,
                     shipping_fee: Optional[int] = None,
                     grand_total: Optional[int] = None,
                     receiver_name: Optional[str] = None,
                     receiver_phone_number: Optional[str] = None,
                     receiver_address: Optional[str] = None,
                     status: Optional[str] = None
    ) -> Optional[Order]:
        order = self.get_order_by_id(order_id)
        if not order:
            return None

        if payment is not None:
            order.payment = payment
        if order_total is not None:
            order.order_total = order_total
        if shipping_fee is not None:
            order.shipping_fee = shipping_fee
        if grand_total is not None:
            order.grand_total = grand_total
        if receiver_name is not None:
            order.receiver_name = receiver_name
        if receiver_phone_number is not None:
            order.receiver_phone_number = receiver_phone_number
        if receiver_address is not None:
            order.receiver_address = receiver_address
        if status is not None:
            order.status = status
            
        order.updated_at = datetime.now()

        order.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(order)
        return order

    def delete_order(self, order_id: int) -> bool:
        order = self.get_order_by_id(order_id)
        if order:
            self.db.delete(order)
            self.db.commit()
            return True
        return False
    
    # ------------------ ORDERITEM ------------------ #
    
    def create_order_item(self, order_id: int, product_id: int, sku: str,
                          quantity: Optional[int] = None,
                          price: Optional[int] = None,
                          subtotal: Optional[int] = None) -> OrderItem:
        order_item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            sku=sku,
            quantity=quantity,
            price=price,
            subtotal=subtotal
        )
        self.db.add(order_item)
        self.db.commit()
        self.db.refresh(order_item)
        return order_item
    
    def create_order_items_bulk(self, order_items: List[OrderItem]) -> Optional[List[OrderItem]]:
        self.db.add_all(order_items)
        self.db.commit()
        for item in order_items:
            self.db.refresh(item)
        return order_items

    def get_order_item_by_id(self, item_id: int) -> Optional[OrderItem]:
        return self.db.query(OrderItem).filter(OrderItem.id == item_id).first()

    def get_items_by_order_id(self, order_id: int) -> List[OrderItem]:
        return self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    
    def get_items_by_order_id_sku_product_id(self,
                                             order_id: int,
                                             product_id: int,
                                             sku: str) -> Optional[OrderItem]:
        
        return (
            self.db.query(OrderItem)
            .filter(
                OrderItem.order_id == order_id,
                OrderItem.product_id == product_id,
                OrderItem.sku == sku
            ).first()
        )

    def update_order_item_quantity(self, item_id: int, new_quantity: int) -> Optional[OrderItem]:
        item = self.get_order_item_by_id(item_id)
        if item:
            item.quantity = new_quantity
            item.subtotal = (item.price or 0) * new_quantity
            self.db.commit()
            self.db.refresh(item)
            return item
        return None

    def delete_items_item_id(self,
                             item_id: int,
    ) -> bool:
        item = self.get_order_item_by_id(
            item_id=item_id
        )
        if item:
            self.db.delete(item)
            self.db.commit()
            return True
        return False

    def delete_order_item(self, item_id: int) -> bool:
        item = self.get_order_item_by_id(item_id)
        if item:
            self.db.delete(item)
            self.db.commit()
            return True
        return False

    # ------------------ PRODUCT DESCRIPTION ------------------ #

    def create_product(self, product_id: int, product_name: str,
                       brief_description: Optional[str] = None,
                       description: Optional[str] = None) -> ProductDescription:
        product = ProductDescription(
            product_id=product_id,
            product_name=product_name,
            brief_description=brief_description,
            description=description
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_product_by_id(self, product_id: int) -> Optional[ProductDescription]:
        return self.db.query(ProductDescription).filter(ProductDescription.product_id == product_id).first()

    def get_all_products(self):
        return self.db.query(ProductDescription).all()

    def delete_product_by_id(self, product_id: int) -> bool:
        product = self.get_product_by_id(product_id)
        if product:
            self.db.delete(product)
            self.db.commit()
            return True
        return False

    # ------------------ PRICING ------------------ #

    def create_pricing(self, product_id: int, sku: str,
                       variance_description: Optional[str] = None,
                       price: Optional[int] = None) -> Pricing:
        pricing = Pricing(
            product_id=product_id,
            sku=sku,
            variance_description=variance_description,
            price=price
        )
        self.db.add(pricing)
        self.db.commit()
        self.db.refresh(pricing)
        return pricing

    def get_pricing_by_sku(self, sku: str) -> Optional[Pricing]:
        return self.db.query(Pricing).filter(Pricing.sku == sku).first()

    def get_all_pricings(self):
        return self.db.query(Pricing).all()
    
    def decrease_inventory(self, order_items: List[OrderItem]):
        try:
            for item in order_items:
                pricing_record = (
                    self.db.query(Pricing)
                    .filter(Pricing.sku == item.sku)
                    .with_for_update()  
                    .one_or_none()
                )
                if not pricing_record:
                    continue
                
                if pricing_record:
                    current_inventory = pricing_record.inventory or 0
                    updated_inventory = current_inventory - item.quantity

                    if updated_inventory < 0:
                        raise ValueError(
                            f"Không đủ tồn kho cho SKU={item.sku}: "
                            f"hiện còn {updated_inventory}, yêu cầu {item.quantity}"
                        )

                    pricing_record.inventory = max(updated_inventory, 0)

            self.db.commit()
        except (ValueError, SQLAlchemyError) as e:
            self.db.rollback()
            # Log exception tuỳ theo context của bạn
            raise 

    def update_pricing_price(self, sku: str, new_price: int) -> Optional[Pricing]:
        pricing = self.get_pricing_by_sku(sku)
        if pricing:
            pricing.price = new_price
            self.db.commit()
            self.db.refresh(pricing)
            return pricing
        return None

    def delete_pricing_by_sku(self, sku: str) -> bool:
        pricing = self.get_pricing_by_sku(sku)
        if pricing:
            self.db.delete(pricing)
            self.db.commit()
            return True
        return False

    # ------------------ INVENTORY ------------------ #

    def create_inventory(self, sku: str, import_price: Optional[int] = None,
                         wholesale_price: Optional[int] = None,
                         inventory_quantity: Optional[int] = None,
                         shelf: Optional[str] = None,
                         shelf_code: Optional[str] = None) -> Inventory:
        inventory = Inventory(
            sku=sku,
            import_price=import_price,
            wholesale_price=wholesale_price,
            inventory_quantity=inventory_quantity,
            shelf=shelf,
            shelf_code=shelf_code
        )
        self.db.add(inventory)
        self.db.commit()
        self.db.refresh(inventory)
        return inventory

    def get_inventory_by_sku(self, sku: str) -> Optional[Inventory]:
        return self.db.query(Inventory).filter(Inventory.sku == sku).first()

    def get_all_inventory(self):
        return self.db.query(Inventory).all()

    def update_inventory_quantity(self, sku: str, quantity: int) -> Optional[Inventory]:
        inventory = self.get_inventory_by_sku(sku)
        if inventory:
            inventory.inventory_quantity = quantity
            self.db.commit()
            self.db.refresh(inventory)
            return inventory
        return None

    def delete_inventory_by_sku(self, sku: str) -> bool:
        inventory = self.get_inventory_by_sku(sku)
        if inventory:
            self.db.delete(inventory)
            self.db.commit()
            return True
        return False
    
    # ------------------ CART ------------------ #
    
    def create_cart(self,
                    chat_id: Optional[str] = None,
                    customer_name: Optional[str] = None,
                    customer_phone: Optional[str] = None,
                    address: Optional[str] = None,
                    list_cart: Optional[dict] = None) -> Cart:
        cart = Cart(
            chat_id=chat_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            address=address,
            list_cart=list_cart
        )
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return cart

    def get_cart_by_id(self, cart_id: int) -> Optional[Cart]:
        return self.db.query(Cart).filter(Cart.id == cart_id).first()

    def get_cart_by_chat_id(self, chat_id: str) -> List[Cart]:
        return self.db.query(Cart).filter(Cart.chat_id == chat_id).all()

    def get_all_carts(self) -> List[Cart]:
        return self.db.query(Cart).all()

    def update_cart(self,
                    cart_id: int,
                    customer_name: Optional[str] = None,
                    customer_phone: Optional[str] = None,
                    address: Optional[str] = None,
                    list_cart: Optional[dict] = None) -> Optional[Cart]:
        cart = self.get_cart_by_id(cart_id)
        if cart:
            if customer_name is not None:
                cart.customer_name = customer_name
            if customer_phone is not None:
                cart.customer_phone = customer_phone
            if address is not None:
                cart.address = address
            if list_cart is not None:
                cart.list_cart = list_cart
            self.db.commit()
            self.db.refresh(cart)
            return cart
        return None

    def delete_cart(self, cart_id: int) -> bool:
        cart = self.get_cart_by_id(cart_id)
        if cart:
            self.db.delete(cart)
            self.db.commit()
            return True
        return False