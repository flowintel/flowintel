#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
import uuid


def utc_timestamp():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_payload(args):
    event_uuid = args.event_uuid or str(uuid.uuid4())

    return {
        "Event": {
            "uuid": event_uuid,
            "id": args.event_id,
            "info": args.title,
            "date": dt.date.today().isoformat(),
            "timestamp": utc_timestamp(),
            "threat_level_id": args.threat_level_id,
            "analysis": "0",
            "Orgc": {"name": args.source},
            "Tag": [
                {"name": "tlp:amber"},
                {"name": f"source:{args.source.lower()}"},
                {"name": "flowintel:test"},
            ],
            "Attribute": [
                {
                    "uuid": str(uuid.uuid4()),
                    "type": "ip-src",
                    "category": "Network activity",
                    "value": "203.0.113.78",
                    "comment": "Remote SSH client observed in failed logins",
                    "to_ids": True,
                },
                {
                    "uuid": str(uuid.uuid4()),
                    "type": "link",
                    "category": "External analysis",
                    "value": "https://siem.example.local/alerts/demo-5715",
                    "comment": "Source alert in SIEM",
                    "to_ids": False,
                },
            ],
            "Object": [
                {
                    "uuid": str(uuid.uuid4()),
                    "name": "file",
                    "template_uuid": "688c46fb-5edb-40a3-8273-1af7923e2215",
                    "Attribute": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "type": "filename",
                            "object_relation": "filename",
                            "value": "suspicious.ps1",
                            "to_ids": False,
                        },
                        {
                            "uuid": str(uuid.uuid4()),
                            "type": "sha256",
                            "object_relation": "sha256",
                            "value": "0" * 64,
                            "to_ids": True,
                        },
                    ],
                }
            ],
        }
    }


def send_alert(args):
    base_url = args.url.rstrip("/")
    endpoint = f"{base_url}/api/alerts/ingest"
    payload = build_payload(args)
    body = json.dumps(payload, indent=2 if args.print_payload else None).encode("utf-8")

    if args.print_payload:
        print(json.dumps(payload, indent=2))

    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": args.api_key,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return response.status, response_body
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        return exc.code, response_body


def main():
    parser = argparse.ArgumentParser(
        description="Send a sample MISP event alert to Flowintel's alert ingest API."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("FLOWINTEL_URL", "http://127.0.0.1:7006"),
        help="Base Flowintel URL. Defaults to FLOWINTEL_URL or http://127.0.0.1:7006.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("FLOWINTEL_ALERT_KEY"),
        help="Connector instance API key. Defaults to FLOWINTEL_ALERT_KEY.",
    )
    parser.add_argument(
        "--source",
        default="Wazuh",
        help="MISP Orgc/source name to include in the event payload.",
    )
    parser.add_argument(
        "--threat-level-id",
        default="1",
        choices=["1", "2", "3", "4"],
        help="MISP threat_level_id: 1 high, 2 medium, 3 low, 4 undefined.",
    )
    parser.add_argument(
        "--title",
        default="Possible SSH brute-force against srv-web-01",
        help="Sample alert title.",
    )
    parser.add_argument(
        "--event-uuid",
        help="MISP event UUID. Reuse it to test occurrence_count increments.",
    )
    parser.add_argument(
        "--event-id",
        default="5715",
        help="MISP event id to include in the sample payload.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--print-payload",
        action="store_true",
        help="Print the JSON payload before sending it.",
    )

    args = parser.parse_args()
    if not args.api_key:
        parser.error("Missing connector API key. Set FLOWINTEL_ALERT_KEY or pass --api-key.")

    status, response_body = send_alert(args)
    try:
        response_json = json.loads(response_body)
        pretty_body = json.dumps(response_json, indent=2)
    except json.JSONDecodeError:
        pretty_body = response_body

    print(f"POST {args.url.rstrip('/')}/api/alerts/ingest -> HTTP {status}")
    print(pretty_body)
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
