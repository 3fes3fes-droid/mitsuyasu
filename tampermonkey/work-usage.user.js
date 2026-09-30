// ==UserScript==
// @name         WORK使用状況 ドーナツグラフ
// @namespace    mitsuyasu-chatgpt-tools
// @version      2.3.1
// @description  ChatGPT右上にWork/Codex共有利用枠をデザイン付きドーナツグラフで表示。詳細はホバー。
// @updateURL    https://raw.githubusercontent.com/3fes3fes-droid/mitsuyasu/main/tampermonkey/work-usage.user.js
// @downloadURL  https://raw.githubusercontent.com/3fes3fes-droid/mitsuyasu/main/tampermonkey/work-usage.user.js
// @match        https://chatgpt.com/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(() => {
  'use strict';

  const ID = 'mitsuyasu-work-usage-chart';
  const REFRESH_MS = 5 * 60 * 1000;
  const TIME_ZONE = 'Asia/Tokyo';

  let root = null;
  let tokenCache = null;

  function parseReset(raw) {
    const n = Number(raw);
    if (Number.isFinite(n) && n > 0) {
      return new Date(n > 1e12 ? n : n * 1000);
    }
    const parsed = Date.parse(String(raw || ''));
    return Number.isFinite(parsed) ? new Date(parsed) : null;
  }

  function resetText(raw) {
    const d = parseReset(raw);
    if (!d) return '—';

    const p = new Intl.DateTimeFormat('ja-JP', {
      timeZone: TIME_ZONE,
      month: 'numeric',
      day: 'numeric',
      weekday: 'short',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).formatToParts(d);

    const v = Object.fromEntries(p.map(x => [x.type, x.value]));
    return `${v.month}/${v.day}(${v.weekday}) ${v.hour}:${v.minute}`;
  }

  function remainingPercent(used) {
    const n = Number(used);
    if (!Number.isFinite(n)) return null;
    return Math.max(0, Math.min(100, 100 - n));
  }

  function pctText(n) {
    if (!Number.isFinite(n)) return '—';
    return Number.isInteger(n) ? `${n}%` : `${n.toFixed(1)}%`;
  }

  function shortLabel(seconds, index) {
    const s = Number(seconds);
    if (Number.isFinite(s)) {
      if (s >= 4 * 3600 && s <= 6 * 3600) return '5h';
      if (s >= 6 * 86400 && s <= 8 * 86400) return '週';
    }
    return index === 0 ? '利用枠' : `利用枠${index + 1}`;
  }

  function palette(left) {
    if (!Number.isFinite(left)) {
      return {
        c1: '#91a0bd',
        c2: '#bbc4d8',
        glow: 'rgba(145,160,189,.30)'
      };
    }
    if (left <= 20) {
      return {
        c1: '#ff5d7d',
        c2: '#ff9a5a',
        glow: 'rgba(255,93,125,.34)'
      };
    }
    if (left <= 50) {
      return {
        c1: '#ffca55',
        c2: '#ff8a59',
        glow: 'rgba(255,188,69,.32)'
      };
    }
    return {
      c1: '#4ce0cf',
      c2: '#5b7cff',
      glow: 'rgba(76,224,207,.32)'
    };
  }

  function extractWindows(data) {
    const rate = data?.rate_limit;
    if (!rate || typeof rate !== 'object') return [];

    return Object.entries(rate)
      .filter(([key, value]) =>
        /window$/i.test(key) &&
        value &&
        typeof value === 'object'
      )
      .map(([key, w]) => {
        const seconds = Number(
          w.limit_window_seconds ??
          w.window_seconds ??
          w.limit_window ??
          0
        );

        let resetAt = w.reset_at;
        if (!resetAt && Number.isFinite(Number(w.reset_after_seconds))) {
          resetAt = Date.now() / 1000 + Number(w.reset_after_seconds);
        }

        return {
          seconds,
          usedPercent: Number(w.used_percent),
          resetAt,
        };
      })
      .filter(w => Number.isFinite(w.usedPercent) || w.resetAt)
      .sort((a, b) => (a.seconds || Infinity) - (b.seconds || Infinity));
  }

  async function getToken(force = false) {
    if (!force && tokenCache) return tokenCache;

    const boot = document.getElementById('client-bootstrap')?.textContent || '';
    const jwt = boot.match(/eyJ[\w-]*\.[\w-]+\.[\w-]+/g);

    if (jwt?.[0]) {
      tokenCache = jwt[0];
      return tokenCache;
    }

    const res = await fetch('/api/auth/session', {
      credentials: 'include',
      cache: 'no-store',
    });

    const session = await res.json();
    tokenCache = session?.accessToken || session?.access_token || null;
    return tokenCache;
  }

  async function fetchUsage(forceToken = false) {
    const token = await getToken(forceToken);
    if (!token) throw new Error('取得失敗');

    const headers = {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    };

    const paths = [
      '/backend-api/wham/usage',
      '/backend-api/codex/usage',
    ];

    for (const path of paths) {
      const res = await fetch(path, {
        method: 'GET',
        headers,
        credentials: 'include',
        cache: 'no-store',
      });

      if (res.status === 401 && !forceToken) {
        tokenCache = null;
        return fetchUsage(true);
      }

      if (res.ok) return await res.json();
    }

    throw new Error('取得失敗');
  }

  function mount() {
    if (document.getElementById(ID)) return;

    const host = document.createElement('div');
    host.id = ID;
    document.body.appendChild(host);

    root = host.attachShadow({ mode: 'open' });

    root.innerHTML = `
      <style>
        #wrap {
          position: fixed;
          top: 66px;
          right: 4px;
          z-index: 2147483647;
          display: flex;
          align-items: center;
          gap: 7px;
          user-select: none;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                       "Noto Sans JP", sans-serif;
        }

        #body {
          display: flex;
          gap: 7px;
          align-items: center;
        }

        .gauge-wrap {
          position: relative;
          width: 82px;
          height: 82px;
          isolation: isolate;
        }

        .gauge {
          --p: 0;
          --c1: #4ce0cf;
          --c2: #5b7cff;
          --glow: rgba(76,224,207,.32);

          position: relative;
          width: 82px;
          height: 82px;
          border-radius: 50%;
          cursor: pointer;

          background:
            conic-gradient(
              from -90deg,
              var(--c1) 0%,
              var(--c2) calc(var(--p) * 1%),
              rgba(138,151,183,.20) calc(var(--p) * 1%),
              rgba(138,151,183,.20) 100%
            );

          -webkit-mask:
            radial-gradient(circle, transparent 0 54%, #000 55% 72%, transparent 73% 100%);
          mask:
            radial-gradient(circle, transparent 0 54%, #000 55% 72%, transparent 73% 100%);

          filter: drop-shadow(0 3px 8px rgba(67,83,124,.16));
          transition: transform .14s ease, filter .14s ease;
        }

        .gauge-wrap::before {
          content: "";
          position: absolute;
          inset: 3px;
          border-radius: 50%;
          pointer-events: none;

          background:
            repeating-conic-gradient(
              from -90deg,
              rgba(153,168,202,.26) 0deg 1.2deg,
              transparent 1.2deg 12deg
            );

          -webkit-mask:
            radial-gradient(circle, transparent 0 76%, #000 77% 80%, transparent 81% 100%);
          mask:
            radial-gradient(circle, transparent 0 76%, #000 77% 80%, transparent 81% 100%);
        }

        .gauge-wrap::after {
          content: "";
          position: absolute;
          inset: 17px;
          border-radius: 50%;
          pointer-events: none;
          border: 1px solid rgba(135,151,188,.16);
          box-shadow:
            inset 0 0 12px rgba(120,141,190,.08),
            0 0 10px rgba(105,128,180,.06);
        }

        .gauge-wrap:hover .gauge {
          transform: scale(1.055);
          filter:
            drop-shadow(0 4px 10px rgba(67,83,124,.20))
            drop-shadow(0 0 9px var(--glow));
        }

        .dot {
          position: absolute;
          left: 50%;
          top: 50%;
          width: 8px;
          height: 8px;
          margin: -4px;
          border-radius: 50%;
          background: var(--dot-color);
          transform:
            rotate(calc(-90deg + var(--angle)))
            translateY(-29px);
          transform-origin: center 29px;
          box-shadow:
            0 0 0 2px rgba(255,255,255,.82),
            0 0 8px var(--dot-glow);
          pointer-events: none;
          z-index: 2;
        }

        .tooltip {
          position: absolute;
          top: 91px;
          right: 0;
          z-index: 30;

          visibility: hidden;
          opacity: 0;
          transform: translateY(-3px);
          pointer-events: none;

          white-space: nowrap;
          padding: 11px 14px;
          border-radius: 11px;

          background:
            linear-gradient(
              135deg,
              rgba(62,73,108,.97),
              rgba(86,97,136,.97)
            );

          color: #fff;
          border: 1px solid rgba(191,205,240,.28);
          box-shadow:
            0 8px 24px rgba(58,68,103,.24),
            inset 0 1px 0 rgba(255,255,255,.12);

          font-size: 24px;
          font-weight: 700;
          line-height: 1.08;
          letter-spacing: -.2px;
          font-variant-numeric: tabular-nums;

          transition:
            opacity .10s ease,
            transform .10s ease;
        }

        .tooltip::before {
          content: "";
          display: inline-block;
          width: 7px;
          height: 24px;
          margin-right: 10px;
          vertical-align: -3px;
          border-radius: 99px;
          background: linear-gradient(180deg, var(--tip1), var(--tip2));
        }

        .gauge-wrap:hover .tooltip {
          visibility: visible;
          opacity: 1;
          transform: translateY(0);
        }

        .error {
          padding: 8px 10px;
          border-radius: 9px;
          background: rgba(232,237,248,.92);
          color: #36415f;
          font-size: 11px;
          border: 1px solid rgba(130,146,182,.18);
        }

        @media (prefers-color-scheme: light) {
          .tooltip {
            background:
              linear-gradient(
                135deg,
                rgba(244,247,255,.98),
                rgba(224,232,250,.98)
              );
            color: #26314c;
            border-color: rgba(93,112,158,.18);
            box-shadow: 0 8px 24px rgba(79,98,143,.18);
          }
        }
      </style>

      <div id="wrap">
        <div id="body"><div class="error">取得中…</div></div>
      </div>
    `;
  }

  function render(data) {
    const windows = extractWindows(data);
    const body = root.getElementById('body');

    if (!windows.length) {
      body.innerHTML = '<div class="error">利用枠なし</div>';
      return;
    }

    body.innerHTML = windows.map((w, i) => {
      const left = remainingPercent(w.usedPercent);
      const c = palette(left);
      const label = shortLabel(w.seconds, i);
      const reset = resetText(w.resetAt);
      const angle = Number.isFinite(left) ? `${left * 3.6}deg` : '0deg';

      return `
        <div
          class="gauge-wrap"
          style="
            --dot-color:${c.c2};
            --dot-glow:${c.glow};
            --tip1:${c.c1};
            --tip2:${c.c2};
          "
        >
          <div
            class="gauge"
            style="
              --p:${Number.isFinite(left) ? left : 0};
              --c1:${c.c1};
              --c2:${c.c2};
              --glow:${c.glow};
            "
            data-refresh="1"
            aria-label="${label} ${pctText(left)} リセット ${reset}"
            title=""
          ></div>

          <span
            class="dot"
            style="--angle:${angle};"
          ></span>

          <div class="tooltip">${label}　${pctText(left)}　${reset}</div>
        </div>
      `;
    }).join('');

    body.querySelectorAll('[data-refresh="1"]').forEach(el => {
      el.addEventListener('click', refresh);
    });
  }

  async function refresh() {
    if (!root) return;

    try {
      const data = await fetchUsage();
      render(data);
    } catch {
      root.getElementById('body').innerHTML =
        '<div class="error">取得失敗</div>';
    }
  }

  function ensureMounted() {
    if (!document.body) return;

    if (!document.getElementById(ID)) {
      mount();
      refresh();
    }
  }

  ensureMounted();

  const observer = new MutationObserver(() => {
    if (!document.getElementById(ID)) ensureMounted();
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true
  });

  setInterval(refresh, REFRESH_MS);

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refresh();
  });
})();