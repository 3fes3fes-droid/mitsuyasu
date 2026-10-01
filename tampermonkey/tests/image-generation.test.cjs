/**
 * Regression fixtures execute the real userscript (only its boot tail is omitted).
 * Run: node --test tampermonkey/tests/image-generation.test.cjs
 * Dependencies: jsdom; optional playwright plus Chromium for IG_TEST_BROWSER=1.
 * IG_TEST_SOURCE can point to the backed-up userscript for regression comparison.
 * No ChatGPT requests, generated-image requests, or real GM storage are used.
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { test, after } = require('node:test');

const sourcePath = process.env.IG_TEST_SOURCE || path.resolve(__dirname, '../image-generation.user.js');
const source = fs.readFileSync(sourcePath, 'utf8');
const bootMarker = "  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot";
assert(source.includes(bootMarker), 'The harness must find the production boot tail');
const BASE = 1_800_000_000_000;
const PROMPT = 'Generate exactly one fixture image, full frame.';

const exposedSource = source.slice(0, source.indexOf(bootMarker)) + `
  render = () => {};
  globalThis.__ig = {
    topLevelTurnElements, turnRole, turnText, turnKey, userTurnElements,
    assistantTurnElements, findExpectedUserTurn, assistantTurnsAfter,
    currentImageSource, isGeneratedImage, generatedImageElements, imageArtifactKey,
    artifactRecords, imageDecoded, generationSnapshot, createDomSignal,
    waitForGenerationComplete, completeCurrent, skipAfterSend, waitUntilNextAt,
    processCurrentItem, createAttempt, captureConversationUrl,
    normalizeState, normalizeAttempt, readState, readLogs, findStopButton,
    attemptCycleStart: typeof attemptCycleStart === 'function' ? attemptCycleStart : null,
    attemptCycleDeadline: typeof attemptCycleDeadline === 'function' ? attemptCycleDeadline : null,
    constants: {
      cycleMinutes: typeof CYCLE_MINUTES === 'number' ? CYCLE_MINUTES : null,
      stableMs: RESULT_COMPLETE_STABLE_MS,
      staleStopStableMs: typeof IMAGE_WITH_STOP_STABLE_MS === 'number' ? IMAGE_WITH_STOP_STABLE_MS : null,
    },
    seed(attemptOverrides = {}, stateOverrides = {}) {
      const attempt = {
        id: 'fixture-attempt', index: 0, stage: 'SENT', promptFormatVersion: 1,
        promptText: ${JSON.stringify(PROMPT)}, createdAt: ${BASE},
        clickCommittedAt: ${BASE}, sentAt: ${BASE},
        conversationUrl: 'https://chatgpt.com/c/fixture',
        sentPageInstanceId: PAGE_INSTANCE_ID, sentByVersion: SCRIPT_VERSION,
        baselineArtifactKeys: [], baselineTurnKeys: [], seenArtifactKeys: [], readyArtifactKeys: [],
        ...attemptOverrides,
      };
      stateCache = saveStateDirect({
        ...defaultState(), ownerTabId: TAB_ID, runToken: 'fixture-run',
        phase: PHASE.WAITING_RESULT, ownerHeartbeatAt: Date.now(), attempt,
        ...stateOverrides,
      });
      return stateCache.attempt;
    },
    save(state) { stateCache = saveStateDirect(state); return stateCache; },
    wake() { wakeSerial += 1; },
  };
})();`;

function fixtureRuntime() {
  const storage = new Map();
  const timers = new Map();
  const pendingStateLocks = new Set();
  if (navigator.locks?.request) {
    const realRequest = navigator.locks.request.bind(navigator.locks);
    navigator.locks.request = (name, ...args) => {
      const callback = args.at(-1);
      let entered;
      const scheduled = new Promise(resolve => { entered = resolve; });
      args[args.length - 1] = (...values) => { entered(); return callback(...values); };
      const operation = realRequest(name, ...args);
      pendingStateLocks.add(scheduled);
      scheduled.then(() => pendingStateLocks.delete(scheduled));
      operation.catch(() => entered());
      if (name.includes('state_lock')) {
        pendingStateLocks.add(operation);
        operation.then(() => pendingStateLocks.delete(operation), () => pendingStateLocks.delete(operation));
      }
      return operation;
    };
  }
  let now = 1_800_000_000_000;
  let serial = 0;
  Date.now = () => now;
  globalThis.GM_getValue = (key, fallback) => storage.has(key) ? storage.get(key) : fallback;
  globalThis.GM_setValue = (key, value) => storage.set(key, value);
  globalThis.GM_getTab = callback => callback({ imageGenerationTabIdV5: 'fixture-tab' });
  globalThis.GM_saveTab = () => {};
  globalThis.GM_addValueChangeListener = () => {};
  globalThis.GM_setClipboard = () => {};
  globalThis.setTimeout = (callback, delay = 0, ...args) => {
    const id = ++serial;
    timers.set(id, { at: now + Math.max(0, Number(delay) || 0), callback: () => callback(...args) });
    return id;
  };
  globalThis.clearTimeout = id => timers.delete(id);
  globalThis.setInterval = (callback, delay = 0) => {
    const id = ++serial;
    timers.set(id, { at: now + Math.max(1, delay), interval: Math.max(1, delay), callback });
    return id;
  };
  globalThis.clearInterval = id => timers.delete(id);
  const flush = async () => {
    for (let i = 0; i < 40; i++) {
      if (pendingStateLocks.size) await Promise.allSettled([...pendingStateLocks]);
      await Promise.resolve();
    }
  };
  globalThis.__clock = {
    get now() { return now; },
    async flush() { await flush(); },
    async advance(ms) {
      const target = now + ms;
      await flush();
      for (let count = 0; count < 100000; count++) {
        const entry = [...timers].filter(([, item]) => item.at <= target)
          .sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
        if (!entry) break;
        const [id, item] = entry;
        now = Math.max(now, item.at);
        timers.delete(id);
        if (item.interval) timers.set(id, { ...item, at: now + item.interval });
        item.callback();
        await flush();
        if (count === 99999) throw new Error('Fixture timer runaway');
      }
      now = target;
      await flush();
    },
    async jump(ms) {
      now += ms; // Simulate background throttling or a suspended tab: expired callbacks run on wake.
      await this.advance(0);
    },
  };
  globalThis.__imageState = (image, options = {}) => {
    const state = { complete: true, width: 1024, height: 1024, currentSrc: image.src, ...options };
    Object.defineProperties(image, {
      complete: { configurable: true, get: () => state.complete },
      naturalWidth: { configurable: true, get: () => state.width },
      naturalHeight: { configurable: true, get: () => state.height },
      currentSrc: { configurable: true, get: () => state.currentSrc },
    });
    image.decode = options.decode || (() => Promise.resolve());
    image.__state = state;
    return image;
  };
  globalThis.__track = (promise, name = '__result') => {
    globalThis[name] = { done: false };
    promise.then(
      value => { globalThis[name] = { done: true, ok: true, value, at: Date.now() }; },
      error => { globalThis[name] = { done: true, ok: false, error: String(error.message), name: error.name, at: Date.now() }; }
    );
  };
}

let sharedBrowser;
let sharedContext;
async function createHarness(html = modernMarkup()) {
  if (process.env.IG_TEST_BROWSER === '1') {
    if (!sharedBrowser) {
      const { chromium } = require('playwright');
      let launchOptions = { headless: true };
      if (process.env.IG_TEST_CHROMIUM_PATH) launchOptions.executablePath = process.env.IG_TEST_CHROMIUM_PATH;
      if (process.env.IG_TEST_CHROMIUM_PACKAGE === '1') {
        const module = require('@sparticuz/chromium');
        const bundled = module.default || module;
        launchOptions = { ...launchOptions, executablePath: process.env.IG_TEST_CHROMIUM_PATH || await bundled.executablePath(), args: bundled.args.filter(arg => arg !== '--single-process') };
      }
      sharedBrowser = await chromium.launch(launchOptions);
      sharedContext = await sharedBrowser.newContext();
    }
    const page = await sharedContext.newPage();
    await page.route('**/*', route => route.fulfill({ contentType: 'text/html', body: '<html><body></body></html>' }));
    await page.goto('https://chatgpt.com/c/fixture');
    await page.setContent(html);
    await page.evaluate(fixtureRuntime);
    await page.evaluate(exposedSource);
    return { evaluate: (fn, arg) => page.evaluate(fn, arg), close: () => page.close() };
  }
  const { JSDOM, VirtualConsole } = require('jsdom');
  const dom = new JSDOM(html, {
    url: 'https://chatgpt.com/c/fixture', runScripts: 'outside-only',
    pretendToBeVisual: true, virtualConsole: new VirtualConsole(),
  });
  const window = dom.window;
  // jsdom has no layout. Native selectors, node identity, and MutationObserver remain real.
  window.Element.prototype.getBoundingClientRect = function () {
    return this.closest('[hidden], [style*="display:none"], [style*="display: none"]')
      ? { x: 0, y: 0, width: 0, height: 0, top: 0, bottom: 0, left: 0, right: 0 }
      : { x: 0, y: 0, width: 500, height: 200, top: 0, bottom: 200, left: 0, right: 500 };
  };
  window.Element.prototype.getClientRects = function () {
    const rect = this.getBoundingClientRect();
    return rect.width ? [rect] : [];
  };
  window.HTMLElement.prototype.scrollIntoView = () => {};
  window.eval(`(${fixtureRuntime.toString()})();`);
  await window.eval(exposedSource);
  return {
    async evaluate(fn, arg) {
      window.__fixtureArg = arg;
      return window.eval(`(${fn.toString()})(globalThis.__fixtureArg)`);
    },
    close: () => window.close(),
  };
}
after(async () => { if (sharedBrowser) await sharedBrowser.close(); });

