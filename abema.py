#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abema 全量クローラー (abema.py) — 2026-05 修正版 r4

r4 修正点:
  - ★ timetable/dataSet を追加取得し、番組表 slots から displayProgramId を回収
  - ★ チャンネルIDからジャンル分類して、ABEMA全体の50チャンネルを拾う入口を追加
  - ★ ニュース汎用枠・期限切れ枠を設定で除外可能
  - ★ timetable由来のカードにチャンネル名・説明文・source を保持

r3 修正点:
  - ★ フィルターボタン群をHTML生成テンプレートから削除
  - ★ render() は常に ALL_ITEMS 全件を表示するように変更

r2 修正点 (4列表示崩れ & py実行で真っ白 対策):
  - ★ JSON payload 中の '</' を '<\\/' にエスケープして
       script タグを途中で閉じてしまう事故を防止
  - ★ ALL_ITEMS が空 / 不正でも render() が落ちないよう try/catch 全体ガード
  - ★ window.onerror で JS 例外を画面表示 (二度と「真っ白」にならない)
  - ★ グリッドを 4 列固定維持しつつ minmax で最低幅確保、各カードの
       メタデータ崩れも修正 (card-text の min-width:0 等)
  - safe_int() で end_at の TypeError 防止 (前回からの継続)

トークン更新方法:
  1. ブラウザで abema.tv を開いて F12 → Application → Local Storage → abm_token をコピー
  2. file/abema_token.txt に保存

更新ボタン:
  POST http://localhost:8000/run/abema (server.py) を叩く
  サーバ無しなら window.location.reload() にフォールバック
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
BASE_DIR    = Path(__file__).parent
OUTPUT_HTML = BASE_DIR / "abema.html"
TOKEN_FILE  = BASE_DIR / "file" / "abema_token.txt"

# 直接トークンを書きたい場合 (空なら token ファイルから読む)
ABM_TOKEN = ""

# 取得上限
MAX_PER_GENRE = 0  # 0 = 無制限。全spotIdを最後まで回す

# サーバ無しでもブラウザから上書きできない型のコンテンツは除外
SKIP_TYPES = {"CONTENT_TYPE_LINK", "CONTENT_TYPE_SLOT", "CONTENT_TYPE_PLAYLIST"}

# timetable/dataSet 由来の番組表も拾う
USE_TIMETABLE_DATASET = True

# True: 見逃し無料が付いている slots だけ拾う。False: 番組表の全 slots を拾う
TIMETABLE_FREE_ONLY = True

# True: すでに見逃し期限が切れている timetable 枠を捨てる
TIMETABLE_DROP_EXPIRED = True

# True: 「ABEMA NEWS 最新ニュース」系の量産枠を捨てる。
# 4103件ぜんぶ見たい時は False にする
TIMETABLE_SKIP_GENERIC_NEWS = True

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

# ABEMAの韓国系チャンネルID。NGワード判定とは別に固定除外する
KOREA_CHANNEL_IDS = {
    "k-world",
}
KOREA_CHANNEL_PREFIXES = (
    "asia-",
)


# ── エンドポイント定義 ─────────────────────────
_API  = "https://api.p-c3-e.abema-tv.com"
_UAPI = "https://user-content-api.p-c3-e.abema-tv.com"

# spotId経由のみ（genre API は404多発のため除外）
# 2026-05 追加: ブラウザ Network タブで取得した spotId (anime/movie/documentary/music)
ENDPOINTS = [
    ("variety",      [f"{_UAPI}/v1/modules?spotId=dbExU5YM&limit=100"]),
    ("drama",        [f"{_UAPI}/v1/modules?spotId=csMgYFy3&limit=100"]),
    ("news",         [f"{_UAPI}/v1/modules?spotId=pjHHH9ov&limit=100"]),
    ("sports",       [f"{_UAPI}/v1/modules?spotId=TEfLRJHA&limit=100"]),
    ("anime",        [f"{_UAPI}/v1/modules?spotId=RtUUNFTVtb&limit=100"]),

    # ABEMA tag page:
    # https://abema.tv/tag/08244a54-a8f8-45db-99a1-00207982ab8a
    # DevTools Request URL:
    # https://user-content-api.p-c3-e.abema-tv.com/v1/modules?spotId=08244a54-a8f8-45db-99a1-00207982ab8a&spotVersion=1&limit=8&qos=SPBrowser&qpl=web&include=liveEvent&variationId=not-available&mylistOrderType=updated_at_desc
    ("anime_tag_08244", [
        f"{_UAPI}/v1/modules?spotId=08244a54-a8f8-45db-99a1-00207982ab8a&spotVersion=1&limit=8&qos=SPBrowser&qpl=web&include=liveEvent&variationId=not-available&mylistOrderType=updated_at_desc"
    ]),

    ("movie",        [f"{_UAPI}/v1/modules?spotId=emcPpE8hSp&limit=100"]),
    ("documentary",  [f"{_UAPI}/v1/modules?spotId=f8MrWu2YEG&limit=100"]),
    ("music",        [f"{_UAPI}/v1/modules?spotId=gGUS8RUiNa&limit=100"]),
]

