# NO SPOILER FOOTBALL

光康サイトからサッカー画面を移した GitHub Pages 版です。

[サッカーページを開く](https://3fes3fes-droid.github.io/mitsuyasu/football/)

4リーグの試合・順位・チーム・選手と、保存済みの補足情報を引き継いでいます。最初に保存データを表示し、ESPN の公開 API から試合・順位を更新します。取得できない場合も保存データで使えます。

画像2,079枚を元と同じ内容で表示します。2,063枚は既存の `../Football_archive_single.html` から必要な範囲だけを読み込み、追加16枚は `players/` に保存しています。既存HTMLの画像領域は `app/archives/football/photo-ranges.json` と対応するため、既存HTMLはそのまま保持してください。

## ビルド

このフォルダで `npm ci`、`npm run build` を実行すると、公開用の `app.b64` が再生成されます。`index.html`、`styles.css`、`app.b64`、`players/` と、親フォルダの `Football_archive_single.html` が公開画面を構成します。

保存データは `app/archives/football/packed-snapshot.mjs` に gzip/base64 で格納されています。表示コードは同フォルダの `dashboard.tsx` です。

## 元サイトのコード・全画像を復元

`football-latest-source.zip` に元サイトの最新版コード・データと追加画像16枚を保存しています。Python 3で `python restore-football.py` を実行すると、`football-restored/` に元のコード・データ・全画像を復元し、画像2,079枚をSHA-256で照合します。

ZIP内の `app/archives/football/football-snapshot.json` が最新版の元データです。既存HTML内の表示データより、このデータを優先します。

元サイトのソース版: `ccd809ef628b8bfefc43ed80e22604624c2970dd`
