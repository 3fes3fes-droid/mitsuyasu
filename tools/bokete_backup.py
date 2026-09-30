#!/usr/bin/env python3
import os, re, sys, time, json, csv, hashlib, mimetypes, threading, queue
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode, unquote
import requests
from bs4 import BeautifulSoup

OUT = Path(os.getenv("OUT_DIR", "bokete_backup"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "250000"))
MAX_ASSETS = int(os.getenv("MAX_ASSETS", "500000"))
MAX_SECONDS = int(os.getenv("MAX_SECONDS", "3300"))
WORKERS = int(os.getenv("WORKERS", "12"))
START = time.time()

PAGE_HOSTS = {"bokete.jp", "www.bokete.jp", "select.bokete.jp"}
BLOCK_PATH = re.compile(r"/(?:login|logout|signup|register|password|settings|auth|oauth|report|delete|edit|new)(?:/|$)", re.I)
ASSET_EXT = {".jpg",".jpeg",".png",".gif",".webp",".svg",".ico",".css",".js",".mjs",".woff",".woff2",".ttf",".otf",".mp4",".webm",".mp3",".wav",".pdf"}
TRACKING = {"fbclid","gclid","yclid","ref","ref_src"}

SEEDS = [
    "https://bokete.jp/",
    "https://bokete.jp/boke/popular",
    "https://bokete.jp/boke/hot",
    "https://bokete.jp/boke/rising",
    "https://bokete.jp/boke/new",
    "https://bokete.jp/boke/select",
    "https://bokete.jp/boke/pickup",
    "https://bokete.jp/odai/new",
    "https://bokete.jp/odai/popular",
    "https://bokete.jp/odai/select",
    "https://bokete.jp/tag",
    "https://bokete.jp/ranking",
    "https://bokete.jp/about",
    "https://bokete.jp/about/howto",
    "https://bokete.jp/about/help",
    "https://select.bokete.jp/",
    "https://select.bokete.jp/boke/popular",
    "https://select.bokete.jp/boke/hot",
    "https://select.bokete.jp/boke/pickup",
]
SITEMAPS = [
    "https://bokete.jp/robots.txt",
    "https://bokete.jp/sitemap.xml",
    "https://bokete.jp/sitemap_index.xml",
    "https://select.bokete.jp/robots.txt",
    "https://select.bokete.jp/sitemap.xml",
]

OUT.mkdir(parents=True, exist_ok=True)
SITE = OUT / "site"
SITE.mkdir(parents=True, exist_ok=True)
LOG = OUT / "logs"
LOG.mkdir(exist_ok=True)

seen, queued = set(), set()
lock = threading.RLock()
q = queue.PriorityQueue()
records, errors = [], []
stats = {"pages":0,"assets":0,"bytes":0,"errors":0,"started":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
thread_local = threading.local()

def session():
    s = getattr(thread_local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36 bokete-preservation/1.0",
            "Accept-Language":"ja,en-US;q=0.8,en;q=0.6",
            "Accept-Encoding":"gzip, deflate, br",
        })
        thread_local.session = s
    return s

def normalize(url, base=None):
    try:
        if base: url = urljoin(base, url)
        p = urlsplit(url)
        if p.scheme not in ("http","https"): return None
        host = p.hostname.lower() if p.hostname else ""
        if not host: return None
        port = f":{p.port}" if p.port and p.port not in (80,443) else ""
        netloc = host + port
        path = re.sub(r"/{2,}", "/", p.path or "/")
        qs = []
        for k,v in parse_qsl(p.query, keep_blank_values=True):
            if k.lower().startswith("utm_") or k.lower() in TRACKING: continue
            qs.append((k,v))
        query = urlencode(sorted(qs))
        return urlunsplit((p.scheme.lower(), netloc, path, query, ""))
    except Exception:
        return None

def is_page(url):
    p = urlsplit(url)
    ext = Path(p.path).suffix.lower()
    return p.hostname in PAGE_HOSTS and ext not in ASSET_EXT and not BLOCK_PATH.search(p.path)

def is_asset(url):
    p = urlsplit(url)
    return Path(p.path).suffix.lower() in ASSET_EXT

