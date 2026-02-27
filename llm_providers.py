"""
Pluggable LLM layer: add your required LLM via env or by implementing generate_insight().

Set LLM_PROVIDER in .env to one of: gemini, openai, ollama, or leave unset for gemini (default).
Add new providers by extending PROVIDERS and implementing the same interface.
"""

import os
import json
from typing import Callable, Optional

# --- Default system instruction (strict JSON, low latency) ---
DEFAULT_SYSTEM_INSTRUCTION = """You are a behavioral classifier. Output ONLY valid JSON with no markdown or extra text.
Schema: {"state": "Focused"|"Confused"|"Distracted", "reason": "one short sentence"}
Keep the reason under 15 words. Total output under 80 tokens."""


def _normalize_json_insight(text: str) -> str:
    """Parse LLM JSON output into a single-line insight string."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].replace("json", "").strip()
    try:
        parsed = json.loads(text)
        return f"{parsed.get('state', 'Unknown')}: {parsed.get('reason', text)}"
    except json.JSONDecodeError:
        return text


# --- Gemini (default) ---
def _gemini_generate(prompt: str) -> str:
    import google.generativeai as genai
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set. Add it to .env or use another LLM_PROVIDER.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-1.5-flash-latest",
        system_instruction=DEFAULT_SYSTEM_INSTRUCTION,
    )
    response = model.generate_content(prompt)
    return _normalize_json_insight(response.text.strip())


# --- OpenAI (optional) ---
def _openai_generate(prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("OpenAI provider requires: pip install openai")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set for LLM_PROVIDER=openai.")
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": DEFAULT_SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
        max_tokens=150,
    )
    text = (response.choices[0].message.content or "").strip()
    return _normalize_json_insight(text)


# --- Ollama (local, no API key) ---
def _ollama_generate(prompt: str) -> str:
    try:
        import urllib.request
        import urllib.error
    except ImportError:
        raise RuntimeError("Ollama provider requires standard library urllib (Python 3).")
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    payload = json.dumps({
        "model": model,
        "prompt": f"{DEFAULT_SYSTEM_INSTRUCTION}\n\n{prompt}",
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        text = (out.get("response") or "").strip()
        return _normalize_json_insight(text)
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama request failed (is Ollama running?): {e}") from e


# --- Registry: add your LLM here ---
PROVIDERS = {
    "gemini": _gemini_generate,
    "openai": _openai_generate,
    "ollama": _ollama_generate,
}


def get_llm() -> Callable[[str], str]:
    """Return the generate function for the configured LLM_PROVIDER (default: gemini)."""
    provider = (os.getenv("LLM_PROVIDER") or "gemini").strip().lower()
    if provider not in PROVIDERS:
        raise RuntimeError(
            f"Unknown LLM_PROVIDER={provider}. Choose one of: {', '.join(PROVIDERS)}. "
            "You can add your own in llm_providers.py (PROVIDERS dict and a generate(prompt) -> str function)."
        )
    return PROVIDERS[provider]


def generate_insight(prompt: str) -> str:
    """Single entry point: call the configured LLM and return a one-line insight."""
    return get_llm()(prompt)