ANIME_KEYWORDS = {"アニメ", "animation", "世界見逃し", "懐かしアニメ", "2.5次元"}

# is_anime() で除外するジャンルIDプレフィックス (これらがあれば絶対アニメ扱いしない)
NON_ANIME_GENRE_IDS = {"drama", "news", "sports", "movie", "variety", "music", "documentary"}

GENERIC_NEWS_TITLE_PATTERNS = (
    "ABEMA NEWS　お休み前に最新ニュース",
    "ABEMA NEWS　お出かけ前に最新ニュース",
    "ABEMA NEWS　すきま時間に最新ニュース",
    "ABEMA NEWS　最新ニュース＆注目会見",
    "ABEMA NEWS　最新ニュース＆話題の企画",
    "最新ニュース＆注目会見を速報",
    "16時の最新ニュース",
)

# ライブ専用チャンネル: s0枠はVOD化されず404になる
TIMETABLE_LIVE_ONLY_CHANNELS = {
    "abema-news", "news-plus", "sumo", "keirin-auto", "boatrace",
}

def is_likely_live_slot(pid: str, channel_id: str) -> bool:
    """ライブ専用チャンネルのs0枠はVODページが存在しない"""
    if channel_id not in TIMETABLE_LIVE_ONLY_CHANNELS:
        return False
    return "_s0_" in pid

# timetable の channelId → genre。足りない分は classify_channel() で文字列判定する
CHANNEL_GENRE_MAP = {
    # news
    "abema-news": "news",
    "news-plus": "news",

    # variety / special
    "abema-special": "variety",
    "special-plus": "variety",
    "special-plus-2": "variety",

    # anime
    "abema-anime": "anime",
    "abema-anime-2": "anime",
    "abema-anime-3": "anime",
    "special-plus-7": "variety",
    "anime-special-2": "anime",
    "anime-live": "anime",
    "anime-live2": "anime",
    "anime-live3": "anime",
    "chibimaruko": "anime",
    "atashinchi": "anime",
    "lovelive": "anime",
    "isekai-anime": "anime",
    "isekai-anime-2": "anime",
    "isekai-anime-3": "anime",
    "pokemon-1": "anime",
    "pokemon-2": "anime",
    "conan": "anime",
    "onepiece": "anime",
    "family-anime-1": "anime",
    "family-anime-2": "anime",
    "lovecomedy-anime": "anime",
    "dailylife-anime": "anime",
    "late-night-anime": "anime",
    "80s-anime-1": "anime",
    "90s-anime-1": "anime",
    "00s-anime-1": "anime",

    # drama / movie
    "asia-drama": "drama",
    "asia-drama-2": "drama",
    "chinese-drama": "drama",
    "asia-love-comedy": "drama",
    "asia-loveromance": "drama",
    "asia-historical": "drama",
    "k-world": "drama",
    "drama": "drama",
    "drama-2": "drama",
    "drama-3": "drama",

    # sports / games
    "mahjong": "sports",
    "shogi": "sports",
    "world-sports": "sports",
    "sumo": "sports",
    "fighting-sports": "sports",
    "boatrace": "sports",
    "keirin-auto": "sports",

    # music / misc
    "hiphop": "music",
    "commercial": "other",
}

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Origin":  "https://abema.tv",
    "Referer": "https://abema.tv/",
    "Accept":          "application/json",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

# ── トークン管理 ─────────────────────────────
def load_token():
    if ABM_TOKEN.strip():
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(ABM_TOKEN.strip(), encoding="utf-8")
        print("  トークンを保存しました (ABM_TOKEN)")
        return ABM_TOKEN.strip()
    if TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if t:
            print(f"  保存済みトークン使用 (...{t[-8:]})")
            return t
    print("ERROR: abm_token がありません。")
    print("  → abema.tv → F12 → Application → Local Storage → abm_token をコピーして")
    print(f"     {TOKEN_FILE} に貼り付けてください")
    sys.exit(1)

# ── 既存 ID 吸い出し ─────────────────────────
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
            # script タグ閉じ防止のために '<\\/' を戻す
            raw = m.group(1).replace(r'<\/', '</')
            for it in json.loads(raw):
                if isinstance(it, dict) and it.get("id"):
                    ids.add(it["id"])
        except Exception:
            pass
    print(f"  前回HTML から {len(ids)} 件のIDを取得")
    return ids

# ── サムネ抽出 ──────────────────────────────
def extract_thumb(item):
    t = item.get("thumb") or item.get("thumbnail") or item.get("thumbnailInfo") or item.get("image") or {}
    if isinstance(t, dict):
        for k in ("landscape", "w1280", "w768", "w480", "url"):
            v = t.get(k)
            if v: return v
        prefix = t.get("urlPrefix")
        fname  = t.get("filename")
        if prefix and fname: return f"{prefix}/{fname}"
    return item.get("thumbnailUrl") or item.get("imageUrl") or ""

