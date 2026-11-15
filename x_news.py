#!/usr/bin/env python3
"""X recent-post feed for the existing news cards. Reads every account from tw.py."""
import argparse
import ast
import concurrent.futures
import datetime as dt
import email.utils
import html as html_lib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FEED = ROOT / "x_news.xml"
STATUS = ROOT / "x_news_status.json"
NS_MEDIA = "http://search.yahoo.com/mrss/"
NS_USER = "urn:mitsuyasu:xfeed"
ET.register_namespace("media", NS_MEDIA)
ET.register_namespace("xf", NS_USER)
POSTS_PER_ACCOUNT = 12
WORKERS = 8
USER_AGENT = "Mozilla/5.0 (compatible; MitsuyasuPersonalNews/1.0)"

def account_list():
    """Keep every tw.py account and add every enabled account from x_news_additions.json."""
    tree = ast.parse((ROOT / "tw.py").read_text(encoding="utf-8"))
    originals = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "HARDCODED_FOLLOWING" for t in node.targets
        ):
            originals = ast.literal_eval(node.value)
            break
    if originals is None:
        raise ValueError("tw.py HARDCODED_FOLLOWING is missing")
    accounts = {str(x).lstrip("@").lower(): str(x).lstrip("@")
                for x in originals if str(x).strip()}
    path = ROOT / "x_news_additions.json"
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for entry in manifest.get("entries", []):
            if not isinstance(entry, dict) or entry.get("enabled", True) is False:
                continue
            handle = str(entry.get("handle") or "").lstrip("@").strip()
            if re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle):
                accounts.setdefault(handle.lower(), handle)
    return sorted(accounts.values(), key=str.casefold)

def _download(handle):
    last_error = ""
    for suffix in [f"feed.xml?count={POSTS_PER_ACCOUNT}",
                   f"feed.xml?count={POSTS_PER_ACCOUNT}",
                   f"media.xml?count={POSTS_PER_ACCOUNT}"]:
        u = "https://fxtwitter.com/" + handle + "/" + suffix
        try:
            req = urllib.request.Request(u, headers={
                "User-Agent": USER_AGENT, "Accept": "application/rss+xml,application/xml,*/*"
            })
            with urllib.request.urlopen(req, timeout=18) as response:
                raw = response.read(900000)
            xml = ET.fromstring(raw)
            posts = _parse_feed(handle, xml)
            if posts:
                return (handle, posts[:POSTS_PER_ACCOUNT], "")
            last_error = "empty feed"
        except Exception as e:
            last_error = type(e).__name__ + ": " + str(e)[:120]
            time.sleep(0.25)
    return (handle, [], last_error)

def _clean_text(value):
    value = html_lib.unescape(value or "")
    value = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>|</p>", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def _parse_feed(handle, root):
    entries = []
    for item in root.findall("./channel/item"):
        link = (item.findtext("link") or "").strip()
        if not re.match(r"^https?://", link):
            continue
        title = _clean_text(item.findtext("title"))
        description = _clean_text(item.findtext("description"))
        if len(title) < 5 and len(description) > len(title):
            title = description
        if not title:
            title = "投稿を開く"
        pub = (item.findtext("pubDate") or "").strip()
        try:
            dt_value = email.utils.parsedate_to_datetime(pub)
            pub = dt_value.isoformat()
        except Exception:
            pub = ""
        thumb = ""
        for element in item.findall(".//{" + NS_MEDIA + "}thumbnail"):
            thumb = (element.get("url") or "").strip()
            if thumb:
                break
        if not thumb:
            for enclosure in item.findall("enclosure"):
                url = (enclosure.get("url") or "").strip()
                typ = (enclosure.get("type") or "").lower()
                if typ.startswith("image/") or re.search(r"\.(?:jpe?g|png|webp)(?:[?#]|$)", url, re.I):
                    thumb = url
                    break
        if not thumb:
            raw_desc = item.findtext("description") or ""
            match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)', raw_desc, re.I)
            if match:
                thumb = html_lib.unescape(match.group(1))
        if "pbs.twimg.com/" in thumb:
            thumb = re.sub(r"([?&])name=orig\b", r"\1name=medium", thumb)
        entries.append({
            "handle": handle, "title": f"@{handle}｜{title[:450]}",
            "text": title, "link": link, "pubDate": pub, "thumb": thumb
        })
    return entries

