# 画像生成モンキー v7.6.0

## 5分周期

`image-generation.user.js` の `CYCLE_MINUTES = 5` は、送信ボタンを押してから次の対象へ進むまでの総時間です。画像の検出時間と残りの待機時間を含みます。

| 状態 | 動作 |
| --- | --- |
| 90秒で完成を確認 | 送信から300秒になるまで残り210秒を待機 |
| 285秒で完成を確認 | 残り15秒を待機 |
| 完成画像があるのに停止ボタンが残る | 画像実体・表示の安定・画像周辺の進行表示で判定し、同じ300秒の予定に従う |
| 300秒まで完成を確認できない | 完成未確認として記録し、次へ進む。さらに1分・8分・30分は足さない |
| 途中で再読み込み | 保存済み送信時刻を使い、5分を最初から数え直さない |

完成未確認の場合は成功件数を増やしません。対象の会話URLと検出状態を診断ログに残し、同じ指示の自動再送を避けます。実際に生成中でも5分の期限でその項目を打ち切る設定です。新規チャットの読み込みや通信処理の分だけ、次の送信は300秒より少し遅れます。

利用制限の表示は既存の制限解除待ちを使い、オフライン中は接続回復を待ちます。Chromeが裏タブを制限したりPCがスリープした場合、JavaScriptを予定どおり実行することはできません。復帰時は元の期限を再評価し、遅れた分の連続送信を行いません。

## 完成検出

- 旧画面の会話・画像URLと、新画面の `data-turn-key` / `data-user-message-bubble` / `generated-image-preview` / `generated-image-gallery` を扱います。
- 新画面の `blob:` 画像と、`picture` / `srcset` が選択した `currentSrc` に対応します。
- 送信前の画像、ユーザー添付、サイドバーの画像、別の会話の画像は除外します。
- 読込完了、画像の実寸（両辺128px以上）、デコード成功、画像ソースが同じことを確認します。
- 画像周辺の進行表示やぼかしが残る途中画像は、完成に数えません。
- 画像が5秒安定したら完成とします。停止ボタンが残り、ダウンロード操作も見つからない場合は15秒の安定を確認します。この確認時間も5分周期に含まれます。
- `MutationObserver`、画像の `load` / `error` イベント、タイマーによる再確認を併用します。

左下にバージョンと「画像確認中」「画像確認済み」「完成未確認」、次へ進むまでの残り時間を表示します。「ログコピー」には送信起点、期限、画像候補数、読込数、進行表示、停止ボタンの有無、前回結果が含まれます。

## バックアップと復元

変更前のスクリプトは [backup/image-generation-v7.5.10-20261001](https://github.com/3fes3fes-droid/mitsuyasu/blob/backup/image-generation-v7.5.10-20261001/tampermonkey/image-generation.user.js) に保存しています。

- 退避元のコミット: `b8d69e0f4c96109e5babbb5c95fe6e1ab7bc94b4`
- 旧スクリプトのblob SHA: `3f34c2a0356594bebb93d4d8090a9ae0f26960e5`
- 復元対象: `tampermonkey/image-generation.user.js` のみ。リポジトリ全体を戻す必要はありません。

GitHub同期で継続して旧動作へ戻す場合は、バックアップ枝のこのファイルを `main` の同じパスへ復元し、`@version` と `SCRIPT_VERSION` を現在版より新しい復元用バージョンへ揃えます。GitHubの他のファイルは変更しません。

進捗の保存キーと形式は旧版と互換です。v7.6.0の初回読み込み時には、それまでの進捗を Tampermonkey の `image_generation_state_before_v7_6_0` に退避します。通常の更新・再読み込みでは退避データを上書きしません。コードを旧版へ戻した際は、その時点の進捗を引き継ぎます。

## 検証

`tests/image-generation.test.cjs` は実際のユーザースクリプトを読み込み、起動末尾だけをテスト用に差し替えて検証します。新旧画面、画像の読込とソース差し替え、停止ボタン残留、途中画像、5分期限、期限前後の再読み込み、タイマー停止からの復帰、会話の誤認、二重送信防止を対象にします。

```bash
npm install --prefix tampermonkey/tests jsdom playwright
node --test tampermonkey/tests/image-generation.test.cjs
npx --prefix tampermonkey/tests playwright install chromium
IG_TEST_BROWSER=1 node --test tampermonkey/tests/image-generation.test.cjs
```

Chromium実行モードは実DOMと実際の画像読込・デコードも検証します。5分の各時点や裏タブからの復帰を再現するケースでは時計を制御します。ChatGPTへの実際の画像生成リクエストや本物のTampermonkey保存領域は使用しません。

## 調査資料

- [MDN: HTMLImageElement.complete](https://developer.mozilla.org/en-US/docs/Web/API/HTMLImageElement/complete) — 空画像や破損画像でもtrueになるため、これだけで完成としない。
- [MDN: HTMLImageElement.decode](https://developer.mozilla.org/en-US/docs/Web/API/HTMLImageElement/decode) — 読込画像のデコードと、ソース変更時の扱い。
- [MDN: load event](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/load_event) — 画像ロードイベントの監視。
- [Chrome: timer throttling](https://developer.chrome.com/blog/timer-throttling-in-chrome-88/) — 非表示タブのタイマー制限。
- [image-useの公開実装](https://github.com/leeguooooo/image-use/blob/main/image-use) — 2026年9月の画面変更に対応した会話・画像枠のセレクター。第三者の観測に基づく互換対応であり、ChatGPTが保証するDOM仕様ではない。
