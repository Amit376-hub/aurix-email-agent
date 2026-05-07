from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

# load API key from .env
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_reply(email_text):

    prompt = f"""
You are writing email replies on behalf of Amit Kumar.

Write a polite and professional reply to the following email.

End the email with:

Best regards,
Amit Kumar

Email:
{email_text}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content