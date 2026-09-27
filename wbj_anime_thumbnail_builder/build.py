from __future__ import annotations

import base64
import concurrent.futures
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

CHANNEL_BASE = "https://www.youtube.com/@wbj_anime"
TARGETS = [
    ("videos", CHANNEL_BASE + "/videos"),
    ("streams", CHANNEL_BASE + "/streams"),
]

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
FINAL_HTML = OUTPUT_DIR / "wbj_anime_all_thumbnails.html"

ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0 Safari/537.36"
)

THUMB_URLS = [
    "https://i.ytimg.com/vi/{id}/mqdefault.jpg",
    "https://i.ytimg.com/vi/{id}/hqdefault.jpg",
    "https://i.ytimg.com/vi/{id}/0.jpg",
    "https://img.youtube.com/vi/{id}/mqdefault.jpg",
]


def collect_ids(label: str, url: str) -> tuple[list[str], int]:
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--flat-playlist",
        "--ignore-errors",
        "--no-warnings",
        "--print",
        "%(id)s",
        url,
    ]
    print(f"[collect] {label}: {url}", flush=True)
    p = subprocess.run(cmd, text=True, capture_output=True)
    ids = []
    for line in p.stdout.splitlines():
        value = line.strip()
        if ID_RE.fullmatch(value):
            ids.append(value)

    if p.stderr.strip():
        print(f"[collect:{label}:stderr]\n{p.stderr[-8000:]}", flush=True)

    print(f"[collect] {label}: rc={p.returncode}, ids={len(ids)}", flush=True)
    return ids, p.returncode


