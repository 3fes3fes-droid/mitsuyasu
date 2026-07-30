(function () {
  'use strict';
  const {
    catalog, esc, queryParam, setId, loadDetail, entityLinks, sourceLinks,
    verificationBadge, mediaThumb, mediaStatusInfo, chapterHref, debounce,
    setupTabs, bindListNavigation
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
    button.dataset.search = `${row.label} ${row.title} ${row.summaryShort} ${(row.highlightKeywords || []).join(' ')}`.toLowerCase();
    button.innerHTML = `<b>${esc(row.label)}　${esc(row.title)}</b><span class="sub">${row.volume === 0 ? '0巻' : `${row.volume}巻`}</span>`;
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
      const show = (!arc.value || row.arcId === arc.value) && (!query || button.dataset.search.includes(query));
      button.hidden = !show;
      if (show) visible += 1;
    }
    count.textContent = `${visible} / ${rows.length}話`;
  }

  function mediaSourceHtml(item) {
    const media = item.media || {};
    const status = mediaStatusInfo(media.verification);
    const links = [
      media.imageUrl ? `<a class="entity-link" href="${esc(media.imageUrl)}" target="_blank" rel="noopener noreferrer">画像URL</a>` : '',
      media.pageUrl ? `<a class="entity-link" href="${esc(media.pageUrl)}" target="_blank" rel="noopener noreferrer">掲載元ページ</a>` : ''
    ].filter(Boolean).join('');
    return `
      <dl class="compact-kv">
        <dt>画像状態</dt><dd><span class="${esc(status.className)}">${esc(status.label)}</span></dd>
        <dt>公式リンク</dt><dd><div class="links">${links || '<span class="muted">未収集</span>'}</div></dd>
      </dl>`;
  }

  async function renderDetail(id) {
    const compact = rows.find((row) => row.id === id) || rows[0];
    if (!compact) return;
    const token = ++renderToken;
    setActive(compact.id);
    detail.innerHTML = '<div class="loading-panel">詳細データを読み込んでいます…</div>';
    aside.innerHTML = '';

    try {
      const item = await loadDetail('chapters', compact.id);
      if (token !== renderToken) return;
      const index = rows.findIndex((row) => row.id === item.id);
      const previous = index > 0 ? rows[index - 1] : null;
      const next = index < rows.length - 1 ? rows[index + 1] : null;
      const arcName = arcMap.get(item.arcId)?.name || '未分類';
      const hasMedia = Boolean(item.media && item.media.imageUrl);
      const events = (item.events || []).map((event) =>
        `<li>${esc(typeof event === 'string' ? event : event.text || JSON.stringify(event))}</li>`
      ).join('') || '<li class="muted">未登録</li>';
      const exactQuotes = (item.memorableQuotes || []).map((quote) => `
        <blockquote class="highlight-quote">
          <q>${esc(quote.text || '')}</q>
          <footer>${esc(quote.speaker || '話者未登録')}${quote.kind ? `／${esc(quote.kind)}` : ''}</footer>
        </blockquote>`).join('');
      const crosscheckedLineRows = item.crosscheckedLines || [];
      const crosscheckedLineCard = (line) => {
        const sourceCount = Number(line.sourceCount || (line.sourceRefs || []).length || 2);
        const attribution = [
          line.speaker ? esc(line.speaker) : '',
          `複数記事照合・${sourceCount}系統`
        ].filter(Boolean).join('／');
        return `
          <article class="verified-line-card">
            <q>${esc(line.text || '')}</q>
            <footer>${attribution}</footer>
          </article>`;
      };
      const crosscheckedVisible = crosscheckedLineRows.slice(0, 6).map(crosscheckedLineCard).join('');
      const crosscheckedHidden = crosscheckedLineRows.slice(6).map(crosscheckedLineCard).join('');
      const crosscheckedLines = crosscheckedLineRows.length ? `
        <div class="record-section verified-line-section">
          <div class="section-heading">
            <h2 class="section-title">複数記事で確認できた短い作中語句・発言</h2>
            <span class="count-label">${crosscheckedLineRows.length}件</span>
          </div>
          <div class="verified-line-grid">${crosscheckedVisible}</div>
          ${crosscheckedHidden ? `
            <details class="verified-line-more">
              <summary>残り${crosscheckedLineRows.length - 6}件を表示</summary>
              <div class="verified-line-grid">${crosscheckedHidden}</div>
            </details>` : ''}
        </div>` : '';
      const popularLineGists = (item.popularLineGists || []).map((line) => `
        <article class="line-gist">
          <header>
            <strong>${esc(line.label || '印象的な言葉')}</strong>
            <span>${esc(line.speaker || '話者未登録')}</span>
          </header>
          <p>${esc(line.text || '')}</p>
        </article>`).join('');
      const dialogueSummaries = (item.dialogueSummaries || []).map((line) => `
        <li>
          <span class="event-type">${esc(line.kind || 'セリフ要旨')}</span>
          <span>${esc(line.text || '')}</span>
        </li>`).join('') || '<li class="muted">この話のあらすじから要旨を抽出できませんでした。</li>';
      const detailedEventRows = item.detailedEvents?.length ? item.detailedEvents : item.events || [];
      const detailedEvents = detailedEventRows.map((event) => {
        const text = typeof event === 'string' ? event : event.text || JSON.stringify(event);
        const level = typeof event === 'string' ? '出来事' : event.level || '出来事';
        return `<li><span class="event-type">${esc(level)}</span><span>${esc(text)}</span></li>`;
      }).join('') || '<li class="muted">未登録</li>';
      const keywords = (item.highlightKeywords || []).map((keyword) =>
        `<span class="highlight-keyword">${esc(keyword)}</span>`
      ).join('');
      const crosscheckedSourceLinks = (item.crosscheckedSourceUrls || []).map((url, sourceIndex) =>
        `<a class="entity-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">照合記事 ${sourceIndex + 1}</a>`
      ).join('');
      const exactQuoteCount = (item.memorableQuotes || []).length;
      const crosscheckedLineCount = crosscheckedLineRows.length;
      const popularLineCount = (item.popularLineGists || []).length;
      const dialogueCount = (item.dialogueSummaries || []).length;
      const detailedEventCount = detailedEventRows.length;
      const keywordCount = (item.highlightKeywords || []).length;

      detail.innerHTML = `
        <article class="record-view">
          <header class="record-header${hasMedia ? '' : ' no-media'}">
            <div class="record-copy">
              <div class="record-kicker">${esc(arcName)}</div>
              <h1 class="record-title">${esc(item.label)}　${esc(item.title)}</h1>
              <div class="record-meta">
                <span class="meta-chip">${item.volume === 0 ? '0巻' : `${item.volume}巻`}</span>
                <span class="meta-chip">開始 p.${esc(item.startPage)}</span>
              </div>
              <p class="record-summary">${esc(item.summaryShort)}</p>
            </div>
            ${hasMedia ? `<div class="record-media">${mediaThumb(item.media, {
              title: '少年ジャンプ＋ 公式サムネイル',
              alt: `${item.label} ${item.title} 公式サムネイル`
            })}</div>` : ''}
          </header>
          <div class="record-tabs" role="tablist" aria-label="各話の情報">
            <button class="record-tab" type="button" role="tab" data-tab="summary">あらすじ</button>
            <button class="record-tab" type="button" role="tab" data-tab="relations">登場・関連</button>
            <button class="record-tab" type="button" role="tab" data-tab="highlights">名言・キーワード</button>
            <button class="record-tab" type="button" role="tab" data-tab="sources">出典・確認</button>
            <div class="record-nav" aria-label="前後の話">
              ${previous ? `<button type="button" data-nav-id="${esc(previous.id)}">← ${esc(previous.label)}</button>` : ''}
              ${next ? `<button type="button" data-nav-id="${esc(next.id)}">${esc(next.label)} →</button>` : ''}
            </div>
          </div>
          <div class="record-scroll">
            <section class="tab-panel record-grid" role="tabpanel" data-tab-panel="summary">
              <div class="record-section">
                <h2 class="section-title">詳細あらすじ</h2>
                <div class="prose">${esc(item.summaryFull)}</div>
              </div>
              <div class="record-section">
                <h2 class="section-title">重要な出来事</h2>
                <ul class="events">${events}</ul>
              </div>
            </section>
            <section class="tab-panel record-grid three" role="tabpanel" data-tab-panel="relations">
              <div class="record-section relation-block"><h2 class="section-title">登場人物</h2><div class="links">${entityLinks('characters', item.characterIds)}</div></div>
              <div class="record-section relation-block"><h2 class="section-title">技・術式</h2><div class="links">${entityLinks('techniques', item.techniqueIds)}</div></div>
              <div class="record-section relation-block"><h2 class="section-title">用語</h2><div class="links">${entityLinks('terms', item.termIds)}</div></div>
            </section>
            <section class="tab-panel highlight-dashboard" role="tabpanel" data-tab-panel="highlights">
              <div class="highlight-stats" aria-label="登録件数">
                <span><b>${crosscheckedLineCount + exactQuoteCount + popularLineCount}</b> 名言・語句</span>
                <span><b>${dialogueCount}</b> セリフ・判断・言動</span>
                <span><b>${detailedEventCount}</b> 詳細出来事</span>
                <span><b>${keywordCount}</b> キーワード</span>
              </div>
              ${crosscheckedLines}
              <div class="highlight-primary-grid">
                <div class="record-section">
                  <h2 class="section-title">代表的な名言・話題句</h2>
                  <div class="quote-list">
                    ${exactQuotes}
                    ${popularLineGists}
                    ${exactQuotes || popularLineGists ? '' : '<span class="muted">代表句は未登録。照合済み発言と下の要旨・出来事を参照。</span>'}
                  </div>
                </div>
                <div class="record-section">
                  <h2 class="section-title">セリフ・判断・言動の要旨</h2>
                  <ul class="compact-event-list">${dialogueSummaries}</ul>
                </div>
                <div class="record-section">
                  <h2 class="section-title">印象的なキーワード</h2>
                  <div class="keyword-list">${keywords || '<span class="muted">個別登録なし</span>'}</div>
                </div>
              </div>
              <div class="record-section highlight-events">
                <div class="section-heading">
                  <h2 class="section-title">詳細出来事タイムライン</h2>
                  <span class="count-label">${detailedEventCount}件</span>
                </div>
                <ol class="event-matrix">${detailedEvents}</ol>
              </div>
              <div class="record-section highlight-relations">
                <div>
                  <h2 class="section-title">技・術式</h2>
                  <div class="links">${entityLinks('techniques', item.techniqueIds)}</div>
                </div>
                <div>
                  <h2 class="section-title">用語</h2>
                  <div class="links">${entityLinks('terms', item.termIds)}</div>
                </div>
              </div>
            </section>
            <section class="tab-panel record-grid" role="tabpanel" data-tab-panel="sources">
              <div class="record-section">
                <h2 class="section-title">確認状態</h2>
                ${verificationBadge(item.verification)}
                ${item.verificationNotes ? `<p class="muted">${esc(item.verificationNotes)}</p>` : ''}
              </div>
              <div class="record-section">
                <h2 class="section-title">出典</h2>
                <div class="links">${sourceLinks(item.sourceRefs)}</div>
                ${crosscheckedSourceLinks ? `
                  <h3 class="section-title source-subtitle">短文照合に使った各話記事</h3>
                  <div class="links">${crosscheckedSourceLinks}</div>` : ''}
                ${item.sourceLocator ? `<p class="muted">${esc(item.sourceLocator)}</p>` : ''}
              </div>
              <div class="record-section wide">
                <h2 class="section-title">公式サムネイル</h2>
                ${mediaSourceHtml(item)}
              </div>
            </section>
          </div>
        </article>`;

      setupTabs(detail, 'summary');
      detail.querySelectorAll('[data-nav-id]').forEach((button) => {
        button.addEventListener('click', () => setId(button.dataset.navId));
      });
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
  arc.addEventListener('change', applyFilter);
  window.addEventListener('jjk:navigate', (event) => renderDetail(event.detail?.id || queryParam('id')));
  window.addEventListener('popstate', () => renderDetail(queryParam('id')));

  applyFilter();
  const initialId = queryParam('id') || rows.find((row) => !buttonMap.get(row.id).hidden)?.id || rows[0]?.id;
  if (initialId && !queryParam('id')) setId(initialId, { replace: true });
  else if (initialId) renderDetail(initialId);
}());
