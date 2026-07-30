(function () {
  'use strict';
  const { catalog, esc } = JJK;
  const meta = catalog.meta || {};
  const counts = meta.counts || {};
  const quality = meta.quality || {};
  const number = (value) => Number(value || 0).toLocaleString('ja-JP');

  const rows = (items) => items.map(([label, value]) =>
    `<div class="status-row"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`
  ).join('');

  document.querySelector('#status-body').innerHTML = `
    <section class="dashboard-card wide">
      <h1>現在の完成状態</h1>
      <div class="status-callout"><strong>動作する第一稿サイト</strong><span>全話を閲覧可能。原作ページ直接監査と、人物・技・用語の個別精査は未完了。</span></div>
    </section>
    <section class="dashboard-card">
      <h2 class="section-title">収録</h2>
      <div class="status-grid">${rows([
        ['各話', `${counts.chapters}件（0巻4話＋本編271話）`],
        ['人物・存在', `${counts.characters}件`],
        ['技・術式', `${counts.techniques}件`],
        ['用語', `${counts.terms}件`],
        ['コミックス', `${counts.volumes}冊（0巻～30巻）`],
        ['補遺', `${counts.supplements}件`]
      ])}</div>
    </section>
    <section class="dashboard-card">
      <h2 class="section-title">精査進捗</h2>
      <div class="status-grid">${rows([
        ['各話あらすじ', `${quality.chapterSummariesEntered} / ${counts.chapters}`],
        ['単行本ページ直接監査', `${quality.chapterPrimaryPageDirectChecked} / ${counts.chapters}`],
        ['人物・個別精査待ち', `${quality.characterFirstPassPending}件`],
        ['技・術式・個別精査待ち', `${quality.techniqueFirstPassPending}件`],
        ['用語・個別精査待ち', `${quality.termFirstPassPending}件`],
        ['用語の直接出典', `${quality.termsWithDirectSourceRefs} / ${counts.terms}`]
      ])}</div>
    </section>
    <section class="dashboard-card wide">
      <h2 class="section-title">話別ハイライト</h2>
      <div class="status-grid">${rows([
        ['詳細出来事', `${number(quality.detailedChapterEvents)}件`],
        ['セリフ・判断・言動の要旨', `${number(quality.dialogueSummaries)}件`],
        ['複数記事で照合できた短い語句・発言', `${number(quality.crosscheckedLines)}件`],
        ['公開名言集で話数照合した要旨', `${number(quality.popularLineGists)}件`],
        ['検索・表示キーワード', `${number(quality.highlightKeywords)}件`],
        ['言動要旨を持つ話', `${quality.chaptersWithDialogueSummary} / ${counts.chapters}`],
        ['照合済み短文を持つ話', `${quality.chaptersWithCrosscheckedLines} / ${counts.chapters}`]
      ])}</div>
    </section>
    <section class="dashboard-card wide">
      <h2 class="section-title">公式情報との対応</h2>
      <div class="status-grid">${rows([
        ['公式コミックス表紙', `${quality.officialVolumeImages} / ${counts.volumes}`],
        ['公式巻紹介ベースのあらすじ', `${quality.officialVolumeSynopses} / ${counts.volumes}`],
        ['人物の公式画像対応', `${quality.officialCharacterImages} / ${counts.characters}`],
        ['各話公式サムネイル', `${quality.officialChapterThumbnails} / ${counts.chapters}`]
      ])}</div>
    </section>`;
}());
