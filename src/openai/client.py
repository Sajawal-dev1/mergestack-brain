import os
from dotenv import load_dotenv
import openai
import json
from datetime import datetime




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
    Extracts metadata and date filters from a natural language question.
    Uses local timezone and ensures full-day date ranges (00:00:00 to 23:59:59).
    """
    # Get local timezone date
    local_tz = datetime.now().astimezone().tzinfo
    today_str = datetime.now(local_tz).strftime("%Y-%m-%d")

    system_prompt = f"""
You are an assistant that extracts structured metadata filters from natural language questions.
Today's date is {today_str} (local timezone).

Respond ONLY with a valid JSON object. Supported fields:

- assignees: list of strings (e.g., ["Ali", "Sajawal khan"])
- project: string
- task_name:string
- date_range: object with optional 'start' and 'end' keys in YYYY-MM-DDTHH:MM:SS format (24-hour clock)

Rules:
- Always use **local timezone calendar dates**, not UTC.
- "today", "yesterday", or day names ("this Tuesday") should return **full day**, i.e.:
  - start: YYYY-MM-DDT00:00:00
  - end:   YYYY-MM-DDT23:59:59
- For week-based ranges:
  - "this week" = current week (Monday 00:00 to Friday 23:59)
  - "last week" = previous week's Monday to Friday

Examples:

Q: What did Sajawal khan do yesterday?
A:
{{
  "assignees": ["Sajawal khan"],
  "date_range": {{
    "start": "2025-07-24T00:00:00",
    "end": "2025-07-24T23:59:59"
  }}
}}

Q: Show MIRA project updates this week
A:
{{
  "project": "MIRA",
  "date_range": {{
    "start": "2025-07-21T00:00:00",
    "end": "2025-07-25T23:59:59"
  }}
}}

Q: Which projects is Sajawal khan actively working on this week?
A:
{{
  "assignees": ["Sajawal khan"],
  "date_range": {{
    "start": "2025-07-21T00:00:00",
    "end": "2025-07-25T23:59:59"
  }}
}}
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
