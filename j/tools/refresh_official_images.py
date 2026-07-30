from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / 'data' / 'source' / 'media_registry.json'
USER_AGENT = 'Mozilla/5.0 (compatible; JJK-Manga-DB-OfficialMediaCollector/1.0)'
ALLOWED_HOSTS = {
    'shonenjumpplus.com',
    'www.shonenjumpplus.com',
    'cdn-scissors.gigaviewer.com',
    'cdn-ak-img.shonenjumpplus.com',
}


class EpisodeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metas: dict[str, str] = {}
        self.current_anchor: dict | None = None
        self.anchors: list[tuple[str, str]] = []
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = {str(k).lower(): str(v or '') for k, v in attrs}
        if tag.lower() == 'meta':
            key = (attrs_dict.get('name') or attrs_dict.get('property') or '').lower()
            value = attrs_dict.get('content', '')
            if key and value:
                self.metas[key] = value
        elif tag.lower() == 'a':
            self.current_anchor = {'href': attrs_dict.get('href', ''), 'text': []}
        elif tag.lower() == 'title':
            self.in_title = True

    def handle_data(self, data: str) -> None:
        if self.current_anchor is not None:
            self.current_anchor['text'].append(data)
        if self.in_title:
            self.title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == 'a' and self.current_anchor is not None:
            text = ' '.join(''.join(self.current_anchor['text']).split())
            self.anchors.append((self.current_anchor['href'], text))
            self.current_anchor = None
        elif tag.lower() == 'title':
            self.in_title = False


def fetch_text(url: str, timeout: int) -> str:
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept-Language': 'ja,en;q=0.5'})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        return response.read().decode(charset, errors='replace')


def valid_remote_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == 'https' and parsed.hostname in ALLOWED_HOSTS


def parse_episode_page(page_url: str, body: str) -> dict:
    parser = EpisodeParser()
    parser.feed(body)
    title = parser.metas.get('og:title') or ' '.join(''.join(parser.title_parts).split())
    image_url = parser.metas.get('twitter:image') or parser.metas.get('og:image') or ''
    canonical = parser.metas.get('og:url') or page_url
    next_url = ''
    for href, label in parser.anchors:
        if '次の話を読む' in label and href:
            next_url = urljoin(page_url, href)
            break
    return {
        'title': html.unescape(title),
        'imageUrl': html.unescape(image_url),
        'episodeUrl': html.unescape(canonical),
        'nextUrl': html.unescape(next_url),
    }


def chapter_number(title: str) -> int | None:
    match = re.search(r'第\s*(\d+)\s*話', title)
    return int(match.group(1)) if match else None


def ensure_expected_series(title: str, series: str) -> None:
    if series == 'main':
        if '呪術廻戦' not in title or '呪術廻戦≡' in title:
            raise ValueError(f'別作品または別シリーズを検出: {title}')
    else:
        if '東京都立呪術高等専門学校' not in title:
            raise ValueError(f'0巻前日譚ではないページを検出: {title}')


def update_row(rows_by_id: dict[str, dict], chapter_id: str, parsed: dict) -> bool:
    image_url = parsed.get('imageUrl', '')
    episode_url = parsed.get('episodeUrl', '')
    if not valid_remote_url(image_url):
        raise ValueError(f'許可外または不正な画像URL: {image_url}')
    if not valid_remote_url(episode_url):
        raise ValueError(f'許可外または不正なエピソードURL: {episode_url}')
    row = rows_by_id[chapter_id]
    changed = row.get('imageUrl') != image_url or row.get('episodeUrl') != episode_url
    row.update({
        'imageUrl': image_url,
        'episodeUrl': episode_url,
        'sourceRef': 'src-jumpplus-episode-thumbnails',
        'verification': 'official-page-direct-link',
        'note': '少年ジャンプ＋の公式エピソードページから収集。',
    })
    return changed


def collect_by_traversal(seed: str, series: str, rows_by_id: dict[str, dict], limit: int, delay: float, timeout: int) -> tuple[int, int]:
    current = seed
    visited: set[str] = set()
    checked = changed = 0
    expected_max = 271 if series == 'main' else 4
    while current and checked < limit and len(visited) < expected_max:
        if current in visited:
            raise RuntimeError(f'循環リンクを検出: {current}')
        visited.add(current)
        body = fetch_text(current, timeout)
        parsed = parse_episode_page(current, body)
        ensure_expected_series(parsed['title'], series)
        number = chapter_number(parsed['title'])
        if number is None or not (1 <= number <= expected_max):
            raise ValueError(f'話数を確定できない: {parsed["title"]}')
        chapter_id = f'ch-{number:03d}' if series == 'main' else f'zero-{number:02d}'
        changed += int(update_row(rows_by_id, chapter_id, parsed))
        checked += 1
        print(f'[{series} {checked}/{limit}] {chapter_id} {parsed["title"]}')
        next_url = parsed.get('nextUrl', '')
        if not next_url or number >= expected_max:
            break
        if not valid_remote_url(next_url):
            raise ValueError(f'次話URLが許可外: {next_url}')
        current = next_url
        if delay > 0:
            time.sleep(delay)
    return checked, changed


