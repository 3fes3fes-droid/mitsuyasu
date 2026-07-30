from __future__ import annotations
import json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data' / 'source'
GEN = ROOT / 'data' / 'generated'
DETAILS = GEN / 'details'
GEN.mkdir(parents=True, exist_ok=True)


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def write_js(path: Path, key: str, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = 'window.JJK_DATA = window.JJK_DATA || {};\n'
    body += f'window.JJK_DATA[{json.dumps(key)}] = '
    body += json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n'
    path.write_text(body, encoding='utf-8')


def write_detail_chunk(path: Path, kind: str, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {x['id']: x for x in rows}
    body = 'window.JJK_DETAIL_STORE = window.JJK_DETAIL_STORE || {};\n'
    body += f'window.JJK_DETAIL_STORE[{json.dumps(kind)}] = window.JJK_DETAIL_STORE[{json.dumps(kind)}] || {{}};\n'
    body += f'Object.assign(window.JJK_DETAIL_STORE[{json.dumps(kind)}], '
    body += json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ');\n'
    path.write_text(body, encoding='utf-8')


phase_re = re.compile(r'_phase(\d+)$')


def latest_phase_field(obj, prefix, default=None):
    found = []
    for key, value in obj.items():
        if key.startswith(prefix + '_phase'):
            match = phase_re.search(key)
            if match and value not in (None, [], {}, ''):
                found.append((int(match.group(1)), value))
    if not found:
        return default, None
    found.sort()
    return found[-1][1], found[-1][0]


def union_phase_lists(obj, prefix, fallback=None):
    values = []
    for key, value in obj.items():
        if key.startswith(prefix + '_phase') and isinstance(value, list):
            values.extend(value)
    if not values and fallback:
        values = list(fallback)
    seen, result = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def unique_strings(values):
    seen, result = set(), []
    for value in values:
        if not isinstance(value, str):
            continue
        value = value.strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def chapter_order(chapter_id: str):
    if chapter_id.startswith('zero-'):
        return int(chapter_id.split('-')[1]) - 10
    match = re.search(r'(\d+)$', chapter_id)
    return int(match.group(1)) if match else 9999


def normalize_chapter(chapter):
    highlights = chapter_highlights_by_id.get(chapter['id'], {})
    raw_crosschecked_lines = highlights.get('crosscheckedLines', [])
    crosschecked_lines = [
        {
            key: line.get(key)
            for key in (
                'speaker', 'text', 'kind', 'verification',
                'sourceCount', 'sourceRefs'
            )
        }
        for line in raw_crosschecked_lines
        if isinstance(line, dict)
    ]
    crosschecked_source_urls = unique_strings([
        url
        for line in raw_crosschecked_lines
        if isinstance(line, dict)
        for url in line.get('sourceUrls', [])
    ])
    events, phase = latest_phase_field(chapter, 'key_events_verified', [])
    character_ids, _ = latest_phase_field(chapter, 'character_ids_verified', chapter.get('character_ids_candidate', []))
    character_appearances, _ = latest_phase_field(chapter, 'character_appearances_verified', [])
    technique_ids, _ = latest_phase_field(chapter, 'technique_ids_verified', chapter.get('technique_ids_candidate', []))
    technique_appearances, _ = latest_phase_field(chapter, 'technique_appearances_verified', [])
    term_ids, _ = latest_phase_field(chapter, 'term_ids_verified', chapter.get('term_ids_candidate', []))
    source_refs, _ = latest_phase_field(chapter, 'source_refs', chapter.get('source_refs', []))
    if highlights.get('popularLineGists'):
        source_refs = unique_strings([*(source_refs or []), 'src-ciatr-quotes-2026'])
    line_source_refs = [
        ref
        for line in crosschecked_lines
        for ref in line.get('sourceRefs', [])
    ]
    source_refs = unique_strings([*(source_refs or []), *line_source_refs])
    notes, _ = latest_phase_field(chapter, 'verification_notes', chapter.get('verification_notes', ''))
    basis, _ = latest_phase_field(chapter, 'verification_basis', chapter.get('verification_basis', {}))
    number, zero_number = chapter.get('number'), chapter.get('zero_number')
    label = f'0巻 第{zero_number}話' if zero_number else f'第{number}話'
    return {
        'id': chapter['id'], 'label': label, 'number': number, 'zeroNumber': zero_number,
        'volume': chapter.get('volume'), 'title': chapter.get('title_official', ''),
        'startPage': chapter.get('start_page'),
        'arcId': chapter.get('db_arc_id') or chapter.get('db_section_draft_id'),
        'officialGroupId': chapter.get('official_group_id'),
        'summaryShort': chapter.get('summary_short', ''), 'summaryFull': chapter.get('summary_full', ''),
        'events': events or [], 'characterIds': character_ids or [],
        'characterAppearances': character_appearances or [], 'techniqueIds': technique_ids or [],
        'techniqueAppearances': technique_appearances or [], 'termIds': term_ids or [],
        'sourceRefs': source_refs or chapter.get('source_refs', []),
        'verification': chapter.get('content_verification', chapter.get('verification')),
        'verificationPhase': phase, 'verificationNotes': notes or '',
        'verificationBasis': basis or {}, 'sourceLocator': chapter.get('source_locator', ''),
        'editorialNotes': chapter.get('editorial_notes', []),
        'memorableQuotes': chapter.get('memorable_quotes', []),
        'crosscheckedLines': crosschecked_lines,
        'crosscheckedSourceUrls': crosschecked_source_urls,
        'popularLineGists': highlights.get('popularLineGists', []),
        'dialogueSummaries': highlights.get('dialogueSummaries', []),
        'detailedEvents': highlights.get('detailedEvents', events or []),
        'highlightKeywords': unique_strings([
            *chapter.get('highlight_keywords', []),
            *highlights.get('highlightKeywords', [])
        ])
    }


def latest_status(entity):
    found = []
    for key, value in entity.items():
        match = re.fullmatch(r'phase(\d+)_status_event', key)
        if match and isinstance(value, dict):
            found.append((int(match.group(1)), value))
    if found:
        found.sort()
        return found[-1][1]
    return {
        'status': entity.get('final_status_candidate', 'unknown'),
        'note': entity.get('final_status_note', ''),
        'as_of_chapter': entity.get('last_chapter_candidate')
    }


def normalize_character(entity):
    chapter_ids = union_phase_lists(entity, 'chapter_ids', entity.get('chapter_ids_candidate', []))
    chapter_ids.sort(key=chapter_order)
    return {
        'id': entity['id'], 'name': entity['name'], 'aliases': entity.get('aliases', []),
        'category': entity.get('category', ''), 'affiliation': entity.get('affiliation', ''),
        'profile': entity.get('profile_short', ''), 'status': latest_status(entity),
        'chapterIds': chapter_ids, 'firstChapter': chapter_ids[0] if chapter_ids else None,
        'lastChapter': chapter_ids[-1] if chapter_ids else None,
        'sourceRefs': entity.get('source_refs', []), 'verification': entity.get('verification', ''),
        'sourceScope': entity.get('source_scope', '')
    }


def normalize_technique(entity):
    chapter_ids = union_phase_lists(entity, 'chapter_ids', entity.get('chapter_ids_candidate', []))
    chapter_ids.sort(key=chapter_order)
    return {
        'id': entity['id'], 'name': entity['name'], 'reading': entity.get('reading', ''),
        'category': entity.get('category', ''), 'users': entity.get('user_names', []),
        'aliases': entity.get('aliases', []), 'description': entity.get('description_short', ''),
        'chapterIds': chapter_ids, 'firstChapter': chapter_ids[0] if chapter_ids else None,
        'lastChapter': chapter_ids[-1] if chapter_ids else None,
        'officialNameStatus': entity.get('official_name_status', ''),
        'sourceRefs': entity.get('source_refs', []), 'verification': entity.get('verification', ''),
        'sourceScope': entity.get('source_scope', '')
    }


def normalize_term(entity):
    chapter_ids = union_phase_lists(entity, 'chapter_ids', [])
    chapter_ids.sort(key=chapter_order)
    return {
        'id': entity['id'], 'name': entity['name'], 'category': entity.get('category', ''),
        'definition': entity.get('definition', ''), 'chapterIds': chapter_ids,
        'firstChapter': chapter_ids[0] if chapter_ids else None,
        'lastChapter': chapter_ids[-1] if chapter_ids else None,
        'officialNameStatus': entity.get('official_name_status', ''),
        'sourceRefs': entity.get('source_refs', []), 'verification': entity.get('verification', ''),
        'sourceScope': entity.get('source_scope', '')
    }


def detail_batches(rows, kind: str, batch_size=28):
    mapping = {}
    if kind == 'chapters':
        by_arc = {}
        for row in rows:
            by_arc.setdefault(row['arcId'] or 'unclassified', []).append(row)
        for arc_id, arc_rows in by_arc.items():
            for index in range(0, len(arc_rows), 12):
                chunk = arc_rows[index:index + 12]
                part = index // 12 + 1
                rel = f'data/generated/details/chapters/{arc_id}-{part:02d}.js'
                write_detail_chunk(ROOT / rel, kind, chunk)
                for row in chunk:
                    mapping[row['id']] = rel
        return mapping
    for index in range(0, len(rows), batch_size):
        chunk = rows[index:index + batch_size]
        part = index // batch_size + 1
        rel = f'data/generated/details/{kind}/part-{part:02d}.js'
        write_detail_chunk(ROOT / rel, kind, chunk)
        for row in chunk:
            mapping[row['id']] = rel
    return mapping


arcs = read_json(SRC / 'arcs.json')
characters_raw = read_json(SRC / 'characters.json')
techniques_raw = read_json(SRC / 'techniques.json')
terms_raw = read_json(SRC / 'terms.json')
supplements = read_json(SRC / 'supplements.json')
sources = read_json(SRC / 'sources_registry.json')
media_registry = read_json(SRC / 'media_registry.json')
volume_records = read_json(SRC / 'volumes.json')
overall = read_json(SRC / 'overall.json')
chapter_highlights_payload = read_json(SRC / 'chapter_highlights.json')
chapter_highlights_by_id = chapter_highlights_payload.get('chapters', {})
chapters_raw = [read_json(path) for path in sorted((SRC / 'chapters').glob('*.json'))]

chapters = sorted((normalize_chapter(x) for x in chapters_raw), key=lambda x: chapter_order(x['id']))
characters = sorted((normalize_character(x) for x in characters_raw), key=lambda x: x['name'])
techniques = sorted((normalize_technique(x) for x in techniques_raw), key=lambda x: x['name'])
terms = sorted((normalize_term(x) for x in terms_raw), key=lambda x: x['name'])

chapter_media_by_id = {x['chapterId']: x for x in media_registry.get('chapterThumbnails', [])}
character_media_by_id = {
    x['characterId']: x for x in media_registry.get('officialCharacterImages', [])
    if x.get('characterId')
}
poll_page_url = media_registry.get('sources', {}).get('characterPoll', '')
for item in chapters:
    media = chapter_media_by_id.get(item['id'], {})
    item['media'] = {
        'type': 'official-jumpplus-thumbnail',
        'imageUrl': media.get('imageUrl', ''),
        'pageUrl': media.get('episodeUrl', ''),
        'sourceRef': media.get('sourceRef', 'src-jumpplus-episode-thumbnails'),
        'verification': media.get('verification', 'pending-official-page-collection'),
        'note': media.get('note', '公式サムネイルURL未収集。')
    }
for item in characters:
    media = character_media_by_id.get(item['id'])
    if media:
        item['media'] = {
            'type': 'official-character-poll',
            'imageUrl': media.get('imageUrl', ''),
            'pageUrl': poll_page_url,
            'sourceRef': media.get('sourceRef', 'src-official-character-vote-4'),
            'verification': media.get('verification', 'official-page-direct-link'),
            'officialLabel': media.get('officialLabel', ''),
            'iconNumber': media.get('iconNumber'),
            'note': '第4回キャラクター人気投票の公式一覧画像。'
        }
    else:
        item['media'] = {
            'type': 'official-character-poll',
            'imageUrl': '',
            'pageUrl': poll_page_url,
            'sourceRef': 'src-official-character-vote-4',
            'verification': 'not-listed-or-unmatched',
            'officialLabel': '',
            'iconNumber': None,
            'note': '公式人気投票画像との対応未確認、または公式一覧に掲載なし。'
        }

if DETAILS.exists():
    shutil.rmtree(DETAILS)
for obsolete in ('chapters.js', 'characters.js', 'techniques.js', 'terms.js'):
    (GEN / obsolete).unlink(missing_ok=True)

supplement_ids_by_character = {}
for item in supplements:
    for character_id in item.get('character_ids', []):
        supplement_ids_by_character.setdefault(character_id, []).append(item['id'])
for item in characters:
    item['supplementIds'] = supplement_ids_by_character.get(item['id'], [])

volume_cover_by_id = {x['id']: x for x in media_registry.get('volumes', [])}
source_by_id = {x['id']: x for x in sources}
chapters_by_volume = {}
for item in chapters:
    chapters_by_volume.setdefault(item.get('volume'), []).append(item)
supplements_by_volume = {}
for item in supplements:
    supplements_by_volume.setdefault(item.get('volume'), []).append(item)

volumes = []
for record in volume_records:
    cover = volume_cover_by_id.get(record['id'], {})
    number = cover.get('number')
    synopsis_source_ref = record.get('synopsis_source_ref', '')
    synopsis_source = source_by_id.get(synopsis_source_ref, {})
    volume_chapters = chapters_by_volume.get(number, [])
    volume_supplements = supplements_by_volume.get(number, [])
    volumes.append({
        'id': record['id'], 'number': number,
        'label': cover.get('label', ''), 'title': cover.get('title', ''),
        'synopsis': record.get('synopsis', ''),
        'synopsisSourceRef': synopsis_source_ref,
        'verification': record.get('verification', ''),
        'imageUrl': cover.get('imageUrl', ''),
        'pageUrl': synopsis_source.get('url') or cover.get('pageUrl', ''),
        'coverPageUrl': cover.get('pageUrl', ''),
        'sourceRef': cover.get('sourceRef', 'src-official-comics-list'),
        'coverVerification': cover.get('verification', ''),
        'chapterCount': len(volume_chapters),
        'chapters': [{
            'id': chapter['id'], 'label': chapter['label'], 'title': chapter['title'],
            'startPage': chapter.get('startPage')
        } for chapter in volume_chapters],
        'supplementCount': len(volume_supplements),
        'supplements': [{
            'id': supplement['id'], 'title': supplement.get('title', ''),
            'summary': supplement.get('summary', '')
        } for supplement in volume_supplements]
    })

character_name_map = {}
for item in characters:
    for label in [item['name'], *item.get('aliases', [])]:
        if label and label not in character_name_map:
            character_name_map[label] = item['id']
for item in techniques:
    item['userRefs'] = [
        {'name': user_name, 'characterId': character_name_map.get(user_name)}
        for user_name in item.get('users', [])
    ]

chapter_detail = detail_batches(chapters, 'chapters')
character_detail = detail_batches(characters, 'characters')
technique_detail = detail_batches(techniques, 'techniques')
term_detail = detail_batches(terms, 'terms')

chapter_direct_checked = sum(bool(x.get('verificationBasis', {}).get('primary_manga_page_direct_check')) for x in chapters)
character_first_pass = sum('first-pass' in (x.get('verification') or '') for x in characters)
technique_first_pass = sum('first-pass' in (x.get('verification') or '') for x in techniques)
term_first_pass = sum('first-pass' in (x.get('verification') or '') for x in terms)
term_with_sources = sum(bool(x.get('sourceRefs')) for x in terms)

meta = {
    'title': '呪術廻戦 原作漫画データベース',
    'subtitle': '0巻4話＋本編271話／漫画原作準拠',
    'counts': {
        'chapters': len(chapters), 'characters': len(characters),
        'techniques': len(techniques), 'terms': len(terms),
        'supplements': len(supplements), 'sources': len(sources), 'volumes': len(volumes)
    },
    'quality': {
        'chapterSummariesEntered': sum(bool(x['summaryFull'].strip()) for x in chapters),
        'chapterPrimaryPageDirectChecked': chapter_direct_checked,
        'characterFirstPassPending': character_first_pass,
        'techniqueFirstPassPending': technique_first_pass,
        'termFirstPassPending': term_first_pass,
        'termsWithDirectSourceRefs': term_with_sources,
        'stage': 'first-draft-complete-primary-page-audit-pending',
        'officialVolumeImages': sum(bool(x.get('imageUrl')) for x in volumes),
        'officialVolumeSynopses': sum(bool(x.get('synopsis')) for x in volumes),
        'officialCharacterImages': sum(bool(x.get('media', {}).get('imageUrl')) for x in characters),
        'officialChapterThumbnails': sum(bool(x.get('media', {}).get('imageUrl')) for x in chapters),
        'detailedChapterEvents': sum(len(x.get('detailedEvents', [])) for x in chapters),
        'dialogueSummaries': sum(len(x.get('dialogueSummaries', [])) for x in chapters),
        'crosscheckedLines': sum(len(x.get('crosscheckedLines', [])) for x in chapters),
        'popularLineGists': sum(len(x.get('popularLineGists', [])) for x in chapters),
        'highlightKeywords': sum(len(x.get('highlightKeywords', [])) for x in chapters),
        'chaptersWithDialogueSummary': sum(bool(x.get('dialogueSummaries')) for x in chapters),
        'chaptersWithCrosscheckedLines': sum(bool(x.get('crosscheckedLines')) for x in chapters)
    },
    'scope': overall.get('scope', {}), 'verification': overall.get('verification', {}),
    'completionNote': overall.get('completion_note', ''),
    'buildVersion': 'site-v8-source-crosschecked-lines', 'canonicalData': 'data/source'
}

catalog = {
    'meta': meta, 'arcs': arcs,
    'chapters': [{
        'id': x['id'], 'label': x['label'], 'title': x['title'], 'volume': x['volume'],
        'arcId': x['arcId'], 'summaryShort': x['summaryShort'],
        'highlightKeywords': x.get('highlightKeywords', [])[:10],
        'detailChunk': Path(chapter_detail[x['id']]).stem,
        'hasMedia': bool(x.get('media', {}).get('imageUrl')),
        'mediaVerification': x.get('media', {}).get('verification', '')
    } for x in chapters],
    'characters': [{
        'id': x['id'], 'name': x['name'], 'aliases': x.get('aliases', []),
        'category': x['category'], 'affiliation': x['affiliation'],
        'detailChunk': int(Path(character_detail[x['id']]).stem.split('-')[-1]),
        'hasMedia': bool(x.get('media', {}).get('imageUrl')),
        'mediaVerification': x.get('media', {}).get('verification', '')
    } for x in characters],
    'techniques': [{
        'id': x['id'], 'name': x['name'], 'reading': x['reading'], 'aliases': x.get('aliases', []),
        'category': x['category'], 'users': x['users'],
        'detailChunk': int(Path(technique_detail[x['id']]).stem.split('-')[-1])
    } for x in techniques],
    'terms': [{
        'id': x['id'], 'name': x['name'], 'category': x['category'],
        'detailChunk': int(Path(term_detail[x['id']]).stem.split('-')[-1])
    } for x in terms],
    'supplements': [{
        'id': x['id'], 'title': x['title'], 'volume': x.get('volume'), 'summary': x.get('summary', '')
    } for x in supplements],
    'volumes': volumes,
    'sources': [{
        'id': x['id'], 'title': x.get('title', ''), 'type': x.get('type', ''),
        'publisher': x.get('publisher', ''), 'url': x.get('url', '')
    } for x in sources]
}

for name, data in [
    ('catalog', catalog), ('chapters', chapters), ('characters', characters),
    ('techniques', techniques), ('terms', terms), ('supplements', supplements), ('sources', sources), ('volumes', volumes)
]:
    write_json(GEN / f'{name}.json', data)

write_js(GEN / 'catalog.js', 'catalog', catalog)
write_js(GEN / 'catalog-characters.js', 'catalog', {
    'meta': meta, 'chapters': catalog['chapters'], 'characters': catalog['characters'],
    'supplements': catalog['supplements'], 'volumes': catalog['volumes'], 'sources': catalog['sources']
})
write_js(GEN / 'catalog-techniques.js', 'catalog', {
    'meta': meta, 'chapters': catalog['chapters'], 'techniques': catalog['techniques'],
    'sources': catalog['sources']
})
write_js(GEN / 'catalog-terms.js', 'catalog', {
    'meta': meta, 'chapters': catalog['chapters'], 'terms': catalog['terms'],
    'sources': catalog['sources']
})
write_js(GEN / 'catalog-supplements.js', 'catalog', {
    'meta': meta, 'characters': catalog['characters'], 'supplements': catalog['supplements'],
    'sources': catalog['sources']
})
write_js(GEN / 'catalog-volumes.js', 'catalog', {
    'meta': meta, 'volumes': catalog['volumes'], 'sources': catalog['sources']
})
write_js(GEN / 'catalog-meta.js', 'catalog', {'meta': meta})
write_js(GEN / 'supplements.js', 'supplements', supplements)
write_js(GEN / 'sources.js', 'sources', sources)
write_js(GEN / 'volumes.js', 'volumes', volumes)
print(
    f'generated: chapters={len(chapters)}, characters={len(characters)}, '
    f'techniques={len(techniques)}, terms={len(terms)}, volumes={len(volumes)}, chunks=' 
    f'{len(set(chapter_detail.values())) + len(set(character_detail.values())) + len(set(technique_detail.values())) + len(set(term_detail.values()))}'
)