# ── アニメ判定 ──────────────────────────────
def is_anime(item):
    # 1) APIが明示的に非アニメジャンルを返している場合は優先してFalseを返す
    for k in ("genre", "genreId", "category", "categoryId"):
        v = str(item.get(k, "")).lower()
        if v and any(v.startswith(ng) for ng in NON_ANIME_GENRE_IDS):
            return False
    # 2) APIがアニメジャンルを明示している場合は True
    for k in ("genre", "genreId", "category", "categoryId"):
        v = str(item.get(k, "")).lower()
        if "animation" in v or v == "anime":
            return True
    # 3) チャンネルIDが非アニメ系なら False（キーワード誤判定を防ぐ）
    cid = str(item.get("channelId") or item.get("channel_id") or "").lower()
    if cid and cid in CHANNEL_GENRE_MAP and CHANNEL_GENRE_MAP[cid] != "anime":
        return False
    # 4) タイトル/シリーズのキーワード判定（フォールバック）
    text = (item.get("title") or "") + (item.get("seriesTitle") or "") + (item.get("contentGroupTitle") or "")
    return any(kw in text for kw in ANIME_KEYWORDS)

def classify_channel(channel_id, channel_name=""):
    """timetable/dataSet の channelId から既存UI用 genre に寄せる"""
    cid = (channel_id or "").lower()
    name = channel_name or ""
    if cid in CHANNEL_GENRE_MAP:
        return CHANNEL_GENRE_MAP[cid]
    text = f"{cid} {name}".lower()
    if "anime" in text or "アニメ" in name or any(x in cid for x in ("pokemon", "conan", "onepiece")):
        return "anime"
    if "news" in text or "ニュース" in name or "会見" in name:
        return "news"
    if "drama" in text or "ドラマ" in name or "韓国" in name or "中国" in name:
        return "drama"
    if "movie" in text or "映画" in name:
        return "movie"
    if "sports" in text or "スポーツ" in name or any(x in name for x in ("麻雀", "将棋", "相撲", "格闘", "競輪", "オートレース", "BOATRACE")):
        return "sports"
    if "music" in text or "hiphop" in text or "音楽" in name:
        return "music"
    return "other"

def is_generic_news_slot(slot):
    title = slot.get("title") or ""
    if not title:
        return False
    if (slot.get("channelId") or "") not in {"abema-news", "news-plus"}:
        return False
    return any(p in title for p in GENERIC_NEWS_TITLE_PATTERNS)

def slot_thumb_url(pid, updated_at=0):
    """
    番組表 slots はサムネURLを直接持たず、displayProgramId と更新時刻だけ持つ。
    ABEMAの番組画像でよく使われる hayabusa のURLを組み立てる。
    もし表示されない場合でもカード自体は生きる。
    """
    if not pid:
        return ""
    u = safe_int(updated_at)
    qs = f"?version={u}" if u else ""
    return f"https://image.p-c2-x.abema-tv.com/image/programs/{pid}/thumb001.png{qs}"

# ── ID 妥当性 ──────────────────────────────
def is_valid_id(cid):
    return bool(cid) and isinstance(cid, str) and not cid.startswith("tabView#")

# ── end_at を安全に int に変換 ─────────────────
def safe_int(v):
    """文字列・None・数値を安全に int に変換。失敗したら 0 を返す"""
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0

# ── 再帰ウォーカでコンテンツ抽出 ────────────────
_LIST_KEYS   = ("items", "contents", "programs", "slots", "modules", "episodes")
_NESTED_KEYS = ("program", "slot", "series", "content", "module")

def _looks_like_content(d):
    if not isinstance(d, dict):
        return False
    return any(k in d for k in ("contentId", "programId", "seriesId", "id"))

def process_items(data, seen, items, genre):
    def walk(node, depth=0):
        if depth > 10:
            return
        if isinstance(node, dict):
            if _looks_like_content(node):
                cid = node.get("contentId") or node.get("id") or node.get("programId")
                if is_valid_id(cid) and cid not in seen:
                    ct = node.get("contentType", "")
                    if not ct or ct not in SKIP_TYPES:
                        seen.add(cid)
                        is_anm = is_anime(node)
                        start_at = safe_int(
                            node.get("startAt")
                            or node.get("freeStartAt")
                            or node.get("publishedAt")
                            or node.get("publishStartAt")
                            or 0
                        )
                        end_at = safe_int(
                            node.get("freeEndAt") or node.get("endAt") or node.get("expiredAt") or 0
                        )
                        title = node.get("title") or node.get("name") or ""
                        thumb = extract_thumb(node)
                        # タイトルなし＆サムネなしはゴミノードなので除外
                        if title or thumb:
                            # anime_tag_* はすべて anime に統一
                            # ただし、エンドポイントが drama/news/sports 等を明示している場合は優先する
                            _non_anime_genres = {"drama", "news", "sports", "movie", "variety", "music", "documentary"}
                            if genre.startswith("anime") or genre == "anime_tag_08244":
                                effective_genre = "anime"
                            elif genre in _non_anime_genres:
                                # エンドポイントの明示ジャンルを尊重し、is_anm では上書きしない
                                effective_genre = genre
                            else:
                                # genre が "other" や未分類の場合のみ is_anm で補完
                                effective_genre = "anime" if is_anm else genre
                            # broadcast_ymd: start_at から "YYYY-MM-DD" を生成
                            broadcast_ymd = ""
                            if start_at > 0:
                                try:
                                    broadcast_ymd = datetime.fromtimestamp(start_at).strftime("%Y-%m-%d")
                                except Exception:
                                    pass
                            items.append({
                                "id":            cid,
                                "contentType":   ct,
                                "genre":         effective_genre,
                                "title":         title or "無題",
                                "series":        node.get("seriesTitle") or node.get("contentGroupTitle") or "",
                                "end_at":        end_at,
                                "start_at":      start_at,
                                "broadcast_ymd": broadcast_ymd,
                                "thumb":         thumb,
                                "url":           f"https://abema.tv/video/episode/{cid}",
                                "is_new":        False,
                            })
            for nk in _NESTED_KEYS:
                if nk in node:
                    walk(node[nk], depth + 1)
            for lk in _LIST_KEYS:
                if lk in node and isinstance(node[lk], list):
                    for it in node[lk]:
                        walk(it, depth + 1)
        elif isinstance(node, list):
            for it in node:
                walk(it, depth + 1)
    walk(data)