def local_path(url, content_type=None):
    p = urlsplit(url)
    host = p.hostname or "unknown"
    raw = unquote(p.path or "/").replace("\x00","")
    parts = [re.sub(r'[^0-9A-Za-z._~\-\u0080-\uffff]+','_', x)[:150] or "_" for x in raw.split("/") if x]
    path = Path(*parts) if parts else Path("index")
    ext = path.suffix.lower()
    htmlish = content_type and ("text/html" in content_type or "application/xhtml" in content_type)
    if htmlish or (p.hostname in PAGE_HOSTS and ext not in ASSET_EXT):
        if ext in (".html",".htm"):
            pass
        elif path.name == "index":
            path = path / "index.html"
        else:
            path = path / "index.html"
    elif not ext and content_type:
        guess = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ""
        if guess:
            path = path.with_suffix(guess)
    if p.query:
        h = hashlib.sha1(p.query.encode()).hexdigest()[:10]
        path = path.with_name(path.stem + "_q_" + h + path.suffix)
    return SITE / host / path

def rel_target(from_path, target_url):
    tp = local_path(target_url)
    return os.path.relpath(tp, from_path.parent).replace(os.sep, "/")

def enqueue(url, priority=0, kind=None):
    u = normalize(url)
    if not u: return
    if kind == "page":
        if not is_page(u): return
    elif kind == "asset":
        pass
    else:
        if not (is_page(u) or is_asset(u)): return
    with lock:
        if u in seen or u in queued: return
        queued.add(u)
    q.put((priority, time.monotonic_ns(), u, kind))

def save_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

CSS_URL = re.compile(r'url\(\s*[\'"]?([^\'")]+)', re.I)

def rewrite_html(url, body, out_path):
    soup = BeautifulSoup(body, "html.parser")
    attrs = [
        ("a","href","page"),("link","href","asset"),("script","src","asset"),
        ("img","src","asset"),("source","src","asset"),("video","src","asset"),
        ("audio","src","asset"),("iframe","src","page"),("form","action",None),
    ]
    for tagname, attr, kind in attrs:
        for tag in soup.find_all(tagname):
            val = tag.get(attr)
            if not val: continue
            absu = normalize(val, url)
            if not absu: continue
            if kind == "page" and is_page(absu):
                enqueue(absu, 0, "page")
                tag[attr] = rel_target(out_path, absu)
            elif kind == "asset":
                enqueue(absu, 1, "asset")
                tag[attr] = rel_target(out_path, absu)
    for tag in soup.find_all(["img","source"]):
        ss = tag.get("srcset")
        if not ss: continue
        new = []
        for item in ss.split(","):
            bits = item.strip().split()
            if not bits: continue
            absu = normalize(bits[0], url)
            if absu:
                enqueue(absu, 1, "asset")
                bits[0] = rel_target(out_path, absu)
            new.append(" ".join(bits))
        tag["srcset"] = ", ".join(new)
    for tag in soup.find_all(style=True):
        style = tag.get("style","")
        def repl(m):
            absu = normalize(m.group(1), url)
            if not absu: return m.group(0)
            enqueue(absu,1,"asset")
            return "url('" + rel_target(out_path, absu) + "')"
        tag["style"] = CSS_URL.sub(repl, style)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return str(soup).encode("utf-8", "replace"), title

def rewrite_css(url, text, out_path):
    def repl(m):
        absu = normalize(m.group(1), url)
        if not absu: return m.group(0)
        enqueue(absu,1,"asset")
        return "url('" + rel_target(out_path, absu) + "')"
    return CSS_URL.sub(repl, text)

