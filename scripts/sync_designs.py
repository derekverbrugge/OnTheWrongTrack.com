"""Synchronize TSW designs from a private Google Calendar iCal feed.

The calendar is authoritative. GitHub Actions runs this script automatically.
Never commit CALENDAR_ICAL_URL: configure it as an Actions secret.
"""
import html
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from icalendar import Calendar

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "designs.json"
LINK_RE = re.compile(r"https?://creatorsclub\.dovetailgames\.com/(?:creations|mods)/\d+", re.I)
IMAGE_RE = re.compile(r"https?://screenshot-prod\.dovetailgames\.net/[\w-]+", re.I)
TAGS_RE = re.compile(r"<[^>]*>")

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
    def handle_data(self, data):
        self.text.append(data)
    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "div"):
            self.text.append(" ")

def clean_text(value):
    # Decode entities without interpreting ordinary text as HTML markup.
    value = html.unescape(html.unescape(str(value)))
    value = re.sub(r"<br\\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"</?(?:p|div|span|b|strong|em|i)(?:\\s+[^>]*)?>", " ", value, flags=re.I)
    value = re.sub(r"\\s+", " ", value).strip()
    # Correct a malformed punctuation sequence; never invent punctuation.
    return re.sub(r"\\.;(?=\\s|$)", ".", value)


def timestamp(prop):
    if not prop:
        return ""
    dt = prop.dt
    if isinstance(dt, datetime):
        return dt.replace(tzinfo=dt.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()
    return ""

def event_title(description):
    for line in description.splitlines():
        if not line.strip() or line.lstrip().startswith(("http", "#")):
            continue
        title = clean_text(re.split(r"\s+#(?:TSW|USA|Germany|BR\d)", line, maxsplit=1, flags=re.I)[0])
        if title:
            return title
    return "Train Sim World design"

def main():
    feed_url = os.environ.get("CALENDAR_ICAL_URL", "").strip()
    if not feed_url.startswith("https://"):
        sys.exit("CALENDAR_ICAL_URL secret is missing or invalid.")
    with urlopen(Request(feed_url, headers={"User-Agent": "OnTheWrongTrack-CalendarSync/1.0"}), timeout=35) as response:
        calendar = Calendar.from_ical(response.read())

    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else []
    previous_by_url = {d["url"]: d for d in previous}
    designs = {}
    for event in calendar.walk("VEVENT"):
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        description, summary = str(event.get("DESCRIPTION", "")), str(event.get("SUMMARY", ""))
        link = LINK_RE.search(description + " " + summary)
        image = IMAGE_RE.search(summary + " " + description)
        if not link or not image:
            continue
        url = link.group(0)
        title = event_title(description)
        old = previous_by_url.get(url, {})
        start = event.get("DTSTART")
        dt = start.dt if start else None
        scheduled = dt.date().isoformat() if isinstance(dt, datetime) else dt.isoformat() if isinstance(dt, date) else ""
        # LAST-MODIFIED is the calendar edit time; DTSTAMP is not a reliable edit signal.
        modified = timestamp(event.get("LAST-MODIFIED"))
        changed = not old or old.get("title") != title or old.get("image") != image or old.get("url") != url
        # Preserve an existing change timestamp across repeat runs.
        if changed:
            updated = modified or datetime.now(timezone.utc).isoformat()
        elif modified and modified > old.get("calendar_modified_at", ""):
            updated = modified
        else:
            updated = old.get("updated_at", "") or modified
        candidate = {
            "title": title, "date": old.get("date") or scheduled,
            "url": url, "image": image.group(0),
            "updated_at": updated, "calendar_modified_at": modified,
        }
        current = designs.get(url)
        if not current or candidate["updated_at"] > current["updated_at"]:
            designs[url] = candidate

    if not designs:
        sys.exit("No matching TSW designs; preserving previous gallery.")
    # Most recently changed entries first, on both the homepage and Designs page.
    result = sorted(designs.values(), key=lambda d: (d["updated_at"], d["url"]), reverse=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Synced {len(result)} TSW designs, newest edits first.")

if __name__ == "__main__":
    main()