# ── timetable/dataSet から slots 抽出 ────────────────
def process_timetable_dataset(data, seen, items):
    """
    /v1/timetable/dataSet の slots から、見逃しURLに使える displayProgramId を抽出する。
    c.py の確認結果では slots はトップレベルに入り、content は dict ではなく str。
    """
    if not isinstance(data, dict):
        return {"slots": 0, "added": 0, "free_skip": 0, "expired_skip": 0, "generic_skip": 0, "dup_skip": 0}

    channels = data.get("channels") or []
    ch_name = {ch.get("id", ""): (ch.get("name") or ch.get("title") or "") for ch in channels if isinstance(ch, dict)}
    slots = data.get("slots") or []

    now = int(time.time())
    stat = {"slots": len(slots), "added": 0, "free_skip": 0, "expired_skip": 0, "generic_skip": 0, "dup_skip": 0}

    for s in slots:
        if not isinstance(s, dict):
            continue

        flags = s.get("flags") or {}
        if TIMETABLE_FREE_ONLY and not flags.get("timeshiftFree"):
            stat["free_skip"] += 1
            continue

        if TIMETABLE_SKIP_GENERIC_NEWS and is_generic_news_slot(s):
            stat["generic_skip"] += 1
            continue

        pid = s.get("displayProgramId") or s.get("programId") or ""
        if not is_valid_id(pid):
            continue
        if pid in seen:
            stat["dup_skip"] += 1
            continue

        start_at = safe_int(s.get("startAt") or s.get("tableStartAt") or 0)
        end_at = safe_int(
            s.get("timeshiftFreeEndAt")
            or s.get("timeshiftEndAt")
            or s.get("endAt")
            or s.get("tableEndAt")
            or 0
        )
        # 未放送(start_at が未来)はVODなし・サムネなし → 除外
        if start_at > 0 and start_at > now:
            stat["future_skip"] = stat.get("future_skip", 0) + 1
            continue
        # ライブ専用チャンネルのs0枠はVODページなし → 除外
        if is_likely_live_slot(pid, s.get("channelId") or ""):
            stat["live_skip"] = stat.get("live_skip", 0) + 1
            continue
        if TIMETABLE_DROP_EXPIRED and end_at and end_at <= now:
            stat["expired_skip"] += 1
            continue

        cid = s.get("channelId") or ""
        cname = ch_name.get(cid, cid)
        title = s.get("title") or "無題"
        desc = s.get("detailHighlight") or s.get("highlight") or s.get("content") or ""
        group_id = s.get("groupId") or ""
        sid = s.get("displaySeriesId") or ""

        broadcast_ymd = ""
        if start_at > 0:
            try:
                broadcast_ymd = datetime.fromtimestamp(start_at).strftime("%Y-%m-%d")
            except Exception:
                pass

        seen.add(pid)
        items.append({
            "id":            pid,
            "slot_id":       s.get("id") or "",
            "group_id":      group_id,
            "series_id":     sid,
            "contentType":   "TIMETABLE_SLOT",
            "source":        "timetable",
            "genre":         classify_channel(cid, cname),
            "title":         title,
            # UIの青文字にはチャンネル名を出す。シリーズIDは保持だけする
            "series":        cname,
            "channel":       cname,
            "channel_id":    cid,
            "description":   desc,
            "end_at":        end_at,
            "start_at":      start_at,
            "broadcast_ymd": broadcast_ymd,
            "thumb":         slot_thumb_url(pid, s.get("displayImageUpdatedAt")),
            "url":           f"https://abema.tv/video/episode/{pid}",
            "is_new":        False,
        })
        stat["added"] += 1

    return stat


