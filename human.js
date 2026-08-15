const REPO='3fes3fes-droid/mitsuyasu';
const BRANCH='main';
const BASE_FILE='birthday_db.json';
const CHANGES_FILE='birthday_db_changes.json';
const API='https://api.github.com/repos/'+REPO+'/contents/';
const PAGE_SIZE=120;
const PENDING_KEY='human_pending_changes_v2';
const TOKEN_KEY='human_github_token_v1';

let basePeople=[];
let remoteChanges={version:1,base:BASE_FILE,updatedAt:null,upserts:[],deletes:[]};
let remoteChangesSha='';
let pending={upserts:[],deletes:[]};
let savedPeople=[];
let remoteResults=[];
let bulkResults=[];
let sortMode='random';
let randomSalt=Math.random().toString(36).slice(2);
let visibleCount=PAGE_SIZE;
let abortCtrl=null;

const $=id=>document.getElementById(id);
const iconEdit='<svg viewBox="0 0 24 24"><path d="m4 20 4.5-1 10-10-3.5-3.5-10 10L4 20Z"/><path d="m13.5 6.5 3.5 3.5"/></svg>';
const iconTrash='<svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13"/></svg>';

function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function norm(s){return String(s??'').toLowerCase().normalize('NFKC').replace(/[\s・･＝=,，、.。'’"“”\-ー_]/g,'')}
function parseBirthday(s){
  s=String(s??'').trim().replace(/[\/.年月]/g,'-').replace(/日/g,'').replace(/\s/g,'');
  if(/^\d{8}$/.test(s))return s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6);
  const m=s.match(/^(\d{1,4})-(\d{1,2})-(\d{1,2})$/);
  return m?m[1].padStart(4,'0')+'-'+m[2].padStart(2,'0')+'-'+m[3].padStart(2,'0'):s;
}
function ageOf(bd){
  if(!bd)return null; const p=bd.split('-').map(Number); if(p.length<3||!p[0])return null;
  const t=new Date(); let a=t.getFullYear()-p[0]; if((t.getMonth()+1<p[1])||(t.getMonth()+1===p[1]&&t.getDate()<p[2]))a--;
  return a>=0&&a<130?a:null;
}
function bdayText(bd){if(!bd)return ''; const p=bd.split('-'); return p.length===3?`${p[0]}/${+p[1]}/${+p[2]}`:bd}
function toast(msg,type='ok'){const n=$('notice');n.textContent=msg;n.className='notice show '+type;clearTimeout(n._t);n._t=setTimeout(()=>n.className='notice',2600)}
function clone(v){return JSON.parse(JSON.stringify(v))}
function uniqueIds(arr){const m=new Map();for(const x of arr||[])if(x&&x.id)m.set(x.id,x);return [...m.values()]}
function normalizeChanges(ch){
  return {version:1,base:BASE_FILE,updatedAt:ch?.updatedAt||null,upserts:uniqueIds(ch?.upserts||[]),deletes:[...new Set((ch?.deletes||[]).filter(Boolean))]};
}
function applyChanges(base,ch){
  const m=new Map((base||[]).filter(x=>x?.id).map(x=>[x.id,clone(x)]));
  for(const id of ch.deletes||[])m.delete(id);
  for(const p of ch.upserts||[])if(p?.id)m.set(p.id,clone(p));
  return [...m.values()];
}
function compose(){
  savedPeople=applyChanges(applyChanges(basePeople,remoteChanges),pending);
  updateHeader();
  renderLocal(true);
}
function pendingCount(){return pending.upserts.length+pending.deletes.length}
function savePending(){localStorage.setItem(PENDING_KEY,JSON.stringify(pending));updateHeader()}
function touchUpsert(p){
  pending.deletes=pending.deletes.filter(id=>id!==p.id);
  pending.upserts=pending.upserts.filter(x=>x.id!==p.id);
  pending.upserts.push(clone(p));savePending();
}
function touchDelete(id){
  pending.upserts=pending.upserts.filter(x=>x.id!==id);
  if(!pending.deletes.includes(id))pending.deletes.push(id);
  savePending();
}
function updateHeader(){
  const dirty=pendingCount();
  $('headerStats').textContent=`${savedPeople.length.toLocaleString()}人`;
  $('syncLabel').textContent=dirty?`未同期 ${dirty}`:'同期';
  $('syncBtn').classList.toggle('dirty',dirty>0);
  const st=[];
  if(dirty)st.push(`<span class="pill warn">未同期 ${dirty}</span>`); else st.push(`<span class="pill ok">GitHub同期済み</span>`);
  if($('omniInput').value.trim()||hasFilters())st.push(`<span class="pill">${getLocalMatches().length}件</span>`);
  $('status').innerHTML=st.join('');
}
async function fetchJsonFile(path,auth=false){
  const headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};
  const token=sessionStorage.getItem(TOKEN_KEY); if(auth&&token)headers.Authorization='Bearer '+token;
  const r=await fetch(API+encodeURIComponent(path)+'?ref='+encodeURIComponent(BRANCH),{headers,cache:'no-store'});
  if(r.status===404)return {data:null,sha:''};
  if(!r.ok)throw new Error('GitHub '+r.status);
  const j=await r.json();
  const text=decodeURIComponent(escape(atob(j.content.replace(/\n/g,''))));
  return {data:JSON.parse(text),sha:j.sha};
}
async function init(){
  try{
    const [b,c]=await Promise.all([
      fetch('./'+BASE_FILE+'?v='+Date.now()).then(r=>{if(!r.ok)throw new Error('DB '+r.status);return r.json()}),
      fetch('./'+CHANGES_FILE+'?v='+Date.now()).then(async r=>r.ok?await r.json():null).catch(()=>null)
    ]);
    basePeople=Array.isArray(b)?b:[];
    remoteChanges=normalizeChanges(c||{});
    try{const meta=await fetchJsonFile(CHANGES_FILE);if(meta.data){remoteChanges=normalizeChanges(meta.data);remoteChangesSha=meta.sha}}catch(e){}
    try{pending=normalizeChanges(JSON.parse(localStorage.getItem(PENDING_KEY)||'{}'))}catch(e){pending=normalizeChanges({})}
    compose();
  }catch(e){$('localResults').innerHTML=`<div class="empty">DBを読み込めませんでした<br>${esc(e.message)}</div>`;toast('DB読込エラー','err')}
}
function toggleFilters(){$('filters').classList.toggle('open');$('filterBtn').classList.toggle('primary',$('filters').classList.contains('open'))}
function toggleBulk(){$('bulkPanel').classList.toggle('open');$('menuPanel').classList.remove('open')}
function toggleMenu(){$('menuPanel').classList.toggle('open');$('bulkPanel').classList.remove('open')}
function hasFilters(){return ['f-year','f-month','f-day','f-job','f-country'].some(id=>$(id).value.trim())}
function filterChanged(){visibleCount=PAGE_SIZE;renderLocal();updateHeader()}
function clearOmni(){$('omniInput').value='';$('clearBtn').classList.add('hidden');hideRemote();visibleCount=PAGE_SIZE;renderLocal();updateHeader();$('omniInput').focus()}
$('omniInput').addEventListener('input',()=>{$('clearBtn').classList.toggle('hidden',!$('omniInput').value);visibleCount=PAGE_SIZE;renderLocal();updateHeader()});
$('omniInput').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();runOmniSearch()}if(e.key==='Escape')clearOmni()});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)){e.preventDefault();$('omniInput').focus()}if(e.key==='Escape'){closeEdit();closeSyncSettings()}if((e.ctrlKey||e.metaKey)&&e.key==='Enter'&&$('editModal').classList.contains('open')){e.preventDefault();saveEdit()}});

