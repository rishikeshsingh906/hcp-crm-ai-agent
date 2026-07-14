"""
Thin wrapper around the Groq API.

Primary model: gemma2-9b-it (fast, cheap — used for the conversational
agent loop and structured extraction).
Fallback model: llama-3.3-70b-versatile (used if gemma2-9b-it errors out,
or when a task benefits from a larger context/reasoning budget).
"""
import json
from groq import Groq

from app.config import settings

_client = Groq(api_key=settings.groq_api_key)


def chat_completion(messages: list[dict], temperature: float = 0.3, model: str | None = None) -> str:
    model = model or settings.groq_model
    try:
        resp = _client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content
    except Exception:
        # fall back to the larger model if the primary one fails
        resp = _client.chat.completions.create(
            model=settings.groq_fallback_model,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content


def extract_json(prompt: str, system: str, model: str | None = None) -> dict:
    """Call the LLM and force-parse a JSON object out of the reply."""
    raw = chat_completion(
        [
            {"role": "system", "content": system + "\nRespond with ONLY valid JSON, no markdown fences."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        model=model,
    )
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1:
            return json.loads(cleaned[start:end + 1])
        raise
