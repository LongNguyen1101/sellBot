from sqlalchemy import (Column, Integer, String, 
                        Text, Boolean, Date, Time, BigInteger,
                        DateTime, ForeignKey, CheckConstraint, DECIMAL, JSON, MetaData)
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
    
class Pricing(Base):
    __tablename__ = "pricing"

    pricing_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("product_description.product_id"), nullable=False)
    variance_description = Column(Text)
    sku = Column(Text, nullable=False, unique=True)
    price = Column(Integer)

    product = relationship("ProductDescription", back_populates="pricing")
    inventory = relationship("Inventory", back_populates="pricing", cascade="all, delete-orphan")
    
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