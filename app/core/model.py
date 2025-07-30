from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME")

def init_model():
    return ChatGoogleGenerativeAI(model=MODEL_NAME)