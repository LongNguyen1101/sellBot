from sqlalchemy.orm import Session
from app.models.normal_models import (
    ProductDescription, Pricing,
    Order, OrderItem, Customer
)
from datetime import datetime
from typing import Any, Optional, List
from sqlalchemy import text, bindparam

UNSHIPPED_STATUSES = ['pending', 'created', 'awaiting_payment', 'confirmed', 'processing']
SHIPPED_STATUSES = ['shipped', 'in_transit', 'delivered', 'cancelled', 'returned', 'refunded']
NON_EDITABLE_STATUSES = ['delivered', 'cancelled', 'returned', 'refunded']

class PublicCRUD:
    def __init__(self, db: Session):
        self.db = db
        
    # ------------------ EMBEDDING QUERY ------------------ #
    
    def call_match_qna(self, 
                       embedding_vector: list[float], 
                       match_count: int = 5
    ) -> List[dict]:
        sql = text("""
            SELECT * FROM match_qna(:query_embedding, :match_count)
        """)

        result = self.db.execute(sql, {
            "query_embedding": embedding_vector,
            "match_count": match_count
        }).fetchall()

        return [dict(r._mapping) for r in result]
    
    def call_match_common_situation(self, 
                                    embedding_vector: list[float], 
                                    match_count: int = 5
    ) -> List[dict]:
        sql = text("""
            SELECT * FROM match_common_situations(:query_embedding, :match_count)
        """)

        result = self.db.execute(sql, {
            "query_embedding": embedding_vector,
            "match_count": match_count
        }).fetchall()

        return [dict(r._mapping) for r in result]
    
    def call_match_product_descriptions(self, 
                                        embedding_vector: list[float], 
                                        match_count: int = 5
    ) -> List[dict]:
        sql = text("""
            SELECT * FROM match_product_descriptions(:query_embedding, :match_count)
        """)

        result = self.db.execute(sql, {
            "query_embedding": embedding_vector,
            "match_count": match_count
        }).fetchall()

        return [dict(r._mapping) for r in result]
        
    # ------------------ OTHER QUERY ------------------ #
    
    def get_order_items_with_details(self, order_id: int) -> List[dict]:
        sql = text("""
            SELECT
                oi.id AS item_id,
                oi.product_id,
                oi.sku,
                pd.product_name,
                p.variance_description AS variance_name,
                oi.quantity,
                oi.price,
                oi.subtotal
            FROM order_item oi
            JOIN product_description pd ON oi.product_id = pd.product_id
            JOIN pricing p ON oi.sku = p.sku
            WHERE oi.order_id = :order_id
        """)

        params = {"order_id": order_id}

        result = self.db.execute(sql, params)
        rows = result.fetchall()

        return [dict(row) for row in rows] if rows else None
    
    def search_products_by_keyword(self, 
                                   keyword: str, 
                                   limit: int = 5,
    ) -> List[dict] | None:
        sql = text("""
            SELECT 
                pd.product_id,
                p.sku,
                pd.product_name,
                p.variance_description,
                pd.brief_description,
                p.price,
                p.inventory
            FROM product_description pd
            JOIN pricing p ON pd.product_id = p.product_id
            WHERE pd.product_name ILIKE :pattern
              AND p.price != 0
            LIMIT :limit
        """)
        params = {"pattern": f"%{keyword}%", "limit": limit}
        
        result = self.db.execute(sql, params)
        self.db.commit()
        rows = result.mappings().all()
        
        return [dict(row) for row in rows] if rows else None
    
    def search_products_by_product_ids(self, 
                                       product_ids: List[int]
    ) -> Optional[List[dict]] | None:
        sql = text("""
            SELECT
                pd.product_id,
                p.sku,
                pd.product_name,
                p.variance_description,
                pd.brief_description,
                p.price,
                p.inventory
            FROM product_description pd
            JOIN pricing p ON pd.product_id = p.product_id
            WHERE pd.product_id IN :product_ids
              AND p.inventory != 0
              AND p.price != 0
        """).bindparams(bindparam("product_ids", expanding=True))

        params = {"product_ids": product_ids}

        result = self.db.execute(sql, params)
        self.db.commit()
        rows = result.mappings().all()
        
        return [dict(row) for row in rows] if rows else None
    
    # ------------------ CUSTOMER ------------------ #
    
    def create_customer(self, 
                        name: Optional[str] = None,
                        phone_number: Optional[str] = None, 
                        address: Optional[str] = None,
                        chat_id: str = None,
                        parse_object: bool = True
    ) -> Customer | dict[str, Any] | None:
        sql = text("""
            INSERT INTO customer (name, phone_number, address, chat_id, created_at)
            VALUES (:name, :phone_number, :address, :chat_id, :created_at)
            RETURNING customer_id, name, phone_number, address, chat_id, created_at
        """)
        
        params = {
            "name": name,
            "phone_number": phone_number,
            "address": address,
            "chat_id": chat_id,
            "created_at": datetime.now()
        }
        
        result = self.db.execute(sql, params)
        self.db.commit()
        row = result.mappings().first()
        
        if not row:
            return None
        
        return Customer(**row) if parse_object else dict(row)
    
    def get_customer_by_id(self, 
                           customer_id: int, 
                           parse_object: bool = True
    ) -> Customer | dict[str, Any] | None:
        sql = text("""
            SELECT customer_id, name, phone_number, address, chat_id
            FROM customer
            WHERE customer_id = :customer_id
            LIMIT 1
        """)

        params = {"customer_id": customer_id}

        result = self.db.execute(sql, params)
        row = result.mappings().first()

        if not row:
            return None
        
        return Customer(**row) if parse_object else dict(row)
    
    
    def get_customer_by_chat_id(self, 
                                chat_id: str, 
                                parse_object: bool = True
    ) -> Customer | dict[str, Any] | None:
        sql = text("""
            SELECT customer_id, name, phone_number, address
            FROM customer
            WHERE chat_id = :chat_id
            LIMIT 1
        """)
        params = {"chat_id": chat_id}
        
        result = self.db.execute(sql, params)
        row = result.mappings().first()
        
        if not row:
            return None
        
        return Customer(**row) if parse_object else dict(row)
    
    def get_or_create_customer(self,
                               chat_id: str,
                               parse_object: bool = True
    ) -> Customer | dict[str, Any] | None:
        sql = text("""
            WITH ins AS (
                INSERT INTO customer (chat_id)
                VALUES (:chat_id)
                ON CONFLICT (chat_id) DO NOTHING
                RETURNING customer_id, name, phone_number, address
            )
            SELECT * FROM ins
            UNION ALL
            SELECT customer_id, name, phone_number, address
            FROM customer
            WHERE chat_id = :chat_id
            LIMIT 1;
        """)
        
        params = {"chat_id": chat_id}
        
        result = self.db.execute(sql, params)
        row = result.mappings().first()
        
        if not row:
            return None
        
        return Customer(**row) if parse_object else dict(row)
    
    def update_customer_info(self,
                             customer_id: int,
                             name: Optional[str] = None,
                             phone_number: Optional[str] = None,
                             address: Optional[str] = None,
                             parse_object: bool = True
    ) -> Customer | dict[str, Any] | None:
        updated_fields = {
            k: v for k, v in {
                "name": name,
                "phone_number": phone_number, 
                "address": address
            }.items() if v is not None
        }
        
        if not updated_fields:
            return self.get_customer_by_id(customer_id, parse_object)

        set_clause_sql = ", ".join(f"{k} = :{k}" for k in updated_fields.keys())
        params = {"customer_id": customer_id, **updated_fields}

        sql = text(f"""
            UPDATE customer 
            SET {set_clause_sql}
            WHERE customer_id = :customer_id
            RETURNING customer_id, name, phone_number, address, chat_id
        """)
        
        result = self.db.execute(sql, params)
        row = result.mappings().first()
        
        if not row:
            return None
        
        return Customer(**row) if parse_object else dict(row)

    def delete_customer(self, customer_id: int) -> bool:
        sql = text("""
            DELETE FROM customer
            WHERE customer_id = :customer_id
            RETURNING 1
        """)
        params = {"customer_id": customer_id}

        res = self.db.execute(sql, params)
        self.db.commit()

        return res.fetchone() is not None
    
    # ------------------ ORDER ------------------ #
    
    def create_order(self,
                     customer_id: int = None,
                     status: str = 'pending',
                     order_total: int = 0,
                     shipping_fee: int = 0,
                     grand_total: int = 0,
                     payment: str = 'COD',
                     receiver_name: Optional[str] = "Không có",
                     receiver_phone_number: Optional[str] = "Không có",
                     receiver_address: Optional[str] = "Không có"
    ) -> int | None:
        sql = text("""
            INSERT INTO orders (
                customer_id, status, order_total, shipping_fee, grand_total, payment,
                created_at, updated_at, receiver_name, receiver_phone_number, receiver_address
            )
            VALUES (
                :customer_id, :status, :order_total, :shipping_fee, :grand_total, :payment,
                :created_at, :updated_at, :receiver_name, :receiver_phone_number, :receiver_address
            )
            RETURNING order_id
        """)

        now = datetime.now()
        params = {
            "customer_id": customer_id,
            "status": status,
            "order_total": order_total,
            "shipping_fee": shipping_fee,
            "grand_total": grand_total,
            "payment": payment,
            "created_at": now,
            "updated_at": now,
            "receiver_name": receiver_name,
            "receiver_phone_number": receiver_phone_number,
            "receiver_address": receiver_address
        }

        result = self.db.execute(sql, params)
        self.db.commit()
        row = result.fetchone()
        
        return row[0] if row else None
            
    def get_editable_orders(self, 
                            customer_id: int
    ) -> List[dict[str, Any]] | None:
        
        all_statuses = set(UNSHIPPED_STATUSES + SHIPPED_STATUSES)
        editable_statuses = list(all_statuses - set(NON_EDITABLE_STATUSES))

        sql = text("""
            SELECT
              o.*,
              COALESCE(oi.items, '[]'::json) AS order_items
            FROM orders o
            LEFT JOIN LATERAL (
              SELECT JSON_AGG(
                       JSON_BUILD_OBJECT(
                         'id', oi.id,
                         'product_id', oi.product_id,
                         'sku', pr.sku,
                         'quantity', oi.quantity,
                         'price', oi.price,
                         'subtotal', oi.subtotal,
                         'product_name', pd.product_name,
                         'variance_name', pr.variance_description
                       ) ORDER BY oi.id
                     ) AS items
              FROM order_items oi
              LEFT JOIN product_description pd ON oi.product_id = pd.product_id
              LEFT JOIN pricing pr ON oi.sku = pr.sku
              WHERE oi.order_id = o.order_id
            ) oi ON true
            WHERE o.customer_id = :customer_id
              AND o.status = ANY(:editable_statuses)
            ORDER BY o.created_at DESC;
        """)

        params = {
            "customer_id": customer_id,
            "editable_statuses": editable_statuses
        }

        result = self.db.execute(sql, params)
        rows = result.mappings().all()

        return [dict(row) for row in rows] if rows else None
    
    def get_order_with_items(self,
                             order_id: int
    ) -> dict[str, Any] | None:
        sql = text("""
            SELECT
              o.*,
              COALESCE(oi.items, '[]'::json) AS order_items
            FROM orders o
            LEFT JOIN LATERAL (
              SELECT JSON_AGG(
                       JSON_BUILD_OBJECT(
                         'id', oi.id,
                         'product_id', oi.product_id,
                         'sku', pr.sku,
                         'quantity', oi.quantity,
                         'price', oi.price,
                         'subtotal', oi.subtotal,
                         'product_name', pd.product_name,
                         'variance_name', pr.variance_description
                       ) ORDER BY oi.id
                     ) AS items
              FROM order_items oi
              LEFT JOIN product_description pd ON oi.product_id = pd.product_id
              LEFT JOIN pricing pr ON oi.sku = pr.sku
              WHERE oi.order_id = o.order_id
            ) oi ON true
            WHERE o.order_id = :order_id;
        """)

        params = {"order_id": order_id}

        result = self.db.execute(sql, params)
        row = result.mappings().first()

        return dict(row) if row else None
    
    def get_order_by_id(self, 
                        order_id: int, 
                        parse_object: bool = True
    ) -> Order | dict[str, Any] | None:
        sql = text("""
            SELECT *
            FROM orders 
            WHERE order_id = :order_id
            LIMIT 1
        """)
        
        params = {"order_id": order_id}
        
        result = self.db.execute(sql, params)
        row = result.mappings().first()
        
        if not row:
            return None
        
        return Order(**row) if parse_object else dict(row)

    def update_order_status(self, 
                            order_id: int, 
                            new_status: str, 
                            parse_object: bool = True
    ) -> Order | dict[str, Any] | None:
        sql = text("""
            UPDATE orders 
            SET status = :new_status, updated_at = :updated_at
            WHERE order_id = :order_id
            RETURNING order_id, customer_id, status, total_amount, created_at, updated_at,
                      shipping_address, notes
        """)
        
        params = {
            "order_id": order_id,
            "new_status": new_status,
            "updated_at": datetime.now()
        }
        
        result = self.db.execute(sql, params)
        self.db.commit()
        row = result.mappings().first()
        
        if not row:
            return None
        
        return Order(**row) if parse_object else dict(row)
    
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
                     parse_object: bool = True
    ) -> Order | dict[str, Any] | None:
        
        updated_fields = {}
        if payment is not None:
            updated_fields["payment"] = payment
        if order_total is not None:
            updated_fields["order_total"] = order_total
        if shipping_fee is not None:
            updated_fields["shipping_fee"] = shipping_fee
        if grand_total is not None:
            updated_fields["grand_total"] = grand_total
        if receiver_name is not None:
            updated_fields["receiver_name"] = receiver_name
        if receiver_phone_number is not None:
            updated_fields["receiver_phone_number"] = receiver_phone_number
        if receiver_address is not None:
            updated_fields["receiver_address"] = receiver_address
        if status is not None:
            updated_fields["status"] = status

        if not updated_fields:
            return self.get_order_by_id(order_id, parse_object)

        set_clause = ", ".join(f"{k} = :{k}" for k in updated_fields.keys())
        params = {"order_id": order_id, "updated_at": datetime.now(), **updated_fields}

        sql = text(f"""
            UPDATE orders
            SET {set_clause}, updated_at = :updated_at
            WHERE order_id = :order_id
            RETURNING *
        """)

        result = self.db.execute(sql, params)
        self.db.commit()
        row = result.mappings().first()

        if not row:
            return None

        return Order(**row) if parse_object else dict(row)
    
    def delete_order(self, order_id: int) -> bool:
        sql = text("""
            DELETE FROM orders 
            WHERE order_id = :order_id
            RETURNING 1
        """)
        
        params = {"order_id": order_id}
        
        res = self.db.execute(sql, params)
        self.db.commit()
        
        return res.fetchone() is not None
    
    # ------------------ ORDERITEM ------------------ #
    
    def create_order_item(self, 
                          order_id: int, 
                          product_id: int, 
                          sku: str,
                          quantity: Optional[int] = None,
                          price: Optional[int] = None,
                          subtotal: Optional[int] = None,
                          parse_object: bool = True
    ) -> OrderItem | dict[str, Any] | None:
    
        sql = text("""
            INSERT INTO order_items (order_id, product_id, sku, quantity, price, subtotal)
            VALUES (:order_id, :product_id, :sku, :quantity, :price, :subtotal)
            RETURNING *
        """)

        params = {
            "order_id": order_id,
            "product_id": product_id,
            "sku": sku,
            "quantity": quantity,
            "price": price,
            "subtotal": subtotal
        }

        result = self.db.execute(sql, params)
        self.db.commit()
        row = result.mappings().first()
        
        if not row:
            return None

        return OrderItem(**row) if parse_object else dict(row)
    
    def create_order_items_bulk(self, 
                                order_items: List[dict], 
                                parse_object: bool = True
    ) -> List[OrderItem] | List[dict[str, Any]] | None:
        if not order_items:
            return []

        sql = text("""
            WITH inserted_items AS (
                INSERT INTO order_items (order_id, product_id, sku, quantity, price, subtotal)
                VALUES (:order_id, :product_id, :sku, :quantity, :price, :subtotal)
                RETURNING *
            )
            SELECT
                ii.*,
                pd.product_name,
                pr.variance_description AS variance_name
            FROM inserted_items ii
            LEFT JOIN product_description pd ON ii.product_id = pd.product_id
            LEFT JOIN pricing pr ON ii.sku = pr.sku
        """)

        result = self.db.execute(sql, order_items)
        self.db.commit()
        rows = result.mappings().all()
        
        if not rows:
            return None
        return [OrderItem(**row) for row in rows] if parse_object else [dict(row) for row in rows]

    def get_order_item_by_id(self, 
                             item_id: int, 
                             parse_object: bool = True
    ) -> OrderItem | dict[str, Any] | None:
        sql = text("""
            SELECT *
            FROM order_items
            WHERE id = :item_id
            LIMIT 1
        """)

        params = {"item_id": item_id}

        result = self.db.execute(sql, params)
        row = result.mappings().first()
        
        if not row:
            return None

        return OrderItem(**row) if parse_object else dict(row)

    def get_items_by_order_id(self, 
                              order_id: int, 
                              parse_object: bool = True
    ) -> List[OrderItem] | List[dict[str, Any]] | None:
        sql = text("""
            SELECT *
            FROM order_items
            WHERE order_id = :order_id
            ORDER BY id
        """)

        params = {"order_id": order_id}

        result = self.db.execute(sql, params)
        rows = result.mappings().all()
        
        if not rows:
            return None

        return [OrderItem(**row) for row in rows] if parse_object else [dict(row) for row in rows]
    
    def update_order_item_quantity(self, 
                                   item_id: int, 
                                   new_quantity: int, 
                                   parse_object: bool = True
    ) -> OrderItem | dict[str, Any] | None:
        sql = text("""
            UPDATE order_items
            SET quantity = :new_quantity,
            WHERE id = :item_id
            RETURNING *
        """)

        params = {
            "item_id": item_id,
            "new_quantity": new_quantity
        }

        result = self.db.execute(sql, params)
        self.db.commit()
        row = result.mappings().first()

        if not row:
            return None

        return OrderItem(**row) if parse_object else dict(row)

    def delete_order_item(self, item_id: int) -> bool:
        sql = text("""
            DELETE FROM order_items
            WHERE id = :item_id
            RETURNING 1
        """)
        
        params = {"item_id": item_id}
        res = self.db.execute(sql, params)
        self.db.commit()
        
        return res.fetchone() is not None

    # ------------------ PRODUCT DESCRIPTION ------------------ #
    
    def create_product(self, 
                       product_name: str,
                       brief_description: Optional[str] = None,
                       description: Optional[str] = None,
                       parse_object: bool = True
    ) -> ProductDescription | dict[str, Any] | None:
    
        sql = text("""
            INSERT INTO product_descriptions (product_name, brief_description, description)
            VALUES (:product_name, :brief_description, :description)
            RETURNING *
        """)

        params = {
            "product_name": product_name,
            "brief_description": brief_description,
            "description": description
        }

        result = self.db.execute(sql, params)
        self.db.commit()
        row = result.mappings().first()
        
        if not row:
            return None
        
        return ProductDescription(**row) if parse_object else dict(row)
    
    def get_product_by_id(self, 
                          product_id: int, 
                          parse_object: bool = True
    ) -> ProductDescription | dict[str, Any] | None:
        sql = text("""
            SELECT *
            FROM product_descriptions
            WHERE product_id = :product_id
            LIMIT 1
        """)

        params = {"product_id": product_id}

        result = self.db.execute(sql, params)
        row = result.mappings().first()

        if not row:
            return None
        
        return ProductDescription(**row) if parse_object else dict(row)
    
    def get_all_products(self, 
                         parse_object: bool = True
    ) -> List[ProductDescription] | List[dict[str, Any]] | None:
        sql = text("""
            SELECT *
            FROM product_descriptions
            ORDER BY product_id
        """)

        result = self.db.execute(sql)
        rows = result.mappings().all()
        
        if not rows:
            return None
        
        return [ProductDescription(**row) for row in rows] if parse_object else [dict(row) for row in rows]

    def delete_product_by_id(self, product_id: int) -> bool:
        sql = text("""
            DELETE FROM product_descriptions
            WHERE product_id = :product_id
            RETURNING 1
        """)

        params = {"product_id": product_id}
        res = self.db.execute(sql, params)
        self.db.commit()

        return res.fetchone() is not None

    # ------------------ PRICING ------------------ #

    def create_pricing(self, 
                       product_id: int, 
                       sku: str,
                       variance_description: Optional[str] = None,
                       price: Optional[int] = None,
                       parse_object: bool = True
    ) -> Pricing | dict[str, Any] | None:
    
        sql = text("""
            INSERT INTO pricings (product_id, sku, variance_description, price)
            VALUES (:product_id, :sku, :variance_description, :price)
            RETURNING *
        """)

        params = {
            "product_id": product_id,
            "sku": sku,
            "variance_description": variance_description,
            "price": price
        }

        result = self.db.execute(sql, params)
        self.db.commit()
        row = result.mappings().first()
        
        if not row:
            return None

        return Pricing(**row) if parse_object else dict(row)
    
    def get_pricing_by_sku(self, 
                           sku: str, 
                           parse_object: bool = True
    ) -> Pricing | dict[str, Any] | None:
        sql = text("""
            SELECT *
            FROM pricings
            WHERE sku = :sku
            LIMIT 1
        """)

        params = {"sku": sku}

        result = self.db.execute(sql, params)
        row = result.mappings().first()

        if not row:
            return None

        return Pricing(**row) if parse_object else dict(row)

    def update_pricing_price(self, 
                             sku: str, 
                             new_price: int, 
                             parse_object: bool = True
    ) -> Pricing | dict[str, Any] | None:
        sql = text("""
            UPDATE pricings
            SET price = :new_price
            WHERE sku = :sku
            RETURNING *
        """)

        params = {
            "sku": sku,
            "new_price": new_price
        }

        result = self.db.execute(sql, params)
        self.db.commit()
        row = result.mappings().first()

        if not row:
            return None

        return Pricing(**row) if parse_object else dict(row)

    def delete_pricing_by_sku(self, sku: str) -> bool:
        sql = text("""
            DELETE FROM pricings
            WHERE sku = :sku
            RETURNING 1
        """)

        params = {"sku": sku}
        res = self.db.execute(sql, params)
        self.db.commit()

        return res.fetchone() is not None