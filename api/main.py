import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scripts.backup_check import check_backups
from scripts.api_health_check import run_health_check
from scripts.log_parser import parse_log_file
from llm.analysis import analyze_data

DATA_DIR = Path(__file__).parent.parent / "data"

app = FastAPI(title="AI Ops Automation Toolkit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_tickets = []


@app.get("/api/backup-status")
def backup_status():
    trace = []
    trace.append(f"Loading backup records from {DATA_DIR / 'backup_jobs.json'}")
    result = check_backups(DATA_DIR / "backup_jobs.json")
    trace.append(f"Checked {result['total_jobs']} backup jobs")
    trace.append(f"Found {len(result['failures'])} failure(s), {len(result['stale'])} stale job(s)")
    trace.append(f"{result['healthy_count']} job(s) healthy")
    return {"trace": trace, "result": result}


@app.get("/api/health-check")
def health_check():
    from scripts.api_health_check import DEFAULT_ENDPOINTS
    trace = [f"Pinging {len(DEFAULT_ENDPOINTS)} endpoint(s)..."]
    result = run_health_check()
    for r in result["results"]:
        status = "OK" if r["healthy"] else "FAILED"
        trace.append(f"  {r['name']}: {status} ({r['response_time_ms']}ms)")
    trace.append(f"{result['healthy_count']}/{result['checked_count']} endpoints healthy")
    return {"trace": trace, "result": result}


@app.get("/api/analyze-logs")
def analyze_logs():
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
def create_ticket(ticket: TicketInput):
    trace = ["Validating ticket fields..."]
    new_ticket = {
        "id": len(_tickets) + 1,
        "title": ticket.title,
        "description": ticket.description,
        "severity": ticket.severity,
    }
    _tickets.append(new_ticket)
    trace.append(f"Ticket #{new_ticket['id']} created and stored (severity: {ticket.severity})")
    return {"trace": trace, "result": {"status": "created", "ticket": new_ticket}}


@app.get("/api/tickets")
def list_tickets():
    trace = [f"Retrieved {len(_tickets)} ticket(s) from session storage"]
    return {"trace": trace, "result": {"tickets": _tickets}}


# Serve the frontend dashboard at the root URL
@app.get("/")
def serve_frontend():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)