(function () {
  'use strict';
  const {
    catalog, esc, queryParam, setId, loadDetail, entityLinks, sourceLinks,
    verificationBadge, chapterHref, debounce
  } = JJK;

  const rows = catalog.chapters || [];
  const arcMap = new Map((catalog.arcs || []).map((item) => [item.id, item]));
  const list = document.querySelector('#item-list');
  const search = document.querySelector('#search');
  const arc = document.querySelector('#arc-filter');
  const count = document.querySelector('#result-count');
  const detail = document.querySelector('#detail');
  const aside = document.querySelector('#aside');
  const buttonMap = new Map();
  let activeId = null;
  let renderToken = 0;

  arc.innerHTML = '<option value="">全区分</option>' + (catalog.arcs || [])
    .map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('');
  const initialArc = new URLSearchParams(location.search).get('arc');
  if (initialArc) arc.value = initialArc;

  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.id = row.id;
    button.dataset.arc = row.arcId || '';
    button.dataset.search = `${row.label} ${row.title} ${row.summaryShort}`.toLowerCase();
    button.innerHTML = `<b>${esc(row.label)} ${esc(row.title)}</b><span class="sub">${esc(arcMap.get(row.arcId)?.name || '未分類')}／${row.volume === 0 ? '0巻' : `${row.volume}巻`}</span>`;
    fragment.appendChild(button);
    buttonMap.set(row.id, button);
  }
  list.appendChild(fragment);

  function setActive(id) {
    if (activeId && buttonMap.has(activeId)) buttonMap.get(activeId).classList.remove('active');
    activeId = id;
    if (buttonMap.has(id)) buttonMap.get(id).classList.add('active');
  }

  function applyFilter() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    for (const row of rows) {
      const button = buttonMap.get(row.id);
      const show = (!arc.value || row.arcId === arc.value) && (!query || button.dataset.search.includes(query));
      button.hidden = !show;
      if (show) visible += 1;
    }
    count.textContent = `${visible} / ${rows.length}話`;
  }

  async function renderDetail(id) {
    const compact = rows.find((row) => row.id === id) || rows[0];
    if (!compact) return;
    const token = ++renderToken;
    setActive(compact.id);
    detail.innerHTML = '<div class="panel loading-panel">詳細データを読み込んでいます…</div>';
    aside.innerHTML = '';

    try {
      const item = await loadDetail('chapters', compact.id);
      if (token !== renderToken) return;
      const index = rows.findIndex((row) => row.id === item.id);
      const previous = index > 0 ? rows[index - 1] : null;
      const next = index < rows.length - 1 ? rows[index + 1] : null;

      detail.innerHTML = `
        <div class="panel">
          <h1 class="detail-title">${esc(item.label)}　${esc(item.title)}</h1>
          <div class="detail-meta">${item.volume === 0 ? '0巻' : `${item.volume}巻`}／開始 ${esc(item.startPage)}ページ／${esc(arcMap.get(item.arcId)?.name || '未分類')}</div>
          <p class="summary-short">${esc(item.summaryShort)}</p>
        </div>
        <div class="panel"><h2 class="section-title">詳細あらすじ</h2><div class="prose">${esc(item.summaryFull)}</div></div>
        <div class="panel"><h2 class="section-title">重要な出来事</h2><ul class="events">${(item.events || []).map((event) => `<li>${esc(typeof event === 'string' ? event : event.text || JSON.stringify(event))}</li>`).join('') || '<li class="muted">未登録</li>'}</ul></div>
        <div class="panel"><h2 class="section-title">確認状態</h2>${verificationBadge(item.verification)}<div class="prose muted">${esc(item.verificationNotes || '')}</div></div>
        <div class="chapter-nav">
          ${previous ? `<button type="button" data-nav-id="${esc(previous.id)}">← ${esc(previous.label)}</button>` : '<span></span>'}
          ${next ? `<button type="button" data-nav-id="${esc(next.id)}">${esc(next.label)} →</button>` : '<span></span>'}
        </div>`;

      aside.innerHTML = `
        <div class="panel"><h2 class="section-title">登場人物</h2><div class="links">${entityLinks('characters', item.characterIds)}</div></div>
        <div class="panel"><h2 class="section-title">技・術式</h2><div class="links">${entityLinks('techniques', item.techniqueIds)}</div></div>
        <div class="panel"><h2 class="section-title">用語</h2><div class="links">${entityLinks('terms', item.termIds)}</div></div>
        <div class="panel"><h2 class="section-title">出典</h2><div class="links">${sourceLinks(item.sourceRefs)}</div><p class="muted">${esc(item.sourceLocator || '')}</p></div>`;

      detail.querySelectorAll('[data-nav-id]').forEach((button) => {
        button.addEventListener('click', () => setId(button.dataset.navId));
      });
    } catch (error) {
      if (token !== renderToken) return;
      detail.innerHTML = `<div class="panel"><h1>読み込みエラー</h1><p class="danger">${esc(error.message)}</p></div>`;
    }
  }

  list.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-id]');
    if (button) setId(button.dataset.id);
  });
  search.addEventListener('input', debounce(applyFilter));
  arc.addEventListener('change', applyFilter);
  window.addEventListener('jjk:navigate', (event) => renderDetail(event.detail?.id || queryParam('id')));
  window.addEventListener('popstate', () => renderDetail(queryParam('id')));

  applyFilter();
  const initialId = queryParam('id') || rows.find((row) => !buttonMap.get(row.id).hidden)?.id || rows[0]?.id;
  if (initialId && !queryParam('id')) setId(initialId, { replace: true });
  else if (initialId) renderDetail(initialId);
}());
