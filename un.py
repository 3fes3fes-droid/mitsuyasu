# -*- coding: utf-8 -*-
"""
U-NEXT 作品データベース更新スクリプト

【基本仕様：ここは維持する】
- U-NEXT のランキングを探索の起点にする。
- manual_seeds から任意の SID を追加できる。
- 各作品のタイトル情報・キャスト・監督・スタッフを取得する。
- 関連作品 / おすすめ作品の SID を幅優先で辿り、未取得作品を増やす。
- 作品データ本体は従来どおり unext.json に SID をキーとして保存する。
- unext.json 内の1作品あたりの項目構成は変更しない。

【GitHub Actions 運用向けに変更した部分：2026-09-19】
1. unext_state.json を追加。
   GitHub Actions が件数上限や時間上限で終了しても、未処理キューを保存して
   次回の実行で続きを再開できるようにした。
2. list.pop(0) ではなく deque を使用。
   キューが大きくなっても先頭取り出しが重くならないようにした。
3. requests.Session と HTTP リトライを追加。
   一時的な通信失敗で探索全体が止まりにくいようにした。
4. JSON は一時ファイルへ書いてから os.replace() する。
   保存途中で止まって JSON が壊れる可能性を下げた。
5. SAVE_EVERY / MAX_ITEMS / MAX_RUNTIME_MINUTES 等を環境変数化。
   ローカル実行では従来どおり無制限、GitHub Actions 側だけ上限を設定できる。
6. 取得失敗 SID は同一実行内で数回だけ再試行する。
   上限まで失敗した SID は deferred として次回実行へ回し、
   ランキング外の関連作品でも探索経路を失わないようにした。
7. unext.json の既存データ形式は変更しない。
   unext.html 等、既存の利用側を壊さないことを最優先にしている。
"""

import json
import os
import time
from collections import deque
from urllib.parse import quote

import requests

HEADERS = {
    'accept': '*/*',
    'content-type': 'application/json',
    'apollographql-client-name': 'cosmo',
    'apollographql-client-version': 'v122.0_2-prod-0806c4d',
}

BASE = 'https://cc.unext.jp/?zxuid=25850d33de4e&zxemp=29580560'
OUTPUT = 'unext.json'

# [変更] Actions の途中終了でも関連作品探索の続きを失わないための状態ファイル。
STATE_FILE = 'unext_state.json'

TITLE_HASH = 'c7d557d11776b11c3ca0c920906d79891861117a39b864c56bc074e5628b7163'
CREDITS_HASH = 'bdf1311121839b73cd5222da069ffbe69c2a072cec04af1ae00c60bbb74b8a73'
RANKING_HASH = 'ab04097085a6d372a8a8408992ca6094bbf319fbf5c6921f754ab5ec62c8bb81'

# [変更] ローカルでは 0 = 無制限。Actions からだけ必要な上限を渡せる。
SAVE_EVERY = max(1, int(os.getenv('SAVE_EVERY', '100')))
MAX_ITEMS = max(0, int(os.getenv('MAX_ITEMS', '0')))
MAX_RUNTIME_MINUTES = max(0, int(os.getenv('MAX_RUNTIME_MINUTES', '0')))
REQUEST_TIMEOUT = max(5, int(os.getenv('REQUEST_TIMEOUT', '30')))
MAX_SID_RETRIES = max(1, int(os.getenv('MAX_SID_RETRIES', '3')))
REQUEST_INTERVAL = max(0.0, float(os.getenv('REQUEST_INTERVAL', '0.8')))

# [変更] TCP/TLS 接続を再利用する。
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_atomic(path, data):
    """[変更] 保存途中の破損を避けるため、一時ファイル完成後に置換する。"""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_db():
    return load_json(OUTPUT, {})


def save_db(db):
    save_json_atomic(OUTPUT, db)


def load_state():
    """
    [変更]
    pending  = 通常の未処理キュー。
    deferred = 前回、通信/APIエラーが上限回数続いたため次回送りにした SID。
    """
    state = load_json(STATE_FILE, {})
    pending = state.get('pending', [])
    deferred = state.get('deferred', [])

    if not isinstance(pending, list):
        pending = []
    if not isinstance(deferred, list):
        deferred = []

    return pending, deferred


