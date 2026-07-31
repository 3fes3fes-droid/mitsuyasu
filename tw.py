#!/usr/bin/env python3
# tw.py - ホームタイムライン取得 → tw.html 生成
#         tw.html  : ホワイトリスト内（フォロー中アカウント）
# 実行: python tw.py
# 前提: twitter-cli (v0.8 以降) が pipx / uv tool でインストール済み
#       ブラウザで x.com にログイン済み、または
#       環境変数 TWITTER_AUTH_TOKEN / TWITTER_CT0 がセット済み

import subprocess
import json
import sys
import os

# Windows環境でのUnicode出力エラー対策
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import re
import html as _html
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ══════════════════════════════════════════════════════════
# 設定
# ══════════════════════════════════════════════════════════
MAX_TWEETS        = 400
FEED_FETCH_ROUNDS = 4
HERE              = Path(__file__).parent
OUTPUT_HTML       = HERE / "tw.html"     # ホワイトリスト内
COOKIE_FILE       = HERE / "file" / "cookie" / "x.com_cookies.txt"

# ══════════════════════════════════════════════════════════
# ホワイトリスト（tw.csv の status=OK のみ・201件）
# ══════════════════════════════════════════════════════════
HARDCODED_FOLLOWING = {
    "32boshiii", "345__chan", "4gamernews", "711sej", "__fubuki",
    "acidman_staff", "aki_e86", "akikiwww", "akira5423", "alicey_mnst",
    "ame__talk", "android", "animejujutsu", "appstore", "appstorejp",
    "ariyoshieeeee", "ariyoshihiroiki", "ariyoshiquiz", "asahi", "ayunid_bish",
    "bakarhythm", "barks_news", "bs_nobrock", "bz_official", "cbc_3puncooking",
    "ciatr_movie", "cinematoday", "cnet_japan", "contents_league", "corombo13",
    "creamnantara", "cx_mezamashi", "daigothebeastjp", "daikeyamamoto",
    "datsuryoku_cx", "delishkitchentv", "dengekionline", "direngrey_jp",
    "dmrc_ayumi", "doorfumi2018", "downtown_plus", "doyokorenbs",
    "eigacom", "eizo_desk", "ellegarden_ofcl", "equal_love_12",
    "esports_rage", "esportsworld_", "famima_now", "famitsu",
    "fearless_pad", "ff16_jp", "ffviir_cloud", "filmarks", "fnn_news",
    "fujitv_nexco", "fukutomemitsuho", "gamebiznews", "gekidanhitori",
    "genspark_japan", "gigazine", "google", "googlejapan", "googleplay",
    "googleplayjp", "gungho_fes", "gusto_official", "hayamizu_lab",
    "hiccorohee0016", "hidukigyouzabou", "hiroe_igeta23", "hoeruyoru_ntv",
    "ilife_official", "impress_watch", "info_puzzdra", "iskw226",
    "itm_nlab", "itmedia_news", "jma_kishou", "jujutsu_pr", "jujutsuphanpara",
    "kano9x", "katayamashozo", "kazlasersub", "kentaro_fujii", "khara_inc",
    "ktai_watch", "kyuso_nekokami", "livedoornews", "londonhearts_sp",
    "madebygoogle", "mahfromsim", "mainichi", "mameshiba_96",
    "matsumoto_city", "mayuhotta0402", "mcdonaldsjapan", "mh_official_jp",
    "michio_isou_bot", "minami373hamabe", "minamishinshu", "mirichamuu_0710",
    "mirrativ_jp", "miyabo01", "mkbhd", "monst_campaign", "monst_goods",
    "monst_mixi", "monst_movie", "monsterbash_", "monsterenergyjp",
    "moon_song", "mori_kasumi_", "moririka_0508", "moueyo_nishida",
    "mst_com", "mth_nao", "mth_official", "musoten_siojiri", "mwamjapan",
    "naganopref", "nana_y1014", "nao0419_gt", "natalie_mu", "nbs_event",
    "nhk_news", "niheiyuka1020", "nikkei_ent", "nikoniko0727",
    "nobrock", "nobrockdocument", "nobrocktv_info", "okbccccccc",
    "openai", "otaueda", "owarai_natalie", "ozwspw", "pad10th",
    "pad_sexy", "papatiwawa", "parlor_abema", "passcodeo", "pazukanachan",
    "pizza_of_death", "playstation_jp", "polngaxnagi", "pop_step_asahi",
    "primevideo_jp", "puzzdra_pr", "puzzdragna", "puzzle_dragonsz",
    "re_road_esports", "realmadrid", "red_star_07", "reutersjapan",
    "rikka_ihara", "rocketnews24", "rockinon_fes", "sama",
    "saraba_morita", "saya__tanaka", "sbctv6ch", "shabekuri007ntv",
    "shiojiritter", "shiro_gw", "sim_official", "skwx", "skyperfectv",
    "soshina3", "spaceshowertv", "sportsnavi", "stage0_jp",
    "sundarpichai", "super_beaver", "taroashida", "tateno_saki1113",
    "tbs_loveit", "tbscdtv", "tenkijp", "the_prodigy", "tiger_sakurai",
    "tim_cook", "tokidoki77", "totsuzen_uranai", "tsubasa_desu",
    "tv_shinshu", "twitchjp", "ucljapan", "un4v5s8bgsvk9xp", "uniqlo_jp",
    "uta_ka923", "wed_downtown", "weeklyascii", "windows_japan",
    "wowow_sogo", "xflag_event", "yahoonewstopics", "yoshizumi_2015",
    "youtube", "youtubejapan", "yudetamagosf","oricon","m3_myk",
    "Anker_JP","adonomori","NetflixJP","denfaminicogame","ore825",
    "HikaruIjuin","anime_jojo","hiruobi_tbs",
    # ── ニュース系追加（一般ニュース・おすすめ5アカウント）──
    "Yomiuri_Online",   # 読売新聞
    "jijicom",          # 時事通信
    "kyodo_official",   # 共同通信
    "sankei_news",      # 産経新聞
    "tbs_news",         # TBSニュース
    # ── 追加アカウント ──
    "daily_gadget_jp",  # デイリーガジェット
    "AUTOMATONJapan",   # AUTOMATON Japan（ゲームメディア）
    "thetvjp",          # the TV（テレビ情報）
    "watch_UNEXT",      # U-NEXT（動画配信）
    "rockinon_com",     # rockin'on（音楽メディア）
    "the_river_jp",     # THE RIVER（映画・海外エンタメ）
    "weeklyflash",      # 週刊FLASH
    "spa_idol",         # SPA!アイドル
}

