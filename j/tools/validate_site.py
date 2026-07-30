from __future__ import annotations
from pathlib import Path
import json, re, subprocess, sys, urllib.parse

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'data' / 'generated'
SRC = ROOT / 'data' / 'source'
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
volumes = load('volumes')
media_registry = json.loads((SRC / 'media_registry.json').read_text(encoding='utf-8'))
volume_records = json.loads((SRC / 'volumes.json').read_text(encoding='utf-8'))
chapter_highlights = json.loads((SRC / 'chapter_highlights.json').read_text(encoding='utf-8'))
chapter_line_evidence = json.loads((SRC / 'chapter_line_evidence.json').read_text(encoding='utf-8'))
manga_source_research = json.loads((ROOT / 'reports' / 'MANGA_SOURCE_RESEARCH.json').read_text(encoding='utf-8'))

expected_chapter_ids = [f'zero-{i:02d}' for i in range(1, 5)] + [f'ch-{i:03d}' for i in range(1, 272)]
expected_numbered_chapter_ids = [f'ch-{i:03d}' for i in range(1, 272)]
if [row['id'] for row in chapters] != expected_chapter_ids:
    errors.append('各話IDが0巻4話＋本編1～271話の連続順になっていない')
if list(chapter_highlights.get('chapters', {})) != expected_chapter_ids:
    errors.append('各話ハイライト原本が275話の連続順・完全集合になっていない')
if list(chapter_line_evidence.get('chapters', {})) != expected_numbered_chapter_ids:
    errors.append('短文照合原本が本編271話の連続順・完全集合になっていない')

for label, rows in [
    ('chapters', chapters), ('characters', characters), ('techniques', techniques),
    ('terms', terms), ('supplements', supplements), ('sources', sources), ('volumes', volumes)
]:
    duplicate_ids(label, rows)

chapter_ids = {row['id'] for row in chapters}
character_ids = {row['id'] for row in characters}
technique_ids = {row['id'] for row in techniques}
term_ids = {row['id'] for row in terms}
supplement_ids = {row['id'] for row in supplements}
source_ids = {row['id'] for row in sources}
arc_ids = {row['id'] for row in catalog['arcs']}
if len(sources) != 92:
    errors.append(f'出典台帳が92件ではない: {len(sources)}')
for ref in chapter_line_evidence.get('sourceRefs', []):
    if ref not in source_ids:
        errors.append(f'短文照合原本の出典参照切れ {ref}')

# 公式画像台帳
allowed_image_hosts = {
    'www.shonenjump.com', 'shonenjumpplus.com', 'www.shonenjumpplus.com',
    'cdn-scissors.gigaviewer.com', 'cdn-ak-img.shonenjumpplus.com'
}
allowed_evidence_hosts = {
    'eiga-manga.com', 'manga-games.com', 'animenb.com', 'idononaka.com',
    'neet-life-blog.com', 'manga5000.com', 'morn.life'
}

def check_remote_url(label, url, allowed_hosts=allowed_image_hosts):
    if not url:
        return
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in allowed_hosts:
        errors.append(f'{label}: 許可外URL {url}')

expected_volume_ids = [f'vol-{i:02d}' for i in range(31)]
if [row.get('id') for row in volume_records] != expected_volume_ids:
    errors.append('コミックス原本が0巻～30巻の31件になっていない')
if [row.get('id') for row in volumes] != expected_volume_ids:
    errors.append('コミックス生成データが0巻～30巻の31件になっていない')
