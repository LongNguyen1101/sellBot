from sqlalchemy.orm import Session
from models.normal_models import ProductDescription
from models.normal_models import Pricing
from models.normal_models import Inventory
from typing import Optional


class PublicCRUD:
    def __init__(self, db: Session):
        self.db = db

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