function modernMarkup(extra = '', stop = false) {
  return `<main>
    <section data-turn-key="u-current"><div data-user-message-bubble>${PROMPT}</div></section>
    <section data-turn-key="a-current"><h4 data-conversation-role="assistant">ChatGPT</h4>
      <div data-markdown-copy></div>${extra}</section>
    <form><div id="prompt-textarea" class="ProseMirror" role="textbox" contenteditable="true"> </div>
      ${stop ? '<button data-testid="stop-button" aria-label="Stop streaming">Stop</button>' : '<button data-testid="send-button">Send</button>'}
    </form></main>`;
}
const modernImage = '<div data-testid="generated-image-preview"><img id="result-image" src="blob:https://chatgpt.com/final-image"></div>';

async function useHarness(t, html) {
  const harness = await createHarness(html);
  t.after(() => harness.close());
  return harness;
}

test('new UI detects data-turn-key users and assistants with blob generated image', async t => {
  const h = await useHarness(t, modernMarkup(modernImage));
  const actual = await h.evaluate(prompt => {
    __imageState(document.querySelector('#result-image'));
    const attempt = __ig.seed();
    const snapshot = __ig.generationSnapshot(attempt, prompt);
    return { roles: __ig.topLevelTurnElements().map(__ig.turnRole), count: snapshot.records.size,
      user: Boolean(snapshot.expectedUserTurn), assistant: Boolean(snapshot.assistant) };
  }, PROMPT);
  assert.deepEqual(JSON.parse(JSON.stringify(actual)), { roles: ['user', 'assistant'], count: 1, user: true, assistant: true });
});

