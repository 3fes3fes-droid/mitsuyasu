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

  function mediaStatusInfo(value) {
    const raw = value || 'unverified';
    if (raw === 'official-page-direct-link') return { label: '公式ページ直リンク確認済み', className: 'good' };
    if (raw === 'pending-official-page-collection') return { label: '公式URL未収集', className: 'warning' };
    if (raw === 'not-listed-or-unmatched') return { label: '公式画像との対応未確認', className: 'warning' };
    return { label: raw, className: 'warning' };
  }

  function mediaCard(media, options = {}) {
    const item = media || {};
    const status = mediaStatusInfo(item.verification);
    const title = options.title || '公式画像';
    const alt = options.alt || title;
    const imageUrl = item.imageUrl || '';
    const pageUrl = item.pageUrl || '';
    const note = item.note || '';
    const image = imageUrl
      ? `<div class="official-media-frame"><img data-official-media src="${esc(imageUrl)}" alt="${esc(alt)}" loading="lazy" decoding="async"><div class="official-media-fallback" hidden>画像を読み込めませんでした。下の公式リンクから確認してください。</div></div>`
      : `<div class="official-media-frame official-media-empty"><div class="official-media-fallback">${esc(options.emptyText || '公式画像URL未収集')}</div></div>`;
    const links = [
      imageUrl ? `<a class="entity-link" href="${esc(imageUrl)}" target="_blank" rel="noopener noreferrer">画像を公式URLで開く</a>` : '',
      pageUrl ? `<a class="entity-link" href="${esc(pageUrl)}" target="_blank" rel="noopener noreferrer">掲載元の公式ページ</a>` : ''
    ].filter(Boolean).join('');
    return `<section class="official-media-card"><h2 class="section-title">${esc(title)}</h2>${image}<div class="media-status ${status.className}">${esc(status.label)}</div>${note ? `<p class="muted media-note">${esc(note)}</p>` : ''}${links ? `<div class="links media-links">${links}</div>` : ''}</section>`;
  }

  function mediaThumb(media, options = {}) {
    const item = media || {};
    const status = mediaStatusInfo(item.verification);
    const imageUrl = item.imageUrl || '';
    const pageUrl = item.pageUrl || imageUrl || '';
    const label = options.alt || options.title || '公式画像';
    const className = options.className ? ` ${esc(options.className)}` : '';
    const content = imageUrl
      ? `<img data-official-media src="${esc(imageUrl)}" alt="${esc(label)}" loading="lazy" decoding="async"><span class="media-thumb-empty" hidden>画像を読み込めません</span>`
      : `<span class="media-thumb-empty">${esc(options.emptyText || '公式画像URL未収集')}</span>`;
    const dot = `<span class="media-status-dot ${esc(status.className)}" title="${esc(status.label)}"></span>`;
    return pageUrl
      ? `<a class="media-thumb${className}" href="${esc(pageUrl)}" target="_blank" rel="noopener noreferrer" aria-label="${esc(label)}">${content}${dot}</a>`
      : `<div class="media-thumb${className}" aria-label="${esc(label)}">${content}${dot}</div>`;
  }

  document.addEventListener('error', (event) => {
    const image = event.target;
    if (!(image instanceof HTMLImageElement) || !image.matches('[data-official-media]')) return;
    image.hidden = true;
    const fallback = image.parentElement && image.parentElement.querySelector('.official-media-fallback,.media-thumb-empty');
    if (fallback) fallback.hidden = false;
  }, true);

  function verificationInfo(value) {
    const raw = value || '未設定';
    if (raw === 'official-volume-synopsis-paraphrased') {
      return { label: '集英社公式の巻紹介を確認・DB用に要約済み', className: 'good' };
    }
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
      if (`${item.label} ${item.title} ${item.summaryShort} ${(item.highlightKeywords || []).join(' ')}`.toLowerCase().includes(q)) {
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

  function shuffleCopy(items, random = Math.random) {
    const output = [...(items || [])];
    for (let index = output.length - 1; index > 0; index -= 1) {
      const randomIndex = Math.floor(random() * (index + 1));
      [output[index], output[randomIndex]] = [output[randomIndex], output[index]];
    }
    return output;
  }

  function setupTabs(root, initialTab = '') {
    if (!root) return () => {};
    const buttons = [...root.querySelectorAll('[data-tab]')];
    const panels = [...root.querySelectorAll('[data-tab-panel]')];
    if (!buttons.length || !panels.length) return () => {};

    function select(tabName, focus = false) {
      const target = buttons.find((button) => button.dataset.tab === tabName) || buttons[0];
      for (const button of buttons) {
        const selected = button === target;
        button.setAttribute('aria-selected', selected ? 'true' : 'false');
        button.tabIndex = selected ? 0 : -1;
      }
      for (const panel of panels) panel.hidden = panel.dataset.tabPanel !== target.dataset.tab;
      if (focus) target.focus();
    }

    for (const button of buttons) {
      button.addEventListener('click', () => select(button.dataset.tab));
      button.addEventListener('keydown', (event) => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        const index = buttons.indexOf(button);
        let nextIndex = index;
        if (event.key === 'ArrowLeft') nextIndex = (index - 1 + buttons.length) % buttons.length;
        if (event.key === 'ArrowRight') nextIndex = (index + 1) % buttons.length;
        if (event.key === 'Home') nextIndex = 0;
        if (event.key === 'End') nextIndex = buttons.length - 1;
        select(buttons[nextIndex].dataset.tab, true);
      });
    }
    select(initialTab || buttons[0].dataset.tab);
    return select;
  }

  function bindListNavigation(list, onSelect) {
    if (!list || typeof onSelect !== 'function') return;
    list.addEventListener('keydown', (event) => {
      if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
      const current = event.target.closest('button[data-id]');
      if (!current) return;
      const visible = [...list.querySelectorAll('button[data-id]')].filter((button) => !button.hidden);
      if (!visible.length) return;
      event.preventDefault();
      const index = Math.max(0, visible.indexOf(current));
      let nextIndex = index;
      if (event.key === 'ArrowUp') nextIndex = Math.max(0, index - 1);
      if (event.key === 'ArrowDown') nextIndex = Math.min(visible.length - 1, index + 1);
      if (event.key === 'Home') nextIndex = 0;
      if (event.key === 'End') nextIndex = visible.length - 1;
      const next = visible[nextIndex];
      next.focus();
      onSelect(next.dataset.id);
    });
  }

  const FONT_TUNER_STORAGE = 'jjk-font-tuner-v1';
  const FONT_TUNER_OPTIONS = [
    { key: 'base', label: '全体の基本文字', css: '--font-base', min: 12, max: 20, value: 14 },
    { key: 'nav', label: '上部メニュー', css: '--font-nav', min: 10, max: 20, value: 13 },
    { key: 'list', label: '左側の一覧', css: '--font-list', min: 10, max: 22, value: 12 },
    { key: 'recordTitle', label: '詳細タイトル', css: '--font-record-title', min: 18, max: 40, value: 25 },
    { key: 'recordSummary', label: '見出し下あらすじ', css: '--font-record-summary', min: 11, max: 26, value: 14 },
    { key: 'tab', label: '詳細タブ', css: '--font-tab', min: 10, max: 20, value: 12 },
    { key: 'detail', label: '本文・出来事', css: '--font-detail', min: 11, max: 24, value: 14 },
    { key: 'detailItem', label: '項目・関連リンク', css: '--font-detail-item', min: 9, max: 20, value: 12 },
    { key: 'sectionTitle', label: '項目見出し', css: '--font-section-title', min: 9, max: 20, value: 11 },
    { key: 'table', label: '収録話・出典表', css: '--font-table', min: 9, max: 20, value: 11 }
  ];

  function readFontSettings() {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(FONT_TUNER_STORAGE) || '{}');
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (_error) {
      return {};
    }
  }

  function writeFontSettings(settings) {
    try {
      window.localStorage.setItem(FONT_TUNER_STORAGE, JSON.stringify(settings));
    } catch (_error) {
      // file:// などで保存が拒否されても、現在のページには反映する。
    }
  }

  function normalizeFontSettings(source = {}) {
    const output = {};
    for (const option of FONT_TUNER_OPTIONS) {
      const raw = Number(source[option.key]);
      output[option.key] = Number.isFinite(raw)
        ? Math.min(option.max, Math.max(option.min, Math.round(raw)))
        : option.value;
    }
    return output;
  }

  function applyFontSettings(source = {}) {
    const settings = normalizeFontSettings(source);
    const style = document.documentElement && document.documentElement.style;
    if (style && typeof style.setProperty === 'function') {
      for (const option of FONT_TUNER_OPTIONS) {
        style.setProperty(option.css, `${settings[option.key]}px`);
      }
    }
    return settings;
  }

  function fontSettingsCss(settings) {
    const values = normalizeFontSettings(settings);
    const lines = FONT_TUNER_OPTIONS.map((option) => `  ${option.css}: ${values[option.key]}px;`);
    return `:root {\n${lines.join('\n')}\n}`;
  }

  function initFontTuner() {
    if (!document.body || !document.documentElement || typeof document.createElement !== 'function') return;
    let settings = applyFontSettings(readFontSettings());
    const launch = document.createElement('button');
    launch.type = 'button';
    launch.className = 'font-tuner-launch';
    launch.textContent = '文字サイズ';
    launch.setAttribute('aria-expanded', 'false');
    launch.setAttribute('aria-controls', 'font-tuner-panel');

    const panel = document.createElement('section');
    panel.id = 'font-tuner-panel';
    panel.className = 'font-tuner';
    panel.hidden = true;
    panel.setAttribute('aria-label', '文字サイズ一時調整');
    panel.innerHTML = `
      <div class="font-tuner-head">
        <strong>文字サイズ一時調整</strong>
        <button class="font-tuner-close" type="button" aria-label="閉じる">×</button>
      </div>
      <p class="font-tuner-note">動かすと即反映し、このブラウザに保存します。「採用値をコピー」で最終固定に使う値を取り出せます。</p>
      <div class="font-tuner-controls"></div>
      <div class="font-tuner-actions">
        <button type="button" data-font-action="reset">初期値に戻す</button>
        <button type="button" data-font-action="copy">採用値をコピー</button>
      </div>
      <textarea class="font-tuner-output" hidden readonly aria-label="採用するCSS"></textarea>
      <p class="font-tuner-status" aria-live="polite"></p>`;

    const controls = panel.querySelector('.font-tuner-controls');
    const inputMap = new Map();
    for (const option of FONT_TUNER_OPTIONS) {
      const row = document.createElement('div');
      row.className = 'font-tuner-row';
      const inputId = `font-tuner-${option.key}`;
      row.innerHTML = `
        <label for="${inputId}">${esc(option.label)}</label>
        <input id="${inputId}" type="range" min="${option.min}" max="${option.max}" step="1" value="${settings[option.key]}">
        <span class="font-tuner-value">${settings[option.key]}px</span>`;
      controls.appendChild(row);
      const input = row.querySelector('input');
      const value = row.querySelector('.font-tuner-value');
      input.addEventListener('input', () => {
        settings[option.key] = Number(input.value);
        settings = applyFontSettings(settings);
        value.textContent = `${settings[option.key]}px`;
        writeFontSettings(settings);
        panel.querySelector('.font-tuner-status').textContent = 'このブラウザへ保存しました';
      });
      inputMap.set(option.key, { input, value });
    }

    function setOpen(open) {
      panel.hidden = !open;
      launch.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) panel.querySelector('input')?.focus();
    }

    launch.addEventListener('click', () => setOpen(panel.hidden));
    panel.querySelector('.font-tuner-close').addEventListener('click', () => setOpen(false));
    panel.querySelector('[data-font-action="reset"]').addEventListener('click', () => {
      settings = applyFontSettings({});
      writeFontSettings(settings);
      for (const option of FONT_TUNER_OPTIONS) {
        const control = inputMap.get(option.key);
        control.input.value = settings[option.key];
        control.value.textContent = `${settings[option.key]}px`;
      }
      panel.querySelector('.font-tuner-output').hidden = true;
      panel.querySelector('.font-tuner-status').textContent = '初期値へ戻しました';
    });
    panel.querySelector('[data-font-action="copy"]').addEventListener('click', async () => {
      const output = panel.querySelector('.font-tuner-output');
      const css = fontSettingsCss(settings);
      output.value = css;
      output.hidden = false;
      output.select();
      let copied = false;
      try {
        if (window.navigator?.clipboard?.writeText) {
          await window.navigator.clipboard.writeText(css);
          copied = true;
        }
      } catch (_error) {
        copied = false;
      }
      panel.querySelector('.font-tuner-status').textContent = copied
        ? '採用値をコピーしました'
        : '下の欄をコピーしてください';
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !panel.hidden) setOpen(false);
    });
    document.body.appendChild(launch);
    document.body.appendChild(panel);
  }

  initFontTuner();

  window.JJK = {
    D, catalog, map, esc, queryParam, setId, loadDetail,
    chapterHref, entityHref, supplementHref, chapterLabel,
    sourceLinks, entityLinks, chapterLinks, supplementLinks, referenceLink,
    verificationInfo, verificationBadge, mediaStatusInfo, mediaCard, mediaThumb, statusLabel,
    globalSearch, debounce, shuffleCopy, setupTabs, bindListNavigation,
    FONT_TUNER_OPTIONS, normalizeFontSettings, applyFontSettings, fontSettingsCss, initFontTuner
  };
}());