JST = timezone(timedelta(hours=9))


# ══════════════════════════════════════════════════════════
# Cookie / CLI 実行ヘルパ
# ══════════════════════════════════════════════════════════
def _load_cookie_dict(cookie_path=COOKIE_FILE):
    cookies = {}
    auth = os.environ.get("TWITTER_AUTH_TOKEN", "").strip()
    ct0  = os.environ.get("TWITTER_CT0", "").strip()
    if auth: cookies["auth_token"] = auth
    if ct0:  cookies["ct0"] = ct0

    path = Path(cookie_path)
    if not path.exists():
        return cookies
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            name  = parts[5].strip()
            value = parts[6].strip()
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            if name and value:
                cookies[name] = value
    except Exception as e:
        print(f"  cookie 読込失敗: {e}", file=sys.stderr)
    return cookies


def _build_cli_env():
    env = os.environ.copy()
    env["OUTPUT"] = "json"
    if not env.get("TWITTER_AUTH_TOKEN") or not env.get("TWITTER_CT0"):
        cookies = _load_cookie_dict()
        auth = cookies.get("auth_token", "")
        ct0  = cookies.get("ct0", "")
        if auth and not env.get("TWITTER_AUTH_TOKEN"):
            env["TWITTER_AUTH_TOKEN"] = auth
        if ct0 and not env.get("TWITTER_CT0"):
            env["TWITTER_CT0"] = ct0
    return env


