import json
from pathlib import Path
import time 
import requests

DEFAULT_TIMEOUT_SECONDS = 5

DEFAULT_ENDPOINTS = [
    {"name": "Google", "url": "https://www.google.com"},
    {"name": "GitHub API", "url": "https://api.github.com"},
    {"name": "Intentional 404 Test", "url": "https://httpbin.org/status/404"},
]

MONITORED_SITES_FILE = Path(__file__).parent.parent / "data" / "monitored_sites.json"


def load_monitored_sites() -> list[dict]:
    with open(MONITORED_SITES_FILE) as f:
        return json.load(f)


def check_endpoint(name, url, timeout=DEFAULT_TIMEOUT_SECONDS):
    start = time.monotonic()
    try:
        response = requests.get(url, timeout=timeout)
        elapsed_ms = round((time.monotonic()-start)*1000, 1)
        return{
            "name": name, 
            "url" : url,
            "status_code": response.status_code,
            "healthy": response.status_code<400,
            "response_time_ms":elapsed_ms,
            "error":None,

        }
    except requests.RequestException as e:
        elapsed_ms= round((time.monotonic()- start)*1000,1)
        return{
            "name": name,
            "url": url,
            "status_code": None,
            "healthy": False,
            "response_time_ms":elapsed_ms,
            "error":str(e),
        }
def run_health_check(endpoints: list[dict] | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    endpoints = endpoints or DEFAULT_ENDPOINTS
    results = [check_endpoint(e["name"], e["url"], timeout=timeout) for e in endpoints]
    healthy_count = sum(1 for r in results if r["healthy"])

    return {
        "checked_count": len(results),
        "healthy_count": healthy_count,
        "unhealthy_count": len(results) - healthy_count,
        "results": results,
    }
if __name__=="__main__":
    import json
    print(json.dumps(run_health_check(), indent=2))