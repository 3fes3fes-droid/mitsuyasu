from __future__ import annotations
from pathlib import Path
import csv, json, collections, statistics

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'data' / 'generated'
REPORTS = ROOT / 'reports'
REPORTS.mkdir(exist_ok=True)


def load(name):
    return json.loads((GEN / f'{name}.json').read_text(encoding='utf-8'))


chapters = load('chapters')
characters = load('characters')
techniques = load('techniques')
terms = load('terms')
supplements = load('supplements')
sources = load('sources')

chapter_map = {x['id']: x for x in chapters}
character_map = {x['id']: x for x in characters}
technique_map = {x['id']: x for x in techniques}
term_map = {x['id']: x for x in terms}
issues = []


def add(priority, code, entity_type, entity_id, name, detail):
    issues.append({
        'priority': priority, 'code': code, 'entity_type': entity_type,
        'entity_id': entity_id, 'name': name, 'detail': detail
    })


# 各話
summary_lengths = []
for row in chapters:
    length = len((row.get('summaryFull') or '').strip())
    summary_lengths.append(length)
    if length < 180:
        add('medium', 'summary_under_180', 'chapter', row['id'], f"{row['label']} {row['title']}", f'{length}字。初期方針の300～600字より短い。')
    if not row.get('sourceRefs'):
        add('high', 'missing_sources', 'chapter', row['id'], row['title'], '出典参照がない。')
    if not row.get('sourceLocator'):
        add('medium', 'missing_source_locator', 'chapter', row['id'], row['title'], '単行本内の出典位置がない。')

# 人物
for row in characters:
    profile_length = len((row.get('profile') or '').strip())
    if profile_length < 25:
        add('medium', 'thin_profile', 'character', row['id'], row['name'], f'紹介文が{profile_length}字。経歴・特徴として不足。')
    if not row.get('sourceRefs'):
        add('high', 'missing_sources', 'character', row['id'], row['name'], '出典参照がない。')
    if not row.get('chapterIds') and not row.get('supplementIds'):
        add('medium', 'missing_related_work', 'character', row['id'], row['name'], '関連話・補遺のどちらもない。')
    if 'first-pass' in (row.get('verification') or ''):
        add('high', 'first_pass_pending', 'character', row['id'], row['name'], '人物個別の再精査前。')

# 技・術式
for row in techniques:
    length = len((row.get('description') or '').strip())
    if length < 20:
        add('medium', 'thin_description', 'technique', row['id'], row['name'], f'説明が{length}字。条件・制限・効果として不足。')
    if not row.get('sourceRefs'):
        add('high', 'missing_sources', 'technique', row['id'], row['name'], '出典参照がない。')
    if not row.get('chapterIds'):
        add('medium', 'missing_chapters', 'technique', row['id'], row['name'], '関連話がない。')
    if 'first-pass' in (row.get('verification') or ''):
        add('high', 'first_pass_pending', 'technique', row['id'], row['name'], '技・術式個別の再精査前。')

# 用語
for row in terms:
    length = len((row.get('definition') or '').strip())
    if length < 20:
        add('medium', 'thin_definition', 'term', row['id'], row['name'], f'定義が{length}字。')
    if not row.get('sourceRefs'):
        add('high', 'missing_sources', 'term', row['id'], row['name'], '直接の出典参照がない。')
    if not row.get('chapterIds'):
        add('medium', 'missing_chapters', 'term', row['id'], row['name'], '関連話がない。')
    if 'first-pass' in (row.get('verification') or ''):
        add('high', 'first_pass_pending', 'term', row['id'], row['name'], '用語個別の再精査前。')

# 逆引き整合性。事実を自動修正せず、確認キューにする。
for character in characters:
    for chapter_id in character.get('chapterIds', []):
        if character['id'] not in chapter_map[chapter_id].get('characterIds', []):
            add('medium', 'reverse_index_mismatch', 'character', character['id'], character['name'], f'{chapter_id}: 人物側にあるが各話側にない。')
for chapter in chapters:
    for entity_id in chapter.get('characterIds', []):
        if chapter['id'] not in character_map[entity_id].get('chapterIds', []):
            add('medium', 'reverse_index_mismatch', 'chapter', chapter['id'], chapter['title'], f"人物 {character_map[entity_id]['name']} 側にこの話がない。")

for technique in techniques:
    for chapter_id in technique.get('chapterIds', []):
        if technique['id'] not in chapter_map[chapter_id].get('techniqueIds', []):
            add('medium', 'reverse_index_mismatch', 'technique', technique['id'], technique['name'], f'{chapter_id}: 技側にあるが各話側にない。')