test('legacy conversation sections retain image detection', async t => {
  const h = await useHarness(t, `<main>
    <section data-testid="conversation-turn-0"><div data-message-author-role="user">${PROMPT}</div></section>
    <section data-testid="conversation-turn-1"><div data-message-author-role="assistant">
      <img id="result-image" src="/backend-api/estuary/content?id=file-legacy" alt="Generated image"></div></section></main>`);
  assert.equal(await h.evaluate(prompt => {
    __imageState(document.querySelector('#result-image'));
    return __ig.generationSnapshot(__ig.seed(), prompt).records.size;
  }, PROMPT), 1);
});

test('currentSrc from srcset is used even without matching src attribute', async t => {
  const h = await useHarness(t, modernMarkup('<div data-testid="generated-image-preview"><img id="result-image" srcset="https://example.oaiusercontent.com/full.png 2x"></div>'));
  const actual = await h.evaluate(prompt => {
    const image = __imageState(document.querySelector('#result-image'), { currentSrc: 'https://example.oaiusercontent.com/full.png' });
    return { src: __ig.currentImageSource(image), count: __ig.generationSnapshot(__ig.seed(), prompt).records.size };
  }, PROMPT);
  assert.equal(actual.src, 'https://example.oaiusercontent.com/full.png');
  assert.equal(actual.count, 1);
});

