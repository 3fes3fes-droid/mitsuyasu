(function () {
  'use strict';
  const {
    catalog, esc, queryParam, setId, loadDetail, chapterLinks, supplementLinks,
    sourceLinks, verificationBadge, statusLabel, referenceLink, entityHref, debounce
  } = JJK;
  const config = window.JJK_PAGE_CONFIG;
  const rows = catalog[config.dataKey] || [];
  const list = document.querySelector('#item-list');
  const search = document.querySelector('#search');
  const category = document.querySelector('#category-filter');
  const count = document.querySelector('#result-count');
  const detail = document.querySelector('#detail');
  const aside = document.querySelector('#aside');
  const buttonMap = new Map();
  let activeId = null;
  let renderToken = 0;

  const categories = [...new Set(rows.map((item) => item.category).filter(Boolean))].sort();
  category.innerHTML = '<option value="">全分類</option>' + categories.map((item) => `<option value="${esc(item)}">${esc(item)}</option>`).join('');

  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.id = row.id;
    button.dataset.category = row.category || '';
    button.dataset.search = [row.name, ...(row.aliases || []), row.reading || '', row.category || '', row.affiliation || '', ...(row.users || [])].join(' ').toLowerCase();
    button.innerHTML = `<b>${esc(row.name)}</b><span class="sub">${esc(row.category || '未分類')}${row.affiliation ? `／${esc(row.affiliation)}` : ''}</span>`;
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
      const show = (!category.value || row.category === category.value) && (!query || button.dataset.search.includes(query));
      button.hidden = !show;
      if (show) visible += 1;
    }
    count.textContent = `${visible} / ${rows.length}件`;
  }

  function detailHtml(item) {
    if (config.dataKey === 'characters') {
      const status = item.status || {};
      return `
        <div class="panel"><h1 class="detail-title">${esc(item.name)}</h1><div class="detail-meta">${esc(item.category || '未分類')}／${esc(item.affiliation || '所属不明')}</div><p class="summary-short">${esc(item.profile)}</p></div>
        <div class="panel"><h2 class="section-title">別名</h2><div>${(item.aliases || []).map((alias) => `<span class="badge">${esc(alias)}</span>`).join('') || '<span class="muted">なし</span>'}</div></div>
        <div class="panel"><h2 class="section-title">最終状態</h2><dl class="kv"><dt>状態</dt><dd>${esc(statusLabel(status.status))}</dd><dt>時点</dt><dd>${referenceLink(status.as_of_chapter)}</dd><dt>注記</dt><dd>${esc(status.note || '')}</dd></dl></div>`;
    }
    if (config.dataKey === 'techniques') {
      return `
        <div class="panel"><h1 class="detail-title">${esc(item.name)}</h1><div class="detail-meta">${esc(item.reading || '')}／${esc(item.category || '未分類')}</div><p class="summary-short">${esc(item.description)}</p></div>
        <div class="panel"><h2 class="section-title">使用者</h2><div class="links">${(item.userRefs || []).map((user) => user.characterId ? `<a class="entity-link" href="${entityHref('characters', user.characterId)}">${esc(user.name)}</a>` : `<span class="badge">${esc(user.name)}</span>`).join('') || '<span class="muted">不明</span>'}</div></div>
        <div class="panel"><h2 class="section-title">名称状態</h2><p>${esc(item.officialNameStatus || '未設定')}</p></div>`;
    }
    return `
      <div class="panel"><h1 class="detail-title">${esc(item.name)}</h1><div class="detail-meta">${esc(item.category || '未分類')}</div><div class="prose">${esc(item.definition)}</div></div>
      <div class="panel"><h2 class="section-title">名称状態</h2><p>${esc(item.officialNameStatus || '未設定')}</p></div>`;
  }

  async function renderDetail(id) {
    const compact = rows.find((row) => row.id === id) || rows[0];
    if (!compact) return;
    const token = ++renderToken;
    setActive(compact.id);
    detail.innerHTML = '<div class="panel loading-panel">詳細データを読み込んでいます…</div>';
    aside.innerHTML = '';
    try {
      const item = await loadDetail(config.dataKey, compact.id);
      if (token !== renderToken) return;
      detail.innerHTML = detailHtml(item) + `
        <div class="panel"><h2 class="section-title">確認状態</h2>${verificationBadge(item.verification)}<p class="muted">対象範囲：${esc(item.sourceScope || '')}</p></div>`;
      aside.innerHTML = `
        <div class="panel"><h2 class="section-title">関連話</h2><div class="links">${chapterLinks(item.chapterIds, 60)}</div></div>
        ${config.dataKey === 'characters' ? `<div class="panel"><h2 class="section-title">関連補遺</h2><div class="links">${supplementLinks(item.supplementIds)}</div></div>` : ''}
        <div class="panel"><h2 class="section-title">出典</h2><div class="links">${sourceLinks(item.sourceRefs)}</div></div>`;
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
  category.addEventListener('change', applyFilter);
  window.addEventListener('jjk:navigate', (event) => renderDetail(event.detail?.id || queryParam('id')));
  window.addEventListener('popstate', () => renderDetail(queryParam('id')));

  applyFilter();
  const initialId = queryParam('id') || rows[0]?.id;
  if (initialId && !queryParam('id')) setId(initialId, { replace: true });
  else if (initialId) renderDetail(initialId);
}());