def is_ng_item(item: dict) -> bool:
    """NGワード対象コンテンツなら True。HTML生成前の固定除外に使う。"""
    if not HIDE_NG_CONTENT or not isinstance(item, dict):
        return False

    channel_id = str(item.get("channel_id") or item.get("channelId") or "").lower()
    if channel_id in KOREA_CHANNEL_IDS:
        return True
    if any(channel_id.startswith(prefix) for prefix in KOREA_CHANNEL_PREFIXES):
        return True

    text = "\n".join(str(item.get(k, "") or "") for k in (
        "title",
        "episode_title",
        "series",
        "channel",
        "description",
        "broadcaster",
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


# ── 取得 ───────────────────────────────────
def fetch_one(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401:
            print(f"    401 (token expired?) {url[:80]}")
        else:
            print(f"    {r.status_code} {url[:80]}")
    except Exception as e:
        print(f"    ERR {e} {url[:80]}")
    return None

def fetch_all(token):
    headers = {**HEADERS_BASE, "Authorization": f"Bearer {token}"}
    items, seen = [], set()

    # 1) 既存の spotId / modules 系
    for genre, urls in ENDPOINTS:
        n0 = len(items)
        for url in urls:
            data = fetch_one(url, headers)
            if data:
                process_items(data, seen, items, genre)
            if MAX_PER_GENRE and len(items) - n0 >= MAX_PER_GENRE:
                break
        print(f"  [{genre:12s}] +{len(items) - n0} 件 (累計 {len(items)})")

    # 2) 新規: ABEMA番組表 dataSet。ここが大量回収ポイント
    if USE_TIMETABLE_DATASET:
        n0 = len(items)
        url = f"{_API}/v1/timetable/dataSet?debug=false"
        data = fetch_one(url, headers)
        if data:
            stat = process_timetable_dataset(data, seen, items)
            print(
                f"  [{'timetable':12s}] +{len(items) - n0} 件 (累計 {len(items)}) "
                f"slots={stat['slots']} freeSkip={stat['free_skip']} futureSkip={stat.get('future_skip',0)} liveSkip={stat.get('live_skip',0)} "
                f"expiredSkip={stat['expired_skip']} genericSkip={stat['generic_skip']} dup={stat['dup_skip']}"
            )

    return items

# ── HTML テンプレート (TVer 風 UI) ─────────────
TEMPLATE_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ABEMA</title>
<style>
:root {
  --bg: #0f0f0f;
  --card: #161616;
  --card-hover: #1f1f1f;
  --text: #f0f0f0;
  --dim: #888;
  --accent: #ff3399;
  --accent2: #ff6ec7;
  --warn: #ffc800;
  --border: #1e1e1e;
  --new-badge: #ff3399;
  --dl-hover: #ff3399;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 100%; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", Meiryo, "Yu Gothic", sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ── ヘッダ ── */
#header {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
}
#header .service-logo {
  display: block;
  width: 104px;
  height: 24px;
  object-fit: contain;
  filter: brightness(0) invert(1);
}
#meta-bar {
  font-size: 12px; color: var(--dim); flex: 1;
}
#refresh-btn {
  background: #222; color: #ccc; border: 1px solid #333;
  padding: 5px 14px; border-radius: 20px; cursor: pointer;
  font-size: 12px; transition: background .15s, color .15s;
}
#refresh-btn:hover { background: #333; color: #fff; }
#refresh-btn:disabled { opacity: .4; cursor: wait; }
#toolbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: #101010;
}
#genre-buttons {
  display: flex; gap: 6px; flex-wrap: wrap; flex: 1;
}
.filter-btn {
  background: #1b1b1b; color: #aaa; border: 1px solid #2a2a2a;
  padding: 5px 10px; border-radius: 999px; cursor: pointer;
  font-size: 12px;
}
.filter-btn:hover { background: #252525; color: #fff; }
.filter-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
#sort-select {
  background: #1b1b1b; color: #ddd; border: 1px solid #333;
  border-radius: 8px; padding: 6px 8px; font-size: 12px;
}

