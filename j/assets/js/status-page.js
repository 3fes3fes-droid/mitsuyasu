(function () {
  'use strict';
  const { catalog, esc } = JJK;
  const meta = catalog.meta || {};
  const counts = meta.counts || {};
  const quality = meta.quality || {};
  document.querySelector('#status-body').innerHTML = `
    <section class="panel"><h1>現在の完成状態</h1>
      <div class="status-callout"><strong>動作する第一稿サイト</strong><span>全話データは閲覧可能。原作ページ直接監査と、人物・技・用語の個別精査は未完了。</span></div>
    </section>
    <section class="panel"><h2 class="section-title">収録</h2><dl class="kv">
      <dt>各話</dt><dd>${esc(counts.chapters)}件（0巻4話＋本編271話）</dd>
      <dt>人物・存在</dt><dd>${esc(counts.characters)}件</dd>
      <dt>技・術式</dt><dd>${esc(counts.techniques)}件</dd>
      <dt>用語</dt><dd>${esc(counts.terms)}件</dd>
      <dt>補遺</dt><dd>${esc(counts.supplements)}件</dd>
    </dl></section>
    <section class="panel"><h2 class="section-title">精査進捗</h2><dl class="kv">
      <dt>各話あらすじ</dt><dd>${esc(quality.chapterSummariesEntered)} / ${esc(counts.chapters)} 入力済み</dd>
      <dt>単行本ページ直接監査</dt><dd>${esc(quality.chapterPrimaryPageDirectChecked)} / ${esc(counts.chapters)}</dd>
      <dt>人物・個別精査待ち</dt><dd>${esc(quality.characterFirstPassPending)}件</dd>
      <dt>技・術式・個別精査待ち</dt><dd>${esc(quality.techniqueFirstPassPending)}件</dd>
      <dt>用語・個別精査待ち</dt><dd>${esc(quality.termFirstPassPending)}件</dd>
      <dt>用語の直接出典リンク</dt><dd>${esc(quality.termsWithDirectSourceRefs)} / ${esc(counts.terms)}</dd>
    </dl></section>`;
}());
