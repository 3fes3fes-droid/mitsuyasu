import base64
import io
import json
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, quote, quote_plus

import requests
from bs4 import BeautifulSoup
from PIL import Image

BASE = "https://i-one.tv"
LIST_URL = BASE + "/content/?filter=subscription&page={page}"
OUT = Path("i-one_subscription_thumbnails.html")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/151.0 Safari/537.36"

session = requests.Session()
session.headers.update({
    "User-Agent": UA,
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://i-one.tv/",
})

def get_with_retry(url, tries=4, timeout=30):
    last = None
    for i in range(tries):
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            time.sleep(1.2 * (i + 1))
    raise last

def pick_img_src(img, page_url):
    if not img:
        return None
    for key in ("data-src", "data-original", "data-lazy-src", "data-lazy", "src"):
        v = img.get(key)
        if v and not v.startswith("data:"):
            return urljoin(page_url, v.strip())
    srcset = img.get("srcset") or img.get("data-srcset")
    if srcset:
        cand = srcset.split(",")[-1].strip().split()[0]
        if cand:
            return urljoin(page_url, cand)
    return None

def derived_key_url(content_id):
    m = re.match(r"^([A-Za-z]+)-([0-9]{2})", content_id)
    if not m:
        return None
    folder = f"{m.group(1)}-{m.group(2)}"
    return f"https://file.i-one.tv/images/content/{folder}/{quote(content_id, safe='-')}/key.jpg"

def detail_id_from_href(href):
    full = urljoin(BASE, href)
    q = parse_qs(urlparse(full).query)
    vals = q.get("id")
    return vals[0] if vals else None

def find_model_name(a):
    p = a
    for _ in range(7):
        p = p.parent
        if not p:
            break
        detail_links = p.find_all("a", href=True)
        detail_count = sum(1 for x in detail_links if "/content/detail/" in x.get("href", ""))
        model_links = [x for x in detail_links if "model=" in x.get("href", "")]
        if model_links and detail_count <= 2:
            name = model_links[0].get_text(" ", strip=True)
            if name:
                return name
    return ""

def extract_page(page):
    url = LIST_URL.format(page=page)
    r = get_with_retry(url)
    soup = BeautifulSoup(r.text, "html.parser")

    heading = None
    for tag in soup.find_all(["h1", "h2", "h3", "div", "p"]):
        txt = tag.get_text(" ", strip=True)
        if txt == "コンテンツ一覧" or "コンテンツ一覧" in txt:
            heading = tag
            break

    anchors = soup.find_all("a", href=True)
    if heading:
        hpos = None
        all_tags = list(soup.find_all(True))
        try:
            hpos = all_tags.index(heading)
        except ValueError:
            pass
        if hpos is not None:
            allowed = set(id(x) for x in all_tags[hpos:])
            anchors = [a for a in anchors if id(a) in allowed]

    seen = set()
    items = []
    for a in anchors:
        href = a.get("href", "")
        if "/content/detail/" not in href or "id=" not in href:
            continue
        cid = detail_id_from_href(href)
        if not cid or cid in seen:
            continue

        img = a.find("img")
        if not img:
            p = a
            for _ in range(5):
                p = p.parent
                if not p:
                    break
                imgs = p.find_all("img", limit=4)
                if imgs:
                    img = imgs[0]
                    break

        src = pick_img_src(img, url)
        if src and any(bad in src.lower() for bad in ("logo", "icon", "loading", "noimage", "common/")):
            src = None
        if not src:
            src = derived_key_url(cid)

        model = find_model_name(a)

        seen.add(cid)
        items.append({
            "id": cid,
            "detail": urljoin(BASE, href),
            "image": src,
            "model": model,
            "page": page,
        })

    print(f"page {page:02d}: {len(items)} items")
    return items

