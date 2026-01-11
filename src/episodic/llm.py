import os
from groq import Groq

# Initialize Groq client with API key (if available)
_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=_api_key) if _api_key else None

def call_llm(messages, model="openai/gpt-oss-120b"):
    if not client:
        # Fallback when no API key is available
        return "LLM response not available - GROQ_API_KEY not set"
    
    res = client.chat.completions.create(
        model=model,
        messages=messages
    )
    return res.choices[0].message.content