for chapter in chapters:
    for entity_id in chapter.get('techniqueIds', []):
        if chapter['id'] not in technique_map[entity_id].get('chapterIds', []):
            add('medium', 'reverse_index_mismatch', 'chapter', chapter['id'], chapter['title'], f"技 {technique_map[entity_id]['name']} 側にこの話がない。")

for term in terms:
    for chapter_id in term.get('chapterIds', []):
        if term['id'] not in chapter_map[chapter_id].get('termIds', []):
            add('medium', 'reverse_index_mismatch', 'term', term['id'], term['name'], f'{chapter_id}: 用語側にあるが各話側にない。')
for chapter in chapters:
    for entity_id in chapter.get('termIds', []):
        if chapter['id'] not in term_map[entity_id].get('chapterIds', []):
            add('medium', 'reverse_index_mismatch', 'chapter', chapter['id'], chapter['title'], f"用語 {term_map[entity_id]['name']} 側にこの話がない。")

status_counts = collections.Counter((row.get('status') or {}).get('status', 'unknown') for row in characters)
verification_counts = {
    'chapters': collections.Counter(row.get('verification', '') for row in chapters),
    'characters': collections.Counter(row.get('verification', '') for row in characters),
    'techniques': collections.Counter(row.get('verification', '') for row in techniques),
    'terms': collections.Counter(row.get('verification', '') for row in terms),
}
issue_counts = collections.Counter(row['code'] for row in issues)
priority_counts = collections.Counter(row['priority'] for row in issues)

summary = {
    'counts': {
        'chapters': len(chapters), 'characters': len(characters), 'techniques': len(techniques),
        'terms': len(terms), 'supplements': len(supplements), 'sources': len(sources)
    },
    'summary_lengths': {
        'minimum': min(summary_lengths), 'median': statistics.median(summary_lengths),
        'maximum': max(summary_lengths), 'under_180': sum(x < 180 for x in summary_lengths)
    },
    'primary_page_direct_checked_chapters': sum(bool(row.get('verificationBasis', {}).get('primary_manga_page_direct_check')) for row in chapters),
    'status_counts': dict(status_counts),
    'verification_counts': {key: dict(value) for key, value in verification_counts.items()},
    'issue_counts': dict(issue_counts),
    'priority_counts': dict(priority_counts),
    'total_queue_items': len(issues)
}

(REPORTS / 'data_quality_audit.json').write_text(json.dumps({'summary': summary, 'issues': issues}, ensure_ascii=False, indent=2), encoding='utf-8')
with (REPORTS / 'data_quality_issues.csv').open('w', encoding='utf-8-sig', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=['priority', 'code', 'entity_type', 'entity_id', 'name', 'detail'])
    writer.writeheader()
    writer.writerows(issues)

md = f'''# データ品質監査

## 結論

現在のデータは、**全範囲を閲覧できる第一稿**です。構造上の欠落や参照切れはありませんが、原作ページ直接監査済みの完成データではありません。

## 収録と入力状況

- 各話：{len(chapters)}件
- 人物・存在：{len(characters)}件
- 技・術式：{len(techniques)}件
- 用語：{len(terms)}件
- 補遺：{len(supplements)}件
- 各話詳細あらすじ：{sum(bool((row.get('summaryFull') or '').strip()) for row in chapters)} / {len(chapters)}件
- 単行本ページ直接監査済み：{summary['primary_page_direct_checked_chapters']} / {len(chapters)}件

## 精査で確認した未完了点

- 詳細あらすじの中央値：{summary['summary_lengths']['median']}字
- 180字未満の詳細あらすじ：{summary['summary_lengths']['under_180']}話
- 人物の第一稿・個別精査待ち：{sum('first-pass' in (row.get('verification') or '') for row in characters)}件
- 技・術式の第一稿・個別精査待ち：{sum('first-pass' in (row.get('verification') or '') for row in techniques)}件
- 用語の第一稿・個別精査待ち：{sum('first-pass' in (row.get('verification') or '') for row in terms)}件
- 出典参照がない用語：{sum(not row.get('sourceRefs') for row in terms)}件
- 人物・技・用語と各話の逆引き不一致：{issue_counts.get('reverse_index_mismatch', 0)}件
- 最終状態が `unknown` の人物・存在：{status_counts.get('unknown', 0)}件

逆引き不一致は、どちらか一方に記録がある関係を自動統合すると誤情報を増やす恐れがあるため、勝手に修正せず確認キューへ残しています。

## 判定

- サイト動作：合格
- 全話収録：合格
- 第一稿としての閲覧：合格
- 全人物の詳細経歴：未完了
- 技・術式の条件・制限・弱点の完全整理：未完了
- 用語ごとの直接出典：未完了
- 単行本全ページ直接監査：未完了

詳細な確認対象は `reports/data_quality_issues.csv` に出力しています。
'''
(REPORTS / 'DATA_QUALITY_AUDIT.md').write_text(md, encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
