# 光康サイト｜GitHub公開リンク台帳・運用ルール

更新日：2026-10-17（日本時間）

## 最初に開く場所

- **光康サイト本体（入口／メニューボタン）**：https://mitsuyasu-memory.mitsuyasuuu.chatgpt.site/
- **GitHub Pages公開画面**：https://3fes3fes-droid.github.io/mitsuyasu/
- **公開コレクション一覧**：https://3fes3fes-droid.github.io/mitsuyasu/collections/
- **GitHubリポジトリ（この場所）**：https://github.com/3fes3fes-droid/mitsuyasu
- **機械可読の公開リンク台帳（唯一の正本）**：[site-links.json](site-links.json)

**「github.com/.../blob/」はソースを確認するURL、「github.io/」は利用者が開く完成ページのURL。混同しないこと。**

### リンクの接続構造

`光康サイト（ChatGPT Sites）のメニューボタン → 公開URL → GitHub PagesのHTML/JS/CSS → 必要な画像・データ（GitHubまたはR2等）`

ここで確認したものは「GitHubリポジトリ内のファイル」と「GitHub Pages上でのHTTP正常応答」。
**Sites側の各ボタンが実際にどのURLへ移動するかは、Sites編集元コードへのアクセスがないため未照合。** 以下の名称対応は照合対象であり、現時点では確定リンクだと扱わない。
Sites内の `/manga` と `/grajapa` はSites側のルートとしてブラウザ上で確認。GitHub上の同名・類似ソースと同一の公開画面とは断定しない。

## 2026-10-17 復旧履歴

- **07:40 JST**：`collections/` と `football/` が別々のコミットで削除された。
- **14:25 JST**：両フォルダだけ、削除前のGitツリーから復元。その他の当日更新は保持。
- [復元コミット](https://github.com/3fes3fes-droid/mitsuyasu/commit/e1b773b00020ca50b06a49dc1068018b95ef09f9)
- [復元後のGitHub Pages公開成功ログ](https://github.com/3fes3fes-droid/mitsuyasu/actions/runs/39006223638)
- 復元後に公開コレクション22カテゴリ、コレクション一覧、サッカーページ・元HTML、`m.html`、別リポジトリ`J/`をHEADで確認し、すべて **200**。地図のJS、食べ物のCSS、サッカーの`app.b64`も **200**。
- **既知のリンク切れ**：`collections/index.html` の「YouTube 54チャンネル」は `https://3fes3fes-droid.github.io/mitsuyasu/youtube/` を参照し、**404**。今回の2フォルダ削除の復元では直らない。現在の正しい移行先URLが確認できるまで変更しない。

## どのリポジトリに何があるか

| リポジトリ | 用途 | 公開画面との関係 |
| --- | --- | --- |
| [mitsuyasu](https://github.com/3fes3fes-droid/mitsuyasu) | コレクション、サッカー、各HTML・JSON、GitHub Actions | メインのGitHub Pages公開元 |
| [J](https://github.com/3fes3fes-droid/J) | 呪術廻戦データベース移行ソース | `/J/` は200。本体Sitesの `/manga` との接続は未照合 |
| [p](https://github.com/3fes3fes-droid/p) | Pythonによる取得・更新処理と生成HTML | 補助・自動化コード |
| [player](https://github.com/3fes3fes-droid/player) | Android/ChromeOS用プレイヤー | Webサイトの公開先ではない |
| [gazou-viewer](https://github.com/3fes3fes-droid/gazou-viewer) | Android/ChromeOS画像ビューアー | Webサイトの公開先ではない |

## 復元した公開コレクション22カテゴリ

下記はすべて2026-10-17に **HTTP 200** を確認。公開URLとソース位置を明示。

| 名称 | GitHub Pages公開URL | GitHub内のHTML実体 | HTTP |
| --- | --- | --- | --- |
| FANZA女優一覧 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/actress-directory/) | `collections/integrated/actress-directory/index.html` | 200 |
| 有吉 Twitter・X年表 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/ariyoshi-x/) | `collections/integrated/ariyoshi-x/index.html` | 200 |
| バカラ | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/baccarat/) | `collections/integrated/baccarat/index.html` | 200 |
| 有名人の自作PC図鑑 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/custom-pc/) | `collections/integrated/custom-pc/index.html` | 200 |
| Fold6とPixel 10aの比較 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/device-compare/) | `collections/integrated/device-compare/index.html` | 200 |
| 格闘ゲーマー名鑑 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/fighting-game/) | `collections/integrated/fighting-game/index.html` | 200 |
| アイドル挨拶一覧 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/greetings/) | `collections/integrated/greetings/index.html` | 200 |
| 一発ネタ | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/hit-gags/) | `collections/integrated/hit-gags/index.html` | 200 |
| アイドル一覧 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/idol/) | `collections/integrated/idol/index.html` | 200 |
| iLiFE! Color Archive | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/ilife/) | `collections/integrated/ilife/index.html` | 200 |
| 食わず嫌い王 年表 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/kuwazugirai/) | `collections/integrated/kuwazugirai/index.html` | 200 |
| 静岡市・一人暮らし生活費 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/living-cost/) | `collections/integrated/living-cost/index.html` | 200 |
| 日本・世界地図 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/maps/) | `collections/integrated/maps/index.html` | 200 |
| MCU アベンジャーズ雑学 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/mcu/) | `collections/integrated/mcu/index.html` | 200 |
| 食べ物一覧・お菓子・菓子パン | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/meals/) | `collections/integrated/meals/index.html` | 200 |
| 映画カタログ（映画棚との対応は未確認） | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/movie-catalogue/) | `collections/integrated/movie-catalogue/index.html` | 200 |
| 恵比寿マスカッツ | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/muscats/) | `collections/integrated/muscats/index.html` | 200 |
| パズドラ称号一覧 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/pazudora-titles/) | `collections/integrated/pazudora-titles/index.html` | 200 |
| SAW 全ゲーム記録 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/saw-game/) | `collections/integrated/saw-game/index.html` | 200 |
| シグマリオンの歴史 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/sigmarion/) | `collections/integrated/sigmarion/index.html` | 200 |
| 水ダウ・すべらない話・SAVE MONEY | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/suiyobi/) | `collections/integrated/suiyobi/index.html` | 200 |
| 雑学 | [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/collections/integrated/trivia/) | `collections/integrated/trivia/index.html` | 200 |