def unique_preserve_order(groups: list[list[str]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for video_id in group:
            if video_id not in seen:
                seen.add(video_id)
                out.append(video_id)
    return out


def looks_like_image(data: bytes, content_type: str | None) -> bool:
    if len(data) < 500:
        return False
    if content_type and content_type.lower().startswith("image/"):
        return True
    return data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n")


def fetch_thumbnail(video_id: str) -> tuple[str, bytes | None, str | None]:
    last_error = None

    for round_no in range(1, 5):
        for template in THUMB_URLS:
            url = template.format(id=video_id)
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Referer": "https://www.youtube.com/",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=25) as r:
                    data = r.read()
                    ctype = r.headers.get("Content-Type")
                    if looks_like_image(data, ctype):
                        return video_id, data, url
                    last_error = f"invalid image: bytes={len(data)} type={ctype} url={url}"
            except Exception as e:
                last_error = f"{type(e).__name__}: {e} url={url}"

        if round_no < 4:
            time.sleep(0.7 * round_no)

    print(f"[thumb:FAILED] {video_id}: {last_error}", flush=True)
    return video_id, None, None


def render_html(video_ids: list[str], thumbs: dict[str, bytes]) -> str:
    cards = []
    for video_id in video_ids:
        b64 = base64.b64encode(thumbs[video_id]).decode("ascii")
        cards.append(
            '<a class="thumb" href="https://www.youtube.com/watch?v='
            + html.escape(video_id, quote=True)
            + '" target="_blank" rel="noopener noreferrer">'
            + '<img loading="lazy" decoding="async" src="data:image/jpeg;base64,'
            + b64
            + '" alt=""></a>'
        )

    return """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title></title>
<style>
html,body{margin:0;padding:0;background:#000}
#grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;padding:4px}
.thumb{display:block;min-width:0}
.thumb img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover}
@media(max-width:600px){#grid{gap:2px;padding:2px}}
</style>
</head>
<body>
<div id="grid">
""" + "\n".join(cards) + """
</div>
<script>
const grid=document.getElementById('grid');
const items=[...grid.children];
for(let i=items.length-1;i>0;i--){
  const j=Math.floor(Math.random()*(i+1));
  [items[i],items[j]]=[items[j],items[i]];
}
for(const item of items) grid.appendChild(item);

let autoScrollId=null;
let direction=1;
let lastTs=0;
const speed=85;

function stopAutoScroll(){
  if(autoScrollId!==null){
    cancelAnimationFrame(autoScrollId);
    autoScrollId=null;
  }
  lastTs=0;
}

function tick(ts){
  if(autoScrollId===null) return;
  if(!lastTs) lastTs=ts;
  const dt=Math.min(50,ts-lastTs);
  lastTs=ts;
  scrollBy(0,direction*speed*dt/1000);

  const atBottom=innerHeight+scrollY>=document.documentElement.scrollHeight-2;
  const atTop=scrollY<=0;
  if((direction>0&&atBottom)||(direction<0&&atTop)){
    stopAutoScroll();
    return;
  }
  autoScrollId=requestAnimationFrame(tick);
}

function startAutoScroll(dir){
  direction=dir;
  if(autoScrollId===null){
    autoScrollId=requestAnimationFrame(tick);
  }
}

document.addEventListener('keydown',e=>{
  if(e.code!=='Space') return;
  const t=e.target;
  if(t&&(t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.isContentEditable)) return;
  e.preventDefault();

  const wanted=e.shiftKey?-1:1;
  if(autoScrollId!==null&&direction===wanted){
    stopAutoScroll();
  }else{
    stopAutoScroll();
    startAutoScroll(wanted);
  }
});
</script>
</body>
</html>
"""


def clean_output_except_final() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for p in OUTPUT_DIR.iterdir():
        if p == FINAL_HTML:
            continue
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if FINAL_HTML.exists():
        FINAL_HTML.unlink()

    collected: dict[str, list[str]] = {}
    returncodes: dict[str, int] = {}

    for label, url in TARGETS:
        ids, rc = collect_ids(label, url)
        collected[label] = ids
        returncodes[label] = rc

    bad_sources = [k for k, rc in returncodes.items() if rc != 0]
    if bad_sources:
        print(json.dumps({
            "channel_url": CHANNEL_BASE,
            "complete": False,
            "reason": "yt-dlp source collection failed",
            "failed_sources": bad_sources,
            "collection_counts": {k: len(v) for k, v in collected.items()},
            "returncodes": returncodes,
        }, ensure_ascii=False, indent=2))
        return 2

    video_ids = unique_preserve_order([collected["videos"], collected["streams"]])
    if not video_ids:
        print(json.dumps({
            "channel_url": CHANNEL_BASE,
            "complete": False,
            "reason": "no video ids collected",
            "collection_counts": {k: len(v) for k, v in collected.items()},
        }, ensure_ascii=False, indent=2))
        return 3

    print(f"[dedupe] unique ids={len(video_ids)}", flush=True)

    thumbs: dict[str, bytes] = {}
    failed: list[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(fetch_thumbnail, vid): vid for vid in video_ids}
        done = 0
        total = len(futures)
        for fut in concurrent.futures.as_completed(futures):
            video_id, data, _url = fut.result()
            done += 1
            if data is None:
                failed.append(video_id)
            else:
                thumbs[video_id] = data
            if done % 100 == 0 or done == total:
                print(f"[thumb] {done}/{total} ok={len(thumbs)} failed={len(failed)}", flush=True)

    report = {
        "channel_url": CHANNEL_BASE,
        "shorts_included": False,
        "collection_sources": {
            "videos": {"returncode": returncodes["videos"], "count": len(collected["videos"])},
            "streams": {"returncode": returncodes["streams"], "count": len(collected["streams"])},
        },
        "unique_video_ids": len(video_ids),
        "embedded_thumbnails": len(thumbs),
        "failed_thumbnails": len(failed),
        "complete": len(failed) == 0 and len(thumbs) == len(video_ids),
    }

    if failed:
        report["failed_ids"] = failed
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        return 4

    html_text = render_html(video_ids, thumbs)
    FINAL_HTML.write_text(html_text, encoding="utf-8")
    clean_output_except_final()

    size = FINAL_HTML.stat().st_size
    report["html_bytes"] = size
    report["output_file"] = str(FINAL_HTML.relative_to(ROOT))
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)

    if list(OUTPUT_DIR.iterdir()) != [FINAL_HTML]:
        print("[verify] output directory contains unexpected files", flush=True)
        return 5

    print(f"[complete] {FINAL_HTML} ({size} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