generated_volume_chapter_ids = []
generated_volume_supplement_ids = []
chapter_by_id = {row['id']: row for row in chapters}
source_by_id = {row['id']: row for row in sources}
for row in volumes:
    n = row.get('number')
    expected_url = f'https://www.shonenjump.com/j/comics/_comicimage/jujutsu{n:03d}.jpg' if isinstance(n, int) else ''
    if row.get('imageUrl') != expected_url:
        errors.append(f"{row.get('id')}: 表紙URL規則不一致 {row.get('imageUrl')}")
    if row.get('sourceRef') != 'src-official-comics-list':
        errors.append(f"{row.get('id')}: 表紙出典不正")
    if row.get('coverVerification') != 'official-page-direct-link':
        errors.append(f"{row.get('id')}: 表紙確認状態不正")
    check_remote_url(f"{row.get('id')} 表紙", row.get('imageUrl', ''))
    synopsis_source_ref = row.get('synopsisSourceRef')
    expected_source_ref = f'src-shueisha-vol-{n:02d}' if isinstance(n, int) else ''
    if synopsis_source_ref != expected_source_ref:
        errors.append(f"{row.get('id')}: 巻あらすじ出典不正 {synopsis_source_ref}")
    synopsis_source = source_by_id.get(synopsis_source_ref)
    if not synopsis_source:
        errors.append(f"{row.get('id')}: 巻あらすじ出典参照切れ {synopsis_source_ref}")
    elif row.get('pageUrl') != synopsis_source.get('url'):
        errors.append(f"{row.get('id')}: 公式商品ページURL不一致")
    if not row.get('synopsis', '').strip():
        errors.append(f"{row.get('id')}: 巻あらすじなし")
    if row.get('verification') != 'official-volume-synopsis-paraphrased':
        errors.append(f"{row.get('id')}: 巻あらすじ確認状態不正")
    embedded_chapters = row.get('chapters', [])
    if row.get('chapterCount') != len(embedded_chapters):
        errors.append(f"{row.get('id')}: 収録話数不一致")
    for embedded in embedded_chapters:
        chapter_id = embedded.get('id')
        generated_volume_chapter_ids.append(chapter_id)
        chapter = chapter_by_id.get(chapter_id)
        if not chapter:
            errors.append(f"{row.get('id')}: 収録話参照切れ {chapter_id}")
            continue
        if chapter.get('volume') != n:
            errors.append(f"{row.get('id')}: 収録巻不一致 {chapter_id}")
        for key in ('label', 'title', 'startPage'):
            if embedded.get(key) != chapter.get(key):
                errors.append(f"{row.get('id')}: 収録話表示不一致 {chapter_id}/{key}")
    embedded_supplements = row.get('supplements', [])
    if row.get('supplementCount') != len(embedded_supplements):
        errors.append(f"{row.get('id')}: 補遺件数不一致")
    generated_volume_supplement_ids.extend(x.get('id') for x in embedded_supplements)

if generated_volume_chapter_ids != expected_chapter_ids:
    errors.append('コミックス収録話が275話の連続順・完全集合になっていない')
expected_volume_supplement_ids = [row['id'] for row in supplements if row.get('volume') is not None]
if generated_volume_supplement_ids != expected_volume_supplement_ids:
    errors.append('コミックス補遺の収録対応が原本と一致しない')

poll_images = media_registry.get('officialCharacterImages', [])
if len(poll_images) != 183:
    errors.append(f'公式人気投票画像が183件ではない: {len(poll_images)}')
icon_numbers = [row.get('iconNumber') for row in poll_images]
if len(icon_numbers) != len(set(icon_numbers)):
    errors.append('公式人気投票画像のiconNumberが重複')
assigned_character_ids = [row.get('characterId') for row in poll_images if row.get('characterId')]
if len(assigned_character_ids) != len(set(assigned_character_ids)):
    errors.append('公式人気投票画像が同一人物へ重複割当')
for row in poll_images:
    icon = row.get('iconNumber')
    expected_url = f'https://www.shonenjump.com/j/vote_jujutsu_kaisen/_image/icon{icon:03d}.png' if isinstance(icon, int) else ''
    if row.get('imageUrl') != expected_url:
        errors.append(f"人気投票 {row.get('officialLabel')}: URL規則不一致")
    if row.get('sourceRef') != 'src-official-character-vote-4':
        errors.append(f"人気投票 {row.get('officialLabel')}: 出典不正")
    if row.get('characterId') and row['characterId'] not in {x['id'] for x in characters}:
        errors.append(f"人気投票 {row.get('officialLabel')}: 人物参照切れ {row['characterId']}")
    check_remote_url(f"人気投票 {row.get('officialLabel')}", row.get('imageUrl', ''))

chapter_media_rows = media_registry.get('chapterThumbnails', [])
if len(chapter_media_rows) != 275:
    errors.append(f'各話画像台帳が275件ではない: {len(chapter_media_rows)}')
if [row.get('chapterId') for row in chapter_media_rows] != expected_chapter_ids:
    errors.append('各話画像台帳のID順・完全集合が不正')