def save_state(queue, deferred):
    save_json_atomic(STATE_FILE, {
        'pending': list(queue),
        'deferred': list(deferred),
    })


def api_get(operation, variables, sha, retries=3):
    v = quote(json.dumps(variables, ensure_ascii=False))
    e = quote(json.dumps({'persistedQuery': {'version': 1, 'sha256Hash': sha}}))
    url = f'{BASE}&operationName={operation}&variables={v}&extensions={e}'

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            r = SESSION.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                wait = attempt * 2
                print(f'API再試行 {attempt}/{retries - 1}: {wait}秒待機')
                time.sleep(wait)

    raise RuntimeError(f'{operation} 取得失敗: {last_error}')


def get_ranking_sids():
    data = api_get(
        'cosmo_videoRanking',
        {'rankingType': 'ALL', 'isCheck': False},
        RANKING_HASH,
    )

    sids = []
    try:
        for item in data['data']['webfront_videoRanking']['titles']:
            sid = item.get('id')
            if sid:
                sids.append(sid)
    except Exception as e:
        print(f'ランキング取得失敗: {e}')

    return sids


def fetch_one(sid):
    title_data = api_get(
        'cosmo_getVideoTitle',
        {'code': sid},
        TITLE_HASH,
    )

    time.sleep(0.5)

    credits_data = api_get(
        'cosmo_getVideoTitleRelatedStuffs',
        {
            'code': sid,
            'creditsPage': 1,
            'creditsPageSize': 100,
            'relatedContentPage': 1,
            'relatedContentPageSize': 20,
            'includePositionPlayLive': True,
        },
        CREDITS_HASH,
    )

    t = title_data.get('data', {}).get('webfront_title_stage', {})
    if not t:
        return None, []

    thumb = t.get('thumbnail', {}).get('standard', '')
    if thumb and not thumb.startswith('http'):
        thumb = 'https://' + thumb

    # 基本仕様：unext.json の1作品分の構造は元版から変えない。
    entry = {
        'id': t.get('id', ''),
        'title': t.get('titleName', ''),
        'story': t.get('story', ''),
        'catchphrase': t.get('catchphrase', ''),
        'year': t.get('productionYear', ''),
        'country': t.get('country', ''),
        'genre': t.get('mainGenreName', ''),
        'thumbnail': thumb,
        'url': f"https://video.unext.jp/title/{t.get('id', '')}",
        'cast': [],
        'director': [],
        'staff': [],
    }

    related_sids = []

    credits = (
        credits_data
        .get('data', {})
        .get('webfront_title_credits', {})
        .get('titleCredits', [])
    )

    for c in credits:
        name = c.get('personName', '')
        role = c.get('castTypeName', '')

        if role == '出演':
            entry['cast'].append(name)
        elif role in ['監督', 'ディレクター']:
            entry['director'].append(name)
        else:
            entry['staff'].append(f'{name}（{role}）')

    # 基本仕様：関連作品を次の探索候補へ入れる。
    for group in credits_data.get('data', {}).get('webfront_title_relatedTitles', []):
        for title in group.get('titles', []):
            rsid = title.get('id')
            if rsid:
                related_sids.append(rsid)

    # 基本仕様：おすすめ作品も次の探索候補へ入れる。
    recommended = (
        credits_data
        .get('data', {})
        .get('webfront_title_recommendedTitles', {})
        .get('titles', [])
    )

    for rec in recommended:
        rsid = rec.get('id')
        if rsid:
            related_sids.append(rsid)

    return entry, related_sids


def add_unseen(queue, seen, sids):
    """未取得かつ未キューの SID だけ追加して件数を返す。"""
    added = 0
    for sid in sids:
        if sid and sid not in seen:
            queue.append(sid)
            seen.add(sid)
            added += 1
    return added


def checkpoint(db, queue, deferred):
    """
    [変更] DB と探索状態を同じタイミングで保存する。
    DBだけ先に進んだり、キューだけ先に進んだりするズレを最小化する。
    """
    save_db(db)
    save_state(queue, deferred)


