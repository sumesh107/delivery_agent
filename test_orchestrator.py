import json
import os

import httpx


def main() -> None:
    base_url = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:8080")
    payload = {
        "session_id": "demo",
        "message": "What is the weather in Zurich and list sales orders",
    }

    response = httpx.post(f"{base_url}/chat", json=payload, timeout=60)
    if response.status_code >= 400:
        print("Request failed:")
        print(f"Status: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    print("Reply:")
    print(data.get("reply", ""))
    print("\nMessages:")
    print(json.dumps(data.get("messages", []), indent=2))


if __name__ == "__main__":
    main()
