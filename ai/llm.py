"""
Optional LLM client for Panther's AI features.

Reads its configuration from settings (which read your .env):
    AI_PROVIDER   openai | anthropic | gemini
    AI_API_KEY    your secret key  (kept server-side, never sent to the browser)
    AI_MODEL      optional model override

If no key is configured, `available()` returns False and callers fall back to the
built-in rule-based logic — so the app works with or without a key. Uses only the
Python standard library (urllib), so there is nothing extra to pip install.
"""
import json
import urllib.error
import urllib.request

from django.conf import settings

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "gemini": "gemini-1.5-flash",
}


def available():
    return bool(getattr(settings, "AI_API_KEY", "")) and \
        getattr(settings, "AI_PROVIDER", "").lower() in _DEFAULT_MODELS


def _model():
    return getattr(settings, "AI_MODEL", "") or _DEFAULT_MODELS.get(
        getattr(settings, "AI_PROVIDER", "").lower(), "")


def _post(url, headers, payload, timeout=20):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def complete(prompt, system="", max_tokens=400):
    """
    Return the model's text response, or None on any error (caller should fall back).
    Never raises — AI is an enhancement, not a hard dependency.
    """
    if not available():
        return None
    provider = settings.AI_PROVIDER.lower()
    key = settings.AI_API_KEY
    model = _model()
    try:
        if provider == "openai":
            data = _post(
                "https://api.openai.com/v1/chat/completions",
                {"Authorization": f"Bearer {key}"},
                {"model": model, "max_tokens": max_tokens, "messages": [
                    {"role": "system", "content": system or "Tu es un assistant."},
                    {"role": "user", "content": prompt}]})
            return data["choices"][0]["message"]["content"]

        if provider == "anthropic":
            data = _post(
                "https://api.anthropic.com/v1/messages",
                {"x-api-key": key, "anthropic-version": "2023-06-01"},
                {"model": model, "max_tokens": max_tokens, "system": system,
                 "messages": [{"role": "user", "content": prompt}]})
            return data["content"][0]["text"]

        if provider == "gemini":
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{model}:generateContent?key={key}")
            body = {"contents": [{"parts": [{"text": prompt}]}]}
            if system:
                body["systemInstruction"] = {"parts": [{"text": system}]}
            data = _post(url, {}, body)
            return data["candidates"][0]["content"]["parts"][0]["text"]

    except (urllib.error.URLError, KeyError, IndexError, ValueError, TimeoutError):
        return None
    return None
