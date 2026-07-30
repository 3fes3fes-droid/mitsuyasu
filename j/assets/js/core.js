(function () {
  'use strict';

  const D = window.JJK_DATA || {};
  const catalog = D.catalog || {};
  const detailStore = window.JJK_DETAIL_STORE = window.JJK_DETAIL_STORE || {};
  const loadedFiles = new Set();
  const pendingFiles = new Map();
  const maps = {};
  let memoryId = null;

  const page = (location.pathname.split('/').pop() || 'index.html');
  document.querySelectorAll('.main-nav a,.utility-nav a').forEach((anchor) => {
    if (anchor.getAttribute('href') === page) anchor.classList.add('active');
  });

  function map(type) {
    if (!maps[type]) maps[type] = new Map((catalog[type] || []).map((item) => [item.id, item]));
    return maps[type];
  }

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);
  }

  function queryParam(name) {
    const value = new URLSearchParams(location.search).get(name);
    return value || (name === 'id' ? memoryId : null);
  }

  function setId(id, options = {}) {
    memoryId = id;
    try {
      const url = new URL(location.href);
      url.searchParams.set('id', id);
      if (options.replace) history.replaceState({}, '', url);
      else history.pushState({}, '', url);
    } catch (_error) {
      // file:// で履歴操作が拒否された場合もメモリ上の選択は維持する。
    }
    window.dispatchEvent(new CustomEvent('jjk:navigate', { detail: { id } }));
  }

  function loadScript(file) {
    if (loadedFiles.has(file)) return Promise.resolve();
    if (pendingFiles.has(file)) return pendingFiles.get(file);

    const promise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = file;
      script.async = true;
      script.onload = () => {
        loadedFiles.add(file);
        pendingFiles.delete(file);
        resolve();
      };
      script.onerror = () => {
        pendingFiles.delete(file);
        reject(new Error(`詳細データを読み込めませんでした: ${file}`));
      };
      document.head.appendChild(script);
    });
    pendingFiles.set(file, promise);
    return promise;
  }

  async function loadDetail(type, id) {
    if (detailStore[type] && detailStore[type][id]) return detailStore[type][id];
    const entry = map(type).get(id);
    if (!entry) throw new Error(`登録されていないIDです: ${type}/${id}`);
    let detailFile;
    if (type === 'chapters') detailFile = `data/generated/details/chapters/${entry.detailChunk}.js`;
    else detailFile = `data/generated/details/${type}/part-${String(entry.detailChunk).padStart(2, '0')}.js`;
    await loadScript(detailFile);
    const detail = detailStore[type] && detailStore[type][id];
    if (!detail) throw new Error(`詳細ファイル内にIDがありません: ${type}/${id}`);
    return detail;
  }

  function chapterHref(id) {
    return `chapters.html?id=${encodeURIComponent(id)}`;
  }

  function entityHref(type, id) {
    return `${type}.html?id=${encodeURIComponent(id)}`;
  }

  function supplementHref(id) {
    return `supplements.html?id=${encodeURIComponent(id)}`;
  }

  function chapterLabel(id) {
    const item = map('chapters').get(id);
    return item ? `${item.label} ${item.title}` : id;
  }

  function supplementLabel(id) {
    const item = map('supplements').get(id);
    return item ? item.title : id;
  }

  function referenceLink(id) {
    if (!id) return '<span class="muted">不明</span>';
    if (map('chapters').has(id)) return `<a class="entity-link" href="${chapterHref(id)}">${esc(chapterLabel(id))}</a>`;
    if (map('supplements').has(id)) return `<a class="entity-link" href="${supplementHref(id)}">${esc(supplementLabel(id))}</a>`;
    return `<span class="muted">${esc(id)}</span>`;
  }

  function sourceLinks(ids) {
    const html = (ids || []).map((id) => {
      const source = map('sources').get(id);
      if (!source) return `<span class="badge danger">不明な出典 ${esc(id)}</span>`;
      const label = esc(source.title || id);
      return source.url
        ? `<a class="entity-link source-link" href="${esc(source.url)}" target="_blank" rel="noopener">${label}</a>`
        : `<span class="entity-link">${label}</span>`;
    }).join('');
    return html || '<span class="muted">登録なし</span>';
  }

  function entityLinks(type, ids) {
    const html = (ids || []).map((id) => {
      const item = map(type).get(id);
      return item
        ? `<a class="entity-link" href="${entityHref(type, id)}">${esc(item.name)}</a>`
        : `<span class="badge danger">参照切れ ${esc(id)}</span>`;
    }).join('');
    return html || '<span class="muted">なし</span>';
  }

  function chapterLinks(ids, limit = 999) {
    const source = ids || [];
    const visible = source.slice(0, limit);
    let html = visible.map((id) => `<a class="entity-link" href="${chapterHref(id)}">${esc(chapterLabel(id))}</a>`).join('');
    if (source.length > limit) html += `<span class="badge">ほか${source.length - limit}話</span>`;
    return html || '<span class="muted">なし</span>';
  }

  function supplementLinks(ids) {
    const html = (ids || []).map((id) => `<a class="entity-link" href="${supplementHref(id)}">${esc(supplementLabel(id))}</a>`).join('');
    return html || '<span class="muted">なし</span>';
  }

  function verificationInfo(value) {
    const raw = value || '未設定';
    if (raw.includes('first-pass')) {
      return { label: '第一稿／個別精査待ち', className: 'warning' };
    }
    if (raw.includes('not-primary-pages') || raw.includes('pending-primary-pages')) {
      return { label: '複数資料で突合済み／原作ページ最終照合前', className: 'warning' };
    }
    if (raw.includes('primary')) {
      return { label: '原作ページ確認済み', className: 'good' };
    }
    return { label: raw, className: 'warning' };
  }

  function verificationBadge(value) {
    const info = verificationInfo(value);
    return `<div class="notice ${info.className}">${esc(info.label)}</div>`;
  }

  function statusLabel(value) {
    const labels = {
      alive: '生存', dead: '死亡', unknown: '不明', active: '活動中', destroyed: '消滅・破壊',
      fictional: '作中作の存在', released: '解放', 'alive-or-unknown': '生存または不明',
      'alive-restored': '生存・回復', 'alive-freed': '生存・解放', 'alive-returned': '生存・復帰',
      'alive-severely-injured': '生存・重傷', 'alive-execution-faked': '生存・処刑偽装',
      'vengeful-curse-exorcised': '怨霊化後に祓除', 'absorbed-and-technique-extracted': '取り込み・術式抽出',
      'captured-by-kenjaku': '羂索に取り込まれた', 'reproduced-after-destruction': '破壊後に再生個体出現',
      'inactive-but-occasionally-moves': '活動停止状態・時折動く',
      'alive-complete-heavenly-restriction': '生存・完全な天与呪縛'
    };
    return labels[value] || value || '不明';
  }

  function globalSearch(query, limit = 24) {
    const q = String(query || '').trim().toLowerCase();
    if (!q) return [];
    const output = [];
    for (const item of catalog.chapters || []) {
      if (`${item.label} ${item.title} ${item.summaryShort}`.toLowerCase().includes(q)) {
        output.push({ type: '各話', label: `${item.label} ${item.title}`, href: chapterHref(item.id) });
      }
    }
    for (const [type, label] of [['characters', '人物'], ['techniques', '技・術式'], ['terms', '用語']]) {
      for (const item of catalog[type] || []) {
        if ([item.name, ...(item.aliases || []), item.reading || '', item.category || '', item.affiliation || '', ...(item.users || [])].join(' ').toLowerCase().includes(q)) output.push({ type: label, label: item.name, href: entityHref(type, item.id) });
      }
    }
    return output.slice(0, limit);
  }

  function debounce(fn, delay = 60) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  }

  window.JJK = {
    D, catalog, map, esc, queryParam, setId, loadDetail,
    chapterHref, entityHref, supplementHref, chapterLabel,
    sourceLinks, entityLinks, chapterLinks, supplementLinks, referenceLink,
    verificationInfo, verificationBadge, statusLabel, globalSearch, debounce
  };
}());
