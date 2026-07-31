#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVer 全量クローラー (tv.py) — 2026-05 復旧版

仕様:
  - platform-api.tver.jp の現行 API を使用 (旧 service-api.tver.jp/api/v1/call/top は廃止済み)
  - device 認証 (platform_uid / platform_token) を自動発行・キャッシュ
  - callNewerDetail/{genre} と callEpisodeRanking, callRanking を巡回
  - 出力 HTML は y.html を踏襲した独立スタイル (shared_ui.css に依存しない)
  - 取得 0 件のときは HTML を上書きしない (既存 UI 保護)
  - HTML 全体を上書きする場合も、テンプレートに __FETCHED_AT__ / __ALL_ITEMS__
    を埋め込むのみ。データ量が多くても UI は壊れない。

更新ボタン:
  ボタンが叩く先は server.py (port 8000) の POST /run/tver
  サーバが無いときは window.location.reload() にフォールバック
"""
import sys
import os

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import time
import re
import requests
from datetime import datetime
from pathlib import Path

# ── 設定 ──────────────────────────────────────
BASE_DIR     = Path(__file__).parent
OUTPUT_HTML  = BASE_DIR / "tver.html"
TOKEN_FILE   = BASE_DIR / "file" / "tver_token.json"
THUMB_BASE   = "https://statics.tver.jp"
PLATFORM_API = "https://platform-api.tver.jp"

# 新着APIのジャンル (drama/variety/anime/sports は OK、documentary/news は廃止)
NEWER_GENRES = ["all", "drama", "variety", "anime", "sports"]

# True: NGワード対象コンテンツをHTMLに埋め込む前に除外する
#      HTML側の表示切替ではなく、定期生成の大本で最初から非表示にする
HIDE_NG_CONTENT = True

CONTENT_NG_WORDS = (
    "韓国",
    "韓流",
    "韓ドラ",
    "K-POP",
    "KPOP",
    "K WORLD",
    "K-WORLD",
    "Korean",
    "中国",
    "アニメ",
    "プロ野球",
    "野球",
)


HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Origin":  "https://tver.jp",
    "Referer": "https://tver.jp/",
    "Accept":  "application/json",
    "x-tver-platform-type": "web",
}

# ── トークン管理 ──────────────────────────────
def get_platform_token():
    """platform_uid / platform_token をキャッシュ or 新規発行"""
    if TOKEN_FILE.exists():
        try:
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            if data.get("platform_uid") and data.get("platform_token"):
                return data["platform_uid"], data["platform_token"]
        except Exception:
            pass

    print("  TVer トークン新規発行中…")
    r = requests.post(
        f"{PLATFORM_API}/v2/api/platform_users/browser/create",
        headers=HEADERS_BASE,
        data={"device_type": "pc"},
        timeout=15,
    )
    r.raise_for_status()
    res = r.json().get("result", {})
    puid = res.get("platform_uid")
    ptok = res.get("platform_token")
    if not puid or not ptok:
        raise RuntimeError(f"トークン発行失敗: {r.text[:200]}")
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(
        json.dumps({"platform_uid": puid, "platform_token": ptok}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  発行完了 puid={puid[:8]}…")
    return puid, ptok

# ── 既存IDの吸い出し (NEW判定用) ───────────────
def load_prev_ids() -> set:
    if not OUTPUT_HTML.exists():
        return set()
    try:
        html = OUTPUT_HTML.read_text(encoding="utf-8")
    except Exception:
        return set()
    ids = set(re.findall(r'data-id="([^"]+)"', html))
    m = re.search(r'const\s+ALL_ITEMS\s*=\s*(\[[\s\S]*?\]);', html)
    if m:
        try:
            for it in json.loads(m.group(1)):
                if isinstance(it, dict) and it.get("id"):
                    ids.add(it["id"])
        except Exception:
            pass
    return ids

# ── レスポンスからエピソード抽出 ───────────────
def _parse_broadcast_ymd(label: str) -> str:
    """'5月11日(月)放送分' → '2026-05-11'  / 解析不能なら ''"""
    if not label:
        return ""
    m = re.match(r'(\d{1,2})月(\d{1,2})日', label)
    if not m:
        return ""
    mon, day = int(m.group(1)), int(m.group(2))
    now = datetime.now()
    # 現在月より大幅に先なら去年扱い（年またぎ対応）
    year = now.year if mon <= now.month + 1 else now.year - 1
    return f"{year:04d}-{mon:02d}-{day:02d}"

def _ep_from_content(c: dict, kind: str = "episode", rank: int = 0) -> dict:
    cid = c.get("id", "")
    tp = c.get("thumbnailPath", "")
    label = c.get("broadcastDateLabel") or ""
    return {
        "kind":          kind,
        "id":            cid,
        "url":           f"https://tver.jp/{'episodes' if kind=='episode' else 'series'}/{cid}",
        "title":         c.get("seriesTitle") or c.get("title") or "",
        "episode_title": c.get("title") or "",
        "broadcaster":   c.get("broadcasterName") or c.get("productionProviderName") or "",
        "airdate":       label,
        "broadcast_ymd": _parse_broadcast_ymd(label),
        "duration":      c.get("duration") or 0,
        "end_at":        c.get("endAt") or 0,
        "thumb":         (THUMB_BASE + tp) if tp else "",
        "rank":          rank,
        "is_new":        False,
    }

def fetch_newer(puid: str, ptok: str):
    """ジャンル別 新着エピソード"""
    items = []
    seen = set()
    params = {"platform_uid": puid, "platform_token": ptok}
    for g in NEWER_GENRES:
        try:
            r = requests.get(
                f"{PLATFORM_API}/service/api/v1/callNewerDetail/{g}",
                headers=HEADERS_BASE, params=params, timeout=20,
            )
            if r.status_code != 200:
                print(f"  WARN newer/{g}: status {r.status_code}")
                continue
            data = r.json().get("result", {})
            inner = data.get("contents", {}).get("contents", [])
            n0 = len(items)
            for raw in inner:
                if raw.get("type") != "episode":
                    continue
                c = raw.get("content", {})
                cid = c.get("id")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                items.append(_ep_from_content(c, "episode"))
            print(f"  NEW [{g:8s}] +{len(items) - n0} 件")
        except Exception as e:
            print(f"  WARN newer/{g}: {e}")
    return items, seen

def fetch_episode_ranking(puid: str, ptok: str, items: list, seen: set):
    """エピソードランキング"""
    params = {"platform_uid": puid, "platform_token": ptok}
    try:
        r = requests.get(
            f"{PLATFORM_API}/service/api/v1/callEpisodeRanking",
            headers=HEADERS_BASE, params=params, timeout=20,
        )
        if r.status_code != 200:
            print(f"  WARN epRanking: status {r.status_code}")
            return
        groups = r.json().get("result", {}).get("contents", [])
        for grp in groups:
            gid = grp.get("content", {}).get("id", "")
            n0 = len(items)
            for i, raw in enumerate(grp.get("contents", []), start=1):
                if raw.get("type") != "episode":
                    continue
                c = raw.get("content", {})
                cid = c.get("id")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                ep = _ep_from_content(c, "episode", rank=i)
                items.append(ep)
            print(f"  RANK-EP [{gid:8s}] +{len(items) - n0} 件")
    except Exception as e:
        print(f"  WARN epRanking: {e}")

def fetch_series_ranking(puid: str, ptok: str, items: list, seen: set):
    """シリーズランキング"""
    params = {"platform_uid": puid, "platform_token": ptok}
    try:
        r = requests.get(
            f"{PLATFORM_API}/service/api/v1/callRanking",
            headers=HEADERS_BASE, params=params, timeout=20,
        )
        if r.status_code != 200:
            print(f"  WARN seRanking: status {r.status_code}")
            return
        groups = r.json().get("result", {}).get("contents", [])
        for grp in groups:
            gid = grp.get("content", {}).get("id", "")
            n0 = len(items)
            for i, raw in enumerate(grp.get("contents", []), start=1):
                if raw.get("type") != "series":
                    continue
                c = raw.get("content", {})
                cid = c.get("id")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                items.append(_ep_from_content(c, "series", rank=i))
            print(f"  RANK-SE [{gid:8s}] +{len(items) - n0} 件")
    except Exception as e:
        print(f"  WARN seRanking: {e}")


def is_ng_item(item: dict) -> bool:
    """NGワード対象コンテンツなら True。HTML生成前の固定除外に使う。"""
    if not HIDE_NG_CONTENT or not isinstance(item, dict):
        return False

    text = "\n".join(str(item.get(k, "") or "") for k in (
        "title",
        "episode_title",
        "series",
        "channel",
        "description",
        "broadcaster",
        "airdate",
    ))
    text_lower = text.lower()

    for word in CONTENT_NG_WORDS:
        w = str(word)
        if w in text or w.lower() in text_lower:
            return True
    return False

def filter_ng_items(items: list) -> list:
    """NGワード対象を固定非表示にした表示用リストを返す。"""
    if not HIDE_NG_CONTENT or not isinstance(items, list):
        return items
    filtered = [it for it in items if not is_ng_item(it)]
    removed = len(items) - len(filtered)
    if removed:
        print(f"  NGワード除外: {removed} 件 (残り {len(filtered)} 件)")
    return filtered


# ── HTML テンプレート (y.html 流用) ────────────
TEMPLATE_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TVer</title>
<style>
:root {
  --bg-color: #0f0f0f;
  --card-bg: #1e1e1e;
  --text-color: #f1f1f1;
  --text-dim: #aaaaaa;
  --accent: #00c8ff;
  --accent-new: #c8ff00;
  --line: #242424;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg-color);
  color: var(--text-color);
  font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif;
}
#header { display: flex; align-items: center; justify-content: flex-start; gap: 10px; padding: 10px 16px; }
#header .service-logo {
  display: block;
  width: 86px;
  height: 30px;
  object-fit: contain;
}
#refresh-btn {
  background: #333; color: #fff; border: none;
  padding: 6px 12px; border-radius: 18px; cursor: pointer; font-size: 13px;
}
#refresh-btn:hover { background: #444; }
#refresh-btn:disabled { opacity: .5; cursor: wait; }
#bar {
  padding: 4px 16px; font-size: 12px; color: var(--text-dim);
  border-bottom: 1px solid var(--line);
  display: flex; gap: 12px; flex-wrap: wrap;
}
#filter-bar {
  display: flex; gap: 6px; flex-wrap: wrap;
  padding: 8px 16px; border-bottom: 1px solid var(--line);
}
.flt-btn {
  background: #2a2a2a; color: var(--text-dim);
  border: 1px solid #3a3a3a; border-radius: 16px;
  padding: 4px 12px; font-size: 12px; cursor: pointer;
  transition: background .15s, color .15s, border-color .15s;
  white-space: nowrap;
}
.flt-btn:hover { background: #383838; color: var(--text-color); }
.flt-btn.active {
  background: var(--accent); color: #000;
  border-color: var(--accent); font-weight: 700;
}
.flt-btn .cnt {
  opacity: .7; font-size: 11px; margin-left: 3px;
}
#grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px; padding: 16px;
}
@media (max-width: 1200px) { #grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 900px)  { #grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px)  { #grid { grid-template-columns: 1fr; } }
.card {
  background: var(--card-bg); border-radius: 8px; overflow: hidden; position: relative;
}
.card.is-new { border-left: 2px solid var(--accent-new); }
.card.is-series { border-left: 2px solid var(--accent); }
.thumb-link {
  display: block; position: relative; aspect-ratio: 16 / 9; background: #000; text-decoration: none;
}
.thumb-link img { width: 100%; height: 100%; object-fit: cover; }
.new-badge {
  position: absolute; top: 4px; left: 4px; z-index: 1;
  background: var(--accent-new); color: #000;
  font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;
}
.rank-badge {
  position: absolute; top: 4px; right: 4px; z-index: 1;
  background: var(--accent); color: #000;
  font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;
}
.dur-badge {
  position: absolute; bottom: 4px; right: 4px; z-index: 1;
  background: rgba(0,0,0,.8); color: #fff;
  font-size: 10px; font-family: monospace;
  padding: 1px 5px; border-radius: 3px;
}
.expiry-badge {
  position: absolute; bottom: 4px; left: 4px; z-index: 1;
  background: rgba(0,0,0,.85); color: #ffc800;
  font-size: 10px; font-family: monospace; font-weight: 700;
  padding: 2px 5px; border-radius: 4px;
}
.expiry-badge.soon { color: #ff6060; }
.info-link { display: block; text-decoration: none; color: inherit; }
.info { display: flex; align-items: stretch; padding: 8px 8px 8px 10px; min-width: 0; }
.info-text { flex: 1; min-width: 0; }
.sub-label { font-size: 10px; font-weight: 700; color: var(--accent); margin-bottom: 2px; }
.title {
  font-size: 14px; font-weight: 500; line-height: 1.4; color: var(--text-color);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sub-text {
  font-size: 12px; color: var(--text-dim); margin-top: 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.dl-btn {
  background: transparent; border: none; cursor: pointer;
  padding: 0 4px 0 8px; margin: 0; flex-shrink: 0; align-self: center;
}
.dl-btn svg {
  width: 16px; height: 16px; fill: none; stroke: var(--text-dim);
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
  transition: stroke .2s;
}
.dl-btn:hover svg { stroke: var(--accent); }
.dl-btn.done svg { stroke: #4caf50; }
#empty, #err { display: none; padding: 24px 16px; color: var(--text-dim); }
#err { color: #ff8a8a; }
#toast {
  position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
  background: #323232; color: #fff; padding: 8px 16px; border-radius: 4px;
  font-size: 14px; opacity: 0; transition: opacity .3s; pointer-events: none; z-index: 1000;
}
#toast.show { opacity: 1; }
</style>
</head>
<body>
<div id="header">
  <img class="service-logo" src="https://upload.wikimedia.org/wikipedia/commons/6/6a/TVer_logo.svg" alt="">
  <button id="refresh-btn" onclick="runUpdate()">↺ 更新</button>
</div>
<div id="bar">
  <span id="count">—</span>
  <span id="meta">—</span>
</div>
<div id="filter-bar"></div>
<div id="grid"></div>
<div id="empty">番組が見つかりません</div>
<div id="err"></div>
<div id="toast"></div>
<script>
const ALL_ITEMS  = __ALL_ITEMS__;
const FETCHED_AT = "__FETCHED_AT__";
const COPY_CMD   = 'y';

function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmtDur(sec) {
  if (!sec) return '';
  const m = Math.floor(sec / 60), s = sec % 60;
  return `${m}:${String(s).padStart(2,'0')}`;
}
function fmtRemain(endAt) {
  if (!endAt) return null;
  const ms = endAt * 1000 - Date.now();
  if (ms <= 0) return null;
  const h = Math.floor(ms / 3600000);
  if (h < 24)  return { text: `あと${h}h`, soon: true };
  if (h < 72)  return { text: `あと${Math.floor(h/24)}d`, soon: false };
  return null;
}
function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise((resolve, reject) => {
    try {
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); ta.remove();
      resolve();
    } catch (e) { reject(e); }
  });
}
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => t.classList.remove('show'), 2200);
}
// ── 日付フィルター ──────────────────────────────
function localDateStr(offsetDays) {
  const d = new Date();
  d.setDate(d.getDate() - offsetDays);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const da = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${da}`;
}

const DAY_LABELS = ['今日', '昨日', '一昨日', '3日前', '4日前', '5日前'];
// offset→YMDのマップを起動時に1回生成
const DAY_YMDS = DAY_LABELS.map((_, i) => localDateStr(i));

// 各日付の件数をカウント
function buildCounts() {
  const cnt = { all: ALL_ITEMS.length };
  DAY_YMDS.forEach((ymd, i) => {
    cnt[ymd] = ALL_ITEMS.filter(v => v.broadcast_ymd === ymd).length;
  });
  return cnt;
}

let CURRENT_FILTER = 'all';

function buildFilterBar() {
  const bar = document.getElementById('filter-bar');
  const counts = buildCounts();
  bar.innerHTML = '';

  // 「全て」ボタン
  const allBtn = document.createElement('button');
  allBtn.className = 'flt-btn' + (CURRENT_FILTER === 'all' ? ' active' : '');
  allBtn.innerHTML = `全て<span class="cnt">${counts.all}</span>`;
  allBtn.onclick = () => setFilter('all');
  bar.appendChild(allBtn);

  // 日付ボタン（件数0でも表示、グレーアウトのみ）
  DAY_LABELS.forEach((label, i) => {
    const ymd = DAY_YMDS[i];
    const cnt = counts[ymd] || 0;
    const btn = document.createElement('button');
    btn.className = 'flt-btn' + (CURRENT_FILTER === ymd ? ' active' : '');
    btn.style.opacity = cnt === 0 ? '0.35' : '1';
    btn.innerHTML = `${label}<span class="cnt">${cnt}</span>`;
    btn.onclick = () => setFilter(ymd);
    bar.appendChild(btn);
  });
}

function setFilter(key) {
  CURRENT_FILTER = key;
  buildFilterBar();
  renderGrid();
}

function applyFilter(items) {
  if (CURRENT_FILTER === 'all') return items;
  return items.filter(v => v.broadcast_ymd === CURRENT_FILTER);
}

function renderGrid() {
  const grid = document.getElementById('grid');
  const empty = document.getElementById('empty');
  grid.innerHTML = '';
  const filtered = applyFilter(ALL_ITEMS);
  document.getElementById('count').textContent =
    CURRENT_FILTER === 'all'
      ? `${ALL_ITEMS.length}件`
      : `${filtered.length}件 / 全${ALL_ITEMS.length}件`;
  if (!filtered.length) { empty.style.display = 'block'; return; }
  empty.style.display = 'none';
  const frag = document.createDocumentFragment();
  for (const v of filtered) {
    const url = v.url || '#';
    const card = document.createElement('div');
    card.className = 'card' + (v.is_new ? ' is-new' : '') + (v.kind === 'series' ? ' is-series' : '');
    card.dataset.id = v.id || '';
    const remain = fmtRemain(v.end_at);
    const durHtml    = v.duration ? `<span class="dur-badge">${fmtDur(v.duration)}</span>` : '';
    const newHtml    = v.is_new ? `<span class="new-badge">NEW</span>` : '';
    const rankHtml   = v.rank ? `<span class="rank-badge">#${v.rank}</span>` : '';
    const expiryHtml = remain ? `<span class="expiry-badge ${remain.soon ? 'soon' : ''}">${esc(remain.text)}</span>` : '';
    const episodeLine = v.episode_title ? `<div class="sub-text">${esc(v.episode_title)}</div>` : '';
    card.innerHTML = `
      <a class="thumb-link" href="${esc(url)}" target="_blank" rel="noopener">
        <img src="${esc(v.thumb || '')}" referrerpolicy="no-referrer" loading="lazy" alt="">
        ${rankHtml}${newHtml}${expiryHtml}${durHtml}
      </a>
      <a class="info-link" href="${esc(url)}" target="_blank" rel="noopener">
        <div class="info">
          <div class="info-text">
            <div class="title" title="${esc(v.title || '無題')}">${esc(v.title || '無題')}</div>
            ${episodeLine}
          </div>
          <button class="dl-btn" data-url="${esc(url)}" title="y URLをコピー">
            <svg viewBox="0 0 24 24"><path d="M12 3v13M7 11l5 5 5-5"/><path d="M4 19h16"/></svg>
          </button>
        </div>
      </a>`;
    frag.appendChild(card);
  }
  grid.appendChild(frag);
}

function render() {
  document.getElementById('meta').textContent = FETCHED_AT
    ? `${FETCHED_AT.replace('T',' ').slice(0,16)} 取得`
    : '';
  buildFilterBar();
  renderGrid();
}
function onDL(e) {
  const btn = e.target.closest('.dl-btn');
  if (!btn) return;
  e.preventDefault(); e.stopPropagation();
  const cmd = `${COPY_CMD} ${btn.dataset.url}`;
  copyText(cmd).then(() => {
    btn.classList.add('done');
    setTimeout(() => btn.classList.remove('done'), 1200);
    showToast(cmd);
  }).catch((err) => {
    const el = document.getElementById('err');
    el.style.display = 'block';
    el.textContent = 'コピー失敗: ' + (err && err.message ? err.message : err);
  });
}
async function runUpdate() {
  const btn = document.getElementById('refresh-btn');
  btn.disabled = true;
  btn.textContent = '更新中…';
  try {
    const res = await fetch('http://localhost:8000/run/tver', { method: 'POST' });
    if (res.ok) { setTimeout(() => location.reload(), 800); return; }
  } catch (e) { /* server なしならただリロード */ }
  setTimeout(() => location.reload(), 200);
}
document.getElementById('grid').addEventListener('click', onDL, true);
render();
</script>
</body>
</html>
"""

