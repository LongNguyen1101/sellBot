from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_NAME_AGENT = os.getenv("MODEL_NAME_AGENT")

def init_model(model_name: Optional[str] = MODEL_NAME):
    if model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(model=model_name)
    else:
        return ChatOpenAI(model=model_name)

llm = init_model()
llm_agent = init_model(model_name="gemini-2.5-flash")