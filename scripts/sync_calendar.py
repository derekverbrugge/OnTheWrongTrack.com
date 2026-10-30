"""Sync existing website designs from the IFTTT Google Calendar."""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

CALENDAR_ID = "35751650b61b50bb6deeafa24cc8d2274d9e6e8e1de7d0aa7ed983ff40eea4f2@group.calendar.google.com"
FILE = Path(__file__).resolve().parents[1] / "designs.json"

def post(url, data):
    request = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def access_token():
    data = post("https://oauth2.googleapis.com/token", {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    })
    return data["access_token"]

def events(token):
    now = datetime.now(timezone.utc)
    params = {
        "timeMin": (now - timedelta(days=730)).isoformat(),
        "timeMax": (now + timedelta(days=1095)).isoformat(),
        "singleEvents": "true",
        "maxResults": "2500",
        "showDeleted": "false",
    }
    while True:
        url = "https://www.googleapis.com/calendar/v3/calendars/" + urllib.parse.quote(CALENDAR_ID, safe="") + "/events?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=60) as response:
            page = json.load(response)
        yield from page.get("items", [])
        if not page.get("nextPageToken"):
            break
        params["pageToken"] = page["nextPageToken"]

def main():
    designs = json.loads(FILE.read_text(encoding="utf-8"))
    by_url = {d.get("url"): d for d in designs}
    changes = 0
    for event in events(access_token()):
        description = re.sub(r"<[^>]+>", "", event.get("description", ""))
        match = re.search(r"https://creatorsclub\\.dovetailgames\\.com/creations/\\d+", description)
        if not match or match.group(0) not in by_url:
            continue
        design = by_url[match.group(0)]
        title = description.splitlines()[0].split("#")[0].strip()
        modified = event.get("updated", "")
        if not title or not modified:
            continue
        old_modified = design.get("calendar_modified_at", "")
        if modified <= old_modified:
            continue
        design["title"] = title
        design["calendar_modified_at"] = modified
        design["updated_at"] = modified
        if event.get("summary", "").startswith("https://"):
            design["image"] = event["summary"]
        changes += 1
    if changes:
        designs.sort(key=lambda d: d.get("updated_at") or d.get("calendar_modified_at") or "", reverse=True)
        FILE.write_text(json.dumps(designs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {changes} designs")

if __name__ == "__main__":
    main()
