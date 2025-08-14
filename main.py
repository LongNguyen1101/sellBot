from fastapi import FastAPI
from app.api.v1.routes import router as api_router
from fastapi.middleware.cors import CORSMiddleware

# Create a FastAPI app instance
app = FastAPI(title="My FastAPI Project")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)


# try:
#     # init_vector_schema_and_indexes()
#     Base.metadata.create_all(bind=engine)
#     print("Tables and HNSW indexes created/verified in Supabase.")
# except Exception as e:
#     print(f"Error during initialization: {e}")

# Include the API router with a prefix
app.include_router(api_router, prefix="/api/v1")

# Define a root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to selling bot"}
