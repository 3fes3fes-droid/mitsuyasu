(function () {
  'use strict';
  const { D, esc, debounce } = JJK;
  const rows = D.sources || [];
  const search = document.querySelector('#search');
  const body = document.querySelector('#source-body');
  const count = document.querySelector('#result-count');
  const rowNodes = [];
  const fragment = document.createDocumentFragment();

  for (const source of rows) {
    const row = document.createElement('tr');
    row.dataset.search = JSON.stringify(source).toLowerCase();
    row.innerHTML = `<td>${esc(source.type || '')}</td><td>${esc(source.title || '')}</td><td>${esc(source.publisher || '')}</td><td>${source.url ? `<a href="${esc(source.url)}" target="_blank" rel="noopener">開く</a>` : ''}</td>`;
    fragment.appendChild(row);
    rowNodes.push(row);
  }
  body.appendChild(fragment);

  function applyFilter() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    for (const row of rowNodes) {
      const show = !query || row.dataset.search.includes(query);
      row.hidden = !show;
      if (show) visible += 1;
    }
    count.textContent = `${visible} / ${rows.length}件`;
  }
  search.addEventListener('input', debounce(applyFilter));
  applyFilter();
}());
