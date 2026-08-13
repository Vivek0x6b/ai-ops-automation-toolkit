# AI Ops Automation Toolkit

![Python](https://img.shields.io/badge/python-3.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)
![Status](https://img.shields.io/badge/status-live-brightgreen)
![Security Tested](https://img.shields.io/badge/security-tested-critical)
![Groq](https://img.shields.io/badge/LLM-Groq%20Llama%203.3-orange)
![Render](https://img.shields.io/badge/hosted%20on-Render-46E3B7)

An AI powered IT operations platform that automates backup monitoring, service health checks, log analysis, and uptime alerting, exposed as an MCP (Model Context Protocol) server for AI agents, and as a live web dashboard for direct use. Built, deployed, and security tested end to end, including a real prompt injection vulnerability found and fixed on live infrastructure.

**Live dashboard:** `https://ai-ops-automation-toolkit-1.onrender.com`
**Live MCP server:** `https://ai-ops-automation-toolkit.onrender.com/mcp`
**Security assessment report:** [`security-assessment-report-formal.pdf`](./security-assessment-report-formal.pdf)

*(Free tier hosting: services sleep after inactivity, so the first request after a while may take 30 to 60 seconds. This is expected.)*

## What it does

IT and MSP teams juggle backup verification, uptime monitoring, and log triage, usually manually, across disconnected tools. This project automates that pipeline at three levels:

1. **Automation scripts** check backup job status, ping service endpoints, and parse logs for errors and patterns.
2. An **LLM analysis layer** (Groq) turns structured data into a plain English severity assessment and recommended action, both for synthetic demo data and for real production logs, pulled live from a monitored service via the hosting provider's API.
3. **Real, unattended automation**: a configurable list of monitored sites is checked on a schedule, and the system emails an alert the moment something goes from healthy to down, with no manual checking required.

All of it is also exposed as **MCP tools**, a standard protocol that lets AI agents call these functions directly. Verified working using the official MCP Inspector, and built to be usable by any MCP compliant client, including Claude Desktop.

## Architecture

```
                    ┌────────────────────────────┐
                    │  MCP Client (MCP Inspector)│
                    └───────────┬────────────────┘
                                 │ MCP protocol
                    ┌────────────▼──────────────┐
                    │      MCP Server           │
                    │  (FastAPI + MCP SDK)      │
                    └────────────┬──────────────┘
                                 │
        ┌──────────┬────────────┼────────────┬─────────────┐
        ▼          ▼            ▼            ▼             ▼
    Backup      Health      Log Parser    Ticket       Uptime
    Check       Check       + LLM         System       Monitor
    Script      Script      Analysis      (mock)       + Email
                             (Groq)                     Alerts
                                                            │
                                                            ▼
                                                    Scheduled by
                                                    cron job.org

        ┌────────────────────────────────────────────────┐
        │   Web Dashboard (FastAPI + vanilla JS)         │
        │   Backup, Health, and Log Analysis demos, plus │
        │   admin gated: Uptime Check, Analyze Live Logs │
        │   (real Token Messiah logs via Render API)     │
        └────────────────────────────────────────────────┘
```

## Tools and endpoints

| Capability | MCP tool | REST endpoint | Access |
|---|---|---|---|
| Backup status (demo data) | `check_backups` | `GET /api/backup-status` | Public |
| Service health check (demo endpoints) | `run_health_check` | `GET /api/health-check` | Public |
| AI log analysis (demo data) | `analyze_logs` | `GET /api/analyze-logs` | Public |
| Create/list tickets | `create_ticket`, `list_tickets` | `POST/GET /api/tickets` | Public |
| **Uptime monitoring and email alerts** (real sites) | — | `GET /api/uptime-check` | Admin key |
| **Real live log AI analysis** (real production logs via Render API) | — | `GET /api/analyze-live-logs` | Admin key |

Public demo endpoints work with zero setup so anyone can click through the dashboard. The two admin gated endpoints operate on real infrastructure and require an API key, entered directly in the dashboard.

## Real automation: uptime monitoring

- **`data/monitored_sites.json`**: an editable list of `{name, url}` pairs to watch. No code changes needed to add or remove sites.
- **`/api/uptime-check`**: only sends an email when status actually changes from healthy to down, not on every check. Distinguishes genuine outages from HTTP 429 (rate limiting), which is not treated as a real failure.
- **Email alerts**: sent via the Resend HTTP API. (Originally built on Gmail SMTP, switched after live testing revealed Render's free tier blocks outbound SMTP entirely. See the security report for details.)
- **Scheduled automatically** via an external cron service, running independent of manual interaction.

Currently monitoring the author's own deployed [Token Messiah](https://token-messiah-frontend.vercel.app/) project as a real world test case.

## Real automation: AI log analysis

`/api/analyze-live-logs` pulls a monitored service's actual recent logs directly from the Render API (looked up by service name, no manual ID lookup needed) and sends them to Groq for analysis, the same AI pipeline as the demo button, but operating on real production data instead of a synthetic file.

## Security

This project underwent a security assessment performed directly by the author against its own live deployment, not a demo checklist, an actual test of actual infrastructure. Full details, methodology, and evidence are in the [security assessment report](./security-assessment-report-formal.pdf). 

Highlights:

- **TLS and SSL configuration**: verified clean (modern protocols only, strong ciphers, forward secrecy).
- **Found and fixed**: an unauthenticated endpoint that allowed anyone on the internet to trigger real email sends and view internal data.
- **Found and fixed**: missing HTTP security headers (CSP, HSTS, X-Content-Type-Options, and others), now enforced via middleware.
- **Found and fixed**: email alerting was silently non functional in production due to a hosting provider restriction invisible in local testing.
- **Found and iteratively fixed: a real prompt injection vulnerability** in the AI log analysis feature. An attacker controlled log entry could fully manipulate the AI into hiding genuine critical errors. The first fix (a keyword based safety net) resolved that, but introduced its own false positive edge case, discovered through further live attack testing. The refined fix has the AI self report when it detects a manipulation attempt, and the safety net defers to that judgment instead of blindly overriding on keyword presence alone. Verified against three distinct live attack variations run against real production traffic.
- Rate limiting, restricted CORS, and input sanitization added proactively and verified live.

## Tech stack

- **Python**: automation scripts, core logic
- **MCP SDK**: exposes functions as agent callable tools
- **Groq API** (Llama 3.3 70B): LLM analysis layer
- **FastAPI and Uvicorn**: REST API, dashboard, and hosted MCP endpoint
- **slowapi**: rate limiting
- **Resend**: transactional email (HTTP based, works around Render's SMTP block)
- **Render API**: pulling real logs from a monitored service
- **Vanilla HTML, CSS, and JS**: dashboard frontend, no framework or build step
- **cron job.org**: external scheduler for automated checks
- **Render**: hosting (two services: MCP server and dashboard)

## Running it yourself

```bash
git clone https://github.com/Vivek0x6b/ai-ops-automation-toolkit.git
cd ai-ops-automation-toolkit
python -m venv venv
venv\Scripts\Activate.ps1      # Windows
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`) with:
```
GROQ_API_KEY=your_groq_key
RESEND_API_KEY=your_resend_key
ALERT_RECIPIENT=where_alerts_should_go
RENDER_API_KEY=your_render_key
UPTIME_CHECK_API_KEY=a_random_key_you_generate
```

**Run the MCP server (stdio, for the MCP Inspector or Claude Desktop):**
```bash
python mcp_server/server.py
```

**Run the web dashboard:**
```bash
python api/main.py
```
Then open `http://localhost:8001`.

**Test the MCP server with the official Inspector:**
```bash
npx @modelcontextprotocol/inspector venv/Scripts/python.exe mcp_server/server.py
```

## Project evolution

- **v1.0 local**: MCP server running locally over stdio, tested via the MCP Inspector
- **v2.0 hosted**: migrated to Streamable HTTP transport, deployed publicly on Render
- **v3.0 dashboard, monitoring, and security**: web dashboard, real scheduled uptime monitoring with email alerts, real live log AI analysis via the Render API, and a full security assessment including a discovered and fixed prompt injection vulnerability

## Notes

- `backup_jobs.json` and `sample_logs.txt` are synthetic demo data.
- `monitored_sites.json` is real. It currently watches the author's own live project.
- Ticket storage is in memory and resets on service restart.
- Free tier hosting: services sleep after inactivity. Automated checks run on a schedule wide enough to stay within Render's free monthly instance hour limit while still catching real issues.