def scrape(seed_sids=None):
    db = load_db()

    # [変更] 前回 Actions の未処理 + 次回送り SID をまとめて再開する。
    saved_pending, saved_deferred = load_state()
    resumed = list(dict.fromkeys(saved_pending + saved_deferred))
    queue = deque(resumed)

    # DB登録済み + 既にキューにいる SID は重複追加しない。
    seen = set(db.keys())
    seen.update(queue)

    # retry_counts は実行ごとにリセットする。
    retry_counts = {}
    deferred = []

    processed = 0
    changed_since_checkpoint = 0
    started = time.monotonic()

    print(f'取得済みDB: {len(db)} 件')
    print(
        f'前回から再開: {len(queue)} 件 '
        f'(通常 {len(saved_pending)} / エラー次回送り {len(saved_deferred)})'
    )

    # 基本仕様：毎回ランキングを見て、新着の探索起点も追加する。
    ranking = get_ranking_sids()
    ranking_added = add_unseen(queue, seen, ranking)
    print(f'ランキング: {len(ranking)} 件 / 新規追加: {ranking_added} 件')

    # 基本仕様：手動シードも探索起点へ追加する。
    if seed_sids:
        manual_added = add_unseen(queue, seen, seed_sids)
        if manual_added:
            print(f'手動シード: {manual_added} 件追加')

    # ランキング/手動シード追加直後にも状態を残す。
    save_state(queue, deferred)

    if not queue:
        print('新着・継続キューなし。終了します。')
        return

    print(f'開始キュー: {len(queue)} 件')
    print('Ctrl+C で中断できます')
    print()

    try:
        while queue:
            if MAX_ITEMS and processed >= MAX_ITEMS:
                print(f'\nMAX_ITEMS={MAX_ITEMS} に到達。続きは次回へ保存します。')
                break

            if MAX_RUNTIME_MINUTES:
                elapsed_minutes = (time.monotonic() - started) / 60
                if elapsed_minutes >= MAX_RUNTIME_MINUTES:
                    print(
                        f'\nMAX_RUNTIME_MINUTES={MAX_RUNTIME_MINUTES} に到達。'
                        '続きは次回へ保存します。'
                    )
                    break

            sid = queue.popleft()
            print(
                f'[{len(db) + 1}件目] {sid} '
                f'(残キュー: {len(queue)}件)',
                end=' ',
                flush=True,
            )

            try:
                entry, related = fetch_one(sid)

                # 成功した SID の再試行記録は不要。
                retry_counts.pop(sid, None)

                if entry:
                    db[sid] = entry
                    processed += 1
                    changed_since_checkpoint += 1

                    new_count = add_unseen(queue, seen, related)
                    print(f'-> {entry["title"]} (+{new_count}件発見)')
                else:
                    # 元版と同じく「データなし」はDBには入れない。
                    print('-> データなし')

            except Exception as e:
                retry_count = retry_counts.get(sid, 0) + 1

                if retry_count < MAX_SID_RETRIES:
                    retry_counts[sid] = retry_count
                    queue.append(sid)
                    print(
                        f'-> エラー: {e} '
                        f'(SID再試行 {retry_count}/{MAX_SID_RETRIES - 1})'
                    )
                else:
                    # [変更] 現在の実行では打ち切るが、SID自体は捨てない。
                    # deferred に残し、次回 Actions の最初で通常キューへ戻す。
                    retry_counts.pop(sid, None)
                    deferred.append(sid)
                    print(f'-> エラー: {e} (次回実行へ延期)')

                time.sleep(2)

            if changed_since_checkpoint >= SAVE_EVERY:
                checkpoint(db, queue, deferred)
                changed_since_checkpoint = 0
                print(
                    f'--- checkpoint: DB {len(db)}件 / '
                    f'残キュー {len(queue)}件 / 延期 {len(deferred)}件 ---'
                )

            if REQUEST_INTERVAL:
                time.sleep(REQUEST_INTERVAL)

    except KeyboardInterrupt:
        print('\n中断要求を受けました。続きは保存します。')

    finally:
        # [変更] 件数/時間上限・Ctrl+C・通常完了のすべてで次回再開可能にする。
        checkpoint(db, queue, deferred)
        print(
            f'完了。今回 {processed} 件更新 / '
            f'DB合計 {len(db)} 件 / '
            f'次回キュー {len(queue) + len(deferred)} 件'
        )


if __name__ == '__main__':
    # 基本仕様：ここへ SID を足せばランキング外からも探索を開始できる。
    manual_seeds = [
        'SID0269679',
        # 'SID0012345',
    ]

    scrape(seed_sids=manual_seeds)
