#!/usr/bin/env python3
"""
Bulk-create MISP objects in a Flowintel case via the REST API.

Usage:
    python create_bulk_misp_objects.py \
        --url http://localhost:7007 \
        --api-key YOUR_API_KEY \
        --case-id 1 \
        --count 100

The script:
  1. Fetches available templates from GET /case/get_misp_object
  2. Creates <count> objects spread across a few common templates,
     each with one or more synthetic attributes.
"""

import argparse
import ipaddress
import random
import string
import sys
import time

import requests

# ---------------------------------------------------------------------------
# Synthetic data generators
# ---------------------------------------------------------------------------

def _rand_ipv4() -> str:
    return str(ipaddress.IPv4Address(random.randint(0x01000001, 0xFEFFFFFE)))


def _rand_domain() -> str:
    tlds = ["com", "net", "org", "io", "xyz"]
    label = "".join(random.choices(string.ascii_lowercase, k=random.randint(4, 10)))
    return f"{label}.{random.choice(tlds)}"


def _rand_url() -> str:
    scheme = random.choice(["http", "https"])
    return f"{scheme}://{_rand_domain()}/{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"


def _rand_hash(length: int) -> str:
    return "".join(random.choices("0123456789abcdef", k=length))


def _rand_cve() -> str:
    return f"CVE-{random.randint(2015, 2026)}-{random.randint(1000, 99999)}"


def _rand_filename() -> str:
    exts = [".exe", ".dll", ".ps1", ".sh", ".py", ".docx", ".pdf", ".zip"]
    name = "".join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(6, 14)))
    return name + random.choice(exts)


# Map template name -> function that returns a list of attribute dicts
TEMPLATE_ATTRIBUTE_FACTORIES = {
    "domain-ip": lambda: [
        {"object_relation": "domain", "type": "domain",       "value": _rand_domain(),      "ids_flag": False, "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
        {"object_relation": "ip",     "type": "ip-dst",        "value": _rand_ipv4(),        "ids_flag": True,  "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
    ],
    "url": lambda: [
        {"object_relation": "url",    "type": "url",           "value": _rand_url(),         "ids_flag": False, "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
        {"object_relation": "domain", "type": "domain",        "value": _rand_domain(),      "ids_flag": False, "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
        {"object_relation": "ip",     "type": "ip-dst",        "value": _rand_ipv4(),        "ids_flag": True,  "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
    ],
    "file": lambda: [
        {"object_relation": "filename", "type": "filename",    "value": _rand_filename(),    "ids_flag": False, "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
        {"object_relation": "md5",      "type": "md5",         "value": _rand_hash(32),      "ids_flag": True,  "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
        {"object_relation": "sha1",     "type": "sha1",        "value": _rand_hash(40),      "ids_flag": True,  "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
        {"object_relation": "sha256",   "type": "sha256",      "value": _rand_hash(64),      "ids_flag": True,  "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
    ],
    "vulnerability": lambda: [
        {"object_relation": "id",          "type": "vulnerability", "value": _rand_cve(),    "ids_flag": False, "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
        {"object_relation": "description", "type": "text",          "value": "Bulk-generated vulnerability entry", "ids_flag": False, "disable_correlation": True, "comment": "bulk", "first_seen": "", "last_seen": ""},
    ],
    "ip-port": lambda: [
        {"object_relation": "ip",   "type": "ip-dst",  "value": _rand_ipv4(),                "ids_flag": True,  "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
        {"object_relation": "port", "type": "port",    "value": str(random.randint(1, 65535)),"ids_flag": False, "disable_correlation": False, "comment": "bulk", "first_seen": "", "last_seen": ""},
    ],
}

FALLBACK_ATTR = lambda name: [
    {"object_relation": "text", "type": "text", "value": f"bulk-generated-{name}-{random.randint(1000,9999)}", "ids_flag": False, "disable_correlation": True, "comment": "bulk", "first_seen": "", "last_seen": ""}
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_templates(base_url: str, headers: dict) -> list:
    url = f"{base_url}/api/case/get_misp_object"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("misp-object", [])


def pick_templates(all_templates: list) -> list:
    """Return a subset of templates to use for bulk creation."""
    preferred = list(TEMPLATE_ATTRIBUTE_FACTORIES.keys())
    chosen = [t for t in all_templates if t["name"] in preferred]
    if not chosen:
        # Fall back to whatever is available
        chosen = all_templates[:5] or all_templates
    return chosen


def build_attributes(template_name: str) -> list:
    factory = TEMPLATE_ATTRIBUTE_FACTORIES.get(template_name, lambda: FALLBACK_ATTR(template_name))
    return factory()


def create_object(base_url: str, headers: dict, case_id: int, template: dict) -> requests.Response:
    url = f"{base_url}/api/case/{case_id}/create_misp_object"
    payload = {
        "object-template": {"uuid": template["uuid"], "name": template["name"]},
        "attributes": build_attributes(template["name"]),
    }
    return requests.post(url, json=payload, headers=headers, timeout=30)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Bulk-create MISP objects in a Flowintel case.")
    parser.add_argument("--url",     required=True,  help="Base URL of the Flowintel instance (e.g. http://localhost:7007)")
    parser.add_argument("--api-key", required=True,  help="Your Flowintel API key (X-API-KEY header)")
    parser.add_argument("--case-id", required=True,  type=int, help="ID of the case to populate")
    parser.add_argument("--count",   default=100,    type=int, help="Number of objects to create (default: 100)")
    parser.add_argument("--delay",   default=0.0,    type=float, help="Seconds to wait between requests (default: 0)")
    return parser.parse_args()


def main():
    args = parse_args()
    base_url = args.url.rstrip("/")
    headers = {
        "X-API-KEY": args.api_key,
        "Content-Type": "application/json",
    }

    print(f"Fetching templates from {base_url} …")
    try:
        all_templates = fetch_templates(base_url, headers)
    except requests.HTTPError as exc:
        print(f"ERROR fetching templates: {exc}", file=sys.stderr)
        sys.exit(1)

    if not all_templates:
        print("ERROR: no templates returned by the server.", file=sys.stderr)
        sys.exit(1)

    templates = pick_templates(all_templates)
    print(f"Using {len(templates)} template(s): {[t['name'] for t in templates]}")
    print(f"Creating {args.count} objects in case {args.case_id} …\n")

    ok = 0
    errors = 0
    for i in range(1, args.count + 1):
        template = templates[(i - 1) % len(templates)]
        try:
            resp = create_object(base_url, headers, args.case_id, template)
            if resp.status_code == 200:
                ok += 1
                status = "OK"
            else:
                errors += 1
                status = f"FAIL {resp.status_code}: {resp.text[:80]}"
        except requests.RequestException as exc:
            errors += 1
            status = f"ERROR: {exc}"

        print(f"  [{i:>4}/{args.count}] {template['name']:<20} {status}")

        if args.delay > 0:
            time.sleep(args.delay)

    print(f"\nDone. {ok} created, {errors} failed.")


if __name__ == "__main__":
    main()