for row in chapter_media_rows:
    image_url = row.get('imageUrl', '')
    episode_url = row.get('episodeUrl', '')
    verification = row.get('verification', '')
    if bool(image_url) != bool(episode_url):
        errors.append(f"{row.get('chapterId')}: 画像URLとエピソードURLの片方だけ登録")
    if image_url and verification != 'official-page-direct-link':
        errors.append(f"{row.get('chapterId')}: URL登録済みなのに確認状態が未確認")
    if not image_url and verification != 'pending-official-page-collection':
        errors.append(f"{row.get('chapterId')}: URL未登録なのに未収集状態ではない")
    check_remote_url(f"{row.get('chapterId')} サムネイル", image_url)
    check_remote_url(f"{row.get('chapterId')} エピソード", episode_url)

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
    media = chapter.get('media') or {}
    if media.get('sourceRef') not in source_ids:
        errors.append(f"{chapter['id']}: 画像出典参照切れ {media.get('sourceRef')}")
    if bool(media.get('imageUrl')) != bool(media.get('pageUrl')):
        errors.append(f"{chapter['id']}: 生成済み画像情報が片側のみ")
    if not isinstance(chapter.get('memorableQuotes'), list):
        errors.append(f"{chapter['id']}: memorableQuotesが配列ではない")
    if not isinstance(chapter.get('highlightKeywords'), list):
        errors.append(f"{chapter['id']}: highlightKeywordsが配列ではない")
    if not isinstance(chapter.get('popularLineGists'), list):
        errors.append(f"{chapter['id']}: popularLineGistsが配列ではない")
    if not isinstance(chapter.get('crosscheckedLines'), list):
        errors.append(f"{chapter['id']}: crosscheckedLinesが配列ではない")
    if not isinstance(chapter.get('dialogueSummaries'), list) or len(chapter.get('dialogueSummaries', [])) < 3:
        errors.append(f"{chapter['id']}: セリフ・判断・言動の要旨が3件未満")
    if not isinstance(chapter.get('detailedEvents'), list) or len(chapter.get('detailedEvents', [])) < 3:
        errors.append(f"{chapter['id']}: 詳細出来事が3件未満")
    if len(chapter.get('highlightKeywords', [])) < 2:
        errors.append(f"{chapter['id']}: キーワードが2件未満")
    for line in chapter.get('popularLineGists', []):
        if line.get('sourceRef') not in source_ids:
            errors.append(f"{chapter['id']}: 名言要旨の出典参照切れ {line.get('sourceRef')}")
        if not line.get('text') or not line.get('speaker') or not line.get('label'):
            errors.append(f"{chapter['id']}: 名言要旨の必須項目不足")
    evidence_lines = chapter_line_evidence.get('chapters', {}).get(chapter['id'], [])
    generated_lines = chapter.get('crosscheckedLines', [])
    if len(generated_lines) != len(evidence_lines):
        errors.append(f"{chapter['id']}: 短文照合の生成件数不一致")
    comparable_evidence = [
        {
            key: line.get(key)
            for key in (
                'speaker', 'text', 'kind', 'verification',
                'sourceCount', 'sourceRefs'
            )
        }
        for line in evidence_lines
    ]
    if generated_lines != comparable_evidence:
        errors.append(f"{chapter['id']}: 短文照合の生成内容不一致")
    expected_evidence_urls = list(dict.fromkeys(
        url
        for line in evidence_lines
        for url in line.get('sourceUrls', [])
    ))
    if chapter.get('crosscheckedSourceUrls', []) != expected_evidence_urls:
        errors.append(f"{chapter['id']}: 短文照合記事URLの生成内容不一致")
    for url in chapter.get('crosscheckedSourceUrls', []):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in allowed_evidence_hosts:
            errors.append(f"{chapter['id']}: 短文照合記事URLが許可外 {url}")
    for line in generated_lines:
        refs = line.get('sourceRefs', [])
        if (
            not line.get('text')
            or len(line.get('text', '')) > 48
            or line.get('verification') != 'crosschecked-manga-secondary'
            or line.get('sourceCount', 0) < 2
            or len(set(refs)) < 2
            or line.get('sourceCount') != len(set(refs))
            or line.get('speaker') is not None
        ):
            errors.append(f"{chapter['id']}: 短文照合の必須条件不足 {line.get('text', '')}")
        for ref in refs:
            if ref not in source_ids:
                errors.append(f"{chapter['id']}: 短文照合の出典参照切れ {ref}")
        if re.search(r'TVアニメ|テレビアニメ|劇場版|声優|放送開始', line.get('text', '')):
            errors.append(f"{chapter['id']}: 短文照合へ映像版語句が混入 {line.get('text', '')}")
        if 'sourceUrls' in line:
            errors.append(f"{chapter['id']}: 表示用短文へ記事URLを重複格納")

quality = catalog.get('meta', {}).get('quality', {})
expected_highlight_counts = chapter_highlights.get('counts', {})
for source_key, quality_key in [
    ('detailedEvents', 'detailedChapterEvents'),
    ('dialogueSummaries', 'dialogueSummaries'),
    ('crosscheckedLines', 'crosscheckedLines'),
    ('popularLineGists', 'popularLineGists'),
    ('highlightKeywords', 'highlightKeywords')
]:
    if quality.get(quality_key) != expected_highlight_counts.get(source_key):
        errors.append(f'ハイライト件数不一致: {quality_key}')
if quality.get('chaptersWithDialogueSummary') != 275:
    errors.append('全275話へセリフ・判断要旨が入っていない')
if quality.get('chaptersWithCrosscheckedLines') != manga_source_research.get('counts', {}).get('chaptersWithCrosscheckedLines'):
    errors.append('照合済み短文を持つ話数が調査報告と一致しない')
if expected_highlight_counts.get('crosscheckedLines') != manga_source_research.get('counts', {}).get('crosscheckedLines'):
    errors.append('照合済み短文の総数が調査報告と一致しない')