# ── 出力 (安全弁つき) ─────────────────────────
def write_html(items: list):
    fetched_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    payload = json.dumps(items, ensure_ascii=False)
    html = TEMPLATE_HTML.replace("__FETCHED_AT__", fetched_at).replace("__ALL_ITEMS__", payload)
    OUTPUT_HTML.write_text(html, encoding="utf-8")

def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] TVer 巡回開始")
    prev_ids = load_prev_ids()
    print(f"  前回ID: {len(prev_ids)} 件")

    try:
        puid, ptok = get_platform_token()
    except Exception as e:
        print(f"  ERROR: トークン発行失敗 {e}")
        print("  → HTML は更新しません (既存 UI を保護)")
        return

    items, seen = fetch_newer(puid, ptok)
    fetch_episode_ranking(puid, ptok, items, seen)
    fetch_series_ranking(puid, ptok, items, seen)

    if not items:
        print("  ERROR: 取得 0 件 (API構造変更/通信エラー)")
        print("  → HTML は更新しません (既存 UI を保護)")
        return

    items = filter_ng_items(items)

    for it in items:
        it["is_new"] = it["id"] not in prev_ids

    # 並び: broadcastDateLabel を月日にパースして降順（新しい放送日が上）
    # 例: '5月11日(月)放送分' → (5, 11)  /  '2021年放送' → (0, 0) で末尾
    now = datetime.now()

    def airdate_sort_key(x):
        label = x.get("airdate", "")
        # '5月11日...' パターン
        m = re.match(r'(\d{1,2})月(\d{1,2})日', label)
        if m:
            mon, day = int(m.group(1)), int(m.group(2))
            # 年またぎ対応: 現在月より大幅に大きければ去年扱い
            year = now.year if mon <= now.month + 1 else now.year - 1
            return (1, year, mon, day)
        # '2024年放送' など年のみ → 末尾グループ
        m2 = re.match(r'(\d{4})年', label)
        if m2:
            return (0, int(m2.group(1)), 0, 0)
        # 完全不明 → 最末尾
        return (0, 0, 0, 0)

    items.sort(key=airdate_sort_key, reverse=True)

    write_html(items)
    print(f"  完了: {len(items)} 件 / NEW {sum(1 for it in items if it['is_new'])} 件 → tver.html")

if __name__ == "__main__":
    main()
