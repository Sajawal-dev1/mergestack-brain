import os
from dotenv import load_dotenv
import openai
import json


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





def extract_filters_from_question(question: str) -> dict:
    """
    Extracts metadata and date filters from a natural language question using OpenAI.
    Returns a Pinecone-compatible filter dictionary.
    """

    system_prompt = """
You are an assistant that extracts structured metadata filters from natural language questions.
Always respond with a valid JSON object. Supported fields:

- assignees: list of strings (e.g., ["Ali", "Sajawal khan"])
- project: string
- status: string
- date_range: object with optional 'start' and 'end' keys in YYYY-MM-DD format

All natural language date expressions (like 'yesterday', 'this week', or 'last Monday')
must be resolved to actual UTC calendar dates in 'YYYY-MM-DD' format.

Respond ONLY with the JSON object.

Examples:

Q: What did Sajawal khan do yesterday?
A:
{
  "assignees": ["Sajawal khan"],
  "date_range": {
    "start": "2025-07-21",
    "end": "2025-07-21"
  }
}

Q: Show MIRA project updates this week
A:
{
  "project": "MIRA",
  "date_range": {
    "start": "2025-07-21",
    "end": "2025-07-27"
  }
}
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.2
    )

    try:
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print("Error parsing filter JSON:", e)
        return {}
   