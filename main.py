from fastapi import FastAPI
from app.api.v1.routes import router as api_router
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import Base, engine
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI(title="My FastAPI Project")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origin
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả các phương thức (GET, POST, PUT, DELETE, ...)
    allow_headers=["*"],  # Cho phép tất cả các headers
)


# try:
#     # init_vector_schema_and_indexes()
#     Base.metadata.create_all(bind=engine)
#     print("Tables and HNSW indexes created/verified in Supabase.")
# except Exception as e:
#     print(f"Error during initialization: {e}")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to selling bot"}
