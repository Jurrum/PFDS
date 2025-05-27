import os
import openai
from openai.error import OpenAIError

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY not set")

def generate_texts(
    category: str | None,
    count: int = 3,
    examples: list[str] = None
) -> list[str]:
    """
    Generate new posts via gpt-3.5-turbo, using `examples` as positive seeds.
    """
    system_msg = "You are a social-media content generator."
    user_msg = f"Generate {count} brief social media post ideas"
    if category:
        user_msg += f" about {category}"
    user_msg += ", each 1–2 sentences."

    if examples:
        # include up to 3 top examples in the prompt
        ex_text = "\n".join(f"- {ex}" for ex in examples[:3])
        user_msg += f"\n\nHere are some posts the user liked:\n{ex_text}\n\nNow generate similar, fresh ideas."

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.8,
            n=1,
        )
        text = resp.choices[0].message.content
    except OpenAIError as e:
        # fallback to stub so UI won’t crash
        print("OpenAI error:", e)
        return []

    return _split_lines(text, count)


def _split_lines(text: str, count: int) -> list[str]:
    posts = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # drop leading list markers
        if len(line) > 1 and line[0].isdigit() and line[1] in (".", ")"):
            line = line[2:].strip()
        posts.append(line)
        if len(posts) >= count:
            break
    return posts
