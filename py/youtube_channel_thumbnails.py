#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import concurrent.futures
import html
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
HANDLE_RE = re.compile(r"@([A-Za-z0-9._-]+)")

THUMBNAIL_CANDIDATES = (
    "https://i.ytimg.com/vi/{id}/mqdefault.jpg",
    "https://i.ytimg.com/vi/{id}/hqdefault.jpg",
    "https://i.ytimg.com/vi/{id}/0.jpg",
    "https://img.youtube.com/vi/{id}/mqdefault.jpg",
)

def ensure_ytdlp():
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        print("yt-dlp がないため自動インストールします。", flush=True)
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp[default]"],
            check=True,
        )

def normalize_channel_base(url: str) -> str:
    url = url.strip()
    if "://" not in url:
        url = "https://" + url.lstrip("/")

    parsed = urlparse(url)
    url = parsed._replace(query="", fragment="").geturl().rstrip("/")

    for suffix in ("/videos", "/shorts", "/streams", "/featured"):
        if url.endswith(suffix):
            url = url[:-len(suffix)]
            break
    return url

def slug_from_url(url: str) -> str:
    m = HANDLE_RE.search(url)
    if m:
        raw = m.group(1)
    else:
        path = urlparse(url).path.strip("/")
        raw = path.split("/")[-1] if path else "youtube_channel"
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_-").lower()
    return slug or "youtube_channel"

def collect_ids(label: str, url: str):
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--ignore-errors",
        "--no-warnings",
        "--print", "%(id)s",
        url,
    ]
    print(f"[{label}] 取得開始: {url}", flush=True)
    p = subprocess.run(cmd, text=True, capture_output=True)
    ids = []
    seen = set()
    for line in p.stdout.splitlines():
        video_id = line.strip()
        if VIDEO_ID_RE.fullmatch(video_id) and video_id not in seen:
            seen.add(video_id)
            ids.append(video_id)
    print(f"[{label}] {len(ids)}件 / rc={p.returncode}", flush=True)
    if p.stderr.strip():
        print(p.stderr.strip(), file=sys.stderr)
    return ids, p.returncode

def collect_all(channel_base: str):
    # Shorts は取得対象外。通常動画と配信だけを統合する。
    targets = [
        ("videos", channel_base + "/videos"),
        ("streams", channel_base + "/streams"),
    ]

    collected = []
    source_counts = {}
    source_rc = {}

    for label, url in targets:
        ids, rc = collect_ids(label, url)
        source_counts[label] = len(ids)
        source_rc[label] = rc
        collected.extend(ids)

    unique = []
    seen = set()
    for video_id in collected:
        if video_id not in seen:
            seen.add(video_id)
            unique.append(video_id)

    if not unique:
        raise RuntimeError(
            "通常動画・配信から動画IDを取得できませんでした。"
            " Shorts は仕様により取得しません。"
        )

    return unique, source_counts, source_rc

def fetch_image(url: str, timeout=20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        ctype = (r.headers.get("Content-Type") or "").lower()
        return data, ctype

def fetch_thumbnail(video_id: str):
    errors = []
    for round_no in range(1, 5):
        for template in THUMBNAIL_CANDIDATES:
            url = template.format(id=video_id)
            try:
                data, ctype = fetch_image(url)
                is_image = "image/" in ctype or data[:3] == b"\xff\xd8\xff"
                if len(data) >= 500 and is_image:
                    mime = ctype.split(";")[0] if "image/" in ctype else "image/jpeg"
                    return video_id, mime, base64.b64encode(data).decode("ascii"), None
                errors.append(f"{url}: invalid image {len(data)} bytes {ctype}")
            except Exception as e:
                errors.append(f"{url}: {type(e).__name__}: {e}")
        time.sleep(min(round_no * 1.25, 4))
    return video_id, None, None, " | ".join(errors[-8:])

def fetch_all_thumbnails(video_ids, workers=16):
    images = {}
    failures = {}
    total = len(video_ids)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_thumbnail, video_id): video_id for video_id in video_ids}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            video_id, mime, b64, error = future.result()
            done += 1
            if b64:
                images[video_id] = (mime, b64)
            else:
                failures[video_id] = error
            if done % 100 == 0 or done == total:
                print(
                    f"サムネイル {done}/{total} 成功={len(images)} 失敗={len(failures)}",
                    flush=True,
                )

    return images, failures