if catalog.get('meta', {}).get('buildVersion') != 'site-v8-source-crosschecked-lines':
    errors.append('buildVersionがv8ではない')

chapter_002 = chapter_by_id.get('ch-002', {})
chapter_089 = chapter_by_id.get('ch-089', {})
if not any('僕 最強だから' in item.get('text', '') for item in chapter_002.get('memorableQuotes', [])):
    errors.append('ch-002: 指定された名言が生成データにない')
if '0.2秒の領域展開' not in chapter_089.get('highlightKeywords', []):
    errors.append('ch-089: 指定されたキーワードが生成データにない')

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
    media = character.get('media') or {}
    if media.get('sourceRef') not in source_ids:
        errors.append(f"人物 {character['name']}: 画像出典参照切れ {media.get('sourceRef')}")
    check_remote_url(f"人物 {character['name']} 画像", media.get('imageUrl', ''))
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
    'supplements.html', 'sources.html', 'status.html', 'volumes.html', 'assets/css/app.css',
    'assets/js/core.js', 'assets/js/chapters-page.js', 'assets/js/entity-page.js',
    'assets/js/volumes-page.js', 'data/generated/catalog-volumes.js', 'data/generated/volumes.js'
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
    if html.name != 'index.html' and 'href="volumes.html"' not in text:
        errors.append(f'{html.name}: コミックス導線なし')
    if html.name != 'index.html' and ('全体像' in text or 'href="index.html"' in text):
        errors.append(f'{html.name}: 廃止した全体像への導線が残っている')
    if html.name in ('chapters.html', 'characters.html', 'techniques.html', 'terms.html'):
        for forbidden in ('data/generated/chapters.js', 'data/generated/characters.js', 'data/generated/techniques.js', 'data/generated/terms.js'):
            if forbidden in text:
                errors.append(f'{html.name}: 全詳細データを初期読込している {forbidden}')

index_text = (ROOT / 'index.html').read_text(encoding='utf-8')
if "location.replace('chapters.html')" not in index_text:
    errors.append('index.htmlが各話ページへ移動しない')

chapter_page_js = (ROOT / 'assets/js/chapters-page.js').read_text(encoding='utf-8')
if 'data-tab="highlights"' not in chapter_page_js or 'data-tab-panel="highlights"' not in chapter_page_js:
    errors.append('各話の名言・キーワードタブが不足')
for required_ui in ('crosscheckedLines', 'crosscheckedSourceUrls', 'verified-line-section', 'verified-line-more', 'popularLineGists', 'dialogueSummaries', 'detailedEvents', 'event-matrix', 'highlight-stats'):
    if required_ui not in chapter_page_js:
        errors.append(f'各話ハイライトUIが不足: {required_ui}')

core_js_text = (ROOT / 'assets/js/core.js').read_text(encoding='utf-8')
if 'FONT_TUNER_OPTIONS' not in core_js_text or core_js_text.count("label: '") < 10:
    errors.append('文字サイズ一時調整の10項目が不足')

# JavaScript構文
for js_path in sorted((ROOT / 'assets/js').glob('*.js')) + sorted((GEN / 'details').rglob('*.js')) + sorted(GEN.glob('catalog*.js')) + [GEN / 'supplements.js', GEN / 'sources.js', GEN / 'volumes.js']:
    result = subprocess.run(['node', '--check', str(js_path)], capture_output=True, text=True)
    if result.returncode:
        errors.append(f'JavaScript構文エラー {js_path.relative_to(ROOT)}: {result.stderr.strip()}')

# 画面幅による全面遮断を禁止
css_text = (ROOT / 'assets/css/app.css').read_text(encoding='utf-8')
for forbidden_css in ('body>*{display:none', '画面幅1180px以上で開いてください', 'min-width:1180px'):
    if forbidden_css in css_text:
        errors.append(f'CSSに画面遮断実装が残っている: {forbidden_css}')
for required_css in ('--font-record-title', '--font-detail', '.font-tuner', 'max-width:320px', 'max-height:408px', '.event-matrix', '.highlight-primary-grid', '.verified-line-grid', '.verified-line-more'):
    if required_css not in css_text:
        errors.append(f'CSSに現行UI設定が不足: {required_css}')

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
    f"terms={len(terms)}, supplements={len(supplements)}, volumes={len(volumes)}, official_character_images={len(poll_images)}, verified_chapter_images={sum(bool(x.get('imageUrl')) for x in chapter_media_rows)}, detail_chunks={len(list((GEN/'details').rglob('*.js')))}, "
    f"catalog_bytes={catalog_size}, max_detail_chunk_bytes={max_detail_size}, warnings={len(warnings)}"
)
if warnings:
    print('WARNINGS')
    print('\n'.join(warnings))
