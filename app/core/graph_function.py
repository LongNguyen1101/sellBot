from sqlalchemy.orm import Session
from app.chain.sell_chain import SellChain
from app.db.database import get_db
from app.services.crud_public import PublicCRUD
from datetime import datetime, date, time as dtime, timedelta

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
        
    