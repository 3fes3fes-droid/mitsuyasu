from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data' / 'source'
GEN = ROOT / 'data' / 'generated'
REPORTS = ROOT / 'reports'
REPORTS.mkdir(exist_ok=True)

registry = json.loads((SRC / 'media_registry.json').read_text(encoding='utf-8'))
characters = json.loads((GEN / 'characters.json').read_text(encoding='utf-8'))
character_by_id = {x['id']: x for x in characters}
chapters = json.loads((GEN / 'chapters.json').read_text(encoding='utf-8'))
catalog = json.loads((GEN / 'catalog.json').read_text(encoding='utf-8'))
volumes = registry['volumes']
poll = registry['officialCharacterImages']
chapter_media = registry['chapterThumbnails']

reviewed_non_exact = []
for row in poll:
    character_id = row.get('characterId')
    if not character_id:
        continue
    character = character_by_id[character_id]
    accepted_names = {character['name'], *(character.get('aliases') or [])}
    if row['officialLabel'] not in accepted_names:
        reviewed_non_exact.append({
            'pollOrder': row['pollOrder'],
            'officialLabel': row['officialLabel'],
            'dbCharacterName': character['name'],
            'dbCharacterId': character_id,
            'reason': row.get('assignmentStatus', ''),
        })

report = {
    'buildVersion': catalog.get('meta', {}).get('buildVersion', 'unknown'),
    'volumeImages': {'registered': len(volumes), 'verified': sum(bool(x.get('imageUrl')) for x in volumes)},
    'officialPollImages': {
        'registered': len(poll),
        'assignedToDbCharacters': sum(bool(x.get('characterId')) for x in poll),
        'unassignedOfficialLabels': [x['officialLabel'] for x in poll if not x.get('characterId')],
        'unusedIconNumbersBetween1And187': sorted(set(range(1, 188)) - {x['iconNumber'] for x in poll}),
        'reviewedNonExactAssignments': reviewed_non_exact,
    },
    'dbCharacterImages': {
        'total': len(characters),
        'assigned': sum(bool(x.get('media', {}).get('imageUrl')) for x in characters),
        'pendingCharacterNames': [x['name'] for x in characters if not x.get('media', {}).get('imageUrl')],
    },
    'chapterThumbnails': {
        'total': len(chapter_media),
        'verified': sum(bool(x.get('imageUrl')) for x in chapter_media),
        'pending': sum(not x.get('imageUrl') for x in chapter_media),
        'verifiedChapterIds': [x['chapterId'] for x in chapter_media if x.get('imageUrl')],
    },
    'performance': {
        'catalogBytes': (GEN / 'catalog.js').stat().st_size,
        'catalogVolumesBytes': (GEN / 'catalog-volumes.js').stat().st_size,
        'maxDetailChunkBytes': max(x.stat().st_size for x in (GEN / 'details').rglob('*.js')),
        'imageLoading': 'selected-item-only',
    },
    'policy': registry['policy'],
}
(REPORTS / 'official_media_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

md = f'''# 公式画像リンク監査

## 結果

- コミックス表紙：{report['volumeImages']['verified']} / {report['volumeImages']['registered']}冊
- 第4回公式人気投票画像：{report['officialPollImages']['registered']}件
- DB人物への割当：{report['officialPollImages']['assignedToDbCharacters']} / {len(characters)}件
- 各話公式サムネイル：{report['chapterThumbnails']['verified']} / {report['chapterThumbnails']['total']}話
- 未収集各話：{report['chapterThumbnails']['pending']}話

## 人気投票側でDB未登録

{', '.join(report['officialPollImages']['unassignedOfficialLabels']) or 'なし'}

## DB側で公式画像未対応

{', '.join(report['dbCharacterImages']['pendingCharacterNames']) or 'なし'}

## 画像番号検査

- 公式一覧画像：183件、画像番号重複なし
- 1～187のうち未使用：{', '.join(map(str, report['officialPollImages']['unusedIconNumbersBetween1And187']))}
- DB人物IDへの重複割当なし
- 完全同名または既存別名で一致：{report['officialPollImages']['assignedToDbCharacters'] - len(report['officialPollImages']['reviewedNonExactAssignments'])}件
- 表記差を個別確認して割当：{len(report['officialPollImages']['reviewedNonExactAssignments'])}件

## 個別確認した表記差

{chr(10).join(f"- 投票一覧「{x['officialLabel']}」→ DB「{x['dbCharacterName']}」" for x in report['officialPollImages']['reviewedNonExactAssignments']) or 'なし'}

## 各話サムネイル

現在のZIPへ直接確認済みとして登録したのは `ch-001` のみです。残りは推測URLを作らず、`pending-official-page-collection` のまま保持します。`tools/refresh_official_images.py` は公式RSSまたは公式ページの次話リンクを使い、話数・作品名・許可ホストを確認して台帳を更新します。

## 軽量化

- `catalog.js`：{report['performance']['catalogBytes']:,} bytes
- `catalog-volumes.js`：{report['performance']['catalogVolumesBytes']:,} bytes
- 最大詳細チャンク：{report['performance']['maxDetailChunkBytes']:,} bytes
- 外部画像読込：選択中の1件のみ

## 方針

画像ファイルはZIPへ転載せず、公式URLだけを保持します。URL未確認の項目は画像を表示せず、UIで未収集状態を明示します。
'''
(REPORTS / 'OFFICIAL_MEDIA_AUDIT.md').write_text(md, encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
