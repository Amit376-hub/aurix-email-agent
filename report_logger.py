"""
report_logger.py

Logs every email scan event to aurix_logs.json for report generation.
Call clear_logs() before each scan, then log_scan_event() for each email.
"""

import json
import os
from datetime import datetime

LOG_FILE = "aurix_logs.json"

def _load_logs() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _save_logs(logs: list):
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

def clear_logs():
    """Wipe all logs before a fresh scan so reports only reflect current results."""
    _save_logs([])

def log_scan_event(
    username: str,
    user_email: str,
    subject: str,
    sender: str,
    is_spam: bool,
    spam_reasons: list = None,
    replied: bool = False,
):
    """Append one email-scan event to the log file."""
    logs = _load_logs()
    logs.append({
        "timestamp":    datetime.now().isoformat(),
        "date":         datetime.now().strftime("%Y-%m-%d"),
        "username":     username,
        "user_email":   user_email,
        "subject":      subject,
        "sender":       sender,
        "is_spam":      is_spam,
        "spam_reasons": spam_reasons or [],
        "replied":      replied,
    })
    _save_logs(logs)

def get_all_logs() -> list:
    return _load_logs()