# app/utils/generation.py

import os
import openai
from openai.error import AuthenticationError, OpenAIError

# load_dotenv should already have run in app/__init__.py
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY not set in environment")

def generate_texts(category: str | None, count: int = 3) -> list[str]:
    """
    Generate `count` post ideas via gpt-3.5-turbo.
    Raises if your key lacks chat scope.
    """
    system_msg = "You are a social-media content generator."
    user_msg = (
        f"Generate {count} brief social media post ideas"
        + (f" about {category}." if category else " on general topics.")
        + " Each should be 1–2 sentences."
    )

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",  "content": system_msg},
                {"role": "user",    "content": user_msg},
            ],
            temperature=0.8,
            n=1,
        )
    except AuthenticationError as e:
        raise RuntimeError(
            "Your OpenAI key cannot access chat.completions for gpt-3.5-turbo. "
            "Please verify the key has the ‘chat.completions’ scope."
        ) from e
    except OpenAIError as e:
        raise RuntimeError(f"OpenAI error: {e}") from e

    text = resp.choices[0].message.content
    return _split_lines(text, count)


def _split_lines(text: str, count: int) -> list[str]:
    posts = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # strip leading "1. " or "1) "
        if len(line) > 1 and line[0].isdigit() and line[1] in (".", ")"):
            line = line[2:].strip()
        posts.append(line)
        if len(posts) >= count:
            break
    return posts
