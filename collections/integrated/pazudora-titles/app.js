const q = document.getElementById('q');
const cat = document.getElementById('cat');
const tier = document.getElementById('tier');
const availabilitySelect = document.getElementById('availability');
const sortSelect = document.getElementById('sort');
const body = document.getElementById('body');
const count = document.getElementById('count');
const viewer = document.getElementById('viewer');
const byId = new Map(DATA.map(item => [item.no, item]));
const esc = value => String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const normalize = value => String(value).normalize('NFKC').toLowerCase();
const external = (url, label) => url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>` : '';

for (const [select, key] of [[cat,'category'],[tier,'tier']]) {
  for (const value of [...new Set(DATA.map(item => item[key]))].sort((a,b) => a.localeCompare(b,'ja'))) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
}

function availability(item, now = Date.now()) {
  if (item.persistent) return {key:'persistent', label:'継続条件', period:null};
  const periods = [...item.periods].sort((a,b) => (b.end || b.endDate).localeCompare(a.end || a.endDate));
  const active = periods.find(period => period.start && period.end && Date.parse(period.start) <= now && now <= Date.parse(period.end));
  if (active) return {key:'active', label:'開催中', period:active};
  const upcoming = periods.filter(period => period.start && Date.parse(period.start) > now).sort((a,b) => a.start.localeCompare(b.start))[0];
  if (upcoming) return {key:'upcoming', label:'開催予定', period:upcoming};
  if (periods.length) return {key:'historical', label:'掲載回終了', period:periods[0]};
  if (['公認','P','声優','原市','むらい','5000日','プロ','王者','優勝','全一','強運','最速'].includes(item.name)) return {key:'special', label:'認定・大会等', period:null};
  return {key:'limited', label:'期間限定', period:null};
}

function tierClass(value) {
  if (value.includes('簡単')) return 'tier-easy';
  if (value.includes('高難度') || value.includes('降臨')) return 'tier-hard';
  if (value.includes('固定')) return 'tier-fixed';
  if (value.includes('TA')) return 'tier-ta';
  if (value.includes('対戦') || value.includes('達成') || value.includes('ランダン')) return 'tier-comp';
  return 'tier-limit';
}

function history(item) {
  const periods = item.periods.map(period => `<li><span class="history-label">${esc(period.label)}</span><span>${esc(period.range)}</span>${external(period.url,'告知')}</li>`).join('');
  const rules = item.rules.length ? `<p><strong>形式</strong> ${esc(item.rules.join(' / '))}</p>` : '';
  const notes = item.notes.map(note => `<p>${esc(note)}</p>`).join('');
  if (!periods && !rules && !notes) return '';
  return `<details class="detail"><summary>形式・補足${periods ? '・開催履歴' : ''}</summary><div>${rules}${notes}${periods ? `<ul class="history">${periods}</ul>` : ''}</div></details>`;
}

function render() {
  const needle = normalize(q.value.trim());
  const now = Date.now();
  const filtered = DATA.filter(item => {
    const state = availability(item, now);
    const hay = normalize([item.name,item.category,item.tier,item.event,item.method,item.time,...item.rules,...item.notes,...item.periods.map(period => period.range)].join(' '));
    return (!needle || hay.includes(needle)) && (!cat.value || item.category === cat.value) && (!tier.value || item.tier === tier.value) && (!availabilitySelect.value || state.key === availabilitySelect.value);
  });
  if (sortSelect.value === 'difficulty') filtered.sort((a,b) => a.sort-b.sort || a.order-b.order);
  else if (sortSelect.value === 'latest') filtered.sort((a,b) => b.order-a.order);
  else if (sortSelect.value === 'list') filtered.sort((a,b) => a.order-b.order);
  else filtered.sort((a,b) => a.name.localeCompare(b.name,'ja'));
  body.innerHTML = filtered.length ? filtered.map(item => {
    const state = availability(item, now);
    return `<tr id="title-${item.no}">
      <td class="num">${item.no}</td>
      <td><div class="identity"><button class="image-button" type="button" data-title="${item.no}" aria-label="${esc(item.name)}の称号画像を拡大"><img src="${esc(item.image)}" alt="${esc(item.name)}の実際の称号画像" width="96" height="56" loading="lazy" decoding="async"></button><div><span class="name">${esc(item.name)}</span><span class="event">${esc(item.event)}</span></div></div></td>
      <td><span class="badge">${esc(item.category)}</span><span class="state state-${state.key}">${state.label}</span></td>
      <td><span class="badge ${tierClass(item.tier)}">${esc(item.tier)}</span></td>
      <td class="time">${esc(item.time)}</td>
      <td class="method"><p>${esc(item.method)}</p>${history(item)}</td>
      <td><div class="links">${external(item.official,'公式告知')}${external(item.guide,'入手・攻略')}${external(item.imageSource,'画像元')}</div></td>
    </tr>`;
  }).join('') : '<tr><td colspan="7" class="empty">該当する称号がありません。検索語や絞り込みを変更してください。</td></tr>';
  count.textContent = `${filtered.length} / ${DATA.length}件`;
}

function renderCurrent() {
  const now = Date.now();
  const current = DATA.map(item => ({item,state:availability(item,now)})).filter(({state}) => state.key === 'active' || state.key === 'upcoming');
  current.sort((a,b) => (a.state.key === 'active' ? 0 : 1)-(b.state.key === 'active' ? 0 : 1) || (a.state.period.end || a.state.period.endDate).localeCompare(b.state.period.end || b.state.period.endDate));
  document.getElementById('current').innerHTML = current.length ? current.map(({item,state}) => `<button type="button" class="current-title" data-find="${item.no}"><img src="${esc(item.image)}" alt="" width="96" height="56"><span><strong>${esc(item.name)}</strong><span class="state state-${state.key}">${state.label}</span><small>${esc(state.period.range)}</small></span></button>`).join('') : '<p class="muted">掲載した開催回の中に、開催中・開催予定のイベントはありません。</p>';
  document.getElementById('overview').textContent = `実画像 ${TITLE_META.imageCount}種 · 開催履歴 ${TITLE_META.historyCount}種 · 確認 ${TITLE_META.checkedAt}（日本時間）`;
}

function openViewer(id) {
  const item = byId.get(Number(id));
  if (!item) return;
  document.getElementById('viewer-name').textContent = item.name;
  const image = document.getElementById('viewer-image');
  image.src = item.image;
  image.alt = item.name + 'の実際の称号画像';
  document.getElementById('viewer-method').textContent = item.method;
  document.getElementById('viewer-event').textContent = item.event;
  document.getElementById('viewer-info').innerHTML = history(item);
  document.getElementById('viewer-links').innerHTML = external(item.official,'公式告知') + external(item.guide,'入手・攻略') + external(item.imageSource,'画像元');
  viewer.showModal();
}

body.addEventListener('click', event => {
  const button = event.target.closest('[data-title]');
  if (button) openViewer(button.dataset.title);
});
document.getElementById('current').addEventListener('click', event => {
  const button = event.target.closest('[data-find]');
  if (!button) return;
  const item = byId.get(Number(button.dataset.find));
  q.value = item.name;cat.value = '';tier.value = '';availabilitySelect.value = '';
  render();
  document.getElementById('tablebox').scrollTop = 0;
  q.focus();
});
document.getElementById('reset').addEventListener('click', () => {
  q.value = '';cat.value = '';tier.value = '';availabilitySelect.value = '';sortSelect.value = 'difficulty';render();
});
viewer.addEventListener('click', event => { if (event.target === viewer) viewer.close(); });
for (const element of [q,cat,tier,availabilitySelect,sortSelect]) element.addEventListener(element === q ? 'input' : 'change',render);
window.addEventListener('pageshow', () => {renderCurrent();render();});
renderCurrent();
render();
