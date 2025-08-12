from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME")
MODEL_NAME_AGENT = os.getenv("MODEL_NAME_AGENT")
MODEL_NAME_TOOLS = os.getenv("MODEL_NAME_TOOLS")

def init_model(
    model_name: Optional[str] = MODEL_NAME,
    reasoning_effort: str = "medium"
):
    if model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(model=model_name)
    else:
        return ChatOpenAI(
            model=model_name,
            reasoning_effort=reasoning_effort,
            use_responses_api=True,
            use_previous_response_id=True
        )

llm = init_model(
    model_name=MODEL_NAME,
    reasoning_effort="low"
)

llm_agent = init_model(
    model_name=MODEL_NAME_AGENT,
    reasoning_effort="minimal"
)

llm_tools = init_model(
    model_name=MODEL_NAME_TOOLS,
    reasoning_effort="minimal"
)