test('same logical turn across legacy and modern wrappers is counted once', async t => {
  const h = await useHarness(t, `<main><section data-turn-key="u-current"><div data-user-message-bubble>${PROMPT}</div></section>
    <section data-turn-key="a-current"><h4 data-conversation-role="assistant">ChatGPT</h4>${modernImage}</section>
    <section data-turn-key="a-current" data-testid="conversation-turn-1"><div data-message-author-role="assistant"></div></section></main>`);
  const result = await h.evaluate(prompt => {
    __imageState(document.querySelector('#result-image'));
    return { users: __ig.userTurnElements().length, assistants: __ig.assistantTurnElements().length,
      images: __ig.generationSnapshot(__ig.seed(), prompt).records.size };
  }, PROMPT);
  assert.equal(result.users, 1);
  assert.equal(result.assistants, 1);
  assert.equal(result.images, 1);
});

test('one keyed exchange can contain both user bubble and assistant image siblings', async t => {
  const h = await useHarness(t, `<main><section data-turn-key="exchange-1">
    <div data-user-message-bubble>${PROMPT}</div><h4 data-conversation-role="assistant">ChatGPT</h4>
    <div data-markdown-copy>Finished</div>${modernImage}</section></main>`);
  const result = await h.evaluate(prompt => {
    __imageState(document.querySelector('#result-image'));
    const snapshot = __ig.generationSnapshot(__ig.seed(), prompt);
    return { roles: __ig.topLevelTurnElements().map(__ig.turnRole), images: snapshot.records.size,
      userText: __ig.turnText(snapshot.expectedUserTurn) };
  }, PROMPT);
  assert.deepEqual(Array.from(result.roles), ['user', 'assistant']);
  assert.equal(result.images, 1);
  assert.equal(result.userText, PROMPT);
});

test('nested duplicate keyed wrappers do not lose or double-count either role', async t => {
  const h = await useHarness(t, `<main><section data-turn-key="exchange-1"><div data-turn-key="exchange-1">
    <div data-user-message-bubble>${PROMPT}</div><div data-message-author-role="assistant">
    <div data-markdown-copy>Finished</div>${modernImage}</div></div></section></main>`);
  assert.deepEqual(Array.from(await h.evaluate(() => __ig.topLevelTurnElements().map(__ig.turnRole))), ['user', 'assistant']);
});

test('assistant heading before reply is not mistaken for a completed answer', async t => {
  const h = await useHarness(t, `<main><section data-turn-key="exchange-1"><div data-user-message-bubble>${PROMPT}</div>
    <h4 data-conversation-role="assistant">ChatGPT</h4></section></main>`);
  assert.equal(await h.evaluate(() => __ig.assistantTurnElements().length), 0);
});

