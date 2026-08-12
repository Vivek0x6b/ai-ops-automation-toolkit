import os
import requests
from dotenv import load_dotenv
load_dotenv()

RENDER_API_BASE = "https://api.render.com/v1"


def _get_headers():
    api_key = os.environ.get("RENDER_API_KEY")
    if not api_key:
        raise RuntimeError("RENDER_API_KEY environment variable not set")
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def find_service_by_name(name_substring: str) -> dict:
    response = requests.get(
        f"{RENDER_API_BASE}/services",
        headers=_get_headers(),
        params={"limit": 50},
        timeout=15,
    )
    response.raise_for_status()
    services = response.json()

    name_lower = name_substring.lower()
    for entry in services:
        service = entry.get("service", entry)
        if name_lower in service.get("name", "").lower():
            return {"id": service["id"], "ownerId": service["ownerId"], "name": service["name"]}

    raise ValueError(f"No service found matching '{name_substring}'")


def fetch_recent_logs(service_name_substring: str, limit: int = 50) -> dict:
    service = find_service_by_name(service_name_substring)

    response = requests.get(
        f"{RENDER_API_BASE}/logs",
        headers=_get_headers(),
        params={
            "ownerId": service["ownerId"],
            "resource": service["id"],
            "limit": limit,
            "direction": "backward",
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    logs = data.get("logs", [])
    return {
        "service_name": service["name"],
        "log_count": len(logs),
        "logs": logs,
    }


if __name__ == "__main__":
    import json
    result = fetch_recent_logs("token-messiah-backend", limit=20)
    print(json.dumps(result, indent=2))