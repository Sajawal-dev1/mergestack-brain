import os
from dotenv import load_dotenv
import openai

client = openai.OpenAI(api_key="your-api-key")


load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedder():
    """Get Open AI embeddings model."""
    return lambda text: client.embeddings.create(input=text, model="text-embedding-ada-002").data[0].embedding

def get_llm():
    """Get Open AI chat model."""
    return lambda messages: client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0
    ).choices[0].message.content