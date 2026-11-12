#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py

Rules (see README):
  * Lines that can't be parsed, and events without a txn_id, are ignored.
  * A payment may be attempted several times under one txn_id. Only the
    latest attempt (by `ts`, not by position in the file) counts.
  * A payment is collected only if that latest attempt is `success`.
"""
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAYMENTS_FILE = HERE / "payments.jsonl"
EXPECTED_FILE = HERE / "expected.txt"


def parse_amount(raw):
    """Return the amount as an exact Decimal.

    The export mixes numbers (3533.05) with strings, some of which carry
    thousands separators ("4,804.15"). Decimal avoids float rounding drift
    when summing tens of thousands of naira amounts.
    """
    return Decimal(str(raw).replace(",", "").strip())


def parse_ts(raw):
    """Parse an ISO-8601 UTC timestamp such as 2026-09-21T15:30:26Z."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def read_events(path):
    """Yield every readable event that has a txn_id."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # truncated / corrupt line
            if not isinstance(event, dict) or not event.get("txn_id"):
                continue
            yield event


def latest_attempts(events):
    """Reduce events to the most recent attempt per txn_id."""
    latest = {}
    for event in events:
        ts = parse_ts(event["ts"])
        current = latest.get(event["txn_id"])
        # `>=` so that, on an identical timestamp, the later line wins.
        if current is None or ts >= current[0]:
            latest[event["txn_id"]] = (ts, event)
    return [event for _, event in latest.values()]


def reconcile(path=PAYMENTS_FILE):
    """Return (number of collected payments, total collected in naira)."""
    collected = [
        e for e in latest_attempts(read_events(path)) if e["status"] == "success"
    ]
    total = sum((parse_amount(e["amount"]) for e in collected), Decimal(0))
    return len(collected), total


def main():
    count, total = reconcile()
    expected = int(EXPECTED_FILE.read_text().strip())

    if count != expected:
        print(f"Check failed: counted {count} successful payments, expected {expected}.")
        print("Something in the data isn't being handled the way the README describes.")
    else:
        print(f"Check passed: {count} successful payments.")
        print(f"Your code: KOYA-{round(total)}")


if __name__ == "__main__":
    main()
