(function () {
  'use strict';
  const { D, esc, queryParam, setId, entityLinks, sourceLinks, verificationBadge } = JJK;
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
    button.innerHTML = `<b>${esc(item.title)}</b><span class="sub">${esc(item.volume)}巻描き下ろし</span>`;
    fragment.appendChild(button);
    buttonMap.set(item.id, button);
  }
  list.appendChild(fragment);

  function render(id) {
    const item = rows.find((row) => row.id === id) || rows[0];
    if (!item) return;
    if (activeId && buttonMap.has(activeId)) buttonMap.get(activeId).classList.remove('active');
    activeId = item.id;
    buttonMap.get(item.id)?.classList.add('active');
    detail.innerHTML = `
      <div class="panel"><h1 class="detail-title">${esc(item.title)}</h1><div class="detail-meta">${esc(item.volume)}巻／${esc(item.kind)}</div><div class="prose">${esc(item.summary)}</div></div>
      <div class="panel"><h2 class="section-title">確認状態</h2>${verificationBadge(item.verification)}</div>`;
    aside.innerHTML = `
      <div class="panel"><h2 class="section-title">人物</h2><div class="links">${entityLinks('characters', item.character_ids || item.characterIds)}</div></div>
      <div class="panel"><h2 class="section-title">出典</h2><div class="links">${sourceLinks(item.source_refs || item.sourceRefs)}</div></div>`;
  }

  list.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-id]');
    if (button) setId(button.dataset.id);
  });
  window.addEventListener('jjk:navigate', (event) => render(event.detail?.id || queryParam('id')));
  window.addEventListener('popstate', () => render(queryParam('id')));

  const initialId = queryParam('id') || rows[0]?.id;
  if (initialId && !queryParam('id')) setId(initialId, { replace: true });
  else if (initialId) render(initialId);
}());
