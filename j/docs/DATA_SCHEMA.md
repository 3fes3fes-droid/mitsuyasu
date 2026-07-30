# データ構造

## 原本

### 各話

`data/source/chapters/*.json`

主要項目：固定ID、公式話名、収録巻、開始ページ、短文・詳細あらすじ、人物・技・用語参照、出典参照、確認状態。

短い逐語引用・手入力キーワードの任意項目：

```text
memorable_quotes[]
  text / speaker / kind / verification
highlight_keywords[]
```

`memorable_quotes` は短いセリフを話単位で個別登録します。長台詞の転載には使いません。

全話ハイライト原本：

`data/source/chapter_highlights.json`

```text
chapters.{chapterId}
  detailedEvents[]
    text / level / basis
  crosscheckedLines[]
    speaker(null) / text / kind / verification
    sourceCount / sourceRefs[]
  dialogueSummaries[]
    text / kind / basis
  popularLineGists[]
    speaker / label / text / rank
    kind / sourceRef / verification
  highlightKeywords[]
```

`detailedEvents` は検証済み重要出来事と詳細あらすじの場面文を近似重複排除して統合します。`dialogueSummaries` は既存の詳細あらすじから発言・判断・心情・言動を要旨として抽出します。`popularLineGists` は公開名言集で話者と漫画話数を照合し、長い原文を転載せず独自の要旨へ変換した項目です。`crosscheckedLines` は下記の照合原本から取り込みます。`tools/build_chapter_highlights.py` で全275話の完全集合を再生成します。

漫画記事の短文照合原本：

`data/source/chapter_line_evidence.json`

```text
scope: manga-only
policy
sourceRefs[]
counts
chapters.ch-NNN[]
  speaker: null
  text
  kind: 短い作中語句・発言
  verification: crosschecked-manga-secondary
  sourceCount
  sourceRefs[]
  sourceUrls[]
```

採用条件は、異なる二つ以上の記事系統で正規化後の同一文言を確認できることです。原本では短文ごとに `sourceUrls` を保持します。表示用データでは短文ごとのURL重複を除き、話単位の `crosscheckedSourceUrls` としてまとめ、`出典・確認` タブから直接開けるようにします。話者は原作ページ直接監査まで `null` 固定です。候補収集と再解析は `tools/research_manga_facts.py`、取得状況と失敗URLは `reports/MANGA_SOURCE_RESEARCH.json` が記録します。

### 人物・技・用語

- `data/source/characters.json`
- `data/source/techniques.json`
- `data/source/terms.json`

IDは変更せず、表示名・説明・関連話を修正します。

### コミックスあらすじ

`data/source/volumes.json`

```text
id
synopsis
synopsis_source_ref
verification
```

`id` は `vol-00`～`vol-30`。`synopsis` は集英社公式の商品ページにある巻紹介を根拠にしたDB用の独自要約です。公式原文をそのまま転載せず、`synopsis_source_ref` で対応する公式出典を明示します。

### 公式画像台帳

`data/source/media_registry.json`

```text
schemaVersion
policy
sources
volumes[]
  id / number / label / title
  imageUrl / pageUrl / sourceRef / verification
officialCharacterImages[]
  pollOrder / officialLabel / iconNumber
  imageUrl / sourceRef / verification
  characterId / assignmentStatus
chapterThumbnails[]
  chapterId
  imageUrl / episodeUrl / sourceRef
  verification / note
```

`chapterThumbnails` は必ず275件の完全集合を保持します。未確認行も削除せず、URLを空文字、確認状態を `pending-official-page-collection` にします。

## 表示用データ

`tools/build_site.py` が原本を正規化し、`data/generated` へJSONとクラシックJavaScriptを生成します。

- 各話・人物の `media` は詳細チャンクへ格納
- 照合済み短文は選択話の詳細チャンクだけへ格納
- 記事URLは短文ごとに重複格納せず、話単位の一意なURL一覧へ縮約
- 一覧カタログには `hasMedia` と確認状態だけを格納
- コミックス31件は小さいため、あらすじ・収録話・補遺を `catalog-volumes.js` へ格納
- 画像ファイル自体は生成・保存しない

生成後のコミックス1件には、次の表示用項目が含まれます。

```text
id / number / label / title
synopsis / synopsisSourceRef / verification
imageUrl / pageUrl / coverPageUrl / sourceRef / coverVerification
chapterCount
chapters[]: id / label / title / startPage
supplementCount
supplements[]: id / title / summary
```

収録話と補遺は既存の各話・補遺原本にある巻番号から生成し、`tools/audit_volumes.py` で275話と4件の重複・欠落を検査します。

表示用データは直接編集しません。
