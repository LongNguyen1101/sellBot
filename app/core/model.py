from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME")

def init_model():
    return ChatOpenAI(model=MODEL_NAME)