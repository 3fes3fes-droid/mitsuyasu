from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'data' / 'generated'
REPORTS = ROOT / 'reports'
REPORTS.mkdir(exist_ok=True)


def load(name: str):
    return json.loads((GEN / f'{name}.json').read_text(encoding='utf-8'))


volumes = load('volumes')
chapters = load('chapters')
supplements = load('supplements')
sources = load('sources')
source_by_ref = {row['id']: row for row in sources}
errors: list[str] = []

if [row.get('id') for row in volumes] != [f'vol-{number:02d}' for number in range(31)]:
    errors.append('コミックスIDが vol-00～vol-30 の完全な連番ではありません。')

embedded_chapter_ids: list[str] = []
embedded_supplement_ids: list[str] = []
rows = []

for volume in volumes:
    volume_id = volume.get('id', 'unknown')
    source_ref = volume.get('synopsisSourceRef')
    if not (volume.get('synopsis') or '').strip():
        errors.append(f'{volume_id}: あらすじが空です。')
    if volume.get('verification') != 'official-volume-synopsis-paraphrased':
        errors.append(f'{volume_id}: あらすじ確認状態が不正です。')
    if source_ref not in source_by_ref:
        errors.append(f'{volume_id}: あらすじ出典 {source_ref!r} が出典台帳にありません。')
    elif not source_by_ref[source_ref].get('url'):
        errors.append(f'{volume_id}: あらすじ出典URLが空です。')

    volume_chapters = volume.get('chapters') or []
    volume_supplements = volume.get('supplements') or []
    embedded_chapter_ids.extend(row.get('id') for row in volume_chapters)
    embedded_supplement_ids.extend(row.get('id') for row in volume_supplements)
    labels = [row.get('label', '') for row in volume_chapters]
    chapter_range = labels[0] if len(labels) == 1 else (
        f'{labels[0]}～{labels[-1]}' if labels else '収録話なし'
    )
    rows.append({
        'id': volume_id,
        'label': volume.get('label'),
        'chapterCount': len(volume_chapters),
        'chapterRange': chapter_range,
        'supplementCount': len(volume_supplements),
        'synopsisSourceRef': source_ref,
        'synopsisSourceUrl': source_by_ref.get(source_ref, {}).get('url', ''),
        'verification': volume.get('verification'),
    })

expected_chapter_ids = [row['id'] for row in chapters]
if embedded_chapter_ids != expected_chapter_ids:
    errors.append('巻別収録話の並びまたは完全性が全275話データと一致しません。')
if len(embedded_chapter_ids) != 275 or len(set(embedded_chapter_ids)) != 275:
    errors.append('巻別収録話が275件の一意な集合ではありません。')

expected_supplement_ids = [row['id'] for row in supplements if row.get('volume') is not None]
if embedded_supplement_ids != expected_supplement_ids:
    errors.append('巻別補遺の割当が補遺原本と一致しません。')

summary = {
    'status': 'PASS' if not errors else 'FAIL',
    'volumeCount': len(volumes),
    'officialSynopsisCount': sum(
        row.get('verification') == 'official-volume-synopsis-paraphrased'
        and bool((row.get('synopsis') or '').strip())
        for row in volumes
    ),
    'chapterAssignmentCount': len(embedded_chapter_ids),
    'supplementAssignmentCount': len(embedded_supplement_ids),
    'errors': errors,
}

(REPORTS / 'volume_content_audit.json').write_text(
    json.dumps({'summary': summary, 'volumes': rows}, ensure_ascii=False, indent=2),
    encoding='utf-8',
)

table_rows = '\n'.join(
    f"| {row['label']} | {row['chapterRange']} | {row['chapterCount']} | "
    f"{row['supplementCount']} | `{row['synopsisSourceRef']}` |"
    for row in rows
)
error_lines = '\n'.join(f'- {message}' for message in errors) or '- なし'
markdown = f"""# コミックス収録内容監査

## 結果

- 判定：**{summary['status']}**
- コミックス：{summary['volumeCount']} / 31冊
- 公式巻紹介を根拠にした要約：{summary['officialSynopsisCount']} / 31冊
- 各話割当：{summary['chapterAssignmentCount']} / 275話
- 補遺割当：{summary['supplementAssignmentCount']} / 4件

## 巻別一覧

| 巻 | 収録範囲 | 話数 | 補遺 | あらすじ出典 |
|---|---:|---:|---:|---|
{table_rows}

## エラー

{error_lines}

あらすじは集英社公式の商品ページにある巻紹介を根拠に、DB用の文章として要約しています。
原文の転載ではありません。収録話は既存の各話原本にある巻番号から機械的に集計し、
全275話と30巻補遺4件の重複・欠落を検査しています。
"""
(REPORTS / 'VOLUME_CONTENT_AUDIT.md').write_text(markdown, encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))

if errors:
    raise SystemExit(1)
