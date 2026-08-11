import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Header, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from scripts.backup_check import check_backups
from scripts.api_health_check import run_health_check, load_monitored_sites
from scripts.log_parser import parse_log_file
from llm.analysis import analyze_data
from notifications.email_alert import send_alert_email

DATA_DIR = Path(__file__).parent.parent / "data"

app = FastAPI(title="AI Ops Automation Toolkit API")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = [
    "https://ai-ops-automation-toolkit-1.onrender.com",
    "http://localhost:8001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "frame-ancestors 'none'"
    )
    return response


def require_api_key(x_api_key: str = Header(default=None)):
    expected = os.environ.get("UPTIME_CHECK_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="API key not configured on server")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def sanitize_for_email(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", text).strip()


_tickets = []
_last_known_status = {}


@app.get("/api/uptime-check")
@limiter.limit("10/minute")
def uptime_check(request: Request, _auth: None = Depends(require_api_key)):
    trace = []
    sites = load_monitored_sites()
    trace.append(f"Loaded {len(sites)} monitored site(s) from config")
    trace.append("Using 45s timeout per site to allow for free-tier cold starts...")
    result = run_health_check(sites, timeout=60)

    alerts_sent = []
    for r in result["results"]:
        name = r["name"]
        was_healthy = _last_known_status.get(name, True)
        is_healthy = r["healthy"]

        if was_healthy and not is_healthy:
            trace.append(f"{name} just went DOWN - sending alert email...")
            email_result = send_alert_email(
                subject=f"[ALERT] {name} is down",
                body=(
                    f"{name} ({r['url']}) failed a health check.\n\n"
                    f"Status code: {r['status_code']}\n"
                    f"Error: {r['error']}\n"
                    f"Response time: {r['response_time_ms']}ms"
                ),
            )
            alerts_sent.append({"site": name, "email_result": email_result})
            trace.append(f"  Email result: {email_result}")
        elif not was_healthy and is_healthy:
            trace.append(f"{name} recovered")

        _last_known_status[name] = is_healthy

    trace.append(f"{result['healthy_count']}/{result['checked_count']} sites healthy")
    return {"trace": trace, "result": result, "alerts_sent": alerts_sent}


@app.get("/api/backup-status")
@limiter.limit("20/minute")
def backup_status(request: Request):
    trace = []
    trace.append(f"Loading backup records from {DATA_DIR / 'backup_jobs.json'}")
    result = check_backups(DATA_DIR / "backup_jobs.json")
    trace.append(f"Checked {result['total_jobs']} backup jobs")
    trace.append(f"Found {len(result['failures'])} failure(s), {len(result['stale'])} stale job(s)")
    trace.append(f"{result['healthy_count']} job(s) healthy")
    return {"trace": trace, "result": result}


@app.get("/api/health-check")
@limiter.limit("20/minute")
def health_check(request: Request):
    from scripts.api_health_check import DEFAULT_ENDPOINTS
    trace = [f"Pinging {len(DEFAULT_ENDPOINTS)} endpoint(s)..."]
    result = run_health_check()
    for r in result["results"]:
        status = "OK" if r["healthy"] else "FAILED"
        trace.append(f"  {r['name']}: {status} ({r['response_time_ms']}ms)")
    trace.append(f"{result['healthy_count']}/{result['checked_count']} endpoints healthy")
    return {"trace": trace, "result": result}


@app.get("/api/analyze-logs")
@limiter.limit("10/minute")
def analyze_logs(request: Request):
    trace = []
    trace.append(f"Parsing log file: {DATA_DIR / 'sample_logs.txt'}")
    parsed = parse_log_file(DATA_DIR / "sample_logs.txt")
    trace.append(f"Parsed {parsed['total_lines']} log lines")
    trace.append(f"Level breakdown: {parsed['level_counts']}")
    trace.append(f"Detected {len(parsed['repeated_issues'])} repeated issue pattern(s)")
    trace.append("Sending structured data to Groq (llama-3.3-70b-versatile)...")
    analysis = analyze_data(parsed)
    trace.append(f"AI response received - severity: {analysis.get('severity', 'unknown')}")
    result = {
        "total_log_lines": parsed["total_lines"],
        "repeated_issues": parsed["repeated_issues"],
        "ai_analysis": analysis,
    }
    return {"trace": trace, "result": result}


class TicketInput(BaseModel):
    title: str
    description: str
    severity: str


@app.post("/api/tickets")
@limiter.limit("20/minute")
def create_ticket(request: Request, ticket: TicketInput):
    trace = ["Validating ticket fields..."]
    new_ticket = {
        "id": len(_tickets) + 1,
        "title": sanitize_for_email(ticket.title),
        "description": sanitize_for_email(ticket.description),
        "severity": sanitize_for_email(ticket.severity),
    }
    _tickets.append(new_ticket)
    trace.append(f"Ticket #{new_ticket['id']} created and stored (severity: {new_ticket['severity']})")
    return {"trace": trace, "result": {"status": "created", "ticket": new_ticket}}


@app.get("/api/tickets")
@limiter.limit("30/minute")
def list_tickets(request: Request):
    trace = [f"Retrieved {len(_tickets)} ticket(s) from session storage"]
    return {"trace": trace, "result": {"tickets": _tickets}}


@app.get("/")
def serve_frontend():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)