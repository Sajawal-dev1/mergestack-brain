import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI


load_dotenv()

def get_embedder():
    return OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

def get_llm():
    return ChatOpenAI(model="gpt-4", temperature=0)
