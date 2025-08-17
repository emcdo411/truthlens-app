import os
from openai import OpenAI

def llm_complete(prompt: str, model: str = None) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("No OPENAI_API_KEY set. Add it to secrets.toml or environment variables.")
    client = OpenAI(api_key=api_key)
    model = model or "gpt-3.5-turbo"
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}")


