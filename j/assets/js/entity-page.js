(function () {
  'use strict';
  const {
    catalog, esc, queryParam, setId, loadDetail, chapterLinks, supplementLinks,
    sourceLinks, verificationBadge, mediaThumb, mediaStatusInfo, statusLabel,
    referenceLink, entityHref, debounce, shuffleCopy, setupTabs, bindListNavigation
  } = JJK;

  const config = window.JJK_PAGE_CONFIG;
  const rows = catalog[config.dataKey] || [];
  const displayRows = shuffleCopy(rows);
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
  category.innerHTML = '<option value="">全分類</option>' + categories
    .map((item) => `<option value="${esc(item)}">${esc(item)}</option>`).join('');

  const fragment = document.createDocumentFragment();
  for (const row of displayRows) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.id = row.id;
    button.dataset.category = row.category || '';
    button.dataset.search = [
      row.name, ...(row.aliases || []), row.reading || '', row.category || '',
      row.affiliation || '', ...(row.users || [])
    ].join(' ').toLowerCase();
    button.innerHTML = `<b>${esc(row.name)}</b><span class="sub">${esc(row.category || '未分類')}</span>`;
    fragment.appendChild(button);
    buttonMap.set(row.id, button);
  }
  list.appendChild(fragment);

  function setActive(id) {
    if (activeId && buttonMap.has(activeId)) {
      buttonMap.get(activeId).classList.remove('active');
      buttonMap.get(activeId).removeAttribute('aria-current');
    }
    activeId = id;
    if (buttonMap.has(id)) {
      const button = buttonMap.get(id);
      button.classList.add('active');
      button.setAttribute('aria-current', 'true');
      button.scrollIntoView({ block: 'nearest' });
    }
  }

  function applyFilter() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    for (const row of displayRows) {
      const button = buttonMap.get(row.id);
      const show = (!category.value || row.category === category.value) &&
        (!query || button.dataset.search.includes(query));
      button.hidden = !show;
      if (show) visible += 1;
    }
    count.textContent = `${visible} / ${rows.length}件`;
  }

  function usersHtml(item) {
    return (item.userRefs || []).map((user) =>
      user.characterId
        ? `<a class="entity-link" href="${entityHref('characters', user.characterId)}">${esc(user.name)}</a>`
        : `<span class="badge">${esc(user.name)}</span>`
    ).join('') || '<span class="muted">不明</span>';
  }

  function headerData(item) {
    if (config.dataKey === 'characters') {
      return {
        kicker: item.category || '人物・存在',
        meta: [item.affiliation || '所属不明'],
        summary: item.profile,
        media: item.media,
        mediaClass: 'character',
        mediaTitle: `${item.name} 公式人気投票画像`
      };
    }
    if (config.dataKey === 'techniques') {
      return {
        kicker: item.category || '技・術式',
        meta: [item.reading || '', ...(item.users || [])].filter(Boolean),
        summary: item.description
      };
    }
    return {
      kicker: item.category || '用語',
      meta: [],
      summary: item.definition
    };
  }

  function overviewHtml(item) {
    if (config.dataKey === 'characters') {
      const status = item.status || {};
      const aliases = (item.aliases || []).map((alias) => `<span class="badge">${esc(alias)}</span>`).join('') || '<span class="muted">なし</span>';
      return `
        <div class="record-section">
          <h2 class="section-title">基本情報</h2>
          <dl class="compact-kv">
            <dt>別名</dt><dd>${aliases}</dd>
            <dt>分類</dt><dd>${esc(item.category || '未分類')}</dd>
            <dt>所属</dt><dd>${esc(item.affiliation || '所属不明')}</dd>
            <dt>初出</dt><dd>${referenceLink(item.firstChapter)}</dd>
            <dt>最終登場</dt><dd>${referenceLink(item.lastChapter)}</dd>
          </dl>
        </div>
        <div class="record-section">
          <h2 class="section-title">最終状態</h2>
          <dl class="compact-kv">
            <dt>状態</dt><dd>${esc(statusLabel(status.status))}</dd>
            <dt>時点</dt><dd>${referenceLink(status.as_of_chapter)}</dd>
            <dt>注記</dt><dd>${esc(status.note || '')}</dd>
          </dl>
        </div>`;
    }
    if (config.dataKey === 'techniques') {
      return `
        <div class="record-section">
          <h2 class="section-title">使用者</h2>
          <div class="links">${usersHtml(item)}</div>
        </div>
        <div class="record-section">
          <h2 class="section-title">登録情報</h2>
          <dl class="compact-kv">
            <dt>読み</dt><dd>${esc(item.reading || '未登録')}</dd>
            <dt>名称状態</dt><dd>${esc(item.officialNameStatus || '未設定')}</dd>
            <dt>初出</dt><dd>${referenceLink(item.firstChapter)}</dd>
            <dt>最終登場</dt><dd>${referenceLink(item.lastChapter)}</dd>
          </dl>
        </div>`;
    }
    return `
      <div class="record-section">
        <h2 class="section-title">登録情報</h2>
        <dl class="compact-kv">
          <dt>分類</dt><dd>${esc(item.category || '未分類')}</dd>
          <dt>名称状態</dt><dd>${esc(item.officialNameStatus || '未設定')}</dd>
          <dt>初出</dt><dd>${referenceLink(item.firstChapter)}</dd>
          <dt>最終登場</dt><dd>${referenceLink(item.lastChapter)}</dd>
        </dl>
      </div>`;
  }

  function mediaSourceHtml(item) {
    if (config.dataKey !== 'characters') return '';
    const media = item.media || {};
    const status = mediaStatusInfo(media.verification);
    const links = [
      media.imageUrl ? `<a class="entity-link" href="${esc(media.imageUrl)}" target="_blank" rel="noopener noreferrer">画像URL</a>` : '',
      media.pageUrl ? `<a class="entity-link" href="${esc(media.pageUrl)}" target="_blank" rel="noopener noreferrer">掲載元ページ</a>` : ''
    ].filter(Boolean).join('');
    return `
      <div class="record-section">
        <h2 class="section-title">公式画像</h2>
        <dl class="compact-kv">
          <dt>画像状態</dt><dd><span class="${esc(status.className)}">${esc(status.label)}</span></dd>
          <dt>公式リンク</dt><dd><div class="links">${links || '<span class="muted">未対応</span>'}</div></dd>
        </dl>
      </div>`;
  }

  async function renderDetail(id) {
    const compact = rows.find((row) => row.id === id) || displayRows[0];
    if (!compact) return;
    const token = ++renderToken;
    setActive(compact.id);
    detail.innerHTML = '<div class="loading-panel">詳細データを読み込んでいます…</div>';
    aside.innerHTML = '';

    try {
      const item = await loadDetail(config.dataKey, compact.id);
      if (token !== renderToken) return;
      const header = headerData(item);
      const hasMedia = Boolean(header.media && header.media.imageUrl);
      const meta = header.meta.map((value) => `<span class="meta-chip">${esc(value)}</span>`).join('');

      detail.innerHTML = `
        <article class="record-view">
          <header class="record-header${hasMedia ? '' : ' no-media'}">
            <div class="record-copy">
              <div class="record-kicker">${esc(header.kicker)}</div>
              <h1 class="record-title">${esc(item.name)}</h1>
              ${meta ? `<div class="record-meta">${meta}</div>` : ''}
              <p class="record-summary">${esc(header.summary || '')}</p>
            </div>
            ${hasMedia ? `<div class="record-media">${mediaThumb(header.media, {
              title: header.mediaTitle,
              alt: header.mediaTitle,
              className: header.mediaClass || ''
            })}</div>` : ''}
          </header>
          <div class="record-tabs" role="tablist" aria-label="${esc(item.name)}の情報">
            <button class="record-tab" type="button" role="tab" data-tab="overview">概要</button>
            <button class="record-tab" type="button" role="tab" data-tab="relations">関連</button>
            <button class="record-tab" type="button" role="tab" data-tab="sources">出典・確認</button>
          </div>
          <div class="record-scroll">
            <section class="tab-panel record-grid" role="tabpanel" data-tab-panel="overview">
              ${overviewHtml(item)}
            </section>
            <section class="tab-panel record-grid" role="tabpanel" data-tab-panel="relations">
              <div class="record-section wide">
                <div class="section-heading"><h2 class="section-title">関連話</h2><span class="count-label">${(item.chapterIds || []).length}話</span></div>
                <div class="links chapter-links">${chapterLinks(item.chapterIds, 999)}</div>
              </div>
              ${config.dataKey === 'characters' ? `
                <div class="record-section wide">
                  <h2 class="section-title">関連補遺</h2>
                  <div class="links">${supplementLinks(item.supplementIds)}</div>
                </div>` : ''}
            </section>
            <section class="tab-panel record-grid" role="tabpanel" data-tab-panel="sources">
              <div class="record-section">
                <h2 class="section-title">確認状態</h2>
                ${verificationBadge(item.verification)}
                <p class="muted">対象範囲：${esc(item.sourceScope || '')}</p>
              </div>
              <div class="record-section">
                <h2 class="section-title">出典</h2>
                <div class="links">${sourceLinks(item.sourceRefs)}</div>
              </div>
              ${mediaSourceHtml(item)}
            </section>
          </div>
        </article>`;
      setupTabs(detail, 'overview');
    } catch (error) {
      if (token !== renderToken) return;
      detail.innerHTML = `<div class="loading-panel"><div><h1>読み込みエラー</h1><p class="danger">${esc(error.message)}</p></div></div>`;
    }
  }

  list.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-id]');
    if (button) setId(button.dataset.id);
  });
  bindListNavigation(list, setId);
  search.addEventListener('input', debounce(applyFilter));
  category.addEventListener('change', applyFilter);
  window.addEventListener('jjk:navigate', (event) => renderDetail(event.detail?.id || queryParam('id')));
  window.addEventListener('popstate', () => renderDetail(queryParam('id')));

  applyFilter();
  const initialId = queryParam('id') || displayRows[0]?.id;
  if (initialId && !queryParam('id')) setId(initialId, { replace: true });
  else if (initialId) renderDetail(initialId);
}());