test('response scoping excludes prior images, uploads, and another subsequent user turn', async t => {
  const h = await useHarness(t, `<main>
    <section data-turn-key="a-old"><h4 data-conversation-role="assistant">ChatGPT</h4><div data-testid="generated-image-preview"><img id="old" src="blob:https://chatgpt.com/old"></div></section>
    <section data-turn-key="u-current"><div data-user-message-bubble>${PROMPT}</div><img id="upload" src="https://a.oaiusercontent.com/upload.png"></section>
    <section data-turn-key="a-current"><h4 data-conversation-role="assistant">ChatGPT</h4>${modernImage}</section>
    <section data-turn-key="u-next"><div data-user-message-bubble>Another request</div></section>
    <section data-turn-key="a-next"><h4 data-conversation-role="assistant">ChatGPT</h4><div data-testid="generated-image-preview"><img id="later" src="blob:https://chatgpt.com/later"></div></section>
    <form><img id="composer-upload" src="https://a.oaiusercontent.com/composer.png"></form></main>`);
  const ids = await h.evaluate(prompt => {
    document.querySelectorAll('img').forEach(img => __imageState(img));
    return [...__ig.generationSnapshot(__ig.seed(), prompt).records.values()].flat().map(img => img.id);
  }, PROMPT);
  assert.deepEqual(Array.from(ids), ['result-image']);
});

test('complete=true with broken dimensions is never accepted as decoded', async t => {
  const h = await useHarness(t, modernMarkup(modernImage));
  assert.equal(await h.evaluate(async () => {
    const image = __imageState(document.querySelector('#result-image'), { width: 0, height: 0 });
    return __ig.imageDecoded(image);
  }), false);
});

test('decode source changed while pending is rejected', async t => {
  const h = await useHarness(t, modernMarkup(modernImage));
  assert.equal(await h.evaluate(async () => {
    const image = __imageState(document.querySelector('#result-image'));
    image.decode = async () => { image.__state.currentSrc = 'blob:https://chatgpt.com/replacement'; };
    return __ig.imageDecoded(image);
  }), false);
});

test('load event wakes DOM watcher even when no attributes mutate', async t => {
  const h = await useHarness(t, modernMarkup(modernImage));
  const woke = await h.evaluate(async () => {
    const signal = __ig.createDomSignal();
    let woke = false;
    signal.wait(1000).then(() => { woke = true; });
    document.querySelector('img').dispatchEvent(new Event('load'));
    await __clock.flush();
    signal.disconnect();
    return woke;
  });
  assert.equal(woke, true);
});

test('pre-send baseline artifacts are excluded even inside current response', async t => {
  const h = await useHarness(t, modernMarkup(modernImage));
  assert.equal(await h.evaluate(prompt => {
    const image = __imageState(document.querySelector('#result-image'));
    const attempt = __ig.seed({ baselineArtifactKeys: [__ig.imageArtifactKey(image)] });
    return __ig.generationSnapshot(attempt, prompt).records.size;
  }, PROMPT), 0);
});

test('persisted ready artifact cannot turn a broken reloaded image into success', async t => {
  const h = await useHarness(t, modernMarkup(modernImage));
  const result = await h.evaluate(async prompt => {
    const image = __imageState(document.querySelector('#result-image'), { width: 0, height: 0 });
    const key = __ig.imageArtifactKey(image);
    __track(__ig.waitForGenerationComplete('fixture-run', __ig.seed({ readyArtifactKeys: [key], seenArtifactKeys: [key] }), prompt));
    await __clock.advance(300000);
    return __result;
  }, PROMPT);
  assert.equal(result.done, true);
  assert.equal(result.ok, false);
});

