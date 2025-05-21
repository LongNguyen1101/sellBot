from fastapi import FastAPI
from app.api.v1.routes import router as api_router
from app.db.database import Base, engine
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI(title="My FastAPI Project")

# try:
#     # init_vector_schema_and_indexes()
#     Base.metadata.create_all(bind=engine)
#     print("Tables and HNSW indexes created/verified in Supabase.")
# except Exception as e:
#     print(f"Error during initialization: {e}")

app.include_router(api_router, prefix="/api/v1")