def _run_cli(cmd, timeout=180):
    env = _build_cli_env()
    try:
        r = subprocess.run(
            cmd,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, env=env,
        )
    except FileNotFoundError:
        print("エラー: `twitter` コマンドが見つかりません。"
              "`pipx install twitter-cli` 等でインストールしてください。",
              file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        return None, f"タイムアウト {timeout}s"

    if r.returncode != 0 or not r.stdout.strip():
        return None, f"rc={r.returncode} stderr={r.stderr.strip()[:400]}"

    raw = r.stdout.strip()
    if not (raw.startswith("{") or raw.startswith("[")):
        return None, f"JSONでない出力: {raw[:200]}"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"JSONパースエラー: {e}"


# ══════════════════════════════════════════════════════════
# Feed 取得
# ══════════════════════════════════════════════════════════
def run_twitter_feed_once():
    candidates = [
        ["twitter", "feed", "-t", "following", "--max", str(MAX_TWEETS), "--json"],
        ["twitter", "feed", "--count", str(MAX_TWEETS), "--json"],
        ["twitter", "feed", "-n", str(MAX_TWEETS), "--json"],
        ["twitter", "feed", "--json"],
    ]
    last = ""
    for cmd in candidates:
        data, err = _run_cli(cmd)
        if data is not None:
            return data, None
        last = err or ""
    return None, last


def run_twitter_feed():
    combined_items = []
    seen = set()
    last_err = ""
    last_envelope = None

    for i in range(FEED_FETCH_ROUNDS):
        print(f"  feed 取得 ({i+1}/{FEED_FETCH_ROUNDS})…")
        data, err = run_twitter_feed_once()
        if data is None:
            last_err = err or ""
            print(f"    取得失敗: {last_err[:200]}", file=sys.stderr)
            continue
        last_envelope = data
        items = unwrap_envelope(data)
        added = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            tid = str(it.get("id") or it.get("id_str") or it.get("restId") or it.get("rest_id") or "")
            if not tid or tid in seen:
                continue
            seen.add(tid)
            combined_items.append(it)
            added += 1
        print(f"    +{added} 件 (累計 {len(combined_items)} 件)")

    if not combined_items and last_envelope is None:
        print(f"エラー: twitter feed の取得に失敗\n{last_err}", file=sys.stderr)
        sys.exit(1)

    if last_envelope is not None and isinstance(last_envelope, dict):
        merged = dict(last_envelope)
        merged["data"] = combined_items
        return merged
    return {"ok": True, "data": combined_items}


# ══════════════════════════════════════════════════════════
# ホワイトリスト
# ══════════════════════════════════════════════════════════
def load_following_whitelist():
    wl = set(HARDCODED_FOLLOWING)
    print(f"  ホワイトリスト: {len(wl)} 件")
    return wl


# ══════════════════════════════════════════════════════════
# エンベロープ剥ぎ & 汎用アクセサ
# ══════════════════════════════════════════════════════════
def unwrap_envelope(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    d = data.get("data")
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for key in ("tweets", "items", "results", "list"):
            v = d.get(key)
            if isinstance(v, list):
                return v
    for key in ("tweets", "timeline", "items", "entries"):
        v = data.get(key)
        if isinstance(v, list):
            return v
    return []


def g(obj, *keys, default=""):
    for key in keys:
        cur = obj
        ok = True
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur not in (None, "", [], {}):
            return cur
    return default


def _dig(obj, parts):
    cur = obj
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


# ══════════════════════════════════════════════════════════
# 広告判定
# ══════════════════════════════════════════════════════════
def is_promoted(tw):
    for key in ("isPromoted", "is_promoted", "promoted", "isAd", "is_ad"):
        if tw.get(key) is True:
            return True
    return False


# ══════════════════════════════════════════════════════════
# メディア抽出
# ══════════════════════════════════════════════════════════
def _pick_best_variant(variants):
    if not isinstance(variants, list):
        return ""
    mp4s = []
    for v in variants:
        if not isinstance(v, dict):
            continue
        url   = v.get("url") or v.get("src") or ""
        ctype = (v.get("content_type") or v.get("contentType") or "").lower()
        if not url:
            continue
        if "mp4" in ctype or url.lower().split("?")[0].endswith(".mp4"):
            try:
                br = int(v.get("bitrate") or v.get("bit_rate") or 0)
            except Exception:
                br = 0
            mp4s.append((br, url))
    if mp4s:
        mp4s.sort(reverse=True)
        return mp4s[0][1]
    for v in variants:
        if isinstance(v, dict):
            u = v.get("url") or v.get("src")
            if u:
                return u
    return ""


def extract_media(item):
    out = []
    raw_media = item.get("media") or []
    if not raw_media:
        for path in ("extended_entities.media", "entities.media",
                     "legacy.extended_entities.media", "legacy.entities.media"):
            v = _dig(item, path.split("."))
            if isinstance(v, list) and v:
                raw_media = v
                break

    for m in raw_media:
        if not isinstance(m, dict):
            continue
        mtype   = (m.get("type") or "photo").lower()
        img_url = (
            m.get("url") or m.get("media_url_https") or m.get("media_url")
            or m.get("previewImageUrl") or m.get("preview_image_url") or ""
        )
        is_video  = mtype in ("video", "animated_gif")
        video_url = ""
        poster    = ""

        if is_video:
            video_url = ""
            poster    = ""

            # 1) 明示的な動画URLキーを探す
            for key in ("videoUrl", "video_url", "playbackUrl", "playback_url",
                        "mp4Url", "mp4_url", "src", "downloadUrl"):
                u = m.get(key)
                if u and isinstance(u, str) and u.startswith("http"):
                    video_url = u
                    break

            # 2) variants から最高ビットレートのmp4を選ぶ
            if not video_url:
                for path in ("video_info.variants", "videoInfo.variants",
                             "video.variants", "variants"):
                    v = _dig(m, path.split("."))
                    picked = _pick_best_variant(v) if v else ""
                    if picked:
                        video_url = picked
                        break

            # 3) img_url（m["url"]）がmp4 / video.twimg.com なら video_url として使う
            if not video_url and img_url:
                _ul = img_url.lower().split("?")[0]
                if _ul.endswith(".mp4") or "video.twimg.com" in img_url.lower():
                    video_url = img_url

            # 4) poster は mp4 以外の URL を優先する（mp4 を poster にしない）
            for key in ("previewImageUrl", "preview_image_url",
                        "media_url_https", "media_url", "thumb", "thumbnail"):
                u = m.get(key)
                if u and isinstance(u, str):
                    _ul = u.lower().split("?")[0]
                    if not (_ul.endswith(".mp4") or "video.twimg.com" in u.lower()):
                        poster = u
                        break

            # img_url が画像ならそれを poster に使う
            if not poster and img_url:
                _ul = img_url.lower().split("?")[0]
                if not (_ul.endswith(".mp4") or "video.twimg.com" in img_url.lower()):
                    poster = img_url

            out.append({
                "url": poster or video_url, "is_video": True,
                "video_url": video_url, "poster": poster,
                "link": m.get("expandedUrl") or m.get("expanded_url") or "",
            })
            continue

        if not img_url:
            continue
        out.append({
            "url": img_url, "is_video": False,
            "video_url": "", "poster": "",
            "link": m.get("expandedUrl") or m.get("expanded_url") or "",
        })
    return out


# ══════════════════════════════════════════════════════════
# ツイートパース
# ══════════════════════════════════════════════════════════
def parse_tweets(raw_data, whitelist=None, mode="include"):
    """
    mode="include" : whitelist に「含まれる」ツイートのみ採用 (従来動作・tw.html 用)
    mode="exclude" : whitelist に「含まれない」ツイートのみ採用 (tww.html 用)
                     ※ whitelist=None の場合は mode に関わらず全件採用（フィルタなし）
    """
    items = unwrap_envelope(raw_data)
    tweets = []
    seen_ids = set()
    skipped_ads      = 0
    skipped_offwhite = 0   # mode=include のときに使う
    skipped_inwhite  = 0   # mode=exclude のときに使う
    skipped_empty    = 0
    offwhite_samples = []

    for item in items:
        if not isinstance(item, dict):
            continue

        author = item.get("author") or {}
        if not isinstance(author, dict):
            author = {}

        screen_name = str(
            g(author, "screenName", "screen_name", "username", "handle")
            or g(item, "screenName", "screen_name") or ""
        ).lstrip("@")

        display_name = str(
            g(author, "name", "displayName", "display_name")
            or g(item, "name") or screen_name or ""
        )

        profile_image = str(
            g(author, "profileImageUrl", "profile_image_url",
              "profile_image_url_https", "avatar.image_url", "avatar") or ""
        )
        if profile_image:
            profile_image = profile_image.replace("http://", "https://")
            profile_image = re.sub(
                r"_normal(\.[a-zA-Z]+)(\?.*)?$",
                r"_400x400\1\2",
                profile_image,
            )

        verified = bool(g(author, "verified", default=False))

        tweet_id = str(g(item, "id", "id_str", "restId", "rest_id") or "")
        if not tweet_id or tweet_id in seen_ids:
            continue

        tweet_url = (
            f"https://x.com/{screen_name}/status/{tweet_id}"
            if screen_name else f"https://x.com/i/status/{tweet_id}"
        )
        profile_url = f"https://x.com/{screen_name}" if screen_name else ""

        text = str(g(item, "text", "full_text") or "")

        raw_time   = g(item, "createdAtISO", "createdAt", "created_at", "timestamp")
        time_str   = format_time(raw_time)
        time_epoch = parse_epoch(raw_time)

        metrics  = item.get("metrics") or {}
        likes    = int(g(metrics, "likes",    default=0) or 0)
        retweets = int(g(metrics, "retweets", default=0) or 0)
        replies  = int(g(metrics, "replies",  default=0) or 0)
        views    = int(g(metrics, "views",    default=0) or 0)

        media_list   = extract_media(item)
        is_retweet   = bool(g(item, "isRetweet", "is_retweet", default=False))
        retweeted_by = str(g(item, "retweetedBy", "retweeted_by") or "")

        quoted = item.get("quotedTweet") or item.get("quoted_tweet") or None
        quoted_html_data = None
        if isinstance(quoted, dict):
            q_author = quoted.get("author") or {}
            quoted_html_data = {
                "name":        str(g(q_author, "name", "displayName") or ""),
                "screen_name": str(g(q_author, "screenName", "screen_name") or "").lstrip("@"),
                "text":        str(quoted.get("text") or ""),
            }

        sn_lower = screen_name.lower() if screen_name else ""

        if is_promoted(item):
            skipped_ads += 1
            continue

        if whitelist is not None:
            actor = retweeted_by.lstrip("@").lower() if (is_retweet and retweeted_by) else sn_lower
            if mode == "exclude":
                # ホワイトリストに「入っている」ものは捨てる
                if actor and actor in whitelist:
                    skipped_inwhite += 1
                    continue
                # actor が空のものはどちらに分類しても情報量が低いので除外
                if not actor:
                    skipped_inwhite += 1
                    continue
                if len(offwhite_samples) < 15:
                    offwhite_samples.append(actor)
            else:
                # mode == "include" (従来動作)
                if not actor or actor not in whitelist:
                    skipped_offwhite += 1
                    if len(offwhite_samples) < 15:
                        offwhite_samples.append(actor or "(no-sn)")
                    continue

        if not text and not media_list and not quoted_html_data:
            skipped_empty += 1
            continue

        seen_ids.add(tweet_id)
        tweets.append({
            "id": tweet_id, "screen_name": screen_name,
            "display_name": display_name, "profile_image": profile_image,
            "profile_url": profile_url, "verified": verified,
            "text": text, "tweet_url": tweet_url,
            "time_str": time_str, "time_epoch": time_epoch,
            "likes": likes, "retweets": retweets,
            "replies": replies, "views": views,
            "media": media_list, "is_retweet": is_retweet,
            "retweeted_by": retweeted_by, "quoted": quoted_html_data,
        })

    total = sum(1 for it in items if isinstance(it, dict))
    label = "[除外側]" if mode == "exclude" else "[ホワイト内]"
    print(f"  {label} 取得 {total} 件 → 表示 {len(tweets)} 件")
    msgs = []
    if skipped_ads:      msgs.append(f"広告(isPromoted) {skipped_ads}")
    if skipped_offwhite: msgs.append(f"フォロー外 {skipped_offwhite}")
    if skipped_inwhite:  msgs.append(f"ホワイトリスト内 {skipped_inwhite}")
    if skipped_empty:    msgs.append(f"空 {skipped_empty}")
    if msgs:
        print("  除外: " + " / ".join(msgs))
    if offwhite_samples:
        uniq = sorted(set(offwhite_samples))
        sample_label = "除外側サンプル" if mode == "exclude" else "フォロー外サンプル"
        print(f"  {sample_label}: {', '.join('@'+u for u in uniq[:12])}"
              f"{' …' if len(uniq) > 12 else ''}")

    tweets.sort(key=lambda t: t["time_epoch"] or 0, reverse=True)
    return tweets


# ══════════════════════════════════════════════════════════
# 日時整形
# ══════════════════════════════════════════════════════════
def format_time(raw):
    if not raw:
        return ""
    raw = str(raw).strip()
    dt = _parse_dt(raw)
    if dt:
        return dt.astimezone(JST).strftime("%m/%d %H:%M")
    return raw[:16]


def parse_epoch(raw):
    if not raw:
        return 0
    raw = str(raw).strip()
    dt = _parse_dt(raw)
    if dt:
        return int(dt.timestamp())
    return 0


def _parse_dt(raw):
    if re.fullmatch(r"\d{10}", raw):
        try:
            return datetime.fromtimestamp(int(raw), tz=timezone.utc)
        except Exception:
            pass
    if re.fullmatch(r"\d{13}", raw):
        try:
            return datetime.fromtimestamp(int(raw) / 1000, tz=timezone.utc)
        except Exception:
            pass
    try:
        return datetime.strptime(raw, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════
# HTML ユーティリティ
# ══════════════════════════════════════════════════════════
def esc(s):
    return _html.escape(str(s), quote=True)


URL_RE = re.compile(r'(https?://[^\s<>"\'）】』]+)', re.IGNORECASE)


def linkify(text):
    escaped = esc(text)
    escaped = URL_RE.sub(
        lambda m: (
            f'<a href="{m.group(1)}" target="_blank" rel="noopener noreferrer" '
            f'class="tw-link" onclick="event.stopPropagation()">'
            f'{m.group(1)}</a>'
        ),
        escaped,
    )
    return escaped.replace("\n", "<br>")


def fmt_num(n):
    try:
        n = int(n)
    except Exception:
        return "0"
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        v = n / 1000
        return f"{v:.1f}K".replace(".0K", "K")
    v = n / 1_000_000
    return f"{v:.1f}M".replace(".0M", "M")


# ══════════════════════════════════════════════════════════
# HTML パーツ
# ══════════════════════════════════════════════════════════
def build_media_item(m, tweet_url=""):
    """
    メディアアイテム1つ分の HTML を返す。
    - 動画 / gif → <video> で再生。リンクは tweet_url 優先
    - 画像       → <a><img> で表示。リンクは tweet_url 優先
    link の優先順位: m["link"]（expandedUrl）→ tweet_url → m["url"]（画像直リンク）
    """
    raw_link = m.get("link") or ""
    # expandedUrl が画像 URL そのものの場合も tweet_url を優先する
    _rl = raw_link.lower().split("?")[0]
    if raw_link and (_rl.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"))
                     or "pbs.twimg.com" in raw_link):
        raw_link = ""  # 画像/動画直URLは link として使わず tweet_url へ fallback

    link = esc(raw_link or tweet_url or m["url"])

    if m.get("is_video"):
        video_url = m.get("video_url") or ""
        poster_raw = m.get("poster") or ""
        poster_attr = f'poster="{esc(poster_raw)}"' if poster_raw else ""
        if video_url:
            # MP4 は src に直接、m3u8 (HLS) は data-tw-src で hls.js に渡す
            _vu = video_url.lower().split("?")[0]
            is_hls = _vu.endswith(".m3u8") or ".m3u8" in video_url.lower()
            if is_hls:
                src_attr = f'data-tw-src="{esc(video_url)}" data-tw-hls="1"'
            else:
                src_attr = f'src="{esc(video_url)}" data-tw-src="{esc(video_url)}"'
            return (
                f'<div class="tw-media-item tw-media-video" '
                f'onclick="event.stopPropagation()" '
                f'onmousedown="event.stopPropagation()">'
                f'<video class="tw-video" {src_attr} '
                f'{poster_attr} controls preload="metadata" '
                f'playsinline crossorigin="anonymous" '
                f'onclick="event.stopPropagation()" '
                f'onerror="this.parentElement.classList.add(\'tw-media-fail\');"></video>'
                f'<a class="tw-media-open" href="{link}" target="_blank" '
                f'rel="noopener noreferrer" '
                f'onclick="event.stopPropagation()" title="X で開く">↗</a>'
                f'</div>'
            )
        return (
            f'<a class="tw-media-item" href="{link}" target="_blank" rel="noopener noreferrer">'
            f'<img src="{esc(m["url"])}" loading="lazy" referrerpolicy="no-referrer" '
            f'onerror="this.parentElement.classList.add(\'tw-media-fail\');">'
            f'<span class="tw-media-badge">▶ 動画 (X で開く)</span>'
            f'</a>'
        )
    return (
        f'<a class="tw-media-item" href="{link}" target="_blank" rel="noopener noreferrer">'
        f'<img src="{esc(m["url"])}" loading="lazy" referrerpolicy="no-referrer" '
        f'onerror="this.parentElement.classList.add(\'tw-media-fail\');">'
        f'</a>'
    )


def build_media_html(media, tweet_url=""):
    if not media:
        return ""
    n   = len(media)
    cls = f"tw-media tw-media-{min(n, 4)}"
    parts = [f'<div class="{cls}" onclick="event.stopPropagation()">']
    for m in media[:4]:
        parts.append(build_media_item(m, tweet_url=tweet_url))
    parts.append("</div>")
    return "".join(parts)


def build_quoted_html(q):
    if not q:
        return ""
    q_name   = esc(q["name"] or q["screen_name"])
    q_text   = linkify(q["text"])
    q_handle = esc(q["screen_name"])
    q_prof   = f"https://x.com/{q_handle}" if q_handle else "#"
    return (
        f'<a class="tw-quoted" href="{q_prof}" target="_blank" rel="noopener noreferrer" '
        f'onclick="event.stopPropagation()">'
        f'<span class="tw-quoted-head">'
        f'<span class="tw-quoted-name">{q_name}</span>'
        f'</span>'
        f'<span class="tw-quoted-body">{q_text}</span>'
        f'</a>'
    )


VERIFIED_BADGE = (
    '<svg class="tw-badge" viewBox="0 0 22 22" aria-label="verified">'
    '<path d="M20.396 11a4.35 4.35 0 0 0-2.28-3.83 4.35 4.35 0 0 0-1.297-5.073 4.35 4.35 0 0 0-5.244.252 4.35 4.35 0 0 0-5.244-.252A4.35 4.35 0 0 0 5.034 7.17 4.35 4.35 0 0 0 2.754 11a4.35 4.35 0 0 0 2.28 3.83 4.35 4.35 0 0 0 1.297 5.073 4.35 4.35 0 0 0 5.244-.252 4.35 4.35 0 0 0 5.244.252 4.35 4.35 0 0 0 1.297-5.073A4.35 4.35 0 0 0 20.396 11zm-11.01 3.567L5.95 11.135l1.414-1.414 2.022 2.022 4.65-4.65 1.414 1.414-6.064 6.06z" fill="#1d9bf0"/></svg>'
)

ICON_REPLY = '<svg viewBox="0 0 24 24"><path d="M1.751 10c0-4.42 3.584-8.004 8.005-8.004h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.96-1.607 5.68-4.196 7.11l-8.054 4.46v-3.69h-.067c-4.49.001-8.183-3.61-8.183-8.006zm8.005-6.004c-3.317 0-6.005 2.69-6.005 6.004 0 3.318 2.688 6.005 6.005 6.005h2.067v2.31l5.108-2.83a6.13 6.13 0 0 0 3.152-5.36c0-3.387-2.742-6.13-6.128-6.13H9.756z" fill="currentColor"/></svg>'
ICON_RT    = '<svg viewBox="0 0 24 24"><path d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46L18.5 16.45V8c0-1.1-.896-2-2-2z" fill="currentColor"/></svg>'
ICON_LIKE  = '<svg viewBox="0 0 24 24"><path d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.805 1.09-.806-1.09C9.984 6.01 8.526 5.44 7.304 5.5c-1.243.07-2.349.78-2.91 1.91-.552 1.12-.633 2.78.479 4.82 1.074 1.97 3.257 4.27 7.129 6.61 3.87-2.34 6.052-4.64 7.126-6.61 1.111-2.04 1.03-3.7.477-4.82-.561-1.13-1.666-1.84-2.908-1.91zm4.187 7.69c-1.351 2.48-4.001 5.12-8.379 7.67l-.503.3-.504-.3c-4.379-2.55-7.029-5.19-8.382-7.67-1.36-2.5-1.41-4.86-.514-6.67.887-1.79 2.647-2.91 4.601-3.01 1.651-.09 3.368.56 4.798 2.01 1.429-1.45 3.146-2.1 4.796-2.01 1.954.1 3.714 1.22 4.601 3.01.896 1.81.846 4.17-.514 6.67z" fill="currentColor"/></svg>'
ICON_VIEWS = '<svg viewBox="0 0 24 24"><path d="M8.75 21V3h2v18h-2zM18 21V8.5h2V21h-2zM4 21l.004-10h2L6 21H4zm9.248 0v-7h2v7h-2z" fill="currentColor"/></svg>'


def build_card(t, idx):
    profile_image = esc(t["profile_image"])
    display_name  = esc(t["display_name"])
    screen_name   = esc(t["screen_name"])
    tweet_url     = esc(t["tweet_url"])
    profile_url   = esc(t["profile_url"] or tweet_url)
    time_str      = esc(t["time_str"])
    body_html     = linkify(t["text"])
    media_html    = build_media_html(t.get("media") or [], tweet_url=t["tweet_url"])
    quoted_html   = build_quoted_html(t.get("quoted"))

    if profile_image:
        avatar = (
            f'<img class="tw-avatar" src="{profile_image}" alt="{display_name}" '
            f'loading="lazy" referrerpolicy="no-referrer" '
            f'onerror="this.onerror=null;this.classList.add(\'tw-avatar-blank\');">'
        )
    else:
        avatar = f'<div class="tw-avatar tw-avatar-blank" aria-label="{display_name}"></div>'

    badge = VERIFIED_BADGE if t.get("verified") else ""

    rt_badge = ""
    if t.get("is_retweet") and t.get("retweeted_by"):
        rt_badge = (
            f'<div class="tw-rt-badge">'
            f'{ICON_RT}<span>@{esc(t["retweeted_by"])} がリポスト</span>'
            f'</div>'
        )

    metrics_html = (
        f'<div class="tw-metrics">'
        f'  <span class="tw-metric">{ICON_REPLY}<span>{fmt_num(t.get("replies"))}</span></span>'
        f'  <span class="tw-metric">{ICON_RT}<span>{fmt_num(t.get("retweets"))}</span></span>'
        f'  <span class="tw-metric">{ICON_LIKE}<span>{fmt_num(t.get("likes"))}</span></span>'
        f'  <span class="tw-metric">{ICON_VIEWS}<span>{fmt_num(t.get("views"))}</span></span>'
        f'  <a class="tw-metric tw-metric-open" href="{tweet_url}" '
        f'     target="_blank" rel="noopener noreferrer" '
        f'     onclick="event.stopPropagation()">開く ↗</a>'
        f'</div>'
    )

    _sn_js = screen_name.lower()
    hide_btn = (
        f'<button class="tw-hide-btn" title="非表示にする" '
        f'onclick="event.stopPropagation();twHide(this,&quot;{_sn_js}&quot;)" '
        f'aria-label="非表示">🚫</button>'
    )
    return f"""<article class="tw-card" data-idx="{idx}" data-url="{tweet_url}" data-sn="{screen_name}">
  {hide_btn}
  {rt_badge}
  <header class="tw-header">
    <a class="tw-avatar-link" href="{profile_url}" target="_blank" rel="noopener noreferrer"
       title="@{screen_name} のプロフィールを開く"
       onclick="event.stopPropagation()">{avatar}</a>
    <div class="tw-names">
      <a class="tw-name" href="{profile_url}" target="_blank" rel="noopener noreferrer"
         onclick="event.stopPropagation()">{display_name}{badge}</a>
    </div>
    <div class="tw-header-right">
      <a class="tw-time" href="{tweet_url}" target="_blank" rel="noopener noreferrer"
         onclick="event.stopPropagation()">{time_str}</a>
    </div>
  </header>
  <div class="tw-body">{body_html}</div>
  {media_html}
  {quoted_html}
  {metrics_html}
</article>"""


# ══════════════════════════════════════════════════════════
# HTML 全体
# ══════════════════════════════════════════════════════════
def build_html(tweets, generated_at, mode="include"):
    """
    mode="include" : ホワイトリスト内 (tw.html)
    mode="exclude" : ホワイトリスト外 (tww.html)  ← 見出し表記だけ変える
    """
    if tweets:
        cards_html = "\n".join(build_card(t, i) for i, t in enumerate(tweets))
    else:
        cards_html = (
            '<div class="tw-empty">'
            'ツイートが0件でした。<br>'
            'ターミナルで <code>twitter whoami</code> を実行して認証状態をご確認ください。'
            '</div>'
        )

    count       = len(tweets)
    gen_str     = generated_at.strftime("%Y/%m/%d %H:%M:%S")
    gen_epoch   = int(generated_at.timestamp())
    if mode == "exclude":
        page_title  = "X タイムライン (除外)"
        head_title  = "タイムライン（除外）"
        wl_label    = f"ホワイトリスト外 / 全 {len(HARDCODED_FOLLOWING)} 件中の非対象"
    else:
        page_title  = "X タイムライン"
        head_title  = "タイムライン"
        wl_label    = f"ホワイトリスト {len(HARDCODED_FOLLOWING)} 件"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title} ({count})</title>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.15/dist/hls.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
:root{{
  --bg:#0c0c12;
  --sf:rgba(255,255,255,0.04);
  --sf2:rgba(255,255,255,0.07);
  --bd:rgba(255,255,255,0.08);
  --bdh:rgba(255,255,255,0.22);
  --tx:#e4e2dc;
  --tx2:#c3c1bb;
  --mu:#8a8a8a;
  --mu2:#6e6e6e;
  --ac:#1d9bf0;
  --danger:#f4212e;
  --ff: Meiryo, "メイリオ", "Yu Gothic UI", "Hiragino Kaku Gothic ProN", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
}}
html,body{{background:var(--bg);color:var(--tx);font-family:var(--ff);
  font-size:13px;min-height:100%;-webkit-font-smoothing:antialiased;}}
a{{color:inherit;text-decoration:none;font-family:var(--ff);}}
button,input{{font-family:var(--ff);}}
#tw-toolbar{{
  position:sticky;top:0;z-index:100;
  background:rgba(12,12,18,0.92);backdrop-filter:blur(20px);
  -webkit-backdrop-filter:blur(20px);
  border-bottom:1px solid var(--bd);
  display:flex;align-items:center;gap:10px;
  padding:0 14px;height:46px;flex-wrap:wrap;
}}
#tw-title{{font-size:14px;font-weight:700;color:#fff;display:flex;align-items:center;gap:8px;}}
#tw-title svg{{width:16px;height:16px;fill:#fff;flex-shrink:0;}}
#tw-count{{font-size:12px;color:var(--mu);font-weight:600;}}
#tw-wl{{font-size:11px;color:var(--mu2);padding:2px 8px;border:1px solid var(--bd);border-radius:999px;}}
#tw-generated{{
  font-size:11px;color:var(--mu);margin-left:auto;
  display:flex;align-items:center;gap:6px;
}}
#tw-age{{color:var(--mu2);font-variant-numeric:tabular-nums;}}
#tw-age.stale{{color:#e5a84a;}}
#tw-age.very-stale{{color:var(--danger);}}
.tw-tb-btn{{
  background:rgba(29,155,240,0.14);border:1px solid rgba(29,155,240,0.35);
  color:#1d9bf0;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:700;
  cursor:pointer;transition:all .15s;white-space:nowrap;
  display:inline-flex;align-items:center;gap:6px;
}}
.tw-tb-btn:hover{{background:rgba(29,155,240,0.28);transform:translateY(-1px);}}
#tw-list{{
  max-width:1680px;margin:0 auto;padding:14px 14px 80px;
  display:grid;grid-template-columns:repeat(3,1fr);
  gap:12px;align-items:start;
}}
@media (max-width:1100px){{ #tw-list{{grid-template-columns:repeat(2,1fr);}} }}
@media (max-width:700px){{  #tw-list{{grid-template-columns:1fr;}} }}
.tw-card{{
  background:var(--sf);border:1px solid var(--bd);border-radius:14px;
  padding:12px 14px 10px;display:flex;flex-direction:column;gap:8px;
  transition:border-color .15s, background .15s, transform .15s;
  overflow:hidden;position:relative;
}}
.tw-card:hover{{border-color:var(--bdh);background:var(--sf2);}}
.tw-rt-badge{{
  display:flex;align-items:center;gap:6px;
  font-size:11px;color:var(--mu);padding:0 0 2px 48px;
  margin-bottom:-2px;
}}
.tw-rt-badge svg{{width:12px;height:12px;}}
.tw-header{{display:flex;align-items:flex-start;gap:10px;}}
.tw-avatar-link{{flex-shrink:0;display:block;border-radius:50%;overflow:hidden;}}
.tw-avatar{{
  width:42px;height:42px;border-radius:50%;
  object-fit:cover;display:block;
  background:rgba(255,255,255,0.08);
}}
.tw-avatar-blank{{
  background:linear-gradient(135deg,#2a2a33 0%,#45454f 100%) !important;
}}
.tw-avatar-link:hover .tw-avatar{{opacity:.9;}}
.tw-names{{display:flex;flex-direction:column;min-width:0;flex:1;line-height:1.25;padding-top:2px;}}
.tw-name{{
  font-size:15px;font-weight:700;color:#e8e6e1;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  display:inline-flex;align-items:center;gap:4px;max-width:100%;
}}
.tw-name:hover{{text-decoration:underline;}}
.tw-badge{{width:16px;height:16px;flex-shrink:0;}}
.tw-header-right{{
  display:flex;align-items:center;gap:6px;flex-shrink:0;padding-top:3px;
}}
.tw-time{{font-size:11.5px;color:var(--mu);white-space:nowrap;}}
.tw-time:hover{{color:var(--ac);text-decoration:underline;}}
.tw-body{{
  font-size:17px;line-height:1.6;color:#d4d2cc;
  word-break:break-word;max-height:380px;overflow:hidden;
  position:relative;white-space:pre-wrap;
  letter-spacing:0.01em;
}}
.tw-body::after{{
  content:"";position:absolute;left:0;right:0;bottom:0;height:32px;
  background:linear-gradient(to bottom, transparent, var(--sf) 90%);
  pointer-events:none;opacity:0;transition:opacity .15s;
}}
.tw-card:hover .tw-body::after{{background:linear-gradient(to bottom, transparent, var(--sf2) 90%);}}
.tw-body.overflow::after{{opacity:1;}}
.tw-link{{color:#6ab0f5;}}
.tw-link:hover{{text-decoration:underline;}}
.tw-media{{
  display:grid;gap:2px;border-radius:12px;overflow:hidden;
  border:1px solid var(--bd);background:#000;
}}
.tw-media-1{{grid-template-columns:1fr;}}
.tw-media-2{{grid-template-columns:1fr 1fr;}}
.tw-media-3{{grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;}}
.tw-media-3 .tw-media-item:first-child{{grid-row:span 2;}}
.tw-media-4{{grid-template-columns:1fr 1fr;}}
.tw-media-item{{
  position:relative;width:100%;aspect-ratio:16/10;overflow:hidden;background:#111;display:block;
}}
.tw-media-1 .tw-media-item{{aspect-ratio:16/9;}}
.tw-media-item img{{
  width:100%;height:100%;object-fit:cover;display:block;transition:transform .25s;
}}
.tw-media-item:hover img{{transform:scale(1.03);}}
.tw-media-badge{{
  position:absolute;top:8px;right:8px;
  background:rgba(0,0,0,0.72);color:#fff;
  font-size:11px;padding:2px 7px;border-radius:10px;
  backdrop-filter:blur(4px);
}}
.tw-media-video{{background:#000;}}
.tw-media-video .tw-video{{
  width:100%;height:100%;display:block;object-fit:contain;background:#000;
}}
.tw-media-video .tw-media-open{{
  position:absolute;top:8px;right:8px;z-index:2;
  background:rgba(0,0,0,0.72);color:#fff;
  font-size:12px;padding:2px 8px;border-radius:10px;
  backdrop-filter:blur(4px);text-decoration:none;
}}
.tw-media-video .tw-media-open:hover{{background:rgba(29,155,240,0.85);}}
.tw-media-fail{{position:relative;}}
.tw-media-fail::before{{
  content:"🖼️ メディアを読み込めません";
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  color:var(--mu);font-size:12px;background:#14141b;
  border:1px dashed rgba(255,255,255,0.1);z-index:1;
}}
.tw-media-fail img, .tw-media-fail video{{visibility:hidden;}}
.tw-quoted{{
  display:block;border:1px solid var(--bd);border-radius:10px;
  padding:8px 10px;background:rgba(255,255,255,0.02);
  transition:background .12s, border-color .12s;
}}
.tw-quoted:hover{{background:rgba(255,255,255,0.05);border-color:var(--bdh);}}
.tw-quoted-head{{display:flex;gap:6px;align-items:baseline;font-size:13px;margin-bottom:3px;}}
.tw-quoted-name{{font-weight:700;color:#e8e6e1;}}
.tw-quoted-body{{
  display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;
  overflow:hidden;font-size:15px;color:var(--tx2);line-height:1.55;
  white-space:pre-wrap;
}}
.tw-metrics{{
  display:flex;gap:14px;align-items:center;
  padding-top:6px;border-top:1px dashed var(--bd);
  color:var(--mu);font-size:12px;
}}
.tw-metric{{display:inline-flex;align-items:center;gap:4px;}}
.tw-metric svg{{width:14px;height:14px;opacity:0.8;}}
.tw-metric-open{{margin-left:auto;color:var(--ac);font-weight:600;}}
.tw-metric-open:hover{{text-decoration:underline;}}
.tw-empty{{
  text-align:center;padding:80px 20px;color:var(--mu);font-size:14px;
  grid-column:1/-1;line-height:1.8;
}}
.tw-empty code{{
  background:rgba(255,255,255,0.06);padding:2px 6px;border-radius:4px;
  font-family:Menlo,Consolas,monospace;color:var(--ac);
}}
.tw-hide-btn{{
  position:absolute;top:8px;right:8px;z-index:10;
  background:rgba(0,0,0,0);border:none;
  font-size:14px;cursor:pointer;opacity:0;
  transition:opacity .15s;padding:2px 4px;border-radius:6px;
  line-height:1;
}}
.tw-card:hover .tw-hide-btn{{opacity:0.6;}}
.tw-hide-btn:hover{{opacity:1 !important;background:rgba(255,50,50,0.2);}}
::-webkit-scrollbar{{width:10px;height:10px;}}
::-webkit-scrollbar-track{{background:transparent;}}
::-webkit-scrollbar-thumb{{background:rgba(255,255,255,0.12);border-radius:5px;}}
::-webkit-scrollbar-thumb:hover{{background:rgba(255,255,255,0.22);}}
</style>
</head>
<body>

<div id="tw-toolbar">
  <div id="tw-title">
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.74l7.73-8.835L1.254 2.25H8.08l4.26 5.632 5.905-5.632Zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
    {head_title}
  </div>
  <span id="tw-count">{count} 件</span>
  <span id="tw-wl">{esc(wl_label)}</span>
  <span id="tw-generated">
    <span>生成: {gen_str}</span>
    <span id="tw-age" data-epoch="{gen_epoch}">—</span>
  </span>
  <button class="tw-tb-btn" id="tw-reload" title="クリックで tw.html を再読込（tw.py は手動実行）">
    ↻ 再読込
  </button>
</div>

<div id="tw-list">
{cards_html}
</div>

<script>
(function(){{
  var ageEl = document.getElementById('tw-age');
  var genEpoch = parseInt(ageEl.getAttribute('data-epoch'), 10) * 1000;
  function updateAge(){{
    var sec = Math.max(0, Math.floor((Date.now() - genEpoch) / 1000));
    var label;
    if (sec < 60)         label = sec + '秒前';
    else if (sec < 3600)  label = Math.floor(sec/60) + '分前';
    else if (sec < 86400) label = Math.floor(sec/3600) + '時間前';
    else                  label = Math.floor(sec/86400) + '日前';
    ageEl.textContent = '(' + label + ')';
    ageEl.classList.remove('stale','very-stale');
    if (sec >= 1800) ageEl.classList.add('stale');
    if (sec >= 7200) ageEl.classList.add('very-stale');
  }}
  updateAge();
  setInterval(updateAge, 30000);

  (function(){{
    var btn = document.getElementById('tw-reload');
    if(!btn) return;
    btn.addEventListener('click', function(){{
      if (btn.disabled) return;
      btn.disabled = true;
      btn.textContent = '⏳ 再読込中…';
      // tw.html 自身を再読込（キャッシュ回避クエリ付与）
      try {{
        var url = location.pathname + '?_=' + Date.now();
        location.replace(url);
      }} catch(e) {{
        location.reload();
      }}
    }});
  }})();

  var knownLM = null;
  async function checkFreshness(){{
    try{{
      var r = await fetch(location.pathname + '?ts=' + Date.now(), {{method:'HEAD', cache:'no-store'}});
      var lm = r.headers.get('Last-Modified') || r.headers.get('last-modified');
      if (!lm) return;
      if (knownLM === null) {{ knownLM = lm; return; }}
      if (lm !== knownLM) {{
        knownLM = lm;
        location.replace(location.pathname + '?_=' + Date.now());
      }}
    }}catch(e){{}}
  }}
  window.addEventListener('focus', checkFreshness);
  document.addEventListener('visibilitychange', function(){{
    if (document.visibilityState === 'visible') checkFreshness();
  }});

  var TW_HIDDEN_KEY = 'tw_hidden_accounts';
  function twGetHidden(){{
    try{{ return JSON.parse(localStorage.getItem(TW_HIDDEN_KEY) || '[]'); }}
    catch(e){{ return []; }}
  }}
  function twHide(btn, sn){{
    var hidden = twGetHidden();
    if(hidden.indexOf(sn) === -1){{
      hidden.push(sn);
      localStorage.setItem(TW_HIDDEN_KEY, JSON.stringify(hidden));
    }}
    var card = btn.closest('.tw-card');
    if(card){{
      card.style.transition = 'opacity .3s';
      card.style.opacity = '0';
      setTimeout(function(){{ card.remove(); }}, 300);
    }}
  }}
  (function(){{
    var hidden = twGetHidden();
    if(!hidden.length) return;
    document.querySelectorAll('.tw-card').forEach(function(card){{
      var sn = (card.getAttribute('data-sn') || '').toLowerCase();
      if(hidden.indexOf(sn) !== -1) card.remove();
    }});
  }})();

  document.querySelectorAll('.tw-body').forEach(function(el){{
    if (el.scrollHeight > el.clientHeight + 2) el.classList.add('overflow');
  }});

  document.querySelectorAll('.tw-card').forEach(function(card){{
    card.addEventListener('click', function(e){{
      var sel = window.getSelection && window.getSelection().toString();
      if (sel && sel.length > 0) return;
      // 動画/メディア領域内のクリックはカード遷移を発火しない
      if (e.target && e.target.closest && e.target.closest('.tw-media-video, .tw-media, video, audio, button, input, a')) return;
      var tn = (e.target && e.target.tagName || '').toLowerCase();
      if (tn === 'video' || tn === 'source' || tn === 'button' || tn === 'input' || tn === 'a') return;
      var url = card.getAttribute('data-url');
      if (url) window.open(url, '_blank', 'noopener,noreferrer');
    }});
  }});

  // ── 動画再生 (MP4 はネイティブ / m3u8 は hls.js) ──────────────
  function twInitVideo(v){{
    if (v.dataset.twInited === '1') return;
    v.dataset.twInited = '1';
    var src = v.getAttribute('data-tw-src') || v.getAttribute('src') || '';
    var isHls = v.getAttribute('data-tw-hls') === '1' || /\\.m3u8(\\?|$)/i.test(src);
    if (!src) return;
    if (isHls) {{
      // Safari は HLS をネイティブ再生可能
      if (v.canPlayType('application/vnd.apple.mpegurl')) {{
        if (!v.getAttribute('src')) v.setAttribute('src', src);
      }} else if (window.Hls && window.Hls.isSupported()) {{
        try {{
          var hls = new Hls({{ enableWorker: true, lowLatencyMode: false }});
          hls.on(Hls.Events.ERROR, function(_, data){{
            if (data && data.fatal) {{
              v.parentElement && v.parentElement.classList.add('tw-media-fail');
            }}
          }});
          hls.loadSource(src);
          hls.attachMedia(v);
        }} catch(err) {{
          v.parentElement && v.parentElement.classList.add('tw-media-fail');
        }}
      }} else {{
        v.parentElement && v.parentElement.classList.add('tw-media-fail');
      }}
    }} else {{
      if (!v.getAttribute('src')) v.setAttribute('src', src);
      // crossorigin=anonymous で 403 になる Twitter CDN もあるので外す
      v.removeAttribute('crossorigin');
    }}
    // ネイティブの canplay 失敗 → エラー表示
    v.addEventListener('error', function(){{
      v.parentElement && v.parentElement.classList.add('tw-media-fail');
    }});
  }}
  // 初期: ビューポート内の動画だけ初期化（IntersectionObserver で遅延）
  var twVideos = document.querySelectorAll('video.tw-video');
  if ('IntersectionObserver' in window) {{
    var io = new IntersectionObserver(function(entries){{
      entries.forEach(function(en){{
        if (en.isIntersecting) {{
          twInitVideo(en.target);
          io.unobserve(en.target);
        }}
      }});
    }}, {{ rootMargin: '200px' }});
    twVideos.forEach(function(v){{ io.observe(v); }});
  }} else {{
    twVideos.forEach(twInitVideo);
  }}
}})();
</script>

</body>
</html>
"""


# ══════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════
def main():
    print(f"▶ twitter feed を取得中 (max={MAX_TWEETS} × {FEED_FETCH_ROUNDS}回)")
    data = run_twitter_feed()

    if isinstance(data, dict) and data.get("ok") is False:
        err = data.get("error") or {}
        print(f"  警告: ok=false  code={err.get('code')}  msg={err.get('message')}",
              file=sys.stderr)

    print("▶ ホワイトリストを準備中")
    wl = load_following_whitelist()

    generated_at = datetime.now(JST)

    # ── ① ホワイトリスト内 (tw.html) ───────────────────────
    print("▶ ツイートを解析中 [ホワイトリスト内]")
    tweets_in = parse_tweets(data, whitelist=wl, mode="include")
    if not tweets_in:
        print("警告: 表示可能なツイート(ホワイト内)が 0 件でした。", file=sys.stderr)
    print(f"  最終表示 [tw.html]: {len(tweets_in)} 件")
    html_in = build_html(tweets_in, generated_at, mode="include")
    OUTPUT_HTML.write_text(html_in, encoding="utf-8")
    print(f"✅ 生成完了: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
