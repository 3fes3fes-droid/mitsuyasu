(function () {
  'use strict';
  const {
    D, esc, queryParam, setId, entityLinks, sourceLinks, verificationBadge,
    setupTabs, bindListNavigation
  } = JJK;

  const rows = D.supplements || [];
  const list = document.querySelector('#item-list');
  const detail = document.querySelector('#detail');
  const aside = document.querySelector('#aside');
  const buttonMap = new Map();
  let activeId = null;

  const fragment = document.createDocumentFragment();
  for (const item of rows) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.id = item.id;
    button.innerHTML = `<b>${esc(item.title)}</b><span class="sub">${esc(item.volume)}巻</span>`;
    fragment.appendChild(button);
    buttonMap.set(item.id, button);
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

  function render(id) {
    const item = rows.find((row) => row.id === id) || rows[0];
    if (!item) return;
    setActive(item.id);
    aside.innerHTML = '';
    detail.innerHTML = `
      <article class="record-view">
        <header class="record-header no-media">
          <div class="record-copy">
            <div class="record-kicker">${esc(item.volume)}巻描き下ろし</div>
            <h1 class="record-title">${esc(item.title)}</h1>
            <div class="record-meta"><span class="meta-chip">${esc(item.kind)}</span></div>
            <p class="record-summary">${esc(item.summary)}</p>
          </div>
        </header>
        <div class="record-tabs" role="tablist" aria-label="${esc(item.title)}の情報">
          <button class="record-tab" type="button" role="tab" data-tab="overview">概要</button>
          <button class="record-tab" type="button" role="tab" data-tab="relations">人物</button>
          <button class="record-tab" type="button" role="tab" data-tab="sources">出典・確認</button>
        </div>
        <div class="record-scroll">
          <section class="tab-panel record-grid" role="tabpanel" data-tab-panel="overview">
            <div class="record-section">
              <h2 class="section-title">登録情報</h2>
              <dl class="compact-kv">
                <dt>収録巻</dt><dd>${esc(item.volume)}巻</dd>
                <dt>区分</dt><dd>${esc(item.kind)}</dd>
              </dl>
            </div>
          </section>
          <section class="tab-panel" role="tabpanel" data-tab-panel="relations">
            <div class="record-section">
              <h2 class="section-title">登場人物</h2>
              <div class="links">${entityLinks('characters', item.character_ids || item.characterIds)}</div>
            </div>
          </section>
          <section class="tab-panel record-grid" role="tabpanel" data-tab-panel="sources">
            <div class="record-section"><h2 class="section-title">確認状態</h2>${verificationBadge(item.verification)}</div>
            <div class="record-section"><h2 class="section-title">出典</h2><div class="links">${sourceLinks(item.source_refs || item.sourceRefs)}</div></div>
          </section>
        </div>
      </article>`;
    setupTabs(detail, 'overview');
  }

  list.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-id]');
    if (button) setId(button.dataset.id);
  });
  bindListNavigation(list, setId);
  window.addEventListener('jjk:navigate', (event) => render(event.detail?.id || queryParam('id')));
  window.addEventListener('popstate', () => render(queryParam('id')));

  const initialId = queryParam('id') || rows[0]?.id;
  if (initialId && !queryParam('id')) setId(initialId, { replace: true });
  else if (initialId) render(initialId);
}());
