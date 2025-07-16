from dotenv import load_dotenv
import os

def load_env():
    load_dotenv()
    return {
        "CLICKUP_API_KEY": os.getenv("CLICKUP_API_KEY")
    }