/* ── グリッド: 4 列固定だが最小幅を担保して崩れ防止 ── */
#grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 12px 16px;
  width: 100%;
}
@media (max-width: 1100px) { #grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 760px)  { #grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 480px)  { #grid { grid-template-columns: minmax(0, 1fr); } }

/* ── カード ── */
.card {
  background: var(--card);
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  transition: background .15s;
  min-width: 0;       /* grid アイテムが横にはみ出ないように */
}
.card:hover { background: var(--card-hover); }

.thumb-wrap {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #111;
  overflow: hidden;
}
.thumb-wrap img {
  width: 100%; height: 100%; object-fit: cover;
  display: block;
  transition: transform .25s ease;
}
.card:hover .thumb-wrap img { transform: scale(1.03); }

/* バッジ */
.badge-new {
  position: absolute; top: 6px; left: 6px; z-index: 2;
  background: var(--new-badge); color: #fff;
  font-size: 9px; font-weight: 800; padding: 2px 6px;
  border-radius: 3px; letter-spacing: .5px;
}
.badge-exp {
  position: absolute; bottom: 6px; right: 6px; z-index: 2;
  background: rgba(0,0,0,.85); color: var(--warn);
  font-size: 10px; font-weight: 700; font-family: monospace;
  padding: 2px 6px; border-radius: 4px;
}
.badge-exp.red { color: #ff5c5c; }

/* 情報欄 */
.card-body {
  display: flex; align-items: center;
  padding: 9px 10px 9px 12px;
  gap: 6px;
  text-decoration: none; color: inherit;
}
.card-text { flex: 1 1 auto; min-width: 0; overflow: hidden; }
.card-series {
  font-size: 10px; font-weight: 700; color: #2aacff;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  margin-bottom: 2px;
}
.card-title {
  font-size: 13px; font-weight: 500; line-height: 1.35; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.card-meta {
  font-size: 10px; color: #777;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  margin-top: 3px;
}

/* DLボタン */
.dl-btn {
  flex-shrink: 0;
  background: transparent; border: none; cursor: pointer; padding: 6px;
  color: var(--dim); transition: color .15s;
  display: flex; align-items: center;
}
.dl-btn:hover { color: var(--accent); }
.dl-btn.ok { color: #4caf50; }
.dl-btn svg {
  width: 15px; height: 15px; fill: none; stroke: currentColor;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}

/* 空/エラー */
#empty { display: none; padding: 40px 20px; color: var(--dim); font-size: 14px; text-align: center; }
#err   { display: none; padding: 12px 20px; color: #ff7070; font-size: 13px; white-space: pre-wrap; word-break: break-all; }

/* 日付フィルターバー */
#date-bar {
  display: flex; gap: 6px; flex-wrap: wrap;
  padding: 8px 16px; border-bottom: 1px solid var(--border);
}
.date-btn {
  background: #1b1b1b; color: #999; border: 1px solid #2a2a2a;
  border-radius: 16px; padding: 4px 12px; font-size: 12px; cursor: pointer;
  transition: background .15s, color .15s, border-color .15s;
  white-space: nowrap;
}
.date-btn:hover { background: #252525; color: #fff; }
.date-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 700; }
.date-btn .cnt { opacity: .7; font-size: 11px; margin-left: 3px; }

/* トースト */
#toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: #222; color: #eee; padding: 8px 18px;
  border-radius: 6px; font-size: 13px;
  opacity: 0; transition: opacity .25s; pointer-events: none; z-index: 9999;
  border: 1px solid #333; white-space: nowrap; max-width: 90vw; overflow: hidden; text-overflow: ellipsis;
}
#toast.show { opacity: 1; }

</style>
</head>
<body>

<div id="header">
  <img class="service-logo" src="https://upload.wikimedia.org/wikipedia/commons/1/13/Abema_logo.svg" alt="">
  <button id="refresh-btn" onclick="runUpdate()">↺ 更新</button>
  <span id="meta-bar">—</span>
</div>

<div id="toolbar">
  <div id="genre-buttons"></div>
  <select id="sort-select" title="並び順">
    <option value="start_desc">新しい順</option>
    <option value="new_first">NEW優先</option>
    <option value="end_asc">期限近い順</option>
    <option value="genre">ジャンル順</option>
  </select>
</div>

<div id="date-bar"></div>
<div id="err"></div>
<div id="grid"></div>
<div id="empty">コンテンツが見つかりません</div>
<div id="toast"></div>

<script>
// ── グローバル例外を必ず可視化 (もう「真っ白」にしない) ──
window.addEventListener('error', function(ev) {
  try {
    var el = document.getElementById('err');
    if (el) {
      el.style.display = 'block';
      el.textContent = '[JS Error] ' + (ev.message || ev.error || ev);
    }
  } catch(_) {}
});

const ALL_ITEMS  = __ALL_ITEMS__;
const FETCHED_AT = "__FETCHED_AT__";
const COPY_CMD   = 'y';

let currentGenre = localStorage.getItem('abemaGenre') || 'all';
let currentSort  = localStorage.getItem('abemaSort')  || 'start_desc';
let currentDate  = 'all';  // 日付フィルター ('all' or 'YYYY-MM-DD')

const GENRE_LABELS = {
  all: '全て',
  anime: 'アニメ',
  variety: 'バラエティ',
  drama: 'ドラマ',
  news: 'ニュース',
  sports: 'スポーツ',
  movie: '映画',
  documentary: 'ドキュメンタリー',
  music: '音楽',
  other: 'その他'
};

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtRemain(endAt) {
  if (!endAt) return null;
  const ms = endAt * 1000 - Date.now();
  if (ms <= 0) return null;
  const h = Math.floor(ms / 3600000);
  if (h < 24) return { text: 'あと' + h + 'h', red: true };
  if (h < 72) return { text: 'あと' + Math.floor(h / 24) + 'd', red: false };
  return null;
}

function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise(function(res, rej) {
    try {
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.cssText = 'position:fixed;opacity:0';
      document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); ta.remove(); res();
    } catch(e) { rej(e); }
  });
}

function toast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(function(){ t.classList.remove('show'); }, 2400);
}

function ts(v, key) {
  const n = Number(v && v[key] ? v[key] : 0);
  return Number.isFinite(n) ? n : 0;
}

function fmtDate(sec) {
  const n = Number(sec || 0);
  if (!n) return '';
  const d = new Date(n * 1000);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return y + '/' + m + '/' + day;
}

