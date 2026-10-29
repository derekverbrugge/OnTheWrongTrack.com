"""Fetch the actual On The Wrong Track YouTube channel avatar for the website."""
import io
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image
from yt_dlp import YoutubeDL

ROOT = Path(__file__).resolve().parents[1]
CHANNEL = "https://www.youtube.com/@OnTheWrongTrack"
with YoutubeDL({"extract_flat": True, "playlistend": 1, "quiet": True, "no_warnings": True}) as ydl:
    info = ydl.extract_info(CHANNEL, download=False)
thumbs = info.get("thumbnails") or []
square = [t for t in thumbs if t.get("url") and
          (not t.get("width") or not t.get("height") or abs(t["width"]-t["height"]) < 5) and
          ("yt3." in t["url"] or "googleusercontent.com" in t["url"])]
if not square:
    raise RuntimeError("Could not identify the channel's square avatar; no changes made")
url = square[-1]["url"]
with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
    raw = response.read()
im = Image.open(io.BytesIO(raw)).convert("RGB")
if im.width < 50 or im.height < 50 or abs(im.width-im.height)>5:
    raise RuntimeError("Downloaded image was not a square channel avatar")
target = ROOT / "assets" / "youtube-logo.jpg"
target.parent.mkdir(parents=True, exist_ok=True)
im.save(target, format="JPEG", quality=92, optimize=True)
print(f"Saved channel avatar: {im.width}x{im.height}")
