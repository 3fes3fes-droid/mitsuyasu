# mitsuyasu

GitHub Pagesで公開するHTML・データと、取得・更新用コードを管理するリポジトリ。

更新日：2026-10-18（日本時間）

## 公開画面とファイル

| 内容 | 公開URL・編集元 |
| --- | --- |
| NO SPOILER FOOTBALL | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/football/)・`football/` |
| サッカー保存アーカイブ | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/Football_archive_single.html)・`Football_archive_single.html` |
| メディア画面 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/m.html)・`m.html` |
| 各種一覧 | ルートの `anime.html`、`unext.html`、`human.html`、`play.html` などと対応するJSON・CSS・JS |
| 取得・更新処理 | `py/`、`un.py`、`tampermonkey/`、`.github/workflows/` |

公開URLの台帳は [site-links.json](site-links.json)。GitHubの [Actions](https://github.com/3fes3fes-droid/mitsuyasu/actions) にある **Public link audit (manual)** から、登録済みURLを手動確認できる。

サッカー画面の `football/index.html`、`football/app.b64`、`football/styles.css`、`football/players/`、`Football_archive_single.html` は一組の依存関係として管理する。

## 関連リポジトリ

| リポジトリ | 用途 |
| --- | --- |
| [J](https://github.com/3fes3fes-droid/J) | [GitHub版の漫画画面](https://3fes3fes-droid.github.io/J/) |
| [p](https://github.com/3fes3fes-droid/p) | Pythonによる取得・更新処理と生成HTML |
| [player](https://github.com/3fes3fes-droid/player) | Android/ChromeOS用プレイヤー |
| [gazou-viewer](https://github.com/3fes3fes-droid/gazou-viewer) | Android/ChromeOS画像ビューアー |

## 更新時の扱い

- 公開画面と、その画面が読む画像・JSON・CSS・JSを一緒に確認する。
- URLや編集元を変更した際は `site-links.json` も更新する。
- GitHub Pagesの公開成功、主要URLの応答、ブラウザーでの表示・操作を確認する。
- 自動更新による変更を保持するため、復旧時も `main` 全体を過去へ強制巻き戻しせず、必要なファイルの差分を新しいコミットとして適用する。
