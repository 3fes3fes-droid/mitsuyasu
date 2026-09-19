#!/usr/bin/env python3
import base64
import concurrent.futures
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CHANNEL_BASE = "https://www.youtube.com/@sarabaOYC"
TARGETS = [
    ("videos", CHANNEL_BASE + "/videos"),
    ("shorts", CHANNEL_BASE + "/shorts"),
    ("streams", CHANNEL_BASE + "/streams"),
    ("channel", CHANNEL_BASE),
]
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
OUT = Path("sarabaoyc_thumbnail_builder/output")
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "build.log"

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def collect_one(label, url):
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--ignore-errors",
        "--no-warnings",
        "--print", "%(id)s",
        url,
    ]
    log(f"COLLECT START {label}: {url}")
    p = subprocess.run(cmd, text=True, capture_output=True)
    ids, seen = [], set()
    for raw in p.stdout.splitlines():
        v = raw.strip()
        if VIDEO_ID_RE.fullmatch(v) and v not in seen:
            seen.add(v)
            ids.append(v)
    log(f"COLLECT END {label}: rc={p.returncode} ids={len(ids)}")
    if p.stderr.strip():
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"--- yt-dlp stderr {label} ---\n{p.stderr}\n")
    return {"label": label, "url": url, "returncode": p.returncode, "ids": ids}

def collect_all():
    results = [collect_one(label, url) for label, url in TARGETS]
    union, seen = [], set()
    for preferred in ("videos", "shorts", "streams", "channel"):
        r = next(x for x in results if x["label"] == preferred)
        for v in r["ids"]:
            if v not in seen:
                seen.add(v)
                union.append(v)
    if not union:
        raise RuntimeError("No video IDs were collected.")
    successful_explicit_tabs = [
        r for r in results
        if r["label"] in {"videos", "shorts", "streams"} and r["returncode"] == 0
    ]
    if not successful_explicit_tabs:
        raise RuntimeError("All explicit YouTube tab collections failed.")

    (OUT / "video_ids.txt").write_text("\n".join(union) + "\n", encoding="utf-8")
    details = {
        r["label"]: {
            "returncode": r["returncode"],
            "count": len(r["ids"]),
            "url": r["url"],
        }
        for r in results
    }
    (OUT / "collection.json").write_text(
        json.dumps({"unique_count": len(union), "sources": details}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log("UNIQUE VIDEO IDS: " + str(len(union)))
    return union, details

def fetch_url(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        ctype = (r.headers.get("Content-Type") or "").lower()
        return data, ctype

def get_thumbnail(video_id):
    candidates = [
        (f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg", "image/jpeg"),
        (f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg", "image/jpeg"),
        (f"https://i.ytimg.com/vi/{video_id}/0.jpg", "image/jpeg"),
        (f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg", "image/jpeg"),
    ]
    errors = []
    for attempt in range(1, 5):
        for url, fallback_mime in candidates:
            try:
                data, ctype = fetch_url(url)
                if len(data) >= 500 and ("image/" in ctype or data[:3] == b"\xff\xd8\xff"):
                    mime = ctype.split(";")[0] if "image/" in ctype else fallback_mime
                    return video_id, mime, base64.b64encode(data).decode("ascii"), url, None
                errors.append(f"{url}: invalid image ({len(data)} bytes, {ctype})")
            except Exception as e:
                errors.append(f"{url}: {type(e).__name__}: {e}")
        time.sleep(min(1.5 * attempt, 5))
    return video_id, None, None, None, " | ".join(errors[-8:])

def download_all(ids):
    images, failures = {}, {}
    total = len(ids)
    log(f"THUMBNAIL DOWNLOAD START: {total}")
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(get_thumbnail, v): v for v in ids}
        for fut in concurrent.futures.as_completed(futures):
            video_id, mime, b64, source, err = fut.result()
            completed += 1
            if b64:
                images[video_id] = {"mime": mime, "b64": b64, "source": source}
            else:
                failures[video_id] = err
            if completed % 100 == 0 or completed == total:
                log(f"THUMBNAIL PROGRESS: {completed}/{total} success={len(images)} fail={len(failures)}")

    (OUT / "failed_ids.txt").write_text(
        "\n".join(f"{k}\t{v}" for k, v in failures.items()) + ("\n" if failures else ""),
        encoding="utf-8",
    )
    log(f"THUMBNAIL DOWNLOAD END: success={len(images)} fail={len(failures)}")
    return images, failures

def build_html(ids, images):
    cards = []
    for video_id in ids:
        img = images[video_id]
        cards.append(
            '<a class="thumb" href="https://www.youtube.com/watch?v=' + video_id +
            '" target="_blank" rel="noopener noreferrer"><img loading="lazy" decoding="async" src="data:' +
            img["mime"] + ';base64,' + img["b64"] + '" alt=""></a>'
        )

    doc = """<!doctype html>
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
<div id="grid">__CARDS__</div>
<script>
(() => {
  const g = document.getElementById('grid');
  const a = Array.from(g.children);
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  const f = document.createDocumentFragment();
  a.forEach(x => f.appendChild(x));
  g.appendChild(f);
  addEventListener('keydown', e => {
    if (e.code !== 'Space') return;
    e.preventDefault();
    scrollBy({top:(e.shiftKey?-1:1)*innerHeight*0.9,behavior:'smooth'});
  }, {passive:false});
})();
</script>
</body>
</html>""".replace("__CARDS__", "".join(cards))
    path = OUT / "sarabaoyc_all_thumbnails.html"
    path.write_text(doc, encoding="utf-8")
    log(f"HTML WRITTEN: {path} bytes={path.stat().st_size}")
    return path

def main():
    if LOG.exists():
        LOG.unlink()
    ids, details = collect_all()
    images, failures = download_all(ids)
    report = {
        "channel_url": CHANNEL_BASE,
        "unique_video_ids": len(ids),
        "embedded_thumbnails": len(images),
        "failed_thumbnails": len(failures),
        "collection_sources": details,
        "complete": len(failures) == 0 and len(images) == len(ids),
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        log("BUILD FAILED: one or more thumbnails could not be embedded.")
        raise SystemExit(2)
    build_html(ids, images)
    log("BUILD COMPLETE: all collected video IDs have embedded thumbnails.")

if __name__ == "__main__":
    main()
