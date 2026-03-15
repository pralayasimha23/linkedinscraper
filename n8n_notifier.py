"""
n8n_notifier.py
---------------
Posts scraped job results directly to your n8n webhook.
No database involved — n8n receives the raw job data and handles it from there.
"""

import os
import logging
import requests

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")
GITHUB_RUN_ID   = os.environ.get("GITHUB_RUN_ID", "local")


def send_jobs_to_n8n(jobs: list, source: str) -> bool:
    """
    POST scraped jobs directly to n8n.

    Payload your n8n Webhook node receives:
    {
        "source":    "linkedin" | "careers_future",
        "run_id":    "12345678",
        "job_count": 3,
        "jobs": [
            {
                "job_id":      "...",
                "company":     "...",
                "job_title":   "...",
                "location":    "...",
                "level":       "...",
                "provider":    "linkedin" | "careers_future",
                "description": "..."   <- Markdown
            }
        ]
    }
    """
    if not N8N_WEBHOOK_URL:
        logging.warning("N8N_WEBHOOK_URL not set — skipping webhook call.")
        return False

    if not jobs:
        logging.info(f"[n8n] No jobs to send for source '{source}'.")
        return True

    payload = {
        "source":    source,
        "run_id":    GITHUB_RUN_ID,
        "job_count": len(jobs),
        "jobs":      jobs,
    }

    try:
        logging.info(f"[n8n] Sending {len(jobs)} job(s) [{source}] to n8n...")
        resp = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        logging.info(f"[n8n] Accepted — HTTP {resp.status_code}")
        return True
    except requests.exceptions.HTTPError as e:
        logging.error(f"[n8n] HTTP error: {e} — {e.response.text[:300]}")
    except requests.exceptions.RequestException as e:
        logging.error(f"[n8n] Request failed: {e}")

    return False


def send_summary_to_n8n(total: int, errors: list) -> None:
    """Send a run summary — fires even when no new jobs found, useful for monitoring."""
    if not N8N_WEBHOOK_URL:
        return
    try:
        requests.post(
            N8N_WEBHOOK_URL,
            json={
                "type":        "run_summary",
                "run_id":      GITHUB_RUN_ID,
                "total_sent":  total,
                "errors":      errors,
            },
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"[n8n] Failed to send summary: {e}")
