"""Synchronize the website's design gallery from a private Google Calendar iCal feed.

Set CALENDAR_ICAL_URL as a GitHub Actions repository secret. Never commit the URL.
Only events with a Creators Club link and Dovetail screenshot are published.
"""
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen
from icalendar import Calendar

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "designs.json"
URL_RE = re.compile(r"https?://creatorsclub\.dovetailgames\.com/(?:creations|mods)/[0-9]+", re.I)
IMAGE_RE = re.compile(r"https?://screenshot-prod\.dovetailgames\.net/[a-zA-Z0-9-]+", re.I)

def main():
    feed_url = os.environ.get("CALENDAR_ICAL_URL", "").strip()
    if not feed_url.startswith("https://"):
        sys.exit("Set the CALENDAR_ICAL_URL repository secret to your private Google Calendar iCal URL.")
    request = Request(feed_url, headers={"User-Agent": "OnTheWrongTrack-CalendarSync/1.0"})
    with urlopen(request, timeout=35) as response:
        raw = response.read()
    calendar = Calendar.from_ical(raw)
    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else []
    previous_dates = {item["url"]: item.get("date", "") for item in previous}
    designs = {}
    for event in calendar.walk("VEVENT"):
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        description = str(event.get("DESCRIPTION", ""))
        summary = str(event.get("SUMMARY", ""))
        url_match = URL_RE.search(description + " " + summary)
        image_match = IMAGE_RE.search(summary + " " + description)
        if not url_match or not image_match:
            continue
        url = url_match.group(0)
        # Description's first line is the human-readable design name.
        title = next((line.strip() for line in description.splitlines()
                      if line.strip() and not line.lstrip().startswith(("http", "#"))), "")
        title = re.split(r"\s+#(?:TSW|USA|Germany|BR\d)", title, maxsplit=1, flags=re.I)[0].strip()
        if not title:
            title = "Train Sim World design"
        start = event.get("DTSTART")
        dt = start.dt if start else None
        event_date = dt.date().isoformat() if isinstance(dt, datetime) else dt.isoformat() if isinstance(dt, date) else ""
        designs[url] = {
            "title": title,
            "date": previous_dates.get(url) or event_date,
            "url": url,
            "image": image_match.group(0),
        }
    if not designs:
        sys.exit("No matching TSW designs found; preserving existing gallery.")
    result = sorted(designs.values(), key=lambda item: (item["date"], item["title"]))
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Synced {len(result)} designs from calendar (added/updated/removed as needed).")

if __name__ == "__main__":
    main()
