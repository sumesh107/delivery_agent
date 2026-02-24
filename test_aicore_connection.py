import json
import os
from typing import Optional

from gen_ai_hub.proxy.native.openai import OpenAI


def _set_default_env(name: str, value: Optional[str]) -> None:
    if not value:
        return
    if os.getenv(name) is None:
        os.environ[name] = value


def _read_service_binding_json() -> Optional[dict]:
    for key in ("AICORE_SERVICE_BINDING", "SERVICE_BINDING_JSON", "SERVICE_BINDING"):
        raw = os.getenv(key)
        if not raw:
            continue
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    return None


def _load_env_with_json_fallback() -> None:
    if os.getenv("AICORE_SERVICE_BINDING") or os.getenv("AICORE_BASE_URL"):
        return

    default_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
    fallback_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    env_path = os.getenv("ENV_FILE", default_env_path)
    raw = ""
    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            raw = env_file.read().strip()
    except OSError:
        if env_path == default_env_path:
            env_path = fallback_env_path
            try:
                with open(env_path, "r", encoding="utf-8") as env_file:
                    raw = env_file.read().strip()
            except OSError:
                pass

    if raw.startswith("{") and raw.endswith("}"):
        os.environ.setdefault("AICORE_SERVICE_BINDING", raw)
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(env_path)


def _apply_ai_core_env() -> None:
    binding = _read_service_binding_json() or {}
    serviceurls = binding.get("serviceurls") or {}

    _set_default_env("AICORE_BASE_URL", serviceurls.get("AI_API_URL") or os.getenv("AI_API_URL"))
    _set_default_env("AICORE_AUTH_URL", binding.get("url") or os.getenv("url"))
    _set_default_env("AICORE_CLIENT_ID", binding.get("clientid") or os.getenv("clientid"))
    _set_default_env("AICORE_CLIENT_SECRET", binding.get("clientsecret") or os.getenv("clientsecret"))
    _set_default_env("AICORE_RESOURCE_GROUP", binding.get("resource_group") or os.getenv("resource_group"))

    _set_default_env("identityzone", binding.get("identityzone") or os.getenv("identityzone"))
    _set_default_env("identityzoneid", binding.get("identityzoneid") or os.getenv("identityzoneid"))
    _set_default_env("appname", binding.get("appname") or os.getenv("appname"))

    if os.getenv("AICORE_RESOURCE_GROUP") is None:
        os.environ["AICORE_RESOURCE_GROUP"] = "default"


def _print_masked_env(keys: list[str]) -> None:
    print("AI Core env check (masked):")
    for key in keys:
        value = os.getenv(key)
        if value is None:
            print(f"- {key}: NOT SET")
        else:
            print(f"- {key}: set (length={len(value)})")


def main() -> None:
    _load_env_with_json_fallback()
    _apply_ai_core_env()

    _print_masked_env(
        [
            "AICORE_BASE_URL",
            "AICORE_AUTH_URL",
            "AICORE_CLIENT_ID",
            "AICORE_CLIENT_SECRET",
            "AICORE_RESOURCE_GROUP",
            "AICORE_SERVICE_BINDING",
        ]
    )

    client = OpenAI()
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL_NAME", "gpt-4o"),
        messages=[
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Reply with 'AI Core OK'."},
        ],
#        max_completion_tokens=16,
#        temperature=0.0,
    )

    content = response.choices[0].message.content or ""
    print(content)


if __name__ == "__main__":
    main()
