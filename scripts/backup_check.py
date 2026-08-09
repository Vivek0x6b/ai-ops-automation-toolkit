
import json
from datetime import datetime, timedelta
from pathlib import Path

STALE_THRESHOLD_HOURS = 24

def check_backups(data_path):
    # TODO 1: open and read the file
    with open(data_path) as f:
        jobs = json.load(f)
    
    # TODO 2: figure out the reference time
    timestamps = [datetime.fromisoformat(job["timestamp"]) for job in jobs]
    reference_time = max(timestamps)
    

    # Set up empty containers to fill as we loop
    failures = []
    stale = []
    healthy_count = 0

    # TODO 3: loop through each job and classify it
    for job in jobs:
        job_time = datetime.fromisoformat(job["timestamp"])
        age = reference_time - job_time

        if job["status"] == "failed":
            failures.append({
                "job_name": job["job_name"],
                "client": job["client"],
                "error": job.get("error", "Unknown error"),
                "timestamp": job["timestamp"],
            })
       

        elif age > timedelta(hours=STALE_THRESHOLD_HOURS):
            stale.append({
                "job_name": job["job_name"],
                "client": job["client"],
                "last_success": job["timestamp"],
            })

        else:
            healthy_count += 1

    # TODO 4: return everything as one dict
    return {
        "checked_at": reference_time.isoformat(),
        "total_jobs": len(jobs),
        "healthy_count": healthy_count,
        "failures": failures,
        "stale": stale,
    }

if __name__ == "__main__":
    result = check_backups(Path(__file__).parent.parent / "data" / "backup_jobs.json")
    print(json.dumps(result, indent=2))