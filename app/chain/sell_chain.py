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
    
    def extract_product_name(self) -> LLMChain:
        with open("app/chain/prompts/extract_product_name_prompt.txt", encoding="utf-8") as f:
            prompt_text = f.read()
        
        prompt = PromptTemplate.from_template(prompt_text)
        chain = prompt | self.llm
        return chain
    
    def check_identify_product(self) -> LLMChain:
        with open("app/chain/prompts/check_identify_product_prompt.txt", encoding="utf-8") as f:
            prompt_text = f.read()
        
        prompt = PromptTemplate.from_template(prompt_text)
        chain = prompt | self.llm
        return chain
    
    def check_user_confirm_cart(self) -> LLMChain:
        with open("app/chain/prompts/check_user_confirm_cart_prompt.txt", encoding="utf-8") as f:
            prompt_text = f.read()
        
        prompt = PromptTemplate.from_template(prompt_text)
        chain = prompt | self.llm
        return chain
    
    def get_product(self) -> LLMChain:
        with open("app/chain/prompts/get_product_prompt.txt", encoding="utf-8") as f:
            prompt_text = f.read()
        
        prompt = PromptTemplate.from_template(prompt_text)
        chain = prompt | self.llm
        return chain
    
    def product_agent(self, llm_with_tools) -> LLMChain:
        with open("app/chain/prompts/product_agent_prompt.txt", encoding="utf-8") as f:
            prompt_text = f.read()
        
        prompt = PromptTemplate.from_template(prompt_text)
        chain = prompt | llm_with_tools
        return chain
    
    