def build_html(video_ids, images):
    cards = []
    for video_id in video_ids:
        mime, b64 = images[video_id]
        cards.append(
            '<a class="thumb" href="https://www.youtube.com/watch?v='
            + video_id
            + '" target="_blank" rel="noopener noreferrer">'
            + '<img loading="lazy" decoding="async" src="data:'
            + html.escape(mime, quote=True)
            + ";base64,"
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
<div id="grid">__CARDS__</div>
<script>
(() => {
  const grid = document.getElementById('grid');

  const items = Array.from(grid.children);
  for (let i = items.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [items[i], items[j]] = [items[j], items[i]];
  }
  const fragment = document.createDocumentFragment();
  items.forEach(item => fragment.appendChild(item));
  grid.appendChild(fragment);

  let running = false;
  let speed = 80; // px / second
  const minSpeed = 20;
  const maxSpeed = 600;
  const step = 20;
  let previous = null;

  function frame(now) {
    if (previous === null) previous = now;
    const dt = Math.min((now - previous) / 1000, 0.1);
    previous = now;

    if (running) {
      const before = scrollY;
      scrollBy(0, speed * dt);
      if (scrollY === before && scrollY + innerHeight >= document.documentElement.scrollHeight - 1) {
        running = false;
      }
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  addEventListener('keydown', e => {
    if (e.code === 'Space') {
      e.preventDefault();
      running = !running;
      previous = performance.now();
      return;
    }

    if (e.code === 'ArrowUp') {
      e.preventDefault();
      speed = Math.min(maxSpeed, speed + step);
      return;
    }

    if (e.code === 'ArrowDown') {
      e.preventDefault();
      speed = Math.max(minSpeed, speed - step);
    }
  }, {passive:false});
})();
</script>
</body>
</html>""".replace("__CARDS__", "".join(cards))

def main():
    parser = argparse.ArgumentParser(
        description="YouTubeチャンネルの通常動画＋配信を、Base64サムネイルHTMLへ変換します。Shortsは除外します。"
    )
    parser.add_argument("channel_url", help="YouTubeチャンネルURL")
    parser.add_argument(
        "-o", "--output",
        help="出力HTMLパス。省略時は <slug>_all_thumbnails.html",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=16,
        help="サムネイル取得並列数。既定値16",
    )
    args = parser.parse_args()

    ensure_ytdlp()

    channel_base = normalize_channel_base(args.channel_url)
    slug = slug_from_url(channel_base)
    output = Path(args.output) if args.output else Path(f"{slug}_all_thumbnails.html")

    video_ids, source_counts, source_rc = collect_all(channel_base)
    print(f"重複除去後: {len(video_ids)}件", flush=True)

    images, failures = fetch_all_thumbnails(video_ids, max(1, args.workers))

    if failures:
        print("", file=sys.stderr)
        print(f"取得失敗: {len(failures)}件", file=sys.stderr)
        for video_id, error in failures.items():
            print(f"{video_id}\t{error}", file=sys.stderr)
        raise SystemExit(2)

    if len(images) != len(video_ids):
        raise RuntimeError(
            f"件数不一致: IDs={len(video_ids)} images={len(images)}"
        )

    document = build_html(video_ids, images)
    output.write_text(document, encoding="utf-8")

    print("", flush=True)
    print("完成", flush=True)
    print(f"通常動画: {source_counts.get('videos', 0)}件", flush=True)
    print(f"配信: {source_counts.get('streams', 0)}件", flush=True)
    print(f"Shorts: 取得対象外", flush=True)
    print(f"重複除去後: {len(video_ids)}件", flush=True)
    print(f"サムネイル埋め込み: {len(images)}/{len(video_ids)}", flush=True)
    print(f"取得失敗: 0件", flush=True)
    print(f"HTML: {output.resolve()}", flush=True)
    print(f"HTMLサイズ: {output.stat().st_size} bytes", flush=True)

if __name__ == "__main__":
    main()
