'use strict';
const fs = require('fs');
const vm = require('vm');
class HTMLImageElement {}
const listeners = {};
const document = {
  querySelectorAll: () => [],
  addEventListener: (type, callback) => { listeners[type] = callback; },
  createElement: () => ({})
};
const context = {
  window: { JJK_DATA: { catalog: {} }, JJK_DETAIL_STORE: {} },
  document,
  location: { pathname: '/characters.html', search: '', href: 'file:///characters.html' },
  history: { pushState() {}, replaceState() {} },
  CustomEvent: class {},
  HTMLImageElement,
  URL,
  URLSearchParams,
  Set,
  Map,
  Promise,
  console,
  setTimeout,
  clearTimeout,
};
context.window.window = context.window;
context.window.document = document;
context.window.location = context.location;
context.window.history = context.history;
context.window.CustomEvent = context.CustomEvent;
vm.createContext(context);
vm.runInContext(fs.readFileSync('assets/js/core.js', 'utf8'), context);
const JJK = context.window.JJK;
if (!JJK || typeof JJK.mediaCard !== 'function') throw new Error('mediaCard not exported');
if (typeof JJK.mediaThumb !== 'function') throw new Error('mediaThumb not exported');
if (typeof JJK.setupTabs !== 'function') throw new Error('setupTabs not exported');
if (typeof JJK.bindListNavigation !== 'function') throw new Error('bindListNavigation not exported');
if (typeof JJK.normalizeFontSettings !== 'function') throw new Error('normalizeFontSettings not exported');
if (typeof JJK.fontSettingsCss !== 'function') throw new Error('fontSettingsCss not exported');
const fontSettings = JJK.normalizeFontSettings({ detail: 18, table: 99 });
if (fontSettings.detail !== 18 || fontSettings.table !== 20) throw new Error('font settings clamp failed');
const fontCss = JJK.fontSettingsCss(fontSettings);
if (!fontCss.includes('--font-detail: 18px;') || !fontCss.includes('--font-table: 20px;')) {
  throw new Error('font settings CSS failed');
}
const html = JJK.mediaCard({
  imageUrl: 'https://www.shonenjump.com/j/test.png',
  pageUrl: 'https://www.shonenjump.com/j/source/',
  verification: 'official-page-direct-link',
  note: '確認済み'
}, { title: '公式画像', alt: '画像' });
for (const expected of ['loading="lazy"', 'decoding="async"', '公式ページ直リンク確認済み', '画像を公式URLで開く', '掲載元の公式ページ']) {
  if (!html.includes(expected)) throw new Error(`missing: ${expected}`);
}
const pending = JJK.mediaCard({ verification: 'pending-official-page-collection' }, { emptyText: '未収集' });
if (!pending.includes('未収集') || pending.includes('<img')) throw new Error('pending media rendered incorrectly');
const thumb = JJK.mediaThumb({
  imageUrl: 'https://www.shonenjump.com/j/test.png',
  pageUrl: 'https://www.shonenjump.com/j/source/',
  verification: 'official-page-direct-link'
}, { title: '公式画像', alt: '画像' });
for (const expected of ['class="media-thumb', 'data-official-media', 'media-status-dot good', 'target="_blank"']) {
  if (!thumb.includes(expected)) throw new Error(`compact media missing: ${expected}`);
}
if (typeof listeners.error !== 'function') throw new Error('image error fallback handler missing');
const original = [1, 2, 3];
const shuffled = JJK.shuffleCopy(original, () => 0);
if (original.join(',') !== '1,2,3') throw new Error('shuffleCopy mutated source');
if (shuffled.join(',') !== '2,3,1') throw new Error(`shuffleCopy result unexpected: ${shuffled}`);
console.log('PASS: core media and font settings');
