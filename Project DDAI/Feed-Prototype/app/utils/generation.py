# app/utils/generation.py

import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_texts(category: str | None, count: int = 3) -> list[str]:
    """
    Ask OpenAI to produce `count` short post prompts,
    optionally scoped to a category.
    """
    system = "You are a social‑media content generator."
    user = (
        f"Generate {count} brief social media post ideas"
        + (f" about {category}." if category else " on general topics.")
        + " Each should be 1–2 sentences."
    )

    # NEW style call:
    resp = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        temperature=0.8,
        n=1
    )

    # Extract the assistant’s reply
    text = resp.choices[0].message.content

    # Split into lines, strip leading numbers, return up to count
    posts = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Remove leading "1. " or "1) " if present
        if line[0].isdigit() and line[1] in (".", ")"):
            line = line[2:].strip()
        posts.append(line)
        if len(posts) >= count:
            break

    return posts
