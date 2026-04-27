# Python Script to post a job application to B12 using the B12 API
"""
Post a job application to B12 using the B12 API.

Builds a JSON payload with the following fields:
    - timestamp: ISO 8601 UTC formatted string of submission time
    - name: applicant's name
    - email: applicant's email
    - resume_link: link to applicant's resume
    - repository_link: link to applicant's repository
    - action_run_link: link to the triggering GitHub Actions run

The request body is serialized with compact separators, alphabetically
sorted keys, and UTF-8 encoding. A HMAC-SHA256 signature of the request
body is included in the X-Signature-256 header using the signing secret.
"""

import json
import hmac
import hashlib
from urllib import request, error
import os
from datetime import datetime, timezone
import sys

SIGNING_SECRET = b"hello-there-from-b12"
ENDPOINT = "https://webhook.site/d20d7859-0bc1-4f26-a21b-957a9337d2a1"


def build_payload() -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S") +
        f".{now.microsecond // 1000:03d}Z",
        "name": os.environ["APPLICANT_NAME"],
        "email": os.environ["APPLICANT_EMAIL"],
        "resume_link": os.environ["RESUME_LINK"],
        "repository_link": os.environ["REPOSITORY_LINK"],
        "action_run_link": os.environ["ACTION_RUN_LINK"],
    }
    return payload


def canonicalize_payload(payload: dict) -> bytes:
    # The post body should contain no extra whitespace (compact separators),
    # have keys sorted alphabetically, and be UTF-8-encoded.
    return json.dumps(
        payload, separators=(',', ':'), sort_keys=True
        ).encode('utf-8')


def sign(body: bytes) -> str:
    # The post should include a header called X-Signature-256 where the
    # value is a sha256 where the hex digest is the HMAC-SHA256 of the
    # raw UTF-8-encoded JSON request body, using the signing secret as
    # the key.
    digest = hmac.new(SIGNING_SECRET, body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def submit_application() -> str:
    payload = build_payload()
    body = canonicalize_payload(payload)
    signature = sign(body)

    print(f"Submitting payload: {body.decode('utf-8')}")
    print(f"Signature: {signature}")

    headers = {
        "Content-Type": "application/json",
        "X-Signature-256": signature
    }

    req = request.Request(
        ENDPOINT, headers=headers, data=body, method="POST"
    )
    try:
        with request.urlopen(req) as resp:
            response_body = resp.read().decode("utf-8")
            print(f"HTTP {resp.status}: {response_body}")
            data = json.loads(response_body)
            if not data.get("success"):
                raise RuntimeError(f"Submission failed: {response_body}")
            return data["receipt"]
    except error.HTTPError as e:
        print(
            f"HTTP error {e.code}: {e.read().decode('utf-8')}", file=sys.stderr
        )
        raise
    except error.URLError as e:
        print(f"URL error: {e.reason}", file=sys.stderr)
        raise


if __name__ == "__main__":
    receipt = submit_application()
    print(f"\nRECEIPT: {receipt}")
