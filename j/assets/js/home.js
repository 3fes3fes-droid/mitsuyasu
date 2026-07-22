(function () {
  'use strict';
  const { catalog, esc, globalSearch, debounce } = JJK;
  const meta = catalog.meta || {};
  const counts = meta.counts || {};
  const quality = meta.quality || {};

  document.querySelector('#stats').innerHTML = [
    ['各話', counts.chapters], ['人物・存在', counts.characters], ['技・術式', counts.techniques],
    ['用語', counts.terms], ['補遺', counts.supplements]
  ].map(([label, value]) => `<div class="stat"><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`).join('');

  document.querySelector('#quality-status').innerHTML = `
    <div class="quality-card good"><strong>${esc(quality.chapterSummariesEntered || 0)} / ${esc(counts.chapters || 0)}</strong><span>各話あらすじ入力</span></div>
    <div class="quality-card warning"><strong>${esc(quality.chapterPrimaryPageDirectChecked || 0)} / ${esc(counts.chapters || 0)}</strong><span>単行本ページ直接監査</span></div>
    <div class="quality-card warning"><strong>${esc(quality.characterFirstPassPending || 0)}</strong><span>人物の個別精査待ち</span></div>
    <div class="quality-card warning"><strong>${esc(quality.techniqueFirstPassPending || 0)}</strong><span>技・術式の個別精査待ち</span></div>
    <div class="quality-card warning"><strong>${esc(quality.termFirstPassPending || 0)}</strong><span>用語の個別精査待ち</span></div>`;

  document.querySelector('#arcs').innerHTML = (catalog.arcs || []).map((arc) => `
    <a class="arc-card" href="chapters.html?arc=${encodeURIComponent(arc.id)}">
      <h3>${esc(arc.name)}</h3><p>${esc(arc.overview || '')}</p>
    </a>`).join('');

  const input = document.querySelector('#global-search');
  const results = document.querySelector('#global-results');
  const renderResults = debounce(() => {
    const found = globalSearch(input.value);
    results.innerHTML = found.map((item) => `<a class="result" href="${item.href}"><small>${esc(item.type)}</small>${esc(item.label)}</a>`).join('');
  }, 80);
  input.addEventListener('input', renderResults);
}());
