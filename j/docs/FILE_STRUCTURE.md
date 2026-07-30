# ファイル構成

```text
jujutsu-manga-db-site-v8-source-crosschecked-lines/
├─ index.html                  各話ページへの入口
├─ chapters.html               各話・公式サムネイル
├─ volumes.html                コミックス・あらすじ・収録話・公式表紙
├─ characters.html             人物・人気投票公式画像
├─ techniques.html             技・術式
├─ terms.html                  用語
├─ supplements.html            30巻描き下ろし
├─ sources.html                出典台帳
├─ status.html                 現在の完成状態
│
├─ assets/
│  ├─ css/app.css              共通CSS・レスポンシブ表示
│  └─ js/
│     ├─ core.js               共通処理・遅延読込・画像・文字調整
│     ├─ chapters-page.js      各話・名言・キーワード表示
│     ├─ volumes-page.js
│     ├─ entity-page.js
│     ├─ supplements-page.js
│     ├─ sources-page.js
│     └─ status-page.js
│
├─ data/
│  ├─ source/                  編集する原本
│  │  ├─ chapters/             1話1JSON、全275件
│  │  ├─ chapter_highlights.json 全話の名言要旨・言動要旨・詳細出来事・キーワード
│  │  ├─ chapter_line_evidence.json 漫画記事2系統以上で照合した短文原本
│  │  ├─ characters.json
│  │  ├─ techniques.json
│  │  ├─ terms.json
│  │  ├─ supplements.json
│  │  ├─ volumes.json          巻あらすじと公式出典
│  │  ├─ sources_registry.json
│  │  ├─ media_registry.json   表紙・人物画像・各話サムネイル台帳
│  │  ├─ arcs.json
│  │  └─ overall.json
│  └─ generated/               build_site.pyが生成
│     ├─ catalog*.js           ページ別軽量索引
│     ├─ volumes.js/json       コミックス表示データ
│     ├─ *.json                監査・再利用用統合データ
│     └─ details/              遅延読込用54チャンク
│
├─ tools/
│  ├─ build_site.py            表示データ生成
│  ├─ build_chapter_highlights.py 全話ハイライト原本生成
│  ├─ research_manga_facts.py  漫画記事の候補収集・除外・短文照合
│  ├─ validate_site.py         構造・参照・構文・画像台帳検査
│  ├─ audit_official_media.py  公式画像リンク監査
│  ├─ audit_volumes.py         巻あらすじ・収録話・補遺監査
│  ├─ refresh_official_images.py 各話公式画像URL収集
│  ├─ test_official_image_parser.py URL解析単体検査
│  ├─ test_core_media.js       画像カードDOM生成検査
│  ├─ audit_data_quality.py    未精査項目の抽出
│  ├─ make_manifest.py         ファイル台帳生成
│  ├─ package_site.py          ZIP化
│  └─ serve.py                 ローカルHTTP表示
│
├─ reports/
│  ├─ OFFICIAL_MEDIA_AUDIT.md
│  ├─ DATA_QUALITY_AUDIT.md
│  ├─ VOLUME_CONTENT_AUDIT.md
│  ├─ PERFORMANCE_AUDIT.md
│  ├─ COMPACT_UI_AUDIT.md
│  ├─ HIGHLIGHT_CONTENT_AUDIT.md
│  ├─ MANGA_SOURCE_RESEARCH.md
│  ├─ MANGA_SOURCE_RESEARCH.json
│  ├─ data_quality_issues.csv
│  └─ 監査生データ
│
└─ docs/
   ├─ DATA_SCHEMA.md
   ├─ EDITING_GUIDE.md
   ├─ UI_STRUCTURE_V8.md
   ├─ SOURCE_POLICY.md
   └─ history/                 旧フェーズ・旧版監査資料
```

## 原則

- 正本は `data/source`
- `data/generated` は手編集しない
- 巻あらすじの正本は `data/source/volumes.json`
- 画像URLの正本は `data/source/media_registry.json`
- 未確認の画像URLを規則性だけで生成しない
- 一話の本文データ変更は対応する `data/source/chapters/*.json` で行う
- 短文照合原本は二つ以上の記事系統で同一文言を確認したものだけを保持
- 二次記事だけでは話者を確定しない
- 生成後に必ず `validate_site.py` を実行する
- 不確かな関係は自動統合せず、品質監査キューへ残す
