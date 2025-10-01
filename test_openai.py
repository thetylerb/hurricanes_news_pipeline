import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.getenv("OPENAI_API_KEY"))
model = os.getenv("OPENAI_DEPLOYMENT", "gpt-4o")

resp = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "Reply with ONLY valid JSON: {\"ok\": true}"},
        {"role": "user", "content": "ping"}
    ],
    temperature=0,
)

print("RAW:", resp.choices[0].message.content)
