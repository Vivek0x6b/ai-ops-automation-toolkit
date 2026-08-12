import os
import json
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
GROQ_ENDPOINT = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"

def _get_client():
    token = os.environ.get("GROQ_API_KEY")
    if not token:
        raise RuntimeError("GROQ_API_KEY not found. Check your .env file.")
    return OpenAI(base_url=GROQ_ENDPOINT, api_key=token)

ANALYSIS_SYSTEM_PROMPT ="""You are an IT operations assistant for an MSP.
CRITICAL: Output ONLY the JSON object below. No markdown, no explanation, no headers, nothing before or after the JSON.

{
  "severity": "none" | "low" | "medium" | "high" | "critical",
  "summary": "one or two sentence plain-English summary",
  "likely_cause": "brief technical explanation, or null if severity is none",
  "recommended_action": "concrete next step, or null if severity is none"
  "requires_human_review": true or false - true if this needs an engineer's judgment rather than an automated response
}"""

def analyze_data(structured_data, model=DEFAULT_MODEL):
    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(structured_data)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw_text = response.choices[0].message.content.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "severity": "unknown",
            "summary": "Model did not return valid JSON",
            "requires_human_review": True,
            "raw_response": raw_text,
        }


RAW_LOG_ANALYSIS_PROMPT = """You are an IT operations assistant analyzing real production logs
from a live web service. You will be given raw log lines (may include request logs,
application logs, error traces, etc.).

Respond with ONLY valid JSON, no other text, in this exact shape:

{
  "severity": "none" | "low" | "medium" | "high" | "critical",
  "summary": "one or two sentence plain-English summary of what's happening",
  "notable_patterns": ["short description of each recurring or concerning pattern found"],
  "likely_cause": "brief technical explanation, or null if severity is none",
  "recommended_action": "concrete next step, or null if severity is none"
}

Base severity on real signals: repeated errors, 5xx status codes, timeouts, and
crashes are high/critical. Occasional 4xx client errors or normal request traffic
is none/low."""


def analyze_raw_logs(raw_log_text, source_name="service", model=DEFAULT_MODEL):
    client = _get_client()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": RAW_LOG_ANALYSIS_PROMPT},
            {"role": "user", "content": f"Logs from {source_name}:\n\n{raw_log_text}"},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "severity": "unknown",
            "summary": "Model did not return valid JSON",
            "raw_response": raw_text,
        }

if __name__ == "__main__":
    sample = {
        "repeated_issues": [
            {"service": "db-service", "message_pattern": "Connection pool exhausted", "count": 3}
        ]
    }
    print(json.dumps(analyze_data(sample), indent=2))