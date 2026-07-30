# データ構造

## 原本

### 各話

`data/source/chapters/*.json`

主要項目：

- `id`：固定ID
- `title_official`：公式話名
- `volume`、`start_page`：収録巻と開始ページ
- `summary_short`、`summary_full`：短文・詳細あらすじ
- `key_events_verified_phaseN`：そのPhaseで確認した出来事
- `character_ids_verified_phaseN`：人物参照
- `technique_ids_verified_phaseN`：技・術式参照
- `term_ids_verified_phaseN`：用語参照
- `source_refs_phaseN`：出典参照

### 人物・技・用語

- `data/source/characters.json`
- `data/source/techniques.json`
- `data/source/terms.json`

IDは変更せず、表示名・説明・関連話を修正します。

## 表示用データ

`tools/build_site.py`が、Phaseごとの最新確認欄を選択し、`data/generated`へ正規化JSONとJavaScriptを生成します。表示用データは直接編集しません。
