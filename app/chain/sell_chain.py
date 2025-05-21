from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv(override=True)

class SellChain():
    def __init__(self):
        self.model_name = os.getenv('MODEL_NAME')
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            api_key=self.api_key
        )
    
    def check_intent_user(self) -> LLMChain:
        with open("app/chain/prompts/check_intent_user_prompt.txt", encoding="utf-8") as f:
            prompt_text = f.read()
        
        prompt = PromptTemplate.from_template(prompt_text)
        chain = prompt | self.llm
        return chain
    
    