サッカーは [公開画面](https://3fes3fes-droid.github.io/mitsuyasu/football/)／`football/index.html`。ページが参照する `football/app.b64`、`football/styles.css`、`football/players/`、ルートの `Football_archive_single.html` は一組の依存関係。どれか一つだけを削除すると表示が壊れ得る。

## 今後の変更・削除のルール

1. **画面と保存先を分離する。** ChatGPT Sitesは入口・メニュー、GitHubはHTML/JS/CSS・ソース、R2は大容量画像等、Drive等は元データや控え。公開URLがどのサービスを向いているかを `site-links.json` に残す。
2. **リンクが残っているページや、そのページの読み込み素材は削除禁止。** 先にSites側のリンクを確認し、移行先を公開・実表示で確認してから、旧リンクのリダイレクトや案内ページを残す。
3. **URLを固定する。** ファイルを移動するときは、元の公開URLから新しい場所へ転送する薄いHTMLを残す。トップサイトのリンクを壊さない。
4. **変更時は台帳を更新する。** 名称、公開URL、GitHub内の実体、画像・JSONの依存先、Sites側リンクの照合有無、確認日を記録。
5. **表示確認は3段階。** GitHub Pagesのデプロイ成功 → 公開URLと主要素材のHTTP 200 → 実際の画面で表示・操作・Sitesメニューからの遷移を確認。
6. **復旧は差分で行う。** このリポジトリは定期的に自動コミットされるため、過去のコミットへ`main`全体を強制巻き戻ししない。消えたフォルダやファイルだけを新しい復旧コミットで戻す。
7. **大容量画像の移行は公開URLと控えをセットで管理する。** R2に移動した後も、参照先を切り替えたこと・実表示したこと・復元先があることを確認するまで旧データを消さない。

## 公開URLを手動で一括確認する方法

GitHubの [Actions](https://github.com/3fes3fes-droid/mitsuyasu/actions) → **Public link audit (manual)** → **Run workflow**。
これは`workflow_dispatch`専用で、自動実行・定時監視はしない。`site-links.json`の `state: active` をHTTPで確認し、正常でなければワークフローを失敗とする。`known_broken`は既知の問題として明記する。

この台帳の対象は **GitHub Pagesの公開ファイル**。サイト上のボタンを押したときの遷移先、R2のオブジェクトの実在、ログインが必要なSites画面の稼働確認は別工程として扱う。
