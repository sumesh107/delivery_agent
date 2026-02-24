import argparse
import json
import sys
import uuid

import requests


def _post_chat(base_url: str, session_id: str, message: str) -> dict:
    response = requests.post(
        f"{base_url}/chat",
        json={"session_id": session_id, "message": message},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Terminal chat for the orchestrator")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="Orchestrator base URL")
    parser.add_argument("--session-id", default=None, help="Session id (defaults to a random value)")
    parser.add_argument("--once", default=None, help="Send one message and exit")
    args = parser.parse_args()

    session_id = args.session_id or f"cli-{uuid.uuid4().hex[:8]}"
    if args.once:
        result = _post_chat(args.base_url, session_id, args.once)
        print(result.get("reply", ""))
        return 0

    print("Orchestrator chat. Type 'exit' to quit.")
    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nexiting")
            return 0
        if not message:
            continue
        if message.lower() in {"exit", "quit"}:
            return 0
        try:
            result = _post_chat(args.base_url, session_id, message)
        except requests.RequestException as exc:
            print(f"error: {exc}")
            continue
        reply = result.get("reply", "")
        print(f"assistant> {reply}")


if __name__ == "__main__":
    sys.exit(main())
