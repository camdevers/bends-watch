#!/usr/bin/env python3
"""
Watches SeatGeek for The Bends at Irving Plaza (NYC) on Nov 14, 2026
and sends a phone push notification (via ntfy.sh) when the lowest
listed price drops to or below TARGET_PRICE.

Setup:
  1. Get a free SeatGeek client ID: https://seatgeek.com/account/develop
  2. Install the free ntfy app on your phone, subscribe to a private
     topic name (make it long/random), and put it in NTFY_TOPIC below.
  3. pip install requests
  4. Run:  python bends_ticket_watch.py
     (loops forever; or run once from cron with --once)
"""

import json
import os
import sys
import time
import requests

# ---- SETTINGS (override with environment variables) ----
SEATGEEK_CLIENT_ID = os.environ.get("SEATGEEK_CLIENT_ID", "YOUR_CLIENT_ID")
TARGET_PRICE = float(os.environ.get("TARGET_PRICE", "60"))  # alert when lowest <= this (USD)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "bends-irving-plaza-change-me-123")
CHECK_EVERY_MINUTES = 30
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
# --------------------------------------------------------

EVENT_DATE = "2026-11-14"
SEARCH_QUERY = "The Bends"
VENUE_KEYWORD = "irving plaza"

API = "https://api.seatgeek.com/2/events"


def find_event():
    params = {
        "client_id": SEATGEEK_CLIENT_ID,
        "q": SEARCH_QUERY,
        "datetime_local.gte": f"{EVENT_DATE}T00:00:00",
        "datetime_local.lte": f"{EVENT_DATE}T23:59:59",
        "per_page": 25,
    }
    r = requests.get(API, params=params, timeout=20)
    r.raise_for_status()
    for ev in r.json().get("events", []):
        venue = (ev.get("venue", {}).get("name") or "").lower()
        if VENUE_KEYWORD in venue:
            return ev
    return None


def notify(title, message, url=None):
    headers = {"Title": title, "Priority": "high", "Tags": "tickets"}
    if url:
        headers["Click"] = url
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode(),
                  headers=headers, timeout=20)


def check(last_alerted):
    ev = find_event()
    if not ev:
        print("Event not found on SeatGeek yet.")
        return last_alerted
    stats = ev.get("stats", {})
    low = stats.get("lowest_price")
    print(f"{time.strftime('%H:%M')} lowest price: {low}")
    if low is not None and low <= TARGET_PRICE and low != last_alerted:
        notify(
            f"The Bends tix: ${low}",
            f"Lowest price is now ${low} (target ${TARGET_PRICE}) "
            f"for {ev.get('title')} at Irving Plaza.",
            ev.get("url"),
        )
        return low
    return last_alerted


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get("last_alerted")
    except Exception:
        return None


def save_state(last):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_alerted": last}, f)


def main():
    once = "--once" in sys.argv
    last = load_state()
    while True:
        try:
            last = check(last)
            save_state(last)
        except Exception as e:
            print("Error:", e)
        if once:
            break
        time.sleep(CHECK_EVERY_MINUTES * 60)


if __name__ == "__main__":
    main()