for (const arrivalSeconds of [90, 285]) {
  test(`image arriving at ${arrivalSeconds}s starts next item at 300s including detection and wait`, async t => {
    const h = await useHarness(t);
    const result = await h.evaluate(async ({ prompt, arrivalSeconds }) => {
      const attempt = __ig.seed();
      __track((async () => {
        await __ig.waitForGenerationComplete('fixture-run', attempt, prompt);
        const completed = await __ig.completeCurrent('fixture-run', attempt);
        await __ig.waitUntilNextAt('fixture-run');
        return completed;
      })());
      setTimeout(() => {
        document.querySelector('[data-turn-key="a-current"]').insertAdjacentHTML('beforeend', '<div data-testid="generated-image-preview"><img id="result-image" src="blob:https://chatgpt.com/final"></div>');
        __imageState(document.querySelector('#result-image'));
      }, arrivalSeconds * 1000);
      await __clock.advance(299000);
      const before = __result.done;
      await __clock.advance(1000);
      return { before, ...__result, state: __ig.readState() };
    }, { prompt: PROMPT, arrivalSeconds });
    assert.equal(result.before, false);
    assert.equal(result.ok, true, result.error);
    assert.equal(result.at, BASE + 300000);
    assert.equal(result.state.completedCount, 1);
    assert.equal(result.state.nextAt, BASE + 300000);
  });
}

test('stale stop button does not create eight-minute wait', async t => {
  const h = await useHarness(t, modernMarkup(modernImage, true));
  const result = await h.evaluate(async prompt => {
    __imageState(document.querySelector('#result-image'));
    __track(__ig.waitForGenerationComplete('fixture-run', __ig.seed(), prompt));
    await __clock.advance(16000);
    return __result;
  }, PROMPT);
  assert.equal(result.ok, true, result.error);
  assert(result.at <= BASE + 16000);
});

test('explicit image progress prevents preview completion despite decoded image', async t => {
  const h = await useHarness(t, modernMarkup(`<div data-testid="generated-image-preview" aria-busy="true">
    <div role="progressbar" aria-valuenow="50">Generating image 50%</div><img id="result-image" src="blob:https://chatgpt.com/preview"></div>`));
  const result = await h.evaluate(async prompt => {
    __imageState(document.querySelector('#result-image'));
    __track(__ig.waitForGenerationComplete('fixture-run', __ig.seed(), prompt));
    await __clock.advance(60000);
    const previewAccepted = __result.done;
    const preview = document.querySelector('[data-testid="generated-image-preview"]');
    preview.removeAttribute('aria-busy');
    preview.querySelector('[role="progressbar"]').remove();
    await __clock.advance(6000);
    return { previewAccepted, ...__result };
  }, PROMPT);
  assert.equal(result.previewAccepted, false);
  assert.equal(result.ok, true, result.error);
});

test('no image at deadline skips exactly once without extra cooldown minute', async t => {
  const h = await useHarness(t, modernMarkup('', true));
  const result = await h.evaluate(async prompt => {
    __track((async () => {
      try { await __ig.waitForGenerationComplete('fixture-run', __ig.seed(), prompt); }
      catch (error) { await __ig.skipAfterSend('fixture-run', error); }
      await __ig.waitUntilNextAt('fixture-run');
      return __ig.readState();
    })());
    await __clock.advance(300000);
    return __result;
  }, PROMPT);
  assert.equal(result.ok, true, result.error);
  assert.equal(result.at, BASE + 300000);
  assert.equal(result.value.skippedCount, 1);
  assert.equal(result.value.index, 1);
  assert.equal(result.value.completedCount, 0);
});

test('cached loaded image is checked immediately without waiting for load', async t => {
  const h = await useHarness(t, modernMarkup(modernImage));
  const result = await h.evaluate(async prompt => {
    __imageState(document.querySelector('#result-image'));
    __track(__ig.waitForGenerationComplete('fixture-run', __ig.seed(), prompt));
    await __clock.advance(6000);
    return __result;
  }, PROMPT);
  assert.equal(result.ok, true, result.error);
  assert(result.at <= BASE + 6000);
});