def fetch(url, kind):
    if time.time() - START > MAX_SECONDS: return
    with lock:
        if url in seen: return
        seen.add(url)
        queued.discard(url)
    try:
        r = session().get(url, timeout=(8,25), allow_redirects=True)
        final = normalize(r.url) or url
        ct = r.headers.get("content-type","").lower()
        data = r.content
        if len(data) > 60_000_000:
            raise RuntimeError(f"oversize {len(data)}")
        status = r.status_code
        if status >= 400:
            raise RuntimeError(f"HTTP {status}")
        html = "text/html" in ct or "application/xhtml" in ct
        css = "text/css" in ct or final.lower().split("?")[0].endswith(".css")
        outp = local_path(final, ct)
        title = ""
        if html and urlsplit(final).hostname in PAGE_HOSTS:
            with lock:
                if stats["pages"] >= MAX_PAGES: return
                stats["pages"] += 1
            data, title = rewrite_html(final, r.text, outp)
        else:
            with lock:
                if stats["assets"] >= MAX_ASSETS: return
                stats["assets"] += 1
            if css:
                data = rewrite_css(final, r.text, outp).encode("utf-8","replace")
        save_bytes(outp, data)
        with lock:
            stats["bytes"] += len(data)
            records.append({
                "url":url,"final_url":final,"status":status,"content_type":ct,
                "bytes":len(data),"path":str(outp.relative_to(OUT)),"title":title
            })
            n = stats["pages"] + stats["assets"]
            if n % 250 == 0:
                print(json.dumps(stats, ensure_ascii=False), flush=True)
    except Exception as e:
        with lock:
            stats["errors"] += 1
            errors.append({"url":url,"error":str(e)})
            if stats["errors"] <= 50:
                print("ERR", url, e, flush=True)

def worker():
    while True:
        if time.time() - START > MAX_SECONDS: return
        try:
            pri, _, url, kind = q.get(timeout=2)
        except queue.Empty:
            return
        try: fetch(url, kind)
        finally: q.task_done()

# Seed direct pages.
for u in SEEDS: enqueue(u, 0, "page")

# Seed robots/sitemaps; sitemap links are added if accessible.
for sm in SITEMAPS:
    try:
        r = session().get(sm, timeout=10)
        if r.ok:
            (LOG / ("seed_" + hashlib.sha1(sm.encode()).hexdigest()[:8] + ".txt")).write_bytes(r.content)
            text = r.text
            for m in re.findall(r'https?://[^\s<>"\']+', text):
                m = m.replace("&amp;","&")
                if is_page(normalize(m) or ""):
                    enqueue(m,0,"page")
                elif "sitemap" in m.lower():
                    try:
                        rr = session().get(m, timeout=15)
                        if rr.ok:
                            for mm in re.findall(r'<loc>\s*(.*?)\s*</loc>', rr.text, re.I):
                                enqueue(mm,0,"page")
                    except Exception: pass
            for mm in re.findall(r'<loc>\s*(.*?)\s*</loc>', text, re.I):
                enqueue(mm,0,"page")
    except Exception:
        pass

threads = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
for t in threads: t.start()
for t in threads: t.join()

# Persist manifests.
stats["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
stats["elapsed_seconds"] = round(time.time()-START,2)
(OUT/"stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
with (OUT/"manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["url","final_url","status","content_type","bytes","path","title"])
    w.writeheader(); w.writerows(records)
with (OUT/"errors.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["url","error"]); w.writeheader(); w.writerows(errors)

# Offline searchable entry page.
rows = []
for i,r in enumerate(records):
    if "text/html" not in r["content_type"]: continue
    title = (r["title"] or r["final_url"]).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    href = r["path"].replace("\\","/")
    urltxt = r["final_url"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    rows.append(f'<li><a href="{href}">{title}</a><small>{urltxt}</small></li>')
index = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>bokete backup</title><style>
body{font-family:system-ui,sans-serif;margin:20px;background:#111;color:#eee}input{width:100%;box-sizing:border-box;padding:14px;font-size:18px;position:sticky;top:0}
li{margin:8px 0}a{color:#8cc8ff;text-decoration:none}small{display:block;color:#999;word-break:break-all}
</style><h1>bokete backup</h1><p id=s></p><input id=q placeholder="タイトル・URL検索"><ul id=l>""" + "".join(rows) + """</ul>
<script>const a=[...document.querySelectorAll('li')],q=document.querySelector('#q'),s=document.querySelector('#s');
s.textContent=a.length+' HTML pages';q.oninput=()=>{let x=q.value.toLowerCase();for(const e of a)e.hidden=x&&!e.innerText.toLowerCase().includes(x)}</script>"""
(OUT/"index.html").write_text(index, encoding="utf-8")
print(json.dumps(stats, ensure_ascii=False, indent=2))
