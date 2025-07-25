from sqlalchemy import Column, BigInteger, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class QnA(Base):
    __tablename__ = 'qna'
    __table_args__ = {'schema': 'public'}  # vì bạn dùng schema 'public'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    embedding = Column(Vector(1536), nullable=True)  # số chiều embedding (vd: OpenAI là 1536)