test('same image resource replaced during stability period must settle again', async t => {
  const h = await useHarness(t, modernMarkup('<div data-testid="generated-image-preview"><img id="result-image" src="/backend-api/estuary/content?id=same-id&version=1"></div>'));
  const result = await h.evaluate(async prompt => {
    const image = __imageState(document.querySelector('#result-image'));
    __track(__ig.waitForGenerationComplete('fixture-run', __ig.seed(), prompt));
    await __clock.advance(4000);
    image.src = '/backend-api/estuary/content?id=same-id&version=2';
    image.__state.currentSrc = image.src;
    image.__state.complete = false;
    image.__state.width = 0;
    image.__state.height = 0;
    await __clock.advance(2000);
    const premature = __result.done;
    image.__state.complete = true;
    image.__state.width = 1024;
    image.__state.height = 1024;
    image.dispatchEvent(new Event('load'));
    await __clock.advance(6000);
    return { premature, ...__result };
  }, PROMPT);
  assert.equal(result.premature, false);
  assert.equal(result.ok, true, result.error);
});

test('background suspension uses absolute deadline without adding new wait', async t => {
  const h = await useHarness(t, modernMarkup('', true));
  const result = await h.evaluate(async prompt => {
    __track(__ig.waitForGenerationComplete('fixture-run', __ig.seed(), prompt));
    await __clock.advance(90000);
    await __clock.jump(270000);
    return __result;
  }, PROMPT);
  assert.equal(result.done, true);
  assert.equal(result.ok, false);
  assert.equal(result.at, BASE + 360000);
});

test('reloaded SENT attempt keeps original click deadline and does not resend', async t => {
  const h = await useHarness(t, modernMarkup('', true));
  const result = await h.evaluate(async prompt => {
    const attempt = __ig.seed({ clickCommittedAt: Date.now() - 240000, sentAt: Date.now() - 239000 });
    __track(__ig.waitForGenerationComplete('fixture-run', attempt, prompt));
    await __clock.advance(59000);
    const before = __result.done;
    await __clock.advance(1000);
    return { before, ...__result, attempt: __ig.readState().attempt, logs: __ig.readLogs() };
  }, PROMPT);
  assert.equal(result.before, false);
  assert.equal(result.done, true);
  assert.equal(result.ok, false);
  assert.equal(result.at, BASE + 60000);
  assert.equal(result.attempt.stage, 'SENT');
  assert(!result.logs.some(log => log.code === 'SEND_CLICK' || log.code === 'SEND_CONFIRMED'));
});

test('deadline prioritizes click time and falls back through sent and created time', async t => {
  const h = await useHarness(t);
  const result = await h.evaluate(base => [
    __ig.attemptCycleDeadline({ clickCommittedAt: base, sentAt: base + 1000, createdAt: base - 5000 }),
    __ig.attemptCycleDeadline({ sentAt: base, createdAt: base - 5000 }),
    __ig.attemptCycleDeadline({ createdAt: base }),
  ], BASE);
  assert.deepEqual(Array.from(result), [BASE + 300000, BASE + 300000, BASE + 300000]);
});

test('native browser decodes a genuinely loaded cached image', { skip: process.env.IG_TEST_BROWSER !== '1' }, async t => {
  const h = await useHarness(t, modernMarkup('<div data-testid="generated-image-preview"><img id="actual-image"></div>'));
  const result = await h.evaluate(async prompt => {
    const image = document.querySelector('#actual-image');
    const loaded = new Promise((resolve, reject) => { image.onload = resolve; image.onerror = reject; });
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 256;
    canvas.getContext('2d').fillRect(0, 0, 256, 256);
    image.src = canvas.toDataURL('image/png');
    await loaded;
    const decoded = await __ig.imageDecoded(image);
    __track(__ig.waitForGenerationComplete('fixture-run', __ig.seed(), prompt));
    await __clock.advance(6000);
    return { decoded, width: image.naturalWidth, ...__result };
  }, PROMPT);
  assert.equal(result.decoded, true);
  assert.equal(result.width, 256);
  assert.equal(result.ok, true, result.error);
});

test('loaded one-pixel placeholder is not accepted as a completed generation', async t => {
  const h = await useHarness(t, modernMarkup(modernImage));
  assert.equal(await h.evaluate(async () => {
    const image = __imageState(document.querySelector('#result-image'), { width: 1, height: 1 });
    return __ig.imageDecoded(image);
  }), false);
});

