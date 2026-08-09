import re 
from collections import Counter
from pathlib import Path

LOG_LINE_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"(?P<level>INFO|WARNING|ERROR|CRITICAL)\s+"
    r"\[(?P<service>[\w-]+)\]\s+"
    r"(?P<message>.+)$"
)

NOTABLE_LEVELS = {"WARNING","ERROR","CRITICAL"}

def parse_log_file(log_path):
    entries= []
    with open(log_path)as f:
        for line in f:
            match = LOG_LINE_PATTERN.match(line.strip())
            if match:
                entries.append(match.groupdict())
    level_counts = Counter(e["level"] for e in entries)
    notable_entries = [e for e in entries if e["level"]in NOTABLE_LEVELS]

    issue_signature_counts = Counter(
        (e["service"], e["message"].split(" - ")[0])
        for e in notable_entries
    )

    repeated_issues = [
        {"service":service, "message_pattern":pattern,"count":count}
        for (service, pattern), count in issue_signature_counts.items()
        if count >=2
    ]

    return {
        "total_lines": len(entries),
        "level_counts":dict(level_counts),
        "notable_entries":notable_entries,
        "repeated_issues":repeated_issues,
    }


if __name__ == "__main__":
    import json 
    result = parse_log_file(Path(__file__).parent.parent/"data"/"sample_logs.txt")
    print(json.dumps(result,indent=2))