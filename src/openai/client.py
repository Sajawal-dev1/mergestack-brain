import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

def get_embedder():
    return OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
