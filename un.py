# -*- coding: utf-8 -*-
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
TITLE_HASH = 'c7d557d11776b11c3ca0c920906d79891861117a39b864c56bc074e5628b7163'
CREDITS_HASH = 'bdf1311121839b73cd5222da069ffbe69c2a072cec04af1ae00c60bbb74b8a73'
RANKING_HASH = 'ab04097085a6d372a8a8408992ca6094bbf319fbf5c6921f754ab5ec62c8bb81'

SAVE_EVERY = max(1, int(os.getenv('SAVE_EVERY', '25')))
MAX_ITEMS = max(0, int(os.getenv('MAX_ITEMS', '0')))
MAX_RUNTIME_MINUTES = max(0, int(os.getenv('MAX_RUNTIME_MINUTES', '0')))
REQUEST_TIMEOUT = max(5, int(os.getenv('REQUEST_TIMEOUT', '30')))

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def load_db():
    if os.path.exists(OUTPUT):
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_db(db):
    tmp = OUTPUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUTPUT)


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
                time.sleep(attempt * 2)

    raise RuntimeError(f'{operation} 取得失敗: {last_error}')


def get_ranking_sids():
    data = api_get('cosmo_videoRanking', {'rankingType': 'ALL', 'isCheck': False}, RANKING_HASH)
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
    title_data = api_get('cosmo_getVideoTitle', {'code': sid}, TITLE_HASH)
    time.sleep(0.5)
    credits_data = api_get('cosmo_getVideoTitleRelatedStuffs', {
        'code': sid,
        'creditsPage': 1,
        'creditsPageSize': 100,
        'relatedContentPage': 1,
        'relatedContentPageSize': 20,
        'includePositionPlayLive': True,
    }, CREDITS_HASH)

    t = title_data.get('data', {}).get('webfront_title_stage', {})
    if not t:
        return None, []

    thumb = t.get('thumbnail', {}).get('standard', '')
    if thumb and not thumb.startswith('http'):
        thumb = 'https://' + thumb

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
    credits = credits_data.get('data', {}).get('webfront_title_credits', {}).get('titleCredits', [])
    for c in credits:
        name = c.get('personName', '')
        role = c.get('castTypeName', '')
        if role == '出演':
            entry['cast'].append(name)
        elif role in ['監督', 'ディレクター']:
            entry['director'].append(name)
        else:
            entry['staff'].append(f'{name}（{role}）')

    for group in credits_data.get('data', {}).get('webfront_title_relatedTitles', []):
        for title in group.get('titles', []):
            rsid = title.get('id')
            if rsid:
                related_sids.append(rsid)

    for rec in credits_data.get('data', {}).get('webfront_title_recommendedTitles', {}).get('titles', []):
        rsid = rec.get('id')
        if rsid:
            related_sids.append(rsid)

    return entry, related_sids


def scrape(seed_sids=None):
    db = load_db()
    seen = set(db.keys())
    dirty = False
    processed = 0
    started = time.monotonic()

    ranking = get_ranking_sids()
    print(f'ランキングから {len(ranking)} 件取得')

    queue = deque()
    for sid in ranking:
        if sid not in seen:
            queue.append(sid)
            seen.add(sid)

    if seed_sids:
        added = 0
        for sid in seed_sids:
            if sid not in seen:
                queue.append(sid)
                seen.add(sid)
                added += 1
        if added:
            print(f'手動シード {added} 件追加')

    print(f'取得済み: {len(db)} 件 / 新規キュー: {len(queue)} 件')
    if not queue:
        print('新着なし。終了します。')
        return

    print('Ctrl+C で中断できます')
    print()

    try:
        while queue:
            if MAX_ITEMS and processed >= MAX_ITEMS:
                print(f'\nMAX_ITEMS={MAX_ITEMS} に到達。正常終了します。')
                break

            if MAX_RUNTIME_MINUTES:
                elapsed_minutes = (time.monotonic() - started) / 60
                if elapsed_minutes >= MAX_RUNTIME_MINUTES:
                    print(f'\nMAX_RUNTIME_MINUTES={MAX_RUNTIME_MINUTES} に到達。正常終了します。')
                    break

            sid = queue.popleft()
            print(f'[{len(db)+1}件目] {sid} (残キュー: {len(queue)}件)', end=' ', flush=True)

            try:
                entry, related = fetch_one(sid)

                if entry:
                    db[sid] = entry
                    dirty = True
                    processed += 1

                    new_count = 0
                    for rsid in related:
                        if rsid not in seen:
                            queue.append(rsid)
                            seen.add(rsid)
                            new_count += 1

                    if processed % SAVE_EVERY == 0:
                        save_db(db)
                        dirty = False
                        print(f'-> {entry["title"]} (+{new_count}件発見 / checkpoint)')
                    else:
                        print(f'-> {entry["title"]} (+{new_count}件発見)')
                else:
                    print('-> データなし')

            except Exception as e:
                print(f'-> エラー: {e}')
                time.sleep(2)

            time.sleep(0.8)

    except KeyboardInterrupt:
        print('\n中断要求を受けました。')

    finally:
        if dirty:
            save_db(db)
        print(f'完了。今回 {processed} 件更新 / 合計 {len(db)} 件')


if __name__ == '__main__':
    manual_seeds = [
        'SID0269679',
        # 'SID0012345',
    ]
    scrape(seed_sids=manual_seeds)
