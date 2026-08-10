import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.mcpserver import MCPServer
from scripts.backup_check import check_backups as _check_backups
from scripts.api_health_check import run_health_check as _run_health_check
from scripts.log_parser import parse_log_file as _parse_log_file
from llm.analysis import analyze_data as _analyze_data

DATA_DIR = Path(__file__).parent.parent / "data"

server = MCPServer("ai-ops-automation-toolkit")

_tickets = []

@server.tool()
def check_backups() -> dict:
    return _check_backups(DATA_DIR / "backup_jobs.json")


@server.tool()
def run_health_check() -> dict:
    return _run_health_check()


@server.tool()
def analyze_logs() -> dict:
    parsed = _parse_log_file(DATA_DIR / "sample_logs.txt")
    analysis = _analyze_data(parsed)
    return {
        "total_log_lines": parsed["total_lines"],
        "repeated_issues": parsed["repeated_issues"],
        "ai_analysis": analysis,
    }


@server.tool()
def create_ticket(title: str, description: str, severity: str) -> dict:
    ticket = {
        "id": len(_tickets) + 1,
        "title": title,
        "description": description,
        "severity": severity,
    }
    _tickets.append(ticket)
    return {"status": "created", "ticket": ticket}


@server.tool()
def list_tickets() -> dict:
    return {"tickets": _tickets}


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    server.run(transport="streamable-http", host="0.0.0.0", port=port)