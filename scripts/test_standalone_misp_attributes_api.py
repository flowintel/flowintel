#!/usr/bin/env python3
"""
Smoke-test standalone MISP attribute API endpoints.

This script validates the following routes:
- GET  /api/case/get_misp_attribute_types
- GET  /api/case/<cid>/get_case_misp_attributes
- POST /api/case/<cid>/create_misp_attribute
- POST /api/case/<cid>/misp_attribute/<aid>/edit_misp_attribute
- GET  /api/case/<cid>/misp_attribute/<aid>/delete_misp_attribute

Example:
    python scripts/test_standalone_misp_attributes_api.py \
        --url http://localhost:7007 \
        --api-key YOUR_API_KEY \
        --case-id 1
"""

import argparse
import datetime
import json
import sys
import uuid

import requests


def parse_args():
    parser = argparse.ArgumentParser(
        description="Test standalone MISP attribute API endpoints end-to-end."
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Flowintel base URL, e.g. http://localhost:7007",
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="API key used in X-API-KEY header",
    )
    parser.add_argument(
        "--case-id",
        required=True,
        type=int,
        help="Case ID to use for the test",
    )
    parser.add_argument(
        "--attr-type",
        default="text",
        help="MISP attribute type for the test object (default: text)",
    )
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        default=False,
        help="Enable TLS certificate verification (default: disabled)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="HTTP timeout in seconds (default: 20)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep created attribute (do not delete at end)",
    )
    return parser.parse_args()


def fail(message, response=None):
    print(f"[FAIL] {message}")
    if response is not None:
        print(f"  status: {response.status_code}")
        try:
            print("  body:")
            print(json.dumps(response.json(), indent=2))
        except Exception:
            body = response.text.strip()
            if body:
                print(f"  body: {body}")
    sys.exit(1)


def ok(message):
    print(f"[OK] {message}")


def request_json(session, method, url, timeout, **kwargs):
    response = session.request(method, url, timeout=timeout, **kwargs)
    try:
        payload = response.json()
    except Exception:
        payload = None
    return response, payload


def find_attribute(attrs, attr_id):
    for attr in attrs:
        if attr.get("id") == attr_id:
            return attr
    return None


def main():
    args = parse_args()
    base_url = args.url.rstrip("/")
    case_id = args.case_id

    session = requests.Session()
    session.headers.update(
        {
            "X-API-KEY": args.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    session.verify = args.verify_tls

    marker = uuid.uuid4().hex[:10]
    create_value = f"standalone-api-test-{marker}"
    edit_value = f"standalone-api-test-edited-{marker}"
    now_text = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M")

    attr_id = None

    print("=== Standalone MISP Attribute API Smoke Test ===")
    print(f"Base URL: {base_url}")
    print(f"Case ID : {case_id}")

    # 1) Get attribute types
    url_types = f"{base_url}/api/case/get_misp_attribute_types"
    resp, data = request_json(session, "GET", url_types, timeout=args.timeout)
    if resp.status_code != 200:
        fail("Unable to get attribute types", resp)
    if not isinstance(data, dict) or "types" not in data:
        fail("Invalid response for get_misp_attribute_types", resp)
    ok(f"Fetched attribute types ({len(data.get('types', []))} types)")

    # 2) List current standalone attributes
    url_list = f"{base_url}/api/case/{case_id}/get_case_misp_attributes"
    resp, data = request_json(session, "GET", url_list, timeout=args.timeout)
    if resp.status_code != 200:
        fail("Unable to list standalone attributes", resp)
    if not isinstance(data, dict) or "attributes" not in data:
        fail("Invalid response for get_case_misp_attributes", resp)
    before_count = len(data.get("attributes", []))
    ok(f"Listed standalone attributes (before count={before_count})")

    # 3) Create standalone attribute
    url_create = f"{base_url}/api/case/{case_id}/create_misp_attribute"
    create_payload = {
        "value": create_value,
        "type": args.attr_type,
        "comment": "created by standalone API smoke test",
        "ids_flag": False,
        "disable_correlation": False,
        "first_seen": now_text,
        "last_seen": now_text,
    }
    resp, data = request_json(session, "POST", url_create, timeout=args.timeout, json=create_payload)
    if resp.status_code != 201:
        fail("Create standalone attribute failed", resp)
    if not isinstance(data, dict) or "attribute" not in data:
        fail("Invalid create response format", resp)

    created_attr = data.get("attribute") or {}
    attr_id = created_attr.get("id")
    if not attr_id:
        fail("Create response did not return attribute id", resp)
    ok(f"Created standalone attribute (id={attr_id})")

    # 4) Verify attribute appears in list
    resp, data = request_json(session, "GET", url_list, timeout=args.timeout)
    if resp.status_code != 200:
        fail("List after create failed", resp)
    attrs = data.get("attributes", []) if isinstance(data, dict) else []
    found = find_attribute(attrs, attr_id)
    if not found:
        fail(f"Created attribute id={attr_id} not found in list", resp)
    ok("Created attribute is present in list")

    # 5) Edit standalone attribute
    url_edit = f"{base_url}/api/case/{case_id}/misp_attribute/{attr_id}/edit_misp_attribute"
    edit_payload = {
        "value": edit_value,
        "type": args.attr_type,
        "comment": "edited by standalone API smoke test",
        "ids_flag": True,
        "disable_correlation": False,
        "first_seen": now_text,
        "last_seen": now_text,
    }
    resp, _ = request_json(session, "POST", url_edit, timeout=args.timeout, json=edit_payload)
    if resp.status_code != 200:
        fail("Edit standalone attribute failed", resp)
    ok(f"Edited standalone attribute (id={attr_id})")

    # 6) Verify edited value in list
    resp, data = request_json(session, "GET", url_list, timeout=args.timeout)
    if resp.status_code != 200:
        fail("List after edit failed", resp)
    attrs = data.get("attributes", []) if isinstance(data, dict) else []
    found = find_attribute(attrs, attr_id)
    if not found:
        fail(f"Edited attribute id={attr_id} not found in list", resp)
    if found.get("value") != edit_value:
        fail(
            f"Attribute value mismatch after edit: expected {edit_value}, got {found.get('value')}",
            resp,
        )
    ok("Edited value verified")

    if args.keep:
        ok(f"Keep mode enabled, not deleting attribute id={attr_id}")
        print("=== RESULT: PASS ===")
        return

    # 7) Delete standalone attribute
    url_delete = f"{base_url}/api/case/{case_id}/misp_attribute/{attr_id}/delete_misp_attribute"
    resp, _ = request_json(session, "GET", url_delete, timeout=args.timeout)
    if resp.status_code != 200:
        fail("Delete standalone attribute failed", resp)
    ok(f"Deleted standalone attribute (id={attr_id})")

    # 8) Verify it is gone
    resp, data = request_json(session, "GET", url_list, timeout=args.timeout)
    if resp.status_code != 200:
        fail("Final list call failed", resp)
    attrs = data.get("attributes", []) if isinstance(data, dict) else []
    if find_attribute(attrs, attr_id):
        fail(f"Deleted attribute id={attr_id} is still present", resp)
    ok("Deletion verified")

    print("=== RESULT: PASS ===")


if __name__ == "__main__":
    main()
