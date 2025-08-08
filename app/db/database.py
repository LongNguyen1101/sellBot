import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session, scoped_session
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv(override=True)

# Construct the SQLAlchemy connection string
DATABASE_URL = os.getenv('DATABASE_URL')

# Tạo engine cho SQLAlchemy
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_recycle=300,
    pool_pre_ping=True,
    pool_use_lifo=True
)

# engine = create_engine(
#     DATABASE_URL,
#     poolclass=NullPool,
# )

# Tạo session factory
SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionFactory)

# Base class cho các model
Base = declarative_base()
        
# @contextmanager
# def session_scope():
#     """Provide a transactional scope around a series of operations."""
#     session = SessionLocal()
#     try:
#         yield session
#         session.commit()
#     except Exception:
#         session.rollback()
#         raise
#     finally:
#         session.close()

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()  # đây là scoped_session, thread-safe
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        Session.remove()  # cleanup session của thread này

# (Tùy chọn) Hàm kiểm tra kết nối
def test_connection():
    try:
        with engine.connect() as connection:
            print("Successfully connected to Supabase database!")
    except Exception as e:
        print(f"Connection failed: {e}")
        
# def init_vector_schema_and_indexes():
#     try:
#         with engine.connect() as conn:
#             # Tạo schema vector_schema
#             conn.execute("CREATE SCHEMA IF NOT EXISTS vector_schema;")
#             # Kích hoạt pgvector trong public
#             conn.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;")
            
#             # Tạo chỉ mục HNSW cho restaurant_embeddings
#             conn.execute("""
#                 CREATE INDEX IF NOT EXISTS restaurant_embeddings_hnsw_idx 
#                 ON vector_schema.restaurant_embeddings 
#                 USING hnsw (embedding vector_cosine_ops) 
#                 WITH (m = 16, ef_construction = 64);
#             """)
            
#             # Tạo chỉ mục HNSW cho table_embeddings
#             conn.execute("""
#                 CREATE INDEX IF NOT EXISTS table_embeddings_hnsw_idx 
#                 ON vector_schema.table_embeddings 
#                 USING hnsw (embedding vector_cosine_ops) 
#                 WITH (m = 16, ef_construction = 64);
#             """)
            
#             # Tạo chỉ mục HNSW cho reservation_embeddings
#             conn.execute("""
#                 CREATE INDEX IF NOT EXISTS reservation_embeddings_hnsw_idx 
#                 ON vector_schema.reservation_embeddings 
#                 USING hnsw (embedding vector_cosine_ops) 
#                 WITH (m = 16, ef_construction = 64);
#             """)
            
#             conn.commit()
#             print("Initialized vector_schema and HNSW indexes.")
#     except Exception as e:
#         print(f"Error initializing vector schema and indexes: {e}")

if __name__ == "__main__":
    test_connection()