def extract_urls_from_item(item: ET.Element) -> list[str]:
    urls: list[str] = []
    for element in item.iter():
        for value in element.attrib.values():
            if isinstance(value, str) and value.startswith('http'):
                urls.append(html.unescape(value))
        if element.text:
            urls.extend(html.unescape(x) for x in re.findall(r'https?://[^\s<"\']+', element.text))
    return urls


def collect_main_rss(rss_url: str, rows_by_id: dict[str, dict], timeout: int) -> tuple[int, int]:
    body = fetch_text(rss_url, timeout)
    root = ET.fromstring(body)
    checked = changed = 0
    for item in root.findall('.//item'):
        title = (item.findtext('title') or '').strip()
        ensure_expected_series(title, 'main')
        number = chapter_number(title)
        if number is None or not (1 <= number <= 271):
            continue
        urls = extract_urls_from_item(item)
        episode_url = next((u for u in urls if re.match(r'https://shonenjumpplus\.com/episode/\d+', u)), '')
        image_url = next((u for u in urls if 'episode-thumbnail' in u or 'cdn-scissors.gigaviewer.com/image/' in u), '')
        if not episode_url or not image_url:
            continue
        parsed = {'title': title, 'episodeUrl': episode_url, 'imageUrl': image_url}
        changed += int(update_row(rows_by_id, f'ch-{number:03d}', parsed))
        checked += 1
    return checked, changed


def main() -> int:
    parser = argparse.ArgumentParser(description='少年ジャンプ公式ページから画像URL台帳を更新します。画像ファイル自体は保存しません。')
    parser.add_argument('--mode', choices=('all', 'main', 'zero'), default='all')
    parser.add_argument('--main-method', choices=('rss-first', 'traverse-only', 'rss-only'), default='rss-first')
    parser.add_argument('--limit', type=int, default=275, help='巡回方式で確認する最大ページ数')
    parser.add_argument('--delay', type=float, default=1.0, help='ページ間待機秒')
    parser.add_argument('--timeout', type=int, default=30)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--no-build', action='store_true')
    args = parser.parse_args()

    registry = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    rows = registry['chapterThumbnails']
    rows_by_id = {row['chapterId']: row for row in rows}
    expected = {f'zero-{i:02d}' for i in range(1, 5)} | {f'ch-{i:03d}' for i in range(1, 272)}
    if set(rows_by_id) != expected:
        raise SystemExit('media_registry.json の各話IDが275件の完全集合ではありません。')

    checked_total = changed_total = 0
    sources = registry['sources']

    if args.mode in ('all', 'main'):
        if args.main_method in ('rss-first', 'rss-only'):
            try:
                checked, changed = collect_main_rss(sources['jumpPlusMainRss'], rows_by_id, args.timeout)
                checked_total += checked
                changed_total += changed
                print(f'RSS: checked={checked}, changed={changed}')
            except Exception as error:
                if args.main_method == 'rss-only':
                    raise
                print(f'RSS取得失敗。巡回方式へ切替: {error}', file=sys.stderr)
        unresolved_main = sum(not rows_by_id[f'ch-{i:03d}'].get('imageUrl') for i in range(1, 272))
        if args.main_method != 'rss-only' and unresolved_main:
            checked, changed = collect_by_traversal(
                sources['jumpPlusMainSeed'], 'main', rows_by_id,
                min(args.limit, 271), args.delay, args.timeout,
            )
            checked_total += checked
            changed_total += changed

    if args.mode in ('all', 'zero'):
        checked, changed = collect_by_traversal(
            sources['jumpPlusZeroSeed'], 'zero', rows_by_id,
            min(args.limit, 4), args.delay, args.timeout,
        )
        checked_total += checked
        changed_total += changed

    verified = sum(bool(row.get('imageUrl')) for row in rows)
    print(f'完了: checked={checked_total}, changed={changed_total}, verified={verified}/275')
    if args.dry_run:
        print('dry-run: ファイルは更新していません。')
        return 0

    backup = REGISTRY_PATH.with_suffix('.backup.json')
    shutil.copy2(REGISTRY_PATH, backup)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding='utf-8')
    if not args.no_build:
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_site.py')], check=True)
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'validate_site.py')], check=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
