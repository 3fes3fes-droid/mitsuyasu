# 編集ガイド

## 通常データを直す

- 各話：`data/source/chapters/*.json`
- 人物：`data/source/characters.json`
- 技・術式：`data/source/techniques.json`
- 用語：`data/source/terms.json`
- コミックスあらすじ：`data/source/volumes.json`
- 全話ハイライト：`data/source/chapter_highlights.json`
- 漫画記事の短文照合原本：`data/source/chapter_line_evidence.json`

修正後は次を実行します。

```powershell
python tools/build_chapter_highlights.py
python tools/build_site.py
python tools/validate_site.py
python tools/audit_volumes.py
python tools/audit_data_quality.py
```

`build_chapter_highlights.py` は既存の各話あらすじ・検証済み重要出来事・技・用語参照、話数照合済みの名言要旨定義、記事横断照合済み短文を統合します。長い逐語台詞を追加せず、短文と独自の要旨を別項目で登録します。個別に残す短い逐語引用は各話JSONの `memorable_quotes` を使います。

## 漫画記事の照合データを更新する

取得済みページを再解析する場合：

```powershell
set JUJUTSU_CACHE_ONLY=1
python tools/research_manga_facts.py
python tools/build_chapter_highlights.py
python tools/build_site.py
python tools/validate_site.py
```

macOS/Linuxでは `JUJUTSU_CACHE_ONLY=1 python tools/research_manga_facts.py` とします。ネットワークから再収集する場合は環境変数を外します。取得失敗は `reports/MANGA_SOURCE_RESEARCH.json` に残るため、失敗話を推測で手埋めしません。

採用条件：

- 原作漫画の記事部分だけ
- アニメ、劇場版、声優、予想、考察、感想を除外
- 正規化後の同一文言を異なる二つ以上の記事系統で確認
- 表示用の話者は原作ページ直接監査まで空欄
- 記事URLは短文ごとにブラウザへ重複格納せず、話単位の一意な一覧へ縮約

コミックスの収録話は各話原本の `volume`、描き下ろしは補遺原本の `volume` から生成します。表示用の `data/generated/volumes.json` は直接編集しません。

巻あらすじは対応する集英社公式商品ページの巻紹介を根拠に、DB用の文章として要約します。`synopsis_source_ref` は `sources_registry.json` に存在する公式出典IDを指定し、確認状態は `official-volume-synopsis-paraphrased` とします。

## 公式画像リンクを直す

原本は `data/source/media_registry.json` です。

- `volumes`：0巻～30巻の公式表紙
- `officialCharacterImages`：第4回公式人気投票の掲載名・画像番号・DB人物ID
- `chapterThumbnails`：各話ID、公式画像URL、公式エピソードURL、確認状態

未確認URLを規則から推測して入力しません。URLとエピソードページの両方を確認できた場合だけ `official-page-direct-link` にします。

各話画像を収集する場合：

```powershell
python tools/refresh_official_images.py
```

更新後は自動的に `build_site.py` と `validate_site.py` が実行されます。既存台帳は `media_registry.backup.json` へ退避されます。

## 確認状態

- `official-page-direct-link`：公式ページとの直接対応を確認済み
- `official-volume-synopsis-paraphrased`：公式巻紹介を根拠にDB用として要約
- `pending-official-page-collection`：未収集。画面に画像を出さない
- `not-listed-or-unmatched`：公式一覧に掲載なし、またはDB人物との対応未確認
- `first-pass...`：本文データの第一稿、個別精査前
- `...not-primary-pages`：複数資料で突合済み、単行本ページ直接監査前
- `crosschecked-manga-secondary`：二つ以上の漫画記事系統で短文の同一文言を確認。原作ページ直接監査前

## 禁止事項

- アニメ、映画、ゲーム、小説、舞台の描写を原作情報として追加しない
- URL規則だけから未確認の画像URLを生成しない
- 画像ファイルをZIPへ転載・同梱しない
- Fandom等の二次資料だけで確定扱いにしない
- 二次記事の周辺文から推定した話者名を表示しない
- 正式名称不明の技へ勝手な正式名称を付けない
- 生死不明の人物を推測で死亡・生存にしない
