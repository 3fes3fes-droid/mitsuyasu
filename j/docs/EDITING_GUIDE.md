# 編集ガイド

## 各話を直す

1. `data/source/chapters` から話数のJSONを開く
2. 根拠を確認した項目だけ修正する
3. 出典IDと確認状態を更新する
4. 次を順番に実行する

```powershell
python tools/build_site.py
python tools/validate_site.py
python tools/audit_data_quality.py
```

## 人物・技・用語を直す

- 人物：`data/source/characters.json`
- 技・術式：`data/source/techniques.json`
- 用語：`data/source/terms.json`

巨大ファイルを直接編集する場合は、編集前にGit commitを作ることを推奨します。

## 確認状態

- `first-pass...`：第一稿、個別精査前
- `...not-primary-pages`：複数資料で突合済み、単行本ページ直接監査前
- 原作ページを直接確認した場合だけ、直接監査済みの状態へ変更する

## 禁止事項

- アニメ、映画、ゲーム、小説、舞台の描写を原作情報として追加しない
- Fandom等の二次資料だけで確定扱いにしない
- 正式名称不明の技へ勝手な正式名称を付けない
- 生死不明の人物を推測で死亡・生存にしない
- 逆引き不一致を内容確認なしに機械統合しない