test('hidden blurred responsive clone does not block visible final image', async t => {
  const h = await useHarness(t, modernMarkup(`<div data-testid="generated-image-preview" style="display:none; filter:blur(10px)">
    <img id="hidden-preview" src="/backend-api/estuary/content?id=shared"></div>
    <div data-testid="generated-image-preview"><img id="result-image" src="/backend-api/estuary/content?id=shared"></div>`));
  const result = await h.evaluate(async prompt => {
    __imageState(document.querySelector('#hidden-preview'), { width: 2048, height: 2048 });
    __imageState(document.querySelector('#result-image'));
    __track(__ig.waitForGenerationComplete('fixture-run', __ig.seed(), prompt));
    await __clock.advance(6000);
    return __result;
  }, PROMPT);
  assert.equal(result.ok, true, result.error);
});

test('navigation to unrelated conversation cannot rewrite stored target URL', async t => {
  const h = await useHarness(t, modernMarkup(modernImage));
  const result = await h.evaluate(async prompt => {
    const attempt = __ig.seed();
    __imageState(document.querySelector('#result-image'));
    history.replaceState({}, '', '/c/unrelated');
    await __ig.captureConversationUrl('fixture-run', attempt.id);
    const saved = __ig.readState().attempt;
    return { url: saved.conversationUrl, records: __ig.generationSnapshot(saved, prompt).records.size };
  }, PROMPT);
  assert.equal(result.url, 'https://chatgpt.com/c/fixture');
  assert.equal(result.records, 0);
});

test('two full processCurrentItem runs generate valid prompts and click only once each at five-minute cadence', async t => {
  const h = await useHarness(t, '<main></main>');
  const result = await h.evaluate(async () => {
    const sends = [];
    function installHome() {
      history.replaceState({}, '', '/');
      const main = document.querySelector('main');
      main.innerHTML = '<form><textarea id="prompt-textarea"></textarea><button type="button" data-testid="send-button">Send</button></form>';
      main.querySelector('button').addEventListener('click', () => {
        const composer = main.querySelector('textarea');
        const prompt = composer.value;
        sends.push({ at: Date.now(), prompt });
        const turn = document.createElement('section');
        turn.setAttribute('data-turn-key', 'exchange-' + sends.length);
        turn.innerHTML = '<div data-user-message-bubble></div><div data-markdown-copy></div>';
        turn.querySelector('[data-user-message-bubble]').textContent = prompt;
        main.prepend(turn);
        composer.value = '';
        history.replaceState({}, '', '/c/sent-' + sends.length);
        setTimeout(() => {
          const widget = document.createElement('div');
          widget.setAttribute('data-testid', 'generated-image-preview');
          const image = document.createElement('img');
          image.src = 'blob:https://chatgpt.com/output-' + sends.length;
          __imageState(image);
          widget.append(image);
          turn.append(widget);
        }, 90000);
      });
    }
    __ig.seed({}, { attempt: null });
    installHome();
    __track((async () => {
      const first = await __ig.processCurrentItem('fixture-run');
      await __ig.waitUntilNextAt('fixture-run');
      installHome(); // Fixture navigation to the clean page required for the next item.
      const second = await __ig.processCurrentItem('fixture-run');
      return { first, second, sends, state: __ig.readState(), logs: __ig.readLogs() };
    })());
    await __clock.advance(420000);
    return __result;
  });
  assert.equal(result.ok, true, result.error);
  assert.equal(result.value.sends.length, 2);
  assert.equal(result.value.state.completedCount, 2);
  assert.equal(result.value.state.index, 2);
  assert.equal(result.value.logs.filter(log => log.code === 'SEND_CLICK').length, 2);
  assert(result.value.sends.every(send => send.prompt.includes('場所の説明：') && send.prompt.includes('夏服')));
  const cadence = result.value.sends[1].at - result.value.sends[0].at;
  assert(cadence >= 300000 && cadence < 302000, `unexpected cadence ${cadence}ms`);
});