def image_to_data_uri(item):
    urls = []
    if item.get("image"):
        urls.append(item["image"])
    fallback = derived_key_url(item["id"])
    if fallback and fallback not in urls:
        urls.append(fallback)

    last = None
    for url in urls:
        try:
            r = get_with_retry(url, tries=3, timeout=35)
            ctype = (r.headers.get("content-type") or "").split(";")[0].lower()
            if not ctype.startswith("image/"):
                raise ValueError(f"not image: {ctype}")

            data = r.content
            # Keep already-small listing thumbnails as-is; shrink large fallback/key images.
            if len(data) > 180_000:
                im = Image.open(io.BytesIO(data))
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                elif im.mode == "L":
                    im = im.convert("RGB")
                max_w = 360
                if im.width > max_w:
                    h = max(1, round(im.height * max_w / im.width))
                    im = im.resize((max_w, h), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=84, optimize=True)
                data = buf.getvalue()
                ctype = "image/jpeg"

            b64 = base64.b64encode(data).decode("ascii")
            return item["id"], f"data:{ctype};base64,{b64}", url, None
        except Exception as e:
            last = f"{type(e).__name__}: {e}"

    return item["id"], None, None, last

def build_html(items):
    cells = "\n".join(
        (
            f'<a href="https://www.youtube.com/results?search_query={quote_plus(item.get("model") or item["id"])}" '
            f'target="_blank" rel="noopener noreferrer" aria-label="{item.get("model") or item["id"]}">'
            f'<img src="{item["data_uri"]}" loading="eager" decoding="async" alt="">'
            f'</a>'
        )
        for item in items
    )
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>I-ONE TV thumbnails</title>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:#000}}
body{{overflow-y:scroll}}
#gallery{{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:3px;
  padding:3px;
  align-items:start;
}}
#gallery a{{
  display:block;
  min-width:0;
  text-decoration:none;
}}
#gallery img{{
  width:100%;
  height:auto;
  display:block;
  background:#111;
}}
</style>
</head>
<body>
<main id="gallery">
{cells}
</main>
<script>
(() => {{
  const g = document.getElementById('gallery');
  const a = Array.from(g.children);
  for (let i = a.length - 1; i > 0; i--) {{
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }}
  a.forEach(el => g.appendChild(el));

  let auto = false;
  let acc = 0;
  let last = performance.now();

  document.addEventListener('keydown', e => {{
    if (e.code !== 'Space') return;
    const t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
    e.preventDefault();
    auto = !auto;
  }}, {{passive:false}});

  function tick(now) {{
    const dt = Math.min(50, now - last);
    last = now;
    if (auto) {{
      acc += dt * 0.055;
      const px = Math.floor(acc);
      if (px > 0) {{
        acc -= px;
        window.scrollBy(0, px);
        const d = document.documentElement;
        if (window.scrollY + window.innerHeight >= d.scrollHeight - 2) window.scrollTo(0, 0);
      }}
    }}
    requestAnimationFrame(tick);
  }}
  requestAnimationFrame(tick);
}})();
</script>
</body>
</html>
"""

def main():
    all_items = []
    seen = set()
    for page in range(1, 33):
        items = extract_page(page)
        for x in items:
            if x["id"] not in seen:
                seen.add(x["id"])
                all_items.append(x)
        time.sleep(0.15)

    print("unique content ids:", len(all_items))
    Path("i-one_items.json").write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")

    if len(all_items) < 900:
        print("ERROR: extraction count is suspiciously low", file=sys.stderr)
        sys.exit(2)

    results = {}
    failures = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(image_to_data_uri, x): x for x in all_items}
        done = 0
        for fut in as_completed(futs):
            cid, data_uri, used_url, err = fut.result()
            done += 1
            if data_uri:
                results[cid] = (data_uri, used_url)
            else:
                failures[cid] = err
            if done % 50 == 0 or done == len(futs):
                print(f"images {done}/{len(futs)} ok={len(results)} fail={len(failures)}")

    ordered = [
        {**x, "data_uri": results[x["id"]][0]}
        for x in all_items if x["id"] in results
    ]
    OUT.write_text(build_html(ordered), encoding="utf-8")
    Path("i-one_failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")

    print("html images:", len(ordered))
    print("failures:", len(failures))
    print("html bytes:", OUT.stat().st_size)

    if len(ordered) < 900:
        print("ERROR: too many image failures", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    main()