function getViewItems(src) {
  let list = Array.isArray(src) ? src.slice() : [];

  if (currentGenre !== 'all') {
    list = list.filter(function(v) {
      return String(v.genre || 'other') === currentGenre;
    });
  }
  if (currentDate !== 'all') {
    list = list.filter(function(v) { return v.broadcast_ymd === currentDate; });
  }

  list.sort(function(a, b) {
    if (currentSort === 'new_first') {
      return (Number(!!b.is_new) - Number(!!a.is_new))
          || (ts(b, 'start_at') - ts(a, 'start_at'));
    }
    if (currentSort === 'end_asc') {
      const ae = ts(a, 'end_at') || Number.MAX_SAFE_INTEGER;
      const be = ts(b, 'end_at') || Number.MAX_SAFE_INTEGER;
      return (ae - be) || (ts(b, 'start_at') - ts(a, 'start_at'));
    }
    if (currentSort === 'genre') {
      return String(a.genre || '').localeCompare(String(b.genre || ''), 'ja')
          || (ts(b, 'start_at') - ts(a, 'start_at'));
    }
    // default: start_desc = 放送/配信開始が新しい順
    return (ts(b, 'start_at') - ts(a, 'start_at'))
        || (Number(!!b.is_new) - Number(!!a.is_new));
  });

  return list;
}

function localDateStr(offsetDays) {
  const d = new Date();
  d.setDate(d.getDate() - offsetDays);
  return d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0');
}
const DAY_LABELS = ['今日', '昨日', '一昨日', '3日前', '4日前', '5日前'];
const DAY_YMDS   = DAY_LABELS.map(function(_, i) { return localDateStr(i); });

function buildDateBar() {
  const bar = document.getElementById('date-bar');
  if (!bar || !Array.isArray(ALL_ITEMS)) return;
  const counts = { all: ALL_ITEMS.length };
  DAY_YMDS.forEach(function(ymd) {
    counts[ymd] = ALL_ITEMS.filter(function(v) { return v.broadcast_ymd === ymd; }).length;
  });
  bar.innerHTML = '';
  // 「全て」
  const allBtn = document.createElement('button');
  allBtn.className = 'date-btn' + (currentDate === 'all' ? ' active' : '');
  allBtn.innerHTML = '全て<span class="cnt">' + counts.all + '</span>';
  allBtn.onclick = function() { currentDate = 'all'; buildDateBar(); render(); };
  bar.appendChild(allBtn);
  // 日付ボタン
  DAY_LABELS.forEach(function(label, i) {
    const ymd = DAY_YMDS[i];
    const cnt = counts[ymd] || 0;
    const btn = document.createElement('button');
    btn.className = 'date-btn' + (currentDate === ymd ? ' active' : '');
    btn.style.opacity = cnt === 0 ? '0.35' : '1';
    btn.innerHTML = label + '<span class="cnt">' + cnt + '</span>';
    btn.onclick = function() { currentDate = ymd; buildDateBar(); render(); };
    bar.appendChild(btn);
  });
}

function buildControls() {
  const box = document.getElementById('genre-buttons');
  const sel = document.getElementById('sort-select');
  if (!box || !Array.isArray(ALL_ITEMS)) return;

  const counts = { all: ALL_ITEMS.length };
  for (const v of ALL_ITEMS) {
    const g = String(v.genre || 'other');
    counts[g] = (counts[g] || 0) + 1;
  }

  if (!counts[currentGenre]) currentGenre = 'all';

  const genres = ['all'].concat(Object.keys(counts).filter(function(g){ return g !== 'all'; }).sort());
  box.innerHTML = genres.map(function(g) {
    const label = GENRE_LABELS[g] || g;
    const active = g === currentGenre ? ' active' : '';
    return '<button class="filter-btn' + active + '" data-genre="' + esc(g) + '">' +
           esc(label + ' ' + counts[g]) + '</button>';
  }).join('');

  box.onclick = function(e) {
    const btn = e.target.closest && e.target.closest('.filter-btn');
    if (!btn) return;
    currentGenre = btn.dataset.genre || 'all';
    localStorage.setItem('abemaGenre', currentGenre);
    render();
  };

  if (sel) {
    sel.value = currentSort;
    sel.onchange = function() {
      currentSort = sel.value || 'start_desc';
      localStorage.setItem('abemaSort', currentSort);
      render();
    };
  }
}


