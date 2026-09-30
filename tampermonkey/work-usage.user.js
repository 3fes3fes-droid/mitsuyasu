// ==UserScript==
// @name         WORK使用状況 ドーナツグラフ
// @namespace    mitsuyasu-chatgpt-tools
// @version      2.3.2
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
    if (Number.isFinite(n) && n > 0) return new Date(n > 1e12 ? n : n * 1000);
    const parsed = Date.parse(String(raw || ''));
    return Number.isFinite(parsed) ? new Date(parsed) : null;
  }

  function resetText(raw) {
    const d = parseReset(raw);
    if (!d) return '—';
    const p = new Intl.DateTimeFormat('ja-JP', {timeZone: TIME_ZONE, month:'numeric', day:'numeric', weekday:'short', hour:'2-digit', minute:'2-digit', hour12:false}).formatToParts(d);
    const v = Object.fromEntries(p.map(x=>[x.type,x.value]));
    return `${v.month}/${v.day}(${v.weekday}) ${v.hour}:${v.minute}`;
  }

  function remainingPercent(used) {
    const n = Number(used);
    return Number.isFinite(n) ? Math.max(0, Math.min(100,100-n)) : null;
  }

  function pctText(n){return Number.isFinite(n) ? (Number.isInteger(n)?`${n}%`:`${n.toFixed(1)}%`) : '—';}
  function shortLabel(seconds,index){const s=Number(seconds); if(s>=4*3600&&s<=6*3600)return '5h'; if(s>=6*86400&&s<=8*86400)return '週'; return index===0?'利用枠':`利用枠${index+1}`;}

  function extractWindows(data){
    const rate=data?.rate_limit; if(!rate||typeof rate!=='object')return [];
    return Object.entries(rate).filter(([k,v])=>/window$/i.test(k)&&v&&typeof v==='object').map(([k,w])=>({seconds:Number(w.limit_window_seconds??w.window_seconds??w.limit_window??0),usedPercent:Number(w.used_percent),resetAt:w.reset_at||(Number.isFinite(Number(w.reset_after_seconds))?Date.now()/1000+Number(w.reset_after_seconds):null)})).filter(w=>Number.isFinite(w.usedPercent)||w.resetAt).sort((a,b)=>(a.seconds||Infinity)-(b.seconds||Infinity));
  }

  async function getToken(){
    const boot=document.getElementById('client-bootstrap')?.textContent||'';
    const jwt=boot.match(/eyJ[\w-]*\.[\w-]+\.[\w-]+/g);
    if(jwt?.[0])return jwt[0];
    const res=await fetch('/api/auth/session',{credentials:'include',cache:'no-store'}); const s=await res.json(); return s?.accessToken||s?.access_token;
  }

  async function fetchUsage(){
    const token=await getToken();
    for(const path of ['/backend-api/wham/usage','/backend-api/codex/usage']){
      const r=await fetch(path,{headers:{Authorization:`Bearer ${token}`,Accept:'application/json'},credentials:'include',cache:'no-store'});
      if(r.ok)return await r.json();
    }
    throw new Error();
  }

  function mount(){
    const host=document.createElement('div');host.id=ID;document.body.appendChild(host);root=host.attachShadow({mode:'open'});
    root.innerHTML=`<style>#wrap{position:fixed;top:66px;right:28px;z-index:2147483647} .gauge-wrap{position:relative;width:82px;height:82px}.gauge{width:82px;height:82px;border-radius:50%;background:conic-gradient(#4ce0cf 0 70%,rgba(138,151,183,.2) 70%);-webkit-mask:radial-gradient(circle,transparent 0 54%,#000 55% 72%,transparent 73%)}.tooltip{position:absolute;top:91px;right:0;padding:11px 14px;border-radius:11px;background:linear-gradient(135deg,rgba(48,58,92,.94),rgba(86,101,150,.94));color:#fff;font-size:24px;font-weight:700;visibility:hidden;opacity:0;white-space:nowrap}.gauge-wrap:hover .tooltip{visibility:visible;opacity:1}</style><div id="wrap"><div id="body"></div></div>`;
  }

  function render(data){
    const w=extractWindows(data)[0]; if(!w)return; const left=remainingPercent(w.usedPercent); root.getElementById('body').innerHTML=`<div class="gauge-wrap"><div class="gauge"></div><div class="tooltip">${shortLabel(w.seconds,0)}　${pctText(left)}　${resetText(w.resetAt)}</div></div>`;
  }
  async function refresh(){try{render(await fetchUsage())}catch{}}
  function start(){if(!document.getElementById(ID)){mount();refresh()}}
  start();setInterval(refresh,REFRESH_MS);
})();
