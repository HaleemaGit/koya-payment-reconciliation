// Payment reconciliation.
//
// Reads payments.jsonl and works out how much money we actually collected.
// Run:  node reconcile.js
//
// Rules (see README):
//   * Lines that can't be parsed, and events without a txn_id, are ignored.
//   * A payment may be attempted several times under one txn_id. Only the
//     latest attempt (by `ts`, not by position in the file) counts.
//   * A payment is collected only if that latest attempt is `success`.

const fs = require("fs");
const path = require("path");

const PAYMENTS_FILE = path.join(__dirname, "payments.jsonl");
const EXPECTED_FILE = path.join(__dirname, "expected.txt");

// Amounts arrive as numbers (3533.05) or strings, some with thousands
// separators ("4,804.15"). Convert to integer kobo so the sum is exact.
function toKobo(raw) {
  const naira = Number(String(raw).replace(/,/g, "").trim());
  return Math.round(naira * 100);
}

// Every readable event that has a txn_id.
function readEvents(file) {
  const events = [];
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    let event;
    try {
      event = JSON.parse(line);
    } catch {
      continue; // blank, truncated or corrupt line
    }
    if (event === null || typeof event !== "object" || !event.txn_id) continue;
    events.push(event);
  }
  return events;
}

// Reduce events to the most recent attempt per txn_id.
function latestAttempts(events) {
  const latest = new Map();
  for (const event of events) {
    const ts = Date.parse(event.ts);
    const current = latest.get(event.txn_id);
    // `>=` so that, on an identical timestamp, the later line wins.
    if (!current || ts >= current.ts) latest.set(event.txn_id, { ts, event });
  }
  return [...latest.values()].map((entry) => entry.event);
}

function reconcile(file = PAYMENTS_FILE) {
  const collected = latestAttempts(readEvents(file)).filter((e) => e.status === "success");
  const kobo = collected.reduce((sum, e) => sum + toKobo(e.amount), 0);
  return { count: collected.length, total: kobo / 100 };
}

function main() {
  const { count, total } = reconcile();
  const expected = parseInt(fs.readFileSync(EXPECTED_FILE, "utf8").trim(), 10);

  if (count !== expected) {
    console.log(`Check failed: counted ${count} successful payments, expected ${expected}.`);
    console.log("Something in the data isn't being handled the way the README describes.");
  } else {
    console.log(`Check passed: ${count} successful payments.`);
    console.log(`Your code: KOYA-${Math.round(total)}`);
  }
}

main();
