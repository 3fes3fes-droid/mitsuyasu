# サッカー最新版の移行保存

光康サイトのサッカー部分を切り出した最新版です。4リーグの試合・順位・選手データ、表示コード、修正記録、依存コンポーネントを保存しています。

- `football-latest-source.zip`：元サイトの最新版コード・データと追加画像16枚。
- 既存の `../Football_archive_single.html`：画像2,063枚を保存しているファイル。
- 合計2,079枚の画像を元と同じバイト列で復元できます。既存HTMLに入っている表示データより、ZIP内の最新版データを優先します。

## 復元

Python 3で `python restore-football.py` を実行すると、`football-restored/` にコード・データ・全画像を復元します。画像はすべてSHA-256で照合します。

このフォルダはサッカー部分の保存用です。最新版の元データは `app/archives/football/football-snapshot.json`、表示コードは同フォルダの `dashboard.tsx` です。

元サイトのソース版：`ccd809ef628b8bfefc43ed80e22604624c2970dd`
