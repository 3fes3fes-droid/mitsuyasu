# ファイル構成

```text
jujutsu-manga-db-site-v2-audited/
├─ index.html                  全体像・横断検索
├─ chapters.html               各話
├─ characters.html             人物
├─ techniques.html             技・術式
├─ terms.html                  用語
├─ supplements.html            30巻描き下ろし
├─ sources.html                出典台帳
├─ status.html                 現在の完成状態
│
├─ assets/
│  ├─ css/app.css
│  └─ js/
│     ├─ core.js               共通処理・遅延読込
│     ├─ home.js
│     ├─ chapters-page.js
│     ├─ entity-page.js
│     ├─ supplements-page.js
│     ├─ sources-page.js
│     └─ status-page.js
│
├─ data/
│  ├─ source/                  編集する原本
│  │  ├─ chapters/             1話1JSON、全275件
│  │  ├─ characters.json
│  │  ├─ techniques.json
│  │  ├─ terms.json
│  │  ├─ supplements.json
│  │  ├─ sources_registry.json
│  │  ├─ arcs.json
│  │  └─ overall.json
│  └─ generated/               build_site.pyが生成
│     ├─ catalog*.js           ページ別軽量索引
│     ├─ *.json                監査・再利用用統合データ
│     └─ details/              遅延読込用54チャンク
│
├─ tools/
│  ├─ build_site.py            表示データ生成
│  ├─ validate_site.py         構造・参照・構文検査
│  ├─ audit_data_quality.py    未精査項目の抽出
│  ├─ make_manifest.py         ファイル台帳生成
│  ├─ package_site.py          ZIP化
│  └─ serve.py                 ローカルHTTP表示
│
├─ reports/
│  ├─ DATA_QUALITY_AUDIT.md
│  ├─ PERFORMANCE_AUDIT.md
│  ├─ FULL_UI_AUDIT.md
│  ├─ data_quality_issues.csv
│  └─ 監査生データ
│
└─ docs/                       仕様、履歴、旧監査資料
```

## 原則

- 正本は `data/source`
- `data/generated` は手編集しない
- 一話の変更は対応する `data/source/chapters/*.json` だけで行う
- 生成後に必ず `validate_site.py` を実行する
- 不確かな関係は自動統合せず、品質監査キューへ残す
