"""Populate the site using only Train Sim World playlists, never channel-wide uploads."""
import json
import re
import subprocess
from pathlib import Path

CHANNEL = "https://www.youtube.com/@onthewrongtrack"
ROOT = Path(__file__).resolve().parents[1]

def extract(url):
    result = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--dump-single-json", "--no-warnings", url],
        text=True, capture_output=True, check=True, timeout=180
    )
    return json.loads(result.stdout)

def main():
    listing = extract(CHANNEL + "/playlists")
    playlists = []
    for entry in listing.get("entries", []):
        if not entry:
            continue
        title = entry.get("title", "")
        if not re.search(r"train\s*sim\s*world|\btsw\s*\d*\b", title, re.I):
            continue
        playlist_id = entry.get("id", "")
        url = entry.get("url") or entry.get("webpage_url") or ""
        if playlist_id.startswith("PL") or playlist_id.startswith("UU"):
            url = "https://www.youtube.com/playlist?list=" + playlist_id
        elif url and not url.startswith("http"):
            url = "https://www.youtube.com/playlist?list=" + url
        if url:
            playlists.append((title, url))
    if not playlists:
        raise RuntimeError("No TSW playlists discovered; preserving the previous feed.")

    seen = set()
    videos = []
    for title, url in playlists:
        playlist = extract(url)
        for entry in playlist.get("entries", []):
            if not entry:
                continue
            video_id = entry.get("id", "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) or video_id in seen:
                continue
            seen.add(video_id)
            videos.append({"id": video_id, "title": entry.get("title") or "Train Sim World video",
                           "date": entry.get("upload_date") or ""})
    if not videos:
        raise RuntimeError("TSW playlists contained no videos; preserving the previous feed.")
    (ROOT / "videos.json").write_text(json.dumps(videos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(videos)} videos from {len(playlists)} TSW playlists.")

if __name__ == "__main__":
    main()
