# 呪術廻戦 原作漫画DB 精査Phase 1 レポート

## 今回の一区切り

0巻全4話と、本編第1話から第18話までの合計22話を、第一稿から一段階進めた。

各話へ追加した項目は次のとおり。

- 詳細あらすじ `summary_full`
- 重要出来事 `key_events_verified_phase1`
- 人物と登場形態 `character_appearances_verified_phase1`
- 術式・技・呪具と使用関係 `technique_appearances_verified_phase1`
- 関連用語 `term_ids_verified_phase1`
- 精査根拠と限界 `verification_basis`
- Phase 1で使用した出典 `source_refs_phase1`

## 精査段階の意味

今回の状態は `phase1-crosschecked-secondary-not-primary-pages`。

- 話名、巻、開始ページ：集英社公式で確認
- 内容：原作漫画だけを扱う章別資料と過去候補を比較
- 要約：転載せず、日本語で新規作成
- アニメ、劇場版、ゲーム、小説、舞台：不使用
- 原作単行本の各ページを直接開いた最終照合：未実施

したがって、「未検証候補のまま」ではないが、「原作本文で最終確認済み」とも表記していない。

## 修正した明確な誤結合

### 1. 0巻の祈本里香と、本編後の「リカ」を分離

第一稿では、解呪後に乙骨へ残った外付け存在としての「リカ」に、0巻4話も候補参照されていた。

Phase 1では次のように分離した。

- 0巻：`祈本里香`
- 本編再登場後：`リカ`

旧候補は監査記録へ残し、現在の参照からは除外した。

### 2. 0巻第1話と「解」の誤結合を除去

第0巻第1話の候補術式に、宿儺・虎杖の斬撃技「解」が文字列照合の誤りで入っていた。内容上の根拠がないため削除した。

修正内容は `reports/phase1_corrections.json` に記録している。

## データ件数

- 全話：275件
- Phase 1詳細化：22件
- 人物・存在：183件
- 術式・技・呪具：122件
- 用語：89件
- Phase 1で新規追加した術式・呪具：屠坐魔
- Phase 1で新規追加した用語：呪胎、秘匿死刑、京都姉妹校交流会、解呪、領域

## 主なファイル

```text
 data/chapters.json
 data/chapters/zero-01.json ～ zero-04.json
 data/chapters/ch-001.json ～ ch-018.json
 data/characters.json
 data/techniques.json
 data/terms.json
 data/phase1_review_queue.csv
 reports/phase1_corrections.json
 tools/validate_phase1.py
 QA_REPORT.md
```

## 次工程

本編第19話以降も同じ構造で詳細化する。

原作ページ直接確認は最終監査工程として別に残し、現段階で確度を偽装しない。
