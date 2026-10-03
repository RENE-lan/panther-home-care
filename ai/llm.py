"""LLM client for Panther's AI features — cloud OR fully local (Ollama).

Priority:
  1. If AI_API_KEY is set (openai | anthropic | gemini) → use that cloud model.
  2. Else if a LOCAL Ollama server is running (http://localhost:11434) → use it.
     This makes the Copilot answer ANY question, with NO key and NO external API.
  3. Else → callers fall back to the built-in rule-based logic.

Install the free local model once:
    1) Download Ollama from https://ollama.com  (Windows/Mac/Linux)
    2) In a terminal:  ollama pull llama3.2
    3) Restart the Panther server. The Copilot is now unlimited, 100% local.
Config (settings / .env), all optional:
    AI_PROVIDER   openai | anthropic | gemini | ollama
    AI_API_KEY    cloud key (only for cloud providers)
    AI_MODEL      model override (e.g. llama3.2, qwen2.5, mistral)
    OLLAMA_URL    default http://localhost:11434
"""
import json
import time
import urllib.error
import urllib.request

from django.conf import settings

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "gemini": "gemini-1.5-flash",
    "ollama": "llama3.2",
}
_CLOUD = {"openai", "anthropic", "gemini"}

_ollama_cache = {"at": 0.0, "up": False, "model": None}


def _ollama_url():
    return (getattr(settings, "OLLAMA_URL", "") or "http://localhost:11434").rstrip("/")


def _ollama_status():
    """Is a local Ollama server reachable, and which model to use? Cached 20s."""
    now = time.time()
    if now - _ollama_cache["at"] < 20:
        return _ollama_cache["up"], _ollama_cache["model"]
    up, model = False, None
    try:
        req = urllib.request.Request(_ollama_url() + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        if models:
            up = True
            pref = getattr(settings, "AI_MODEL", "") or "llama3.2"
            model = next((m for m in models if m.split(":")[0] == pref.split(":")[0]), models[0])
    except Exception:
        up = False
    _ollama_cache.update(at=now, up=up, model=model)
    return up, model


def _has_cloud_key():
    return bool(getattr(settings, "AI_API_KEY", "")) and \
        getattr(settings, "AI_PROVIDER", "").lower() in _CLOUD


def available():
    if _has_cloud_key():
        return True
    up, _ = _ollama_status()
    return up


def _active():
    """Return (provider, model). Cloud key wins; else local Ollama."""
    if _has_cloud_key():
        p = settings.AI_PROVIDER.lower()
        return p, (getattr(settings, "AI_MODEL", "") or _DEFAULT_MODELS[p])
    up, model = _ollama_status()
    if up:
        return "ollama", (model or "llama3.2")
    return None, None


def _post(url, headers, payload, timeout=60):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(messages, system="", max_tokens=700):
    """Multi-turn chat. Returns text or None (caller falls back). Never raises."""
    provider, model = _active()
    if not provider:
        return None
    key = getattr(settings, "AI_API_KEY", "")
    try:
        if provider == "ollama":
            msgs = ([{"role": "system", "content": system}] if system else []) + messages
            data = _post(_ollama_url() + "/api/chat",
                         {}, {"model": model, "messages": msgs, "stream": False,
                              "options": {"num_predict": max_tokens}})
            return (data.get("message") or {}).get("content", "").strip() or None
        if provider == "openai":
            msgs = ([{"role": "system", "content": system}] if system else []) + messages
            data = _post("https://api.openai.com/v1/chat/completions",
                         {"Authorization": f"Bearer {key}"},
                         {"model": model, "max_tokens": max_tokens, "messages": msgs})
            return data["choices"][0]["message"]["content"]
        if provider == "anthropic":
            data = _post("https://api.anthropic.com/v1/messages",
                         {"x-api-key": key, "anthropic-version": "2023-06-01"},
                         {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages})
            return data["content"][0]["text"]
        if provider == "gemini":
            contents = [{"role": ("model" if m["role"] == "assistant" else "user"),
                         "parts": [{"text": m["content"]}]} for m in messages]
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}")
            body = {"contents": contents}
            if system:
                body["systemInstruction"] = {"parts": [{"text": system}]}
            data = _post(url, {}, body)
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None
    return None


def complete(prompt, system="", max_tokens=400):
    """Single-shot completion. Returns text or None. Never raises."""
    return chat([{"role": "user", "content": prompt}], system=system, max_tokens=max_tokens)


def status_label():
    """Human-readable status for the UI."""
    if _has_cloud_key():
        return f"IA cloud ({settings.AI_PROVIDER})"
    up, model = _ollama_status()
    if up:
        return f"IA locale (Ollama · {model})"
    return "IA locale non détectée"
