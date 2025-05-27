import os
import openai
from openai.error import OpenAIError

openai.api_key = os.getenv("OPENAI_API_KEY")

# If no API key, use a fallback function
def generate_texts(category: str | None, count: int = 3, examples: list[str] = None) -> list[str]:
    """Fallback function when OpenAI API key is not set"""
    return ["Example post about {}".format(category or "general")] * count

def _split_lines(text: str, count: int) -> list[str]:
    return [text] * count

# If API key is set, use the real implementation
if openai.api_key:
    def generate_texts(
        category: str | None,
        count: int = 3,
        examples: list[str] = None
    ) -> list[str]:
        """
        Generate new posts via gpt-3.5-turbo, using `examples` as positive seeds.
        """
        # Build the prompt
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
            # Try OpenAI first
            if openai.api_key:
                print(f"Generating {count} posts with OpenAI for category: {category}")
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
                print(f"Received response from OpenAI: {text[:200]}...")
                posts = _split_lines(text, count)
                print(f"Generated {len(posts)} posts")
                return posts
            
            # If no OpenAI key or error, use fallback
            print("Using fallback generation")
            return [f"Example post {i + 1} about {category or 'general'}" for i in range(count)]
        except OpenAIError as e:
            print(f"OpenAI error: {e}")
            # Use fallback even if OpenAI fails
            return [f"Example post {i + 1} about {category or 'general'}" for i in range(count)]
        except Exception as e:
            print(f"Unexpected error in generation: {e}")
            return [f"Example post {i + 1} about {category or 'general'}" for i in range(count)]

    def _split_lines(text: str, count: int) -> list[str]:
        # Split by common delimiters
        delimiters = ['\n\n', '\n', '. ', '! ', '? ']
        posts = []
        
        # Try different splitting methods
        for delimiter in delimiters:
            if delimiter in text:
                parts = text.split(delimiter)
                for part in parts:
                    # Skip empty parts
                    stripped = part.strip()
                    if not stripped:
                        continue
                        
                    # Remove leading list markers (e.g., "1.", "2.", "1)", "2)")
                    if len(stripped) > 1 and stripped[0].isdigit() and stripped[1] in (".", ")"):
                        stripped = stripped[2:].strip()
                    
                    # Add the processed line
                    posts.append(stripped)
                    
                    # Stop if we have enough posts
                    if len(posts) >= count:
                        return posts[:count]
                
        # If no delimiters found, just split by lines
        lines = text.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped:
                posts.append(stripped)
                if len(posts) >= count:
                    return posts[:count]
        
        # If we still don't have enough posts, use the fallback
        if len(posts) < count:
            remaining = count - len(posts)
            posts.extend([f"Example post {i + 1}" for i in range(remaining)])
        
        return posts[:count]
