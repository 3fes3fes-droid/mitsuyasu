# -*- coding: utf-8 -*-
"""令和ロマン / つべさむねいる single-file thumbnail builder."""
import base64, concurrent.futures, html, json, os, pathlib, random, re, sys, tempfile, time
from collections import OrderedDict
from datetime import datetime, timezone

import requests
import yt_dlp

HANDLE = "official-reiwaroman"
BASE = f"https://www.youtube.com/@{HANDLE}"
TABS = ("videos", "shorts", "streams")
WORK = pathlib.Path(tempfile.gettempdir()) / "official_reiwaroman_thumbnails_work"
WORK.mkdir(exist_ok=True)
DOWNLOAD = pathlib.Path.home() / "Downloads"
DOWNLOAD.mkdir(exist_ok=True)
OUT = DOWNLOAD / "official_reiwaroman_all_thumbnails.html"
LOG = WORK / "report.json"
ID_PATTERN = re.compile(r"^[\w-]{11}$", re.ASCII)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"}

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def extract(tab):
    url = BASE + ("/" + tab if tab != "channel" else "")
    opts = {
        "quiet": True, "no_warnings": True, "ignoreerrors": True,
        "extract_flat": "in_playlist", "skip_download": True, "nocheckcertificate": False,
        "socket_timeout": 25, "retries": 3, "extractor_retries": 3,
        "compat_opts": {"no-youtube-unavailable-videos"},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        raw = ydl.extract_info(url, download=False)
    result = []
    for e in (raw.get("entries") or []) if isinstance(raw, dict) else []:
        if not isinstance(e, dict):
            continue
        vid = (e.get("id") or "").strip()
        if not ID_PATTERN.match(vid):
            u = str(e.get("url") or "")
            m = re.search(r"(?:v=|youtu\.be/|shorts/|/watch/)([\w-]{11})(?:\b|$)", u, re.ASCII)
            vid = m.group(1) if m else ""
        if ID_PATTERN.match(vid):
            result.append({"id": vid, "title": e.get("title") or "", "kind": tab})
    return result

def collect_all():
    entries = OrderedDict()
    counts, errors = {}, {}
    for tab in (*TABS, "channel"):
        print("EXTRACTING", tab, flush=True)
        try:
            items = extract(tab)
            counts[tab] = len(items)
            print("EXTRACTED", tab, len(items), flush=True)
            for it in items:
                entries.setdefault(it["id"], it)
        except Exception as exc:
            counts[tab] = -1
            errors[tab] = repr(exc)
            print("EXTRACT_ERROR", tab, repr(exc)[:360], flush=True)
        save_json(WORK / "video_entries_partial.json", list(entries.values()))
    return list(entries.values()), counts, errors

def get_thumb(video):
    vid = video["id"]
    targets = [
        f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
        f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        f"https://i.ytimg.com/vi/{vid}/0.jpg",
        f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
    ]
    last = ""
    for round_num in range(4):
        for link in targets:
            try:
                r = requests.get(link, headers=HEADERS, timeout=(10, 25))
                if r.status_code == 200 and len(r.content) >= 500 and (r.content[:3] == b"\xff\xd8\xff" or r.headers.get("Content-Type", "").lower().startswith("image/")):
                    mime = "image/jpeg" if r.content[:3] == b"\xff\xd8\xff" else r.headers.get("Content-Type", "image/jpeg").split(";")[0]
                    return vid, base64.b64encode(r.content).decode("ascii"), mime, None
                last = f"{r.status_code} bytes={len(r.content)}"
            except Exception as e:
                last = str(e)[:160]
        time.sleep((round_num + 1) * 1.5 + random.random() * 0.3)
    return vid, None, None, last

def render(items, thumbnails):
    styles = """html,body{margin:0;padding:0;background:#000;overscroll-behavior-y:none}
#grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;padding:4px}
.thumb{display:block;min-width:0;overflow:hidden;background:#050505;outline-offset:-2px}
.thumb img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover}
@media(max-width:600px){#grid{gap:2px;padding:2px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}"""
    js = """(()=>{'use strict';
const grid=document.getElementById('grid');
const items=Array.from(grid.children);
for(let i=items.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[items[i],items[j]]=[items[j],items[i]]}
grid.replaceChildren(...items);
let playing=false, direction=1, speed=95, last=0, frame=0;
const end=()=>Math.max(0,document.documentElement.scrollHeight-innerHeight);
function stop(){playing=false;last=0;if(frame)cancelAnimationFrame(frame);frame=0}
function tick(now){if(!playing)return;if(last){const d=Math.min((now-last)/1000,0.1);const next=Math.min(end(),Math.max(0,scrollY+direction*speed*d));scrollTo(0,next);if((direction>0&&next>=end())||(direction<0&&next<=0)){stop();return}}last=now;frame=requestAnimationFrame(tick)}
function toggle(dir){if(playing&&direction===dir){stop();return}stop();direction=dir;playing=true;frame=requestAnimationFrame(tick)}
document.addEventListener('keydown',e=>{if(e.code==='Space'){e.preventDefault();if(!e.repeat)toggle(e.shiftKey?-1:1)}
else if(e.code==='ArrowUp'){e.preventDefault();speed=Math.min(2000,speed+35)}
else if(e.code==='ArrowDown'){e.preventDefault();speed=Math.max(15,speed-35)}});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop()});
})();"""
    with OUT.open("w", encoding="utf-8") as f:
        f.write('<!doctype html>\n<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n')
        f.write('<title>令和ロマン｜つべさむねいる</title><style>'+styles+'</style></head><body><main id="grid">\n')
        for e in items:
            vid = e["id"]
            obj = thumbnails.get(vid)
            if not obj:
                continue
            encoded, mime = obj
            f.write('<a class="thumb" href="https://www.youtube.com/watch?v='+vid+'" target="_blank" rel="noopener noreferrer" aria-label="YouTube動画を開く"><img loading="lazy" decoding="async" alt="" src="data:'+mime+';base64,'+encoded+'"></a>\n')
        f.write('</main><script>'+js+'</script></body></html>\n')

def main():
    start=time.time()
    entries, counts, extract_errors = collect_all()
    if not entries:
        raise RuntimeError("動画IDが0件。偽の完成HTMLは作成しない。")
    save_json(WORK / "video_entries.json", entries)
    print("UNIQUE_IDS", len(entries), flush=True)
    pics={}
    failed={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(get_thumb,e): e["id"] for e in entries}
        for n, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                vid, pic, mime, error=fut.result()
                if pic:
                    pics[vid]=(pic,mime)
                else:
                    failed[vid]=error
            except Exception as ex:
                failed[futures[fut]]=repr(ex)
            if n%50==0 or n==len(entries):
                print("IMAGES", n, "/", len(entries), "OK", len(pics), "FAIL", len(failed), flush=True)
    print("RENDER", flush=True)
    render(entries, pics)
    report={
        "channel":BASE, "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "tab_counts": counts, "tab_errors":extract_errors, "unique_ids":len(entries),
        "embedded_images":len(pics),"failed_count":len(failed),"failed_ids":failed,
        "complete":not failed and not extract_errors and all(v>=0 for v in counts.values()),
        "output_path":str(OUT),"output_bytes":OUT.stat().st_size,"elapsed_seconds":round(time.time()-start,1),
    }
    save_json(LOG,report)
    print("REPORT",json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__": main()
