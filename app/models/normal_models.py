from sqlalchemy import (Column, Integer, String, 
                        Text, Boolean, Date, Time, BigInteger, TIMESTAMP,
                        DateTime, ForeignKey, UniqueConstraint, DECIMAL, JSON, MetaData)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class ProductDescription(Base):
    __tablename__ = "product_description"

    product_description_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, nullable=False, unique=True)
    product_name = Column(Text, nullable=False)
    brief_description = Column(Text)
    description = Column(Text)

    pricing = relationship("Pricing", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product", cascade="all, delete-orphan")
    
class Pricing(Base):
    __tablename__ = "pricing"

    pricing_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("product_description.product_id"), nullable=False)
    variance_description = Column(Text)
    sku = Column(Text, nullable=False, unique=True)
    price = Column(Integer)

    product = relationship("ProductDescription", back_populates="pricing")
    inventory = relationship("Inventory", back_populates="pricing", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="pricing", cascade="all, delete-orphan")
    
class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(Text, ForeignKey("pricing.sku"), nullable=False)
    import_price = Column(Integer)
    wholesale_price = Column(Integer)
    inventory_quantity = Column(Integer)
    shelf = Column(Text)
    shelf_code = Column(Text)

    pricing = relationship("Pricing", back_populates="inventory")
    
class Cart(Base):
    __tablename__ = "cart"
    __table_args__ = {"schema": "public"}  # vì bảng nằm trong schema "public"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chat_id = Column(String, nullable=True)
    customer_name = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    list_cart = Column(JSON, nullable=True)

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(BigInteger, primary_key=True, autoincrement=True)
    status = Column(Text, default='pending', nullable=True)
    order_total = Column(BigInteger, default=0, nullable=True)
    shipping_fee = Column(BigInteger, default=0, nullable=True)
    grand_total = Column(BigInteger, default=0, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), default=func.now(), onupdate=func.now(), nullable=True)
    payment = Column(Text, default='COD', nullable=True)
    customer_id = Column(BigInteger, ForeignKey("customer.customer_id", ondelete="CASCADE"), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("product_description.product_id"), nullable=False)
    sku = Column(Text, ForeignKey("pricing.sku"), nullable=False)
    quantity = Column(Integer)
    price = Column(BigInteger)
    subtotal = Column(BigInteger)

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("ProductDescription", back_populates="order_items")
    pricing = relationship("Pricing", back_populates="order_items")

class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = (
        UniqueConstraint('chat_id', name='customer_chat_id_key'),
    )

    customer_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True)
    phone_number = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    chat_id = Column(Text, nullable=False, default='')  # default is empty string
    state = Column(JSON, nullable=True)  # JSONB trong PostgreSQL map với JSON trong SQLAlchemy

    # Relationship với Order model
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")