def load_existing():
    if not FEED.exists():
        return {}
    existing = {}
    try:
        root = ET.parse(FEED).getroot()
        for item in root.findall("./channel/item"):
            handle = item.findtext("{" + NS_USER + "}account") or ""
            if not handle:
                continue
            entry = {
                "handle": handle,
                "title": item.findtext("title") or "",
                "text": item.findtext("description") or "",
                "link": item.findtext("link") or "",
                "pubDate": item.findtext("pubDate") or "",
                "thumb": "",
            }
            im = item.find("{" + NS_MEDIA + "}thumbnail")
            entry["thumb"] = im.get("url") if im is not None else ""
            existing.setdefault(handle.lower(), []).append(entry)
    except Exception as e:
        print("existing feed could not be read:", type(e).__name__, flush=True)
    return existing

def _date_key(item):
    try:
        return dt.datetime.fromisoformat(item.get("pubDate") or "").timestamp()
    except Exception:
        return 0

def _atomic_write(path, data):
    fd, name = tempfile.mkstemp(prefix=".xnews_", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def refresh():
    handles = account_list()
    prior = load_existing()
    new_by_account = {}
    failed = []
    success = 0
    print(f"X news: checking tw.py accounts plus additions ({len(handles)} total)", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(_download, handle): handle for handle in handles}
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            handle = futures[future]
            try:
                _, posts, err = future.result()
            except Exception as e:
                posts, err = [], str(e)[:120]
            if posts:
                success += 1
                new_by_account[handle.lower()] = posts
            else:
                failed.append({"account": handle, "reason": err or "no posts"})
            if i % 30 == 0 or i == len(handles):
                print(f"  {i}/{len(handles)} checked; {success} responding", flush=True)
    merged = []
    for handle in handles:
        rows = new_by_account.get(handle.lower())
        if rows is None:
            rows = prior.get(handle.lower(), [])
        merged.extend(rows[:POSTS_PER_ACCOUNT])
    seen = set()
    unique = []
    for row in sorted(merged, key=_date_key, reverse=True):
        if row.get("link") in seen:
            continue
        seen.add(row.get("link"))
        unique.append(row)
    if not unique:
        raise RuntimeError("No X posts available; keeping previous feed untouched")
    rss = ET.Element("rss", {"version":"2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "X投稿 / 元のフォロー＋追加アカウント"
    ET.SubElement(channel, "link").text = "https://x.com/"
    ET.SubElement(channel, "description").text = "Accounts from tw.py and x_news_additions.json, newest first"
    ET.SubElement(channel, "lastBuildDate").text = email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))
    for row in unique:
        elem = ET.SubElement(channel, "item")
        ET.SubElement(elem, "title").text = row["title"]
        ET.SubElement(elem, "link").text = row["link"]
        ET.SubElement(elem, "guid", {"isPermaLink":"true"}).text = row["link"]
        if row.get("pubDate"):
            ET.SubElement(elem, "pubDate").text = row["pubDate"]
        ET.SubElement(elem, "description").text = row.get("text") or ""
        ET.SubElement(elem, "{" + NS_USER + "}account").text = row["handle"]
        if row.get("thumb"):
            ET.SubElement(elem, "{" + NS_MEDIA + "}thumbnail", {"url":row["thumb"]})
    payload = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    _atomic_write(FEED, payload)
    additions_file = ROOT / "x_news_additions.json"
    additions = json.loads(additions_file.read_text(encoding="utf-8")).get("entries", []) if additions_file.exists() else []
    added_count = sum(1 for a in additions if a.get("enabled", True) is not False)
    status = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "accounts_from_tw_py": len(handles) - added_count,
        "added_accounts": added_count,
        "total_accounts": len(handles),
        "successful_accounts": success,
        "failed_accounts": len(failed),
        "posts_in_feed": len(unique),
        "failures": failed,
    }
    _atomic_write(STATUS, json.dumps(status, ensure_ascii=False, indent=2).encode("utf-8"))
    print(json.dumps({k: v for k, v in status.items() if k != "failures"}, ensure_ascii=False), flush=True)
    return status

def mobile_cards(markup):
    """Preserve the existing m.html layout. Add cached posts if a stale index regenerated m."""
    # Keep the existing index/m display version in sync after a stale tab saves m.
    try:
        current_index = (ROOT / "index.html").read_text(encoding="utf-8")
        stamp_match = re.search(r'id="index-last-updated">(\d{12})<', current_index)
        if stamp_match:
            markup = re.sub(r'(?<=id="index-last-updated">)\d{12}', stamp_match.group(1), markup)
    except Exception:
        pass
    if '<div id="grid">' not in markup or not FEED.exists():
        return markup, 0
    try:
        root = ET.parse(FEED).getroot()
    except Exception:
        return markup, 0
    existing_links = set(re.findall(r'<a class="card-link" href="([^"]+)"', markup))
    new_cards = []
    for item in root.findall("./channel/item"):
        link = item.findtext("link") or ""
        if not link:
            continue
        escaped_link = html_lib.escape(link, quote=True)
        if escaped_link in existing_links:
            continue
        existing_links.add(escaped_link)
        title = html_lib.escape(item.findtext("title") or "X投稿")
        stamp = item.findtext("pubDate") or ""
        try:
            when = dt.datetime.fromisoformat(stamp).astimezone()
            display_time = when.strftime("%m/%d %H:%M")
        except Exception:
            display_time = ""
        thumb_elem = item.find("{" + NS_MEDIA + "}thumbnail")
        image = (thumb_elem.get("url") if thumb_elem is not None else "") or ""
        image_escaped = html_lib.escape(image, quote=True)
        badge = (
            '<span class="source-badge" style="background:#99999920;color:#bfc3d2;'
            'border:1px solid #99999935"><img class="badge-favicon" '
            'src="https://www.google.com/s2/favicons?domain=x.com&amp;sz=32" '
            'alt=""><span>X投稿</span></span>'
        )
        meta = '<div class="card-meta">' + badge + '<span class="time-label">' + display_time + '</span></div>'
        body = '<div class="card-body">' + meta + '<div class="card-title">' + title + '</div></div>'
        if image:
            wrapper = '<div class="card"><div class="card-thumb"><img loading="lazy" src="' + image_escaped + '" alt=""></div>' + body + '</div>'
        else:
            wrapper = '<div class="card card-list"><div class="card-list-accent" style="background:#bfc3d2"></div>' + body + '</div>'
        new_cards.append('<a class="card-link" href="' + escaped_link + '" target="_blank" rel="noopener noreferrer">' + wrapper + '</a>')
    if not new_cards:
        return markup, 0

    # Insert chronologically among existing news, without changing their relative order.
    def clock(card):
        m = re.search(r'<span class="time-label">([^<]+)</span>', card)
        value = html_lib.unescape(m.group(1)).strip() if m else ""
        t = re.search(r'(?:(\d{4})/)?(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})', value)
        if not t:
            return -1
        try:
            year = int(t.group(1) or dt.datetime.now().year)
            z = dt.timezone(dt.timedelta(hours=9))
            return dt.datetime(year, int(t.group(2)), int(t.group(3)),
                               int(t.group(4)), int(t.group(5)), tzinfo=z).timestamp()
        except Exception:
            return -1

    start = re.search(r'<div id="grid">\s*', markup)
    if start:
        tail = markup[start.end():]
        card_regex = re.compile(r'<a class="card-link"[^>]*>.*?</a>', re.S)
        current = []
        pos = 0
        while True:
            match = card_regex.match(tail, pos)
            if not match:
                break
            current.append(match.group(0))
            pos = match.end()
            while pos < len(tail) and tail[pos] in "\r\n":
                pos += 1
        if current:
            merged = []
            j = 0
            dated_new = [(clock(c), c) for c in new_cards]
            for old in current:
                old_time = clock(old)
                while j < len(dated_new) and dated_new[j][0] >= old_time:
                    merged.append(dated_new[j][1])
                    j += 1
                merged.append(old)
            merged.extend(c for _, c in dated_new[j:])
            markup = markup[:start.end()] + "\n".join(merged) + "\n" + tail[pos:]
            return markup, len(new_cards)

    # Preserve all posts even if an unfamiliar m.html card structure is received.
    markup = markup.replace('<div id="grid">', '<div id="grid">\n' + '\n'.join(new_cards) + '\n', 1)
    return markup, len(new_cards)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="Count tw.py accounts without downloading")
    args = ap.parse_args()
    if args.check:
        print("Total accounts (tw.py + additions):", len(account_list()))
    else:
        refresh()