function render() {
  try {
    const grid  = document.getElementById('grid');
    const empty = document.getElementById('empty');
    const meta  = document.getElementById('meta-bar');
    if (!grid) return;
    grid.innerHTML = '';

    // メタ情報
    const ft = FETCHED_AT ? FETCHED_AT.replace('T',' ').slice(0,16) : '';
    if (meta) {
      meta.textContent =
        (Array.isArray(ALL_ITEMS) ? ALL_ITEMS.length : 0) + '件' + (ft ? ' · ' + ft + ' 取得' : '');
    }

    if (!Array.isArray(ALL_ITEMS) || ALL_ITEMS.length === 0) {
      if (empty) empty.style.display = 'block';
      return;
    }

    buildControls();
    buildDateBar();
    const view = getViewItems(ALL_ITEMS);

    if (meta) {
      meta.textContent =
        view.length + '/' + ALL_ITEMS.length + '件' + (ft ? ' · ' + ft + ' 取得' : '');
    }

    if (view.length === 0) {
      if (empty) {
        empty.style.display = 'block';
        empty.textContent = 'この条件に合うコンテンツがありません';
      }
      return;
    }

    if (empty) empty.style.display = 'none';

    const frag = document.createDocumentFragment();
    for (const v of view) {
      try {
        const url    = v.url || '#';
        const remain = fmtRemain(v.end_at);
        const card   = document.createElement('div');
        card.className = 'card';
        card.dataset.id = v.id || '';

        const newBadge  = v.is_new ? '<span class="badge-new">NEW</span>' : '';
        const expBadge  = remain ? ('<span class="badge-exp' + (remain.red ? ' red' : '') + '">' + esc(remain.text) + '</span>') : '';

        card.innerHTML =
          '<a href="' + esc(url) + '" target="_blank" rel="noopener" style="display:block;text-decoration:none">' +
            '<div class="thumb-wrap">' +
              '<img src="' + esc(v.thumb || '') + '" referrerpolicy="no-referrer" loading="lazy" alt="" onerror="this.style.display=\'none\'">' +
              newBadge + expBadge +
            '</div>' +
          '</a>' +
          '<div class="card-body">' +
            '<div class="card-text">' +
              (v.series ? ('<div class="card-series">' + esc(v.series) + '</div>') : '') +
              '<div class="card-title" title="' + esc(v.title || '無題') + '">' + esc(v.title || '無題') + '</div>' +
              '<div class="card-meta">' + esc((GENRE_LABELS[v.genre] || v.genre || 'その他') + (v.channel ? ' · ' + v.channel : '') + (v.start_at ? ' · ' + fmtDate(v.start_at) : '')) + '</div>' +
            '</div>' +
            '<button class="dl-btn" data-url="' + esc(url) + '" title="y URLをコピー">' +
              '<svg viewBox="0 0 24 24"><path d="M12 3v13M7 11l5 5 5-5"/><path d="M4 19h16"/></svg>' +
            '</button>' +
          '</div>';
        frag.appendChild(card);
      } catch (eCard) {
        // 1 枚壊れても全体は描画継続
        console.warn('card render error', eCard, v);
      }
    }
    grid.appendChild(frag);
  } catch (e) {
    const el = document.getElementById('err');
    if (el) { el.style.display = 'block'; el.textContent = '[render error] ' + (e && e.message ? e.message : e); }
  }
}

// DL ボタン
(function(){
  const grid = document.getElementById('grid');
  if (!grid) return;
  grid.addEventListener('click', function(e){
    const btn = e.target.closest && e.target.closest('.dl-btn');
    if (!btn) return;
    e.preventDefault(); e.stopPropagation();
    const cmd = COPY_CMD + ' ' + btn.dataset.url;
    copyText(cmd).then(function(){
      btn.classList.add('ok');
      setTimeout(function(){ btn.classList.remove('ok'); }, 1400);
      toast(cmd);
    }).catch(function(err){
      const el = document.getElementById('err');
      if (el) {
        el.style.display = 'block';
        el.textContent = 'コピー失敗: ' + (err && err.message ? err.message : err);
      }
    });
  }, true);
})();


// 更新
async function runUpdate() {
  const btn = document.getElementById('refresh-btn');
  if (btn) { btn.disabled = true; btn.textContent = '更新中…'; }
  try {
    const res = await fetch('http://localhost:8000/run/abema', { method: 'POST' });
    if (res.ok) { setTimeout(function(){ location.reload(); }, 800); return; }
  } catch (_) {}
  setTimeout(function(){ location.reload(); }, 200);
}

render();
</script>
</body>
</html>
"""

def _safe_json_for_script(items):
    r"""
    HTML <script> ブロックに JSON を埋め込むときの安全化:
      - '</' を '<\/' に置換 → </script> による途中閉じを防止
      - U+2028 / U+2029 を \u エスケープ → 一部ブラウザで JS パースエラーになる
    """
    s = json.dumps(items, ensure_ascii=False)
    s = s.replace('</', '<\\/')
    s = s.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return s

def write_html(items: list):
    fetched_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    payload = _safe_json_for_script(items if isinstance(items, list) else [])
    # str.replace を 2 段で。順番は重要 (FETCHED_AT を先に)
    html = TEMPLATE_HTML.replace("__FETCHED_AT__", fetched_at).replace("__ALL_ITEMS__", payload)
    OUTPUT_HTML.write_text(html, encoding="utf-8")

def run_once():
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Abema 巡回開始")
    prev_ids = load_prev_ids()
    token = load_token()
    items = fetch_all(token)

    if not items:
        print("  ERROR: 0 件 (トークン切れ or API 構造変更)")
        print("  → HTML は更新しません (既存 UI を保護)")
        return False

    items = filter_ng_items(items)

    for it in items:
        it["is_new"] = it["id"] not in prev_ids

    # 並び: 放送/配信開始が新しい順 → NEW → ジャンル順
    def sort_key(x):
        start = safe_int(x.get("start_at") or 0)
        end = safe_int(x.get("end_at") or 0)
        return (
            -start if start else 0,
            not x["is_new"],
            x.get("genre") or "",
            end if end else 9_999_999_999,
        )
    items.sort(key=sort_key)

    write_html(items)
    new_cnt = sum(1 for it in items if it["is_new"])
    print(f"  完了: {len(items)} 件 / NEW {new_cnt} 件 → abema.html")
    return True

if __name__ == "__main__":
    run_once()
