"""Parsers and helpers for the system-wide Audit logs view (UC-27)."""
import csv
import io
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from flask import current_app

from ..case.common_core import HISTORY_DIR
from ..db_class.db import Case, Login_Event, User
from ..utils.logger import flowintel_log


# [YYYY-MM-DD HH:MM](user): action
HISTORY_LINE_RE = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]\(([^)]*)\):\s*(.*)$'
)

# 22/Apr/2026 19:54:41 - 127.0.0.1 - - "AUDIT: 200 - Case created. User: x@y CaseId: 14
AUDIT_LINE_RE = re.compile(
    r'^(?P<ts>\d{2}/\w{3}/\d{4} \d{2}:\d{2}:\d{2})\s-\s.*?'
    r'"AUDIT:\s*(?P<sev>\d+)\s*-\s*(?P<action>.+?)'
    r'(?:\.\s+(?P<extra>\w+:.*))?$'
)

_AUDIT_USER_RE = re.compile(r'\bUser:\s*(\S+)')
_AUDIT_CASE_RE = re.compile(r'\bCaseId:\s*(\d+)')


def _safe_path(base, entry):
    """Return the resolved path of `entry` if it stays inside `base`, else None."""
    base = Path(base).resolve()
    try:
        candidate = (base / entry).resolve()
        candidate.relative_to(base)
    except (OSError, ValueError):
        return None
    return candidate


def safe_log_path():
    """Resolve the configured log file under logs/, rejecting traversal."""
    log_name = current_app.config.get("LOG_FILE", "record.log")
    candidate = _safe_path("logs", log_name)
    if candidate is None:
        flowintel_log("audit", 403, "Audit logs: log path outside logs/ rejected",
                      LogFile=str(log_name))
        return None
    return candidate if candidate.is_file() else None


def safe_history_path(entry):
    """Resolve a per-case history file under HISTORY_DIR, rejecting traversal."""
    candidate = _safe_path(HISTORY_DIR, entry)
    if candidate is None:
        flowintel_log("audit", 403, "Audit logs: history path outside HISTORY_DIR rejected",
                      Entry=str(entry))
        return None
    return candidate if candidate.is_file() else None


def parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _row_text(row):
    return " ".join(str(row.get(k, "") or "") for k in ("user", "action", "extra")).lower()


def row_matches(row, start_dt, end_dt, user_q, action_q, exclude_q):
    try:
        row_dt = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M")
    except (ValueError, KeyError, TypeError):
        return False
    if start_dt and row_dt < start_dt:
        return False
    if end_dt and row_dt >= end_dt + timedelta(days=1):
        return False
    if user_q and user_q not in (row.get("user") or "").lower():
        return False
    if action_q and action_q not in (row.get("action") or "").lower():
        return False
    if exclude_q and exclude_q in _row_text(row):
        return False
    return True


def filter_rows(rows, args):
    start_dt = parse_iso_date(args.get("start_date"))
    end_dt = parse_iso_date(args.get("end_date"))
    user_q = (args.get("user") or "").strip().lower()
    action_q = (args.get("action") or "").strip().lower()
    exclude_q = (args.get("exclude") or "").strip().lower()
    return [
        r for r in rows
        if row_matches(r, start_dt, end_dt, user_q, action_q, exclude_q)
    ]


def has_active_filters(args):
    return any(
        (args.get(key) or "").strip()
        for key in ("start_date", "end_date", "user", "action", "exclude")
    )


def collect_history_rows():
    rows = []
    if not os.path.isdir(HISTORY_DIR):
        flowintel_log("audit", 500, "Audit logs: HISTORY_DIR missing",
                      HistoryDir=HISTORY_DIR)
        return rows

    uuid_to_case = {
        c.uuid: c.id
        for c in Case.query.with_entities(Case.id, Case.uuid).all()
    }

    for entry in os.listdir(HISTORY_DIR):
        path = safe_history_path(entry)
        if path is None:
            continue
        case_id = uuid_to_case.get(entry)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = HISTORY_LINE_RE.match(line.strip())
                    if not m:
                        continue
                    rows.append({
                        "timestamp": m.group(1),
                        "user": m.group(2),
                        "action": m.group(3),
                        "case_id": case_id,
                        "case_uuid": entry,
                        "source": "case_history",
                        "raw": line.rstrip("\n"),
                    })
        except OSError as exc:
            flowintel_log("audit", 500,
                          "Audit logs: failed to read history file",
                          File=str(path), Error=str(exc))
    return rows


def collect_login_rows():
    user_map = {
        u.id: u.email
        for u in User.query.with_entities(User.id, User.email).all()
    }
    events = Login_Event.query.order_by(Login_Event.login_date.desc()).all()
    rows = []
    for ev in events:
        if not ev.login_date:
            continue
        rows.append({
            "timestamp": ev.login_date.strftime("%Y-%m-%d %H:%M"),
            "user": user_map.get(ev.user_id, f"user#{ev.user_id}"),
            "action": "Login",
            "case_id": None,
            "case_uuid": None,
            "source": "login",
            "raw": f"Login user_id={ev.user_id} at {ev.login_date.isoformat()}",
        })
    return rows


def collect_audit_rows():
    rows = []
    log_path = safe_log_path()
    if log_path is None:
        return rows
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "AUDIT:" not in line:
                    continue
                m = AUDIT_LINE_RE.match(line.rstrip())
                if not m:
                    continue
                try:
                    ts = datetime.strptime(m.group("ts"), "%d/%b/%Y %H:%M:%S")
                except ValueError:
                    continue
                extra = (m.group("extra") or "").strip()
                user_match = _AUDIT_USER_RE.search(extra)
                case_match = _AUDIT_CASE_RE.search(extra)
                rows.append({
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M"),
                    "severity": int(m.group("sev")),
                    "user": user_match.group(1) if user_match else "",
                    "action": m.group("action").strip(),
                    "case_id": int(case_match.group(1)) if case_match else None,
                    "extra": extra,
                    "source": "audit_log",
                    "raw": line.rstrip("\n"),
                })
    except OSError as exc:
        flowintel_log("audit", 500, "Audit logs: cannot read log file",
                      File=str(log_path), Error=str(exc))
    return rows


def rows_to_csv(rows, fields):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({f: ("" if r.get(f) is None else r.get(f)) for f in fields})
    return output.getvalue()


def rows_to_json(rows, fields):
    payload = [{f: r.get(f) for f in fields} for r in rows]
    return json.dumps(payload, indent=2, default=str)
