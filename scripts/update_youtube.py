import json, subprocess
from pathlib import Path
url="https://www.youtube.com/@onthewrongtrack/videos"
cmd=["yt-dlp","--flat-playlist","--playlist-end","100","--dump-single-json","--no-warnings",url]
result=subprocess.run(cmd,capture_output=True,text=True,check=True)
data=json.loads(result.stdout)
videos=[]
for item in data.get("entries",[]):
    if not item: continue
    vid=item.get("id") or item.get("url","").split("v=")[-1]
    if not vid or len(vid)!=11: continue
    videos.append({"id":vid,"title":item.get("title") or "Train Sim World video","date":item.get("upload_date") or ""})
if not videos: raise RuntimeError("No channel videos found; preserving existing feed")
Path("videos.json").write_text(json.dumps(videos,indent=2,ensure_ascii=False)+"\n")
print("Saved",len(videos),"videos")