function getLocalMatches(){
  const q=norm($('omniInput').value),year=$('f-year').value.trim(),month=+$('f-month').value,day=+$('f-day').value,job=norm($('f-job').value),country=norm($('f-country').value);
  return savedPeople.filter(p=>{
    if(q&&!([p.name,p.nameEn,p.realName,p.memo].some(v=>norm(v).includes(q))))return false;
    if(year&&!String(p.birthday||'').startsWith(year))return false;
    if(month&&+(p.birthday||'').slice(5,7)!==month)return false;
    if(day&&+(p.birthday||'').slice(8,10)!==day)return false;
    if(job&&!norm((p.occupation||'')+' '+(p.description||'')).includes(job))return false;
    if(country&&!norm(p.country).includes(country))return false;
    return true;
  });
}
function hashOrder(id){let h=2166136261;const s=id+randomSalt;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
function toggleSort(){sortMode=sortMode==='random'?'birthday':'random';if(sortMode==='random')randomSalt=Math.random().toString(36).slice(2);renderLocal(true);toast(sortMode==='random'?'ランダム順':'誕生日順')}
function renderLocal(reset=false){
  if(reset)visibleCount=PAGE_SIZE;
  let a=getLocalMatches();
  if(sortMode==='birthday')a.sort((x,y)=>(x.birthday||'9999').slice(5).localeCompare((y.birthday||'9999').slice(5))||(x.name||'').localeCompare(y.name||''));
  else if(!$('omniInput').value.trim()&&!hasFilters())a.sort((x,y)=>hashOrder(x.id)-hashOrder(y.id));
  else a.sort((x,y)=>(x.name||'').localeCompare(y.name||'','ja'));
  $('localCount').textContent=a.length.toLocaleString();
  if(!a.length){$('localResults').innerHTML='<div class="empty">一致する人物はいません</div>';$('moreBtn').classList.add('hidden');return}
  const shown=a.slice(0,visibleCount);
  $('localResults').innerHTML=`<div class="grid">${shown.map(p=>cardHtml(p,true)).join('')}</div>`;
  $('moreBtn').classList.toggle('hidden',shown.length>=a.length);
  $('moreBtn').textContent=`さらに表示（${Math.min(PAGE_SIZE,a.length-shown.length)}）`;
}
function showMore(){visibleCount+=PAGE_SIZE;renderLocal()}
function cardHtml(p,isSaved){
  const age=ageOf(p.birthday),google='https://www.google.com/search?q='+encodeURIComponent(p.name||'');
  const tags=[p.occupation,p.country,p.birthplace].filter(Boolean).slice(0,3).map(x=>`<span class="tag">${esc(x)}</span>`).join('');
  return `<article class="card" id="card-${esc(p.id)}"><div class="card-top"><div style="min-width:0"><div class="name"><a target="_blank" rel="noopener" href="${google}">${esc(p.name||'不明')}</a></div>${p.nameEn?`<div class="alias">${esc(p.nameEn)}</div>`:''}${p.realName?`<div class="meta">本名 ${esc(p.realName)}</div>`:''}</div><div>${age!==null?`<div class="age">${age}<span style="font-size:10px;color:var(--muted);font-weight:400">歳</span></div>`:''}<div class="bday">${esc(bdayText(p.birthday))}</div></div></div><div class="tags">${tags}</div>${p.memo?`<div class="memo">${esc(p.memo)}</div>`:''}<div class="card-actions">${isSaved?`<button title="編集" onclick="openEdit('${esc(p.id)}')">${iconEdit}</button><button class="remove" title="削除" onclick="removePerson('${esc(p.id)}')">${iconTrash}</button>`:`<button class="save" onclick="saveRemote('${esc(p.id)}')">保存</button>`}</div></article>`;
}
async function runOmniSearch(){
  const q=$('omniInput').value.trim();if(!q&&!hasFilters()){toast('名前か条件を入力してください','warn');return}
  if(abortCtrl)abortCtrl.abort();abortCtrl=new AbortController();
  $('remoteSearchBtn').disabled=true;$('remoteSection').classList.add('show');$('remoteResults').innerHTML='<div class="empty">検索中</div>';
  try{
    let results=q?await searchWikidata(q,abortCtrl.signal):await searchByFilters(abortCtrl.signal);
    remoteResults=applyRemoteFilters(results);renderRemote();
  }catch(e){if(e.name!=='AbortError'){$('remoteResults').innerHTML='<div class="empty">Wikidata検索エラー</div>';toast(e.message,'err')}}finally{$('remoteSearchBtn').disabled=false}
}
function applyRemoteFilters(a){
  const year=$('f-year').value.trim(),month=+$('f-month').value,day=+$('f-day').value,job=norm($('f-job').value),country=norm($('f-country').value);
  return (a||[]).filter(p=>{
    if(year&&!String(p.birthday||'').startsWith(year))return false;
    if(month&&+(p.birthday||'').slice(5,7)!==month)return false;
    if(day&&+(p.birthday||'').slice(8,10)!==day)return false;
    if(job&&!norm((p.occupation||'')+' '+(p.description||'')).includes(job))return false;
    if(country&&!norm(p.country).includes(country))return false;
    return true;
  });
}
async function searchByFilters(signal){
  const year=$('f-year').value.trim(),month=+$('f-month').value,day=+$('f-day').value;
  const filters=[];
  if(year)filters.push(`FILTER(YEAR(?birth) = ${+year})`);
  if(month)filters.push(`FILTER(MONTH(?birth) = ${month})`);
  if(day)filters.push(`FILTER(DAY(?birth) = ${day})`);
  if(!filters.length)return [];
  const q=`SELECT DISTINCT ?person ?personLabel ?birth ?countryLabel ?occLabel WHERE { ?person wdt:P31 wd:Q5; wdt:P569 ?birth. OPTIONAL {?person wdt:P27 ?country.} OPTIONAL {?person wdt:P106 ?occ.} ${filters.join(' ')} SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". } } LIMIT 60`;
  const r=await fetch('https://query.wikidata.org/sparql?format=json&query='+encodeURIComponent(q),{headers:{Accept:'application/sparql-results+json'},signal});
  if(!r.ok)throw new Error('Wikidata Query '+r.status);const j=await r.json(),m=new Map();
  for(const row of j.results?.bindings||[]){const id=row.person.value.split('/').pop();if(!m.has(id))m.set(id,{id,name:row.personLabel?.value||id,nameEn:'',birthday:row.birth?.value?.slice(0,10)||'',occupation:'',country:row.countryLabel?.value||'',realName:'',birthplace:'',description:'',memo:''});const p=m.get(id),occ=row.occLabel?.value||'';if(occ&&!p.occupation.split('・').includes(occ))p.occupation+=(p.occupation?'・':'')+occ;}
  return [...m.values()].filter(p=>p.birthday&&!p.name.startsWith('Q'));
}
async function searchWikidata(q,signal){
  const u=`https://www.wikidata.org/w/api.php?action=wbsearchentities&search=${encodeURIComponent(q)}&language=ja&uselang=ja&type=item&limit=15&format=json&origin=*`;
  const sr=await fetch(u,{signal});if(!sr.ok)throw new Error('Wikidata '+sr.status);const sj=await sr.json();const ids=(sj.search||[]).map(x=>x.id);if(!ids.length)return [];
  const details=await fetchDetails(ids,signal);const map=new Map(details.map(x=>[x.id,x]));
  return ids.map(id=>map.get(id)).filter(Boolean);
}
async function fetchDetails(ids,signal){
  if(!ids.length)return[];
  const sparql=`SELECT DISTINCT ?person ?personLabel ?birth ?countryLabel ?occLabel ?realName ?bpLabel WHERE {
    VALUES ?person { ${ids.map(id=>'wd:'+id).join(' ')} }
    ?person wdt:P31 wd:Q5; wdt:P569 ?birth.
    OPTIONAL {?person wdt:P27 ?country.} OPTIONAL {?person wdt:P106 ?occ.}
    OPTIONAL {?person wdt:P1477 ?realName.} OPTIONAL {?person wdt:P19 ?bp.}
    SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". }
  }`;
  const r=await fetch('https://query.wikidata.org/sparql?format=json&query='+encodeURIComponent(sparql),{headers:{Accept:'application/sparql-results+json'},signal});
  if(!r.ok)throw new Error('Wikidata Query '+r.status);const j=await r.json(),m=new Map();
  for(const row of j.results?.bindings||[]){
    const id=row.person.value.split('/').pop();
    if(!m.has(id))m.set(id,{id,name:row.personLabel?.value||id,nameEn:'',birthday:row.birth?.value?.slice(0,10)||'',occupation:'',country:row.countryLabel?.value||'',realName:row.realName?.value||'',birthplace:row.bpLabel?.value||'',description:'',memo:''});
    const p=m.get(id),occ=row.occLabel?.value||'';if(occ&&!p.occupation.split('・').includes(occ))p.occupation+=(p.occupation?'・':'')+occ;
  }
  return [...m.values()];
}
function renderRemote(){
  $('remoteCount').textContent=remoteResults.length;$('remoteSection').classList.add('show');
  $('remoteResults').innerHTML=remoteResults.length?`<div class="grid">${remoteResults.map(p=>cardHtml(p,false)).join('')}</div>`:'<div class="empty">候補がありません</div>';
}
function hideRemote(){$('remoteSection').classList.remove('show');remoteResults=[]}
function saveRemote(id){
  const p=remoteResults.find(x=>x.id===id);if(!p)return;
  if(savedPeople.some(x=>x.id===id)){toast('保存済み','warn');return}
  const item={...p,savedAt:new Date().toISOString()};touchUpsert(item);savedPeople.push(item);renderLocal(true);renderRemote();updateHeader();toast('保存しました');
}
function openNewEntry(){openEdit('')}
function openEdit(id){
  const p=id?savedPeople.find(x=>x.id===id):null;
  $('editTitle').textContent=p?'人物を編集':'新規追加';$('editId').value=p?.id||'';
  $('editName').value=p?.name||'';$('editRealName').value=p?.realName||'';$('editBirthday').value=p?.birthday||'';
  $('editOccupation').value=p?.occupation||'';$('editCountry').value=p?.country||'';$('editBirthplace').value=p?.birthplace||'';
  $('editNameEn').value=p?.nameEn||'';$('editMemo').value=p?.memo||'';$('editModal').classList.add('open');setTimeout(()=>$('editName').focus(),20);
}
function closeEdit(){$('editModal').classList.remove('open')}
async function autofillFromWikidata(){
  const name=$('editName').value.trim();if(!name){toast('表示名を入力してください','warn');return}
  const btn=$('autofillBtn');btn.disabled=true;const old=btn.textContent;btn.textContent='検索中';
  try{
    const list=await searchWikidata(name);if(!list.length){toast('Wikidata候補なし','warn');return}
    const p=list[0];$('editName').value=p.name||name;$('editRealName').value=p.realName||$('editRealName').value;$('editBirthday').value=p.birthday||$('editBirthday').value;$('editOccupation').value=p.occupation||$('editOccupation').value;$('editCountry').value=p.country||$('editCountry').value;$('editBirthplace').value=p.birthplace||$('editBirthplace').value;$('editNameEn').value=p.nameEn||$('editNameEn').value;
    if(!$('editId').value&&p.id)$('editId').value=p.id;toast('Wikidataから入力');
  }catch(e){toast('自動入力失敗: '+e.message,'err')}finally{btn.disabled=false;btn.textContent=old}
}
function saveEdit(){
  const name=$('editName').value.trim();if(!name){toast('名前が必要です','warn');return}
  let id=$('editId').value||'local_'+Date.now().toString(36);
  const old=savedPeople.find(x=>x.id===id)||{};
  const p={...old,id,name,realName:$('editRealName').value.trim(),birthday:parseBirthday($('editBirthday').value),occupation:$('editOccupation').value.trim(),country:$('editCountry').value.trim(),birthplace:$('editBirthplace').value.trim(),nameEn:$('editNameEn').value.trim(),memo:$('editMemo').value.trim(),savedAt:old.savedAt||new Date().toISOString()};
  const i=savedPeople.findIndex(x=>x.id===id);if(i>=0)savedPeople[i]=p;else savedPeople.push(p);
  touchUpsert(p);closeEdit();renderLocal(true);updateHeader();toast('保存しました');
}
function removePerson(id){
  const p=savedPeople.find(x=>x.id===id);if(!p||!confirm(`「${p.name}」を削除しますか？`))return;
  savedPeople=savedPeople.filter(x=>x.id!==id);touchDelete(id);renderLocal(true);updateHeader();toast('削除しました');
}
async function fetchAllBirthplaces(){
  const targets=savedPeople.filter(p=>p.id?.startsWith('Q')&&!p.birthplace);if(!targets.length){toast('補完対象なし');return}
  toast(`${targets.length}人を補完中`,'warn');let updated=0;
  for(let i=0;i<targets.length;i+=70){
    const batch=targets.slice(i,i+70),q=`SELECT ?person ?bpLabel WHERE { VALUES ?person { ${batch.map(p=>'wd:'+p.id).join(' ')} } ?person wdt:P19 ?bp. SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". } }`;
    try{
      const r=await fetch('https://query.wikidata.org/sparql?format=json&query='+encodeURIComponent(q),{headers:{Accept:'application/sparql-results+json'}});const j=await r.json(),m=new Map((j.results?.bindings||[]).map(x=>[x.person.value.split('/').pop(),x.bpLabel?.value||'']));
      for(const p of batch){const bp=m.get(p.id);if(bp){p.birthplace=bp;touchUpsert(p);updated++}}
    }catch(e){}
    await new Promise(r=>setTimeout(r,250));
  }
  renderLocal();updateHeader();toast(`${updated}人を補完`);
}
function exportJSON(){
  const blob=new Blob([JSON.stringify(savedPeople,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='birthday_db_'+new Date().toISOString().slice(0,10)+'.json';a.click();URL.revokeObjectURL(a.href);
}
async function importJSON(ev){
  const file=ev.target.files?.[0];if(!file)return;
  try{
    const arr=JSON.parse(await file.text());if(!Array.isArray(arr))throw new Error('配列ではありません');
    const baseEffective=applyChanges(basePeople,remoteChanges),baseMap=new Map(baseEffective.map(x=>[x.id,x])),newMap=new Map(arr.filter(x=>x?.id).map(x=>[x.id,x]));
    pending={upserts:[],deletes:[]};
    for(const [id,p] of newMap){if(JSON.stringify(baseMap.get(id)||null)!==JSON.stringify(p))pending.upserts.push(p)}
    for(const id of baseMap.keys())if(!newMap.has(id))pending.deletes.push(id);
    savePending();compose();toast(`JSON読込: 未同期 ${pendingCount()}件`);
  }catch(e){toast('JSONを読めません: '+e.message,'err')}finally{ev.target.value=''}
}
function discardPending(){
  if(!pendingCount()){toast('未同期変更はありません');return}
  if(!confirm('未同期の変更を破棄しますか？'))return;pending=normalizeChanges({});savePending();compose();toast('未同期変更を破棄');
}
$('bulkTextarea').addEventListener('input',updateBulkMeta);
function updateBulkMeta(){const a=$('bulkTextarea').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);$('bulkMeta').textContent=`${a.length}行 / 重複 ${a.length-new Set(a).size}`}
function clearBulk(){$('bulkTextarea').value='';$('bulkLog').innerHTML='';$('bulkGrid').innerHTML='';$('bulkSaveRow').classList.add('hidden');bulkResults=[];updateBulkMeta()}
async function fetchGroupMembers(ids,groupName){
  if(!ids.length)return [];
  const q=`SELECT DISTINCT ?member ?memberLabel ?birth ?occLabel ?countryLabel ?realName ?bpLabel WHERE { VALUES ?group { ${ids.map(id=>'wd:'+id).join(' ')} } ?group wdt:P527 ?member. ?member wdt:P31 wd:Q5. OPTIONAL {?member wdt:P569 ?birth.} OPTIONAL {?member wdt:P106 ?occ.} OPTIONAL {?member wdt:P27 ?country.} OPTIONAL {?member wdt:P1477 ?realName.} OPTIONAL {?member wdt:P19 ?bp.} SERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en". } } LIMIT 40`;
  try{
    const r=await fetch('https://query.wikidata.org/sparql?format=json&query='+encodeURIComponent(q),{headers:{Accept:'application/sparql-results+json'}});if(!r.ok)return[];const j=await r.json(),m=new Map();
    for(const row of j.results?.bindings||[]){const id=row.member.value.split('/').pop();if(!m.has(id))m.set(id,{id,name:row.memberLabel?.value||id,nameEn:'',birthday:row.birth?.value?.slice(0,10)||'',occupation:'',country:row.countryLabel?.value||'',realName:row.realName?.value||'',birthplace:row.bpLabel?.value||'',description:'',memo:'',_query:groupName,_fromGroup:groupName,_found:true});const p=m.get(id),occ=row.occLabel?.value||'';if(occ&&!p.occupation.split('・').includes(occ))p.occupation+=(p.occupation?'・':'')+occ;}
    return [...m.values()].filter(p=>p.birthday&&!p.name.startsWith('Q'));
  }catch(e){return[]}
}
async function startBulk(){
  const names=[...new Set($('bulkTextarea').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean))];if(!names.length){toast('名前を入力','warn');return}
  $('bulkStartBtn').disabled=true;bulkResults=[];$('bulkGrid').innerHTML='';$('bulkLog').innerHTML='';
  for(let i=0;i<names.length;i++){
    const name=names[i];$('bulkLog').innerHTML+=`<div>${i+1}/${names.length} ${esc(name)}</div>`;
    try{
      const u=`https://www.wikidata.org/w/api.php?action=wbsearchentities&search=${encodeURIComponent(name)}&language=ja&uselang=ja&type=item&limit=8&format=json&origin=*`;
      const sj=await fetch(u).then(r=>r.json()),ids=(sj.search||[]).map(x=>x.id),details=await fetchDetails(ids.slice(0,8)),map=new Map(details.map(x=>[x.id,x]));
      const chosen=ids.map(id=>map.get(id)).find(Boolean);
      if(chosen)bulkResults.push({...chosen,_query:name,_found:true});
      else{
        const members=await fetchGroupMembers(ids.slice(0,3),name);
        if(members.length)bulkResults.push(...members);else bulkResults.push({_query:name,_found:false});
      }
    }catch(e){bulkResults.push({_query:name,_found:false})}
    await new Promise(r=>setTimeout(r,220));
  }
  $('bulkStartBtn').disabled=false;renderBulk();
}
function renderBulk(){
  $('bulkGrid').innerHTML=bulkResults.map((p,i)=>p._found?`<div class="bulk-item"><label><input type="checkbox" id="bulk-${i}" ${savedPeople.some(x=>x.id===p.id)?'':'checked'}><div><div class="candidate">${esc(p.name)}</div><div class="query">${esc(p._query)} → ${esc(bdayText(p.birthday))}</div><div class="meta">${esc(p.occupation)} ${p.country?' / '+esc(p.country):''}</div></div></label></div>`:`<div class="bulk-item bad"><div class="candidate">${esc(p._query)}</div><div class="meta">候補なし。手動追加を使用</div></div>`).join('');
  $('bulkSaveRow').classList.toggle('hidden',!bulkResults.some(x=>x._found));
}
function bulkToggleAll(v){bulkResults.forEach((p,i)=>{const c=$('bulk-'+i);if(c)c.checked=v})}
function bulkSaveChecked(){
  let n=0;bulkResults.forEach((p,i)=>{const c=$('bulk-'+i);if(!p._found||!c?.checked||savedPeople.some(x=>x.id===p.id))return;const item={...p,savedAt:new Date().toISOString()};delete item._found;delete item._query;delete item._fromGroup;savedPeople.push(item);touchUpsert(item);n++});
  renderLocal(true);updateHeader();toast(`${n}人保存`);
}
function openSyncSettings(){$('tokenInput').value=sessionStorage.getItem(TOKEN_KEY)||'';$('syncModal').classList.add('open')}
function closeSyncSettings(){$('syncModal').classList.remove('open')}
function saveToken(){const t=$('tokenInput').value.trim();if(!t){toast('トークンを入力','warn');return}sessionStorage.setItem(TOKEN_KEY,t);closeSyncSettings();toast('このタブに保存')}
function forgetToken(){sessionStorage.removeItem(TOKEN_KEY);$('tokenInput').value='';toast('トークンを削除')}
function mergeChanges(baseCh,extra){
  const result=normalizeChanges(baseCh),map=new Map(result.upserts.map(p=>[p.id,p])),del=new Set(result.deletes);
  for(const id of extra.deletes||[]){map.delete(id);del.add(id)}
  for(const p of extra.upserts||[]){del.delete(p.id);map.set(p.id,clone(p))}
  result.upserts=[...map.values()];result.deletes=[...del];result.updatedAt=new Date().toISOString();return result;
}
function changesForId(ch,id){return (ch.deletes||[]).includes(id)?'delete':(ch.upserts||[]).find(x=>x.id===id)||null}
async function syncGitHub(){
  if(!pendingCount()){
    try{const latest=await fetchJsonFile(CHANGES_FILE);if(latest.data){remoteChanges=normalizeChanges(latest.data);remoteChangesSha=latest.sha;compose();toast('GitHubから更新')}}catch(e){toast(e.message,'err')}return;
  }
  const token=sessionStorage.getItem(TOKEN_KEY);if(!token){openSyncSettings();toast('最初にGitHubトークンを設定','warn');return}
  $('syncBtn').disabled=true;$('syncLabel').textContent='同期中';
  try{
    const latest=await fetchJsonFile(CHANGES_FILE,true);let current=normalizeChanges(latest.data||{});
    if(remoteChangesSha&&latest.sha&&latest.sha!==remoteChangesSha){
      const touched=[...new Set([...pending.upserts.map(x=>x.id),...pending.deletes])];
      const conflicts=touched.filter(id=>JSON.stringify(changesForId(remoteChanges,id))!==JSON.stringify(changesForId(current,id)));
      if(conflicts.length&&!confirm(`GitHub側でも ${conflicts.length}件 更新されています。こちらの未同期変更を優先して続けますか？`))throw new Error('同期を中止しました');
    }
    const merged=mergeChanges(current,pending),content=JSON.stringify(merged,null,2);
    const utf8=btoa(unescape(encodeURIComponent(content)));
    const headers={'Accept':'application/vnd.github+json','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28','Authorization':'Bearer '+token};
    const body={message:`Update birthday DB (${pendingCount()} changes)`,content:utf8,branch:BRANCH};if(latest.sha)body.sha=latest.sha;
    const r=await fetch(API+encodeURIComponent(CHANGES_FILE),{method:'PUT',headers,body:JSON.stringify(body)});if(!r.ok){let msg='';try{msg=(await r.json()).message}catch(e){}throw new Error(`GitHub ${r.status} ${msg}`)}
    const j=await r.json();remoteChanges=merged;remoteChangesSha=j.content?.sha||'';pending=normalizeChanges({});savePending();compose();toast('GitHubへ同期しました');
  }catch(e){toast(e.message||'同期失敗','err');updateHeader()}finally{$('syncBtn').disabled=false;updateHeader()}
}
init();