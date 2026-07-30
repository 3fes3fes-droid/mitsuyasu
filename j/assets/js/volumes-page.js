(function () {
  'use strict';
  const {
    catalog, esc, queryParam, setId, mediaThumb, mediaStatusInfo, sourceLinks,
    chapterHref, supplementHref, verificationBadge, setupTabs, bindListNavigation
  } = JJK;

  const rows = catalog.volumes || [];
  const list = document.querySelector('#item-list');
  const search = document.querySelector('#search');
  const count = document.querySelector('#result-count');
  const detail = document.querySelector('#detail');
  const aside = document.querySelector('#aside');
  const buttonMap = new Map();
  let activeId = null;

  function rangeLabel(row) {
    const chapters = row.chapters || [];
    if (!chapters.length) return '収録話未登録';
    if (chapters.length === 1) return chapters[0].label;
    return `${chapters[0].label}～${chapters[chapters.length - 1].label}`;
  }

  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.id = row.id;
    button.dataset.search = [
      row.label, row.title, row.synopsis,
      ...(row.chapters || []).flatMap((chapter) => [chapter.label, chapter.title])
    ].join(' ').toLowerCase();
    button.innerHTML = `<b>${esc(row.label)}</b><span class="sub">${esc(rangeLabel(row))}</span>`;
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
    for (const row of rows) {
      const button = buttonMap.get(row.id);
      const show = !query || button.dataset.search.includes(query);
      button.hidden = !show;
      if (show) visible += 1;
    }
    count.textContent = `${visible} / ${rows.length}冊`;
  }

  function renderDetail(id) {
    const row = rows.find((item) => item.id === id) || rows[0];
    if (!row) return;
    setActive(row.id);
    aside.innerHTML = '';
    const chapters = row.chapters || [];
    const supplements = row.supplements || [];
    const media = {
      imageUrl: row.imageUrl,
      pageUrl: row.pageUrl,
      sourceRef: row.sourceRef,
      verification: row.coverVerification
    };
    const mediaStatus = mediaStatusInfo(row.coverVerification);
    const chapterRows = chapters.map((chapter) => `
      <tr>
        <td class="volume-number">${esc(chapter.label)}</td>
        <td><a href="${chapterHref(chapter.id)}">${esc(chapter.title)}</a></td>
        <td>${chapter.startPage ? `p.${esc(chapter.startPage)}` : '未登録'}</td>
      </tr>`).join('');
    const supplementRows = supplements.map((item) => `
      <a class="volume-supplement" href="${supplementHref(item.id)}">
        <strong>${esc(item.title)}</strong>
        <span>${esc(item.summary)}</span>
      </a>`).join('');
    const sourceIds = [...new Set([row.synopsisSourceRef, row.sourceRef].filter(Boolean))];

    detail.innerHTML = `
      <article class="record-view">
        <header class="record-header">
          <div class="record-copy">
            <div class="record-kicker">${esc(row.label)}</div>
            <h1 class="record-title">${esc(row.title)}</h1>
            <div class="record-meta">
              <span class="meta-chip">${esc(rangeLabel(row))}</span>
              <span class="meta-chip">${row.chapterCount || 0}話収録</span>
              ${row.supplementCount ? `<span class="meta-chip">描き下ろし${row.supplementCount}件</span>` : ''}
            </div>
            <p class="record-summary">${esc(row.synopsis || '巻あらすじ未登録')}</p>
            <p class="record-subnote">集英社公式の巻紹介を根拠に、DB用の文章として要約。</p>
          </div>
          <div class="record-media">${mediaThumb(media, {
            title: `${row.title} 公式表紙`,
            alt: `${row.title} 公式表紙`
          })}</div>
        </header>
        <div class="record-tabs" role="tablist" aria-label="${esc(row.label)}の情報">
          <button class="record-tab" type="button" role="tab" data-tab="chapters">収録話</button>
          ${supplements.length ? '<button class="record-tab" type="button" role="tab" data-tab="supplements">巻末補遺</button>' : ''}
          <button class="record-tab" type="button" role="tab" data-tab="sources">出典・巻情報</button>
        </div>
        <div class="record-scroll">
          <section class="tab-panel" role="tabpanel" data-tab-panel="chapters">
            <div class="table-wrap">
              <table class="record-table">
                <thead><tr><th>話数</th><th>話名</th><th>開始</th></tr></thead>
                <tbody>${chapterRows}</tbody>
              </table>
            </div>
          </section>
          ${supplements.length ? `
            <section class="tab-panel" role="tabpanel" data-tab-panel="supplements">
              <div class="record-section">
                <div class="section-heading"><h2 class="section-title">巻末描き下ろし・補遺</h2><span class="count-label">${supplements.length}件</span></div>
                <div class="volume-supplement-list">${supplementRows}</div>
              </div>
            </section>` : ''}
          <section class="tab-panel record-grid" role="tabpanel" data-tab-panel="sources">
            <div class="record-section">
              <h2 class="section-title">巻データ</h2>
              <dl class="compact-kv">
                <dt>収録範囲</dt><dd>${esc(rangeLabel(row))}</dd>
                <dt>収録話数</dt><dd>${row.chapterCount || 0}話</dd>
                <dt>描き下ろし</dt><dd>${row.supplementCount || 0}件</dd>
                <dt>表紙画像</dt><dd><span class="${esc(mediaStatus.className)}">${esc(mediaStatus.label)}</span></dd>
              </dl>
            </div>
            <div class="record-section">
              <h2 class="section-title">確認状態</h2>
              ${verificationBadge(row.verification)}
            </div>
            <div class="record-section wide">
              <h2 class="section-title">公式出典</h2>
              <div class="links">${sourceLinks(sourceIds)}</div>
              <p class="muted">収録話と開始ページは既存の公式目次照合データから生成。巻あらすじは公式紹介を根拠に独自要約しています。</p>
            </div>
          </section>
        </div>
      </article>`;
    setupTabs(detail, 'chapters');
  }

  list.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-id]');
    if (button) setId(button.dataset.id);
  });
  bindListNavigation(list, setId);
  search.addEventListener('input', applyFilter);
  window.addEventListener('jjk:navigate', (event) => renderDetail(event.detail?.id || queryParam('id')));
  window.addEventListener('popstate', () => renderDetail(queryParam('id')));

  applyFilter();
  const initialId = queryParam('id') || rows[0]?.id;
  if (initialId && !queryParam('id')) setId(initialId, { replace: true });
  else if (initialId) renderDetail(initialId);
}());
