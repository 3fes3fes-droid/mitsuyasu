'use strict';

const assert = require('assert');
const path = require('path');
const { JSDOM, ResourceLoader, VirtualConsole } = require('jsdom');


const ROOT = path.resolve(__dirname, '..');


class LocalOnlyLoader extends ResourceLoader {
  fetch(url, options) {
    if (/^https?:/i.test(url)) return null;
    return super.fetch(url, options);
  }
}


function fileUrl(filename, query = '') {
  return `file://${path.join(ROOT, filename)}${query}`;
}


async function waitFor(test, label, timeout = 5000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const value = test();
    if (value) return value;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error(`timeout: ${label}`);
}


async function openPage(filename, query = '') {
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', (error) => errors.push(error));
  virtualConsole.on('error', (message) => errors.push(new Error(String(message))));
  const dom = await JSDOM.fromFile(path.join(ROOT, filename), {
    url: fileUrl(filename, query),
    runScripts: 'dangerously',
    resources: new LocalOnlyLoader(),
    pretendToBeVisual: true,
    virtualConsole,
    beforeParse(window) {
      window.HTMLElement.prototype.scrollIntoView = function scrollIntoView() {};
    },
  });
  await waitFor(
    () => dom.window.document.readyState === 'complete',
    `${filename} load`
  );
  await waitFor(
    () => dom.window.document.querySelector('.font-tuner-launch'),
    `${filename} font tuner`
  );
  const fatal = errors.filter((error) => !/Could not load link/i.test(error.message));
  assert.deepStrictEqual(fatal.map((error) => error.message), [], `${filename} runtime errors`);
  return dom;
}


function checkFontTuner(document) {
  const launch = document.querySelector('.font-tuner-launch');
  launch.click();
  const panel = document.querySelector('#font-tuner-panel');
  assert.strictEqual(panel.hidden, false);
  assert.strictEqual(panel.querySelectorAll('input[type="range"]').length, 10);
}


async function checkRecordPage(filename, expectedRows) {
  const dom = await openPage(filename);
  const { document } = dom.window;
  await waitFor(() => document.querySelector('.record-view'), `${filename} record`);
  assert.strictEqual(document.querySelectorAll('#item-list button[data-id]').length, expectedRows);
  const tabs = [...document.querySelectorAll('.record-tab')];
  const panels = [...document.querySelectorAll('.tab-panel')];
  assert.strictEqual(tabs.length, panels.length);
  assert.strictEqual(panels.filter((panel) => !panel.hidden).length, 1);
  if (tabs.length > 1) {
    tabs[1].click();
    assert.strictEqual(panels.filter((panel) => !panel.hidden).length, 1);
    assert.strictEqual(panels.find((panel) => !panel.hidden).dataset.tabPanel, tabs[1].dataset.tab);
  }
  checkFontTuner(document);
  dom.window.close();
}


async function checkChapterHighlights() {
  const dom = await openPage('chapters.html', '?id=ch-002');
  const { document } = dom.window;
  await waitFor(() => document.querySelector('.record-view'), 'chapter detail');
  const highlightTab = document.querySelector('[data-tab="highlights"]');
  highlightTab.click();
  const panel = document.querySelector('[data-tab-panel="highlights"]');
  assert.strictEqual(panel.hidden, false);
  assert.strictEqual(panel.querySelectorAll('.highlight-stats span').length, 4);
  assert(panel.querySelector('.highlight-quote').textContent.includes('僕 最強だから'));
  assert(panel.querySelectorAll('.line-gist').length >= 2);
  assert(panel.querySelectorAll('.compact-event-list li').length >= 2);
  assert(panel.querySelectorAll('.event-matrix li').length >= 3);
  assert(panel.querySelectorAll('.highlight-keyword').length >= 2);
  assert(panel.textContent.includes('死なせたくない'));

  const chapter89 = document.querySelector('#item-list button[data-id="ch-089"]');
  chapter89.click();
  await waitFor(
    () => document.querySelector('.record-title')?.textContent.includes('第89話'),
    'chapter 89 detail'
  );
  document.querySelector('[data-tab="highlights"]').click();
  assert(document.querySelector('[data-tab-panel="highlights"]').textContent.includes('0.2秒の領域展開'));

  const chapter148 = document.querySelector('#item-list button[data-id="ch-148"]');
  chapter148.click();
  await waitFor(
    () => document.querySelector('.record-title')?.textContent.includes('第148話'),
    'chapter 148 detail'
  );
  document.querySelector('[data-tab="highlights"]').click();
  const verified = document.querySelector('.verified-line-section');
  assert(verified, 'crosschecked line section missing');
  assert.strictEqual(verified.querySelectorAll(':scope > .verified-line-grid .verified-line-card').length, 6);
  assert(verified.querySelector('.verified-line-more'));
  assert(verified.textContent.includes('複数記事照合'));
  assert(verified.textContent.includes('答えろやカス'));
  document.querySelector('[data-tab="sources"]').click();
  const sourcePanel = document.querySelector('[data-tab-panel="sources"]');
  assert(sourcePanel.textContent.includes('短文照合に使った各話記事'));
  assert(sourcePanel.querySelectorAll('.source-subtitle + .links a').length >= 2);
  dom.window.close();
}


async function checkAggregatePages() {
  const sources = await openPage('sources.html');
  await waitFor(
    () => sources.window.document.querySelectorAll('#source-body tr').length === 92,
    'source rows'
  );
  assert.strictEqual(sources.window.document.querySelector('#result-count').textContent, '92 / 92件');
  checkFontTuner(sources.window.document);
  sources.window.close();

  const status = await openPage('status.html');
  await waitFor(
    () => status.window.document.querySelector('#status-body')?.textContent.includes('2,109'),
    'status highlight counts'
  );
  const statusText = status.window.document.querySelector('#status-body').textContent;
  for (const expected of ['2,109件', '1,221件', '972件', '62件', '2,738件', '275 / 275', '128 / 275']) {
    assert(statusText.includes(expected), `status missing ${expected}`);
  }
  checkFontTuner(status.window.document);
  status.window.close();
}


async function main() {
  await checkChapterHighlights();
  for (const [filename, rows] of [
    ['volumes.html', 31],
    ['characters.html', 189],
    ['techniques.html', 179],
    ['terms.html', 173],
    ['supplements.html', 4],
  ]) {
    await checkRecordPage(filename, rows);
  }
  await checkAggregatePages();
  console.log('PASS: 8 content pages, source-crosschecked lines, compact folds, tabs, font tuner, and aggregate counts');
}


main().catch((error) => {
  console.error(error.stack || error);
  process.exit(1);
});
