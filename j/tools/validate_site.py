from __future__ import annotations
from pathlib import Path
import json, re, subprocess, sys, urllib.parse

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'data' / 'generated'
errors: list[str] = []
warnings: list[str] = []


def load(name):
    return json.loads((GEN / f'{name}.json').read_text(encoding='utf-8'))


def duplicate_ids(label, rows):
    ids = [row['id'] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append(f'{label}: ID重複')


catalog = load('catalog')
chapters = load('chapters')
characters = load('characters')
techniques = load('techniques')
terms = load('terms')
supplements = load('supplements')
sources = load('sources')

expected_chapter_ids = [f'zero-{i:02d}' for i in range(1, 5)] + [f'ch-{i:03d}' for i in range(1, 272)]
if [row['id'] for row in chapters] != expected_chapter_ids:
    errors.append('各話IDが0巻4話＋本編1～271話の連続順になっていない')

for label, rows in [
    ('chapters', chapters), ('characters', characters), ('techniques', techniques),
    ('terms', terms), ('supplements', supplements), ('sources', sources)
]:
    duplicate_ids(label, rows)

chapter_ids = {row['id'] for row in chapters}
character_ids = {row['id'] for row in characters}
technique_ids = {row['id'] for row in techniques}
term_ids = {row['id'] for row in terms}
supplement_ids = {row['id'] for row in supplements}
source_ids = {row['id'] for row in sources}
arc_ids = {row['id'] for row in catalog['arcs']}

for chapter in chapters:
    if not chapter['summaryFull'].strip():
        errors.append(f"{chapter['id']}: 詳細あらすじなし")
    if chapter['arcId'] not in arc_ids:
        errors.append(f"{chapter['id']}: 区分参照切れ {chapter['arcId']}")
    for key, valid in [
        ('characterIds', character_ids), ('techniqueIds', technique_ids),
        ('termIds', term_ids), ('sourceRefs', source_ids)
    ]:
        for ref in chapter.get(key, []):
            if ref not in valid:
                errors.append(f"{chapter['id']}: {key}参照切れ {ref}")
    if chapter.get('verificationBasis', {}).get('anime_movie_game_novel_used') is True:
        errors.append(f"{chapter['id']}: 禁止媒体使用フラグがtrue")

for character in characters:
    if not character.get('profile', '').strip():
        errors.append(f"人物 {character['name']}: 紹介なし")
    for ref in character.get('chapterIds', []):
        if ref not in chapter_ids:
            errors.append(f"人物 {character['name']}: 話参照切れ {ref}")
    for ref in character.get('supplementIds', []):
        if ref not in supplement_ids:
            errors.append(f"人物 {character['name']}: 補遺参照切れ {ref}")
    for ref in character.get('sourceRefs', []):
        if ref not in source_ids:
            errors.append(f"人物 {character['name']}: 出典参照切れ {ref}")
    as_of = (character.get('status') or {}).get('as_of_chapter')
    if as_of and as_of not in chapter_ids and as_of not in supplement_ids:
        warnings.append(f"人物 {character['name']}: 状態時点が話・補遺IDではない {as_of}")

for technique in techniques:
    if not technique.get('description', '').strip():
        errors.append(f"技 {technique['name']}: 説明なし")
    for ref in technique.get('chapterIds', []):
        if ref not in chapter_ids:
            errors.append(f"技 {technique['name']}: 話参照切れ {ref}")
    for ref in technique.get('sourceRefs', []):
        if ref not in source_ids:
            errors.append(f"技 {technique['name']}: 出典参照切れ {ref}")

for term in terms:
    if not term.get('definition', '').strip():
        errors.append(f"用語 {term['name']}: 定義なし")
    for ref in term.get('chapterIds', []):
        if ref not in chapter_ids:
            errors.append(f"用語 {term['name']}: 話参照切れ {ref}")
    for ref in term.get('sourceRefs', []):
        if ref not in source_ids:
            errors.append(f"用語 {term['name']}: 出典参照切れ {ref}")

for supplement in supplements:
    for ref in supplement.get('character_ids', []):
        if ref not in character_ids:
            errors.append(f"補遺 {supplement['title']}: 人物参照切れ {ref}")
    for ref in supplement.get('source_refs', []):
        if ref not in source_ids:
            errors.append(f"補遺 {supplement['title']}: 出典参照切れ {ref}")

for source in sources:
    scope = str(source.get('media_scope') or '').lower()
    if any(word in scope for word in ('anime', 'movie', 'game', 'novel', 'stage')):
        errors.append(f"禁止媒体の出典が登録されている: {source['id']} / {scope}")
    url = source.get('url') or ''
    if url:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            errors.append(f"出典URL不正: {source['id']} / {url}")

# カタログと遅延読込ファイル
for kind, rows in [
    ('chapters', catalog['chapters']), ('characters', catalog['characters']),
    ('techniques', catalog['techniques']), ('terms', catalog['terms'])
]:
    for row in rows:
        if kind == 'chapters':
            detail_file = f"data/generated/details/chapters/{row.get('detailChunk')}.js"
        else:
            chunk = row.get('detailChunk')
            if not isinstance(chunk, int):
                errors.append(f"{kind}/{row['id']}: detailChunkなし")
                continue
            detail_file = f"data/generated/details/{kind}/part-{chunk:02d}.js"
        path = ROOT / detail_file
        if not path.exists():
            errors.append(f"{kind}/{row['id']}: 詳細ファイル不足 {detail_file}")
        elif json.dumps(row['id'], ensure_ascii=False) not in path.read_text(encoding='utf-8'):
            errors.append(f"{kind}/{row['id']}: 詳細ファイル内にIDがない {detail_file}")

required = [
    'index.html', 'chapters.html', 'characters.html', 'techniques.html', 'terms.html',
    'supplements.html', 'sources.html', 'status.html', 'assets/css/app.css',
    'assets/js/core.js', 'assets/js/chapters-page.js', 'assets/js/entity-page.js'
]
for relative in required:
    if not (ROOT / relative).exists():
        errors.append(f'ファイル不足 {relative}')

for html in ROOT.glob('*.html'):
    text = html.read_text(encoding='utf-8')
    for ref in re.findall(r'(?:src|href)="([^"]+)"', text):
        if ref.startswith(('http:', 'https:', '#', '?')):
            continue
        path = html.parent / ref.split('?')[0]
        if not path.exists():
            errors.append(f'{html.name}: 参照ファイル不足 {ref}')
    catalog_refs = re.findall(r'data/generated/catalog[^" ]*\.js', text)
    if catalog_refs and 'assets/js/core.js' in text:
        if min(text.index(ref) for ref in catalog_refs) > text.index('assets/js/core.js'):
            errors.append(f'{html.name}: catalog系JSより先にcore.jsを読み込んでいる')
    if html.name in ('chapters.html', 'characters.html', 'techniques.html', 'terms.html'):
        for forbidden in ('data/generated/chapters.js', 'data/generated/characters.js', 'data/generated/techniques.js', 'data/generated/terms.js'):
            if forbidden in text:
                errors.append(f'{html.name}: 全詳細データを初期読込している {forbidden}')

# JavaScript構文
for js_path in sorted((ROOT / 'assets/js').glob('*.js')) + sorted((GEN / 'details').rglob('*.js')) + sorted(GEN.glob('catalog*.js')) + [GEN / 'supplements.js', GEN / 'sources.js']:
    result = subprocess.run(['node', '--check', str(js_path)], capture_output=True, text=True)
    if result.returncode:
        errors.append(f'JavaScript構文エラー {js_path.relative_to(ROOT)}: {result.stderr.strip()}')

# 軽量化予算（非圧縮）
catalog_size = (GEN / 'catalog.js').stat().st_size
max_detail_size = max(path.stat().st_size for path in (GEN / 'details').rglob('*.js'))
if catalog_size > 350_000:
    warnings.append(f'catalog.jsが大きい: {catalog_size} bytes')
if max_detail_size > 180_000:
    warnings.append(f'最大詳細チャンクが大きい: {max_detail_size} bytes')

if errors:
    print('FAIL')
    print('\n'.join(errors[:500]))
    if warnings:
        print('\nWARNINGS')
        print('\n'.join(warnings[:200]))
    sys.exit(1)

print(
    f"PASS: chapters={len(chapters)}, characters={len(characters)}, techniques={len(techniques)}, "
    f"terms={len(terms)}, supplements={len(supplements)}, detail_chunks={len(list((GEN/'details').rglob('*.js')))}, "
    f"catalog_bytes={catalog_size}, max_detail_chunk_bytes={max_detail_size}, warnings={len(warnings)}"
)
if warnings:
    print('WARNINGS')
    print('\n'.join(warnings))
