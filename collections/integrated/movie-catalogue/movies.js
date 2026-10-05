'use strict';
const $=s=>document.querySelector(s),el=(t,c,txt)=>{const n=document.createElement(t);if(c)n.className=c;if(txt!==undefined)n.textContent=txt;return n},norm=s=>String(s||'').normalize('NFKC').toLowerCase(),fmt=n=>Number(n).toLocaleString('ja-JP');
let movies=[],byKey=new Map(),people=new Map(),limit=72,mode='movies',selectedGenres=new Set(),randomRank=new Map(),stack=[],dataset;
const pkey=p=>String(p.id||p.url||p.name),credits=m=>[...(m.directors||[]).map(p=>({...p,role:'監督'})),...(m.cast||[]).map(p=>({...p,role:'出演'}))];
function url(v){try{const u=new URL(v);return u.protocol==='https:'?u.href:''}catch{return ''}}

function trailerId(m){
  if(/^[\w-]{11}$/.test(m.trailer_id||''))return m.trailer_id;
  for(const value of [m.resolved_youtube_url,m.youtube_url]){
    try{
      const u=new URL(value);let id='';
      if(u.protocol!=='https:')continue;
      if(u.hostname==='youtu.be')id=u.pathname.split('/')[1];
      else if(['youtube.com','www.youtube.com','m.youtube.com','www.youtube-nocookie.com'].includes(u.hostname)){
        if(u.pathname==='/watch')id=u.searchParams.get('v');
        else if(/^\/(embed|shorts)\//.test(u.pathname))id=u.pathname.split('/')[2];
      }
      if(/^[\w-]{11}$/.test(id||''))return id;
    }catch{}
  }
  return '';
}
function playTrailer(m){
  const id=trailerId(m);if(!id)return;
  const frame=el('iframe');
  frame.title=m.title;
  frame.allow='autoplay; encrypted-media; fullscreen; picture-in-picture';
  frame.allowFullscreen=true;
  frame.referrerPolicy='strict-origin-when-cross-origin';
  frame.src='https://www.youtube.com/embed/'+id+'?autoplay=1&rel=0';
  $('#trailerBody').replaceChildren(frame);
  if(!$('#trailer').open)$('#trailer').showModal();
}
function poster(m,compact=false,split=false){
  const n=el(split?'div':'button',split?'poster poster-split':'poster');
  if(split){n.setAttribute('role','group');n.setAttribute('aria-label',m.title)}
  else{n.type='button';n.setAttribute('aria-label',m.title+'の予告編を再生');n.onclick=()=>playTrailer(m)}
  const visual=el('span','poster-visual');n.append(visual);
  const fallback=()=>visual.replaceChildren(el('span','fallback',compact?'':m.title));
  if(m.poster_url){const img=el('img');img.src=url(m.poster_url);img.alt=m.title;img.loading='lazy';img.decoding='async';img.referrerPolicy='no-referrer';img.onerror=fallback;visual.append(img)}else fallback();
  if(m.isWatched){const badge=el('span','badge watched-icon','✓');badge.setAttribute('role','img');badge.setAttribute('aria-label','観た');n.append(badge)}
  if(split){
    const preview=el('button','poster-zone poster-zone-preview'),details=el('button','poster-zone poster-zone-details');
    preview.type=details.type='button';
    preview.setAttribute('aria-label',m.title+'の予告編を再生');preview.onclick=()=>playTrailer(m);
    details.setAttribute('aria-label',m.title+'の出演者・詳細を開く');details.onclick=()=>show({type:'film',key:m.key});
    n.append(preview,details);
  }
  return n;
}
function card(m){
  const a=el('article','card'),info=el('div','card-info'),b=el('button','title',m.title);
  b.onclick=()=>show({type:'film',key:m.key});info.append(b);
  const year=m.release_date||m.production_year||m.year||'';
  if(year)info.append(el('p','meta',String(year)));
  a.append(poster(m),info);return a;
}
function genreList(m){return m.genres?.length?m.genres:(m.genre?[m.genre]:[])}
function shuffle(){const a=movies.map(m=>m.key);for(let i=a.length-1;i>0;i--){let j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}randomRank=new Map(a.map((k,i)=>[k,i]))}
function rebuild(){byKey=new Map(movies.map(m=>[m.key,m]));people=new Map();for(const m of movies){m.search=norm([m.title,...credits(m).map(p=>p.name)].join(' '));for(const p of credits(m)){if(!p.name)continue;const k=pkey(p);if(!people.has(k))people.set(k,{...p,key:k,keys:new Set(),roles:new Set()});people.get(k).keys.add(m.key);people.get(k).roles.add(p.role)}}shuffle();const gs=[...new Set(movies.flatMap(genreList))].sort((a,b)=>a.localeCompare(b,'ja'));$('#genres').replaceChildren(...gs.map(g=>{const l=el('label'),i=el('input');i.type='checkbox';i.value=g;i.onchange=()=>{i.checked?selectedGenres.add(g):selectedGenres.delete(g);limit=72;render()};l.append(i,document.createTextNode(g));return l}))}
function matches(m){const scope=$('#scope').value;if(scope==='watched'&&!m.isWatched||scope==='unwatched'&&m.isWatched||scope==='personal'&&!m.personalList)return false;if(selectedGenres.size){const hit=genreList(m).some(g=>selectedGenres.has(g));if($('#genreMode').value==='include'?!hit:hit)return false}return true}
function sorted(list){const s=$('#sort').value;return list.sort((a,b)=>s==='random'?randomRank.get(a.key)-randomRank.get(b.key):s==='title'?a.title.localeCompare(b.title,'ja'):s==='year'?(Number(b.production_year||b.year)||0)-(Number(a.production_year||a.year)||0):(b[s]??-1)-(a[s]??-1))}
function personCard(p){const b=el('button','person-card');b.append(el('strong','',p.name),el('small','',[...p.roles].join('・')+' · '+fmt(p.keys.size)));b.onclick=()=>show({type:'person',key:p.key});return b}
function render(){const terms=norm($('#search').value).trim().split(/\s+/).filter(Boolean);let list;if(mode==='people'){list=[...people.values()].filter(p=>terms.every(t=>norm(p.name).includes(t))&&[...p.keys].some(k=>matches(byKey.get(k)))).sort((a,b)=>b.keys.size-a.keys.size);$('#heading').textContent='出演者・監督';$('#grid').replaceChildren(...list.slice(0,limit).map(personCard))}else{list=sorted(movies.filter(m=>matches(m)&&terms.every(t=>m.search.includes(t))));$('#heading').textContent=({'all':'すべての映画','watched':'観た映画','unwatched':'未鑑賞の映画','personal':'Filmarksの自分のリスト'})[$('#scope').value];$('#grid').replaceChildren(...list.slice(0,limit).map(card))}$('#count').textContent=fmt(list.length);if(!list.length)$('#grid').append(el('p','empty','該当する作品・人物がありません'));$('#more').hidden=list.length<=limit;$('#peopleView').textContent=mode==='people'?'映画一覧':'出演者・監督';$('#genreCount').textContent=selectedGenres.size?'（'+selectedGenres.size+'）':''}

function show(view,back=false){
  if(!back&&(stack.at(-1)?.type!==view.type||stack.at(-1)?.key!==view.key))stack.push(view);
  const body=$('#detailBody');body.replaceChildren();$('#dialogBack').hidden=stack.length<2;
  if(view.type==='film'){
    const m=byKey.get(view.key);if(!m)return;
    const head=el('div','film-head'),info=el('div','film-info');
    info.append(el('h2','',m.title),el('p','meta',[m.release_date||m.production_year||m.year,m.isWatched?'観た':'未鑑賞'].filter(Boolean).join(' · ')));
    for(const [label,list] of [['出演',m.cast||[]],['監督',m.directors||[]]]){
      if(!list.length)continue;
      info.append(el('h3','section-title',label));const chips=el('div','chips');
      for(const p of list){
        const k=pkey(p),b=el('button','chip',p.name);
        b.append(el('small','',fmt(people.get(k)?.keys.size||0)));
        b.onclick=()=>show({type:'person',key:k});chips.append(b);
      }
      info.append(chips);
    }
    if(!credits(m).length)info.append(el('p','meta','出演者・監督の情報は未収録です。'));
    head.append(poster(m,false,true),info);body.append(head);
    const shared=new Map();
    for(const p of credits(m))for(const key of people.get(pkey(p))?.keys||[]){if(key===m.key)continue;if(!shared.has(key))shared.set(key,new Set());shared.get(key).add(p.name)}
    const related=[...shared].sort((a,b)=>b[1].size-a[1].size).slice(0,18);
    if(related.length){
      body.append(el('h3','section-title','この人、これにも出ています'));
      const grid=el('div','grid related');
      for(const [key]of related)grid.append(poster(byKey.get(key),true,true));
      body.append(grid);
    }
  }else{
    const p=people.get(view.key);if(!p)return;
    const top=el('div','person-top');
    top.append(el('h2','',p.name),el('p','meta',[...p.roles].join('・')+' · '+fmt(p.keys.size)));body.append(top);
    const grid=el('div','grid related');
    grid.append(...[...p.keys].map(k=>byKey.get(k)).sort((a,b)=>(Number(b.production_year||b.year)||0)-(Number(a.production_year||a.year)||0)).map(m=>poster(m,true,true)));body.append(grid);
  }
  if(!$('#detail').open)$('#detail').showModal();$('#detail').scrollTop=0;
}
$('#close').onclick=()=>$('#detail').close();$('#detail').addEventListener('close',()=>stack=[]);
$('#dialogBack').onclick=()=>{stack.pop();show(stack.at(-1),true)};
$('#trailerClose').onclick=()=>$('#trailer').close();$('#trailer').addEventListener('close',()=>$('#trailerBody').replaceChildren());
for(const id of ['detail','trailer']){
  const dialog=$('#'+id);
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()}});
}
function setSearchOpen(open){
  $('#search').hidden=!open;$('#movieFilters').hidden=!open;$('#searchToggle').setAttribute('aria-expanded',String(open));
  if(open)$('#search').focus();
  else $('#searchToggle').focus();
}
$('#searchToggle').onclick=()=>setSearchOpen($('#search').hidden);
$('#search').addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();setSearchOpen(false)}});
$('#movieFilters').addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();setSearchOpen(false)}});
$('#search').addEventListener('input',()=>{mode='movies';limit=72;render()});
for(const id of ['scope','sort','genreMode'])$('#'+id).addEventListener('change',()=>{limit=72;render()});
$('#peopleView').onclick=()=>{mode=mode==='movies'?'people':'movies';limit=72;render()};
$('#more').onclick=()=>{limit+=72;render()};
$('#shuffle').onclick=()=>{shuffle();$('#sort').value='random';limit=72;render()};
$('#genreClear').onclick=()=>{selectedGenres.clear();$('#genres').querySelectorAll('input').forEach(i=>i.checked=false);render()};
document.body.dataset.size='large';
async function init(){
  let r,stale=false;
  try{r=await fetch('movie-data.json',{cache:'no-store'});if(!r.ok)throw Error('api')}catch{stale=true;r=await fetch('movie-data.json')}
  if(!r.ok)throw Error('data');dataset=await r.json();movies=dataset.movies;rebuild();
  if(stale){$('#coverage').hidden=false;$('#coverage').textContent='保存済みデータを表示しています。'}
  render();
}
init().catch(()=>{$('#grid').append(el('p','empty','読み込みに失敗しました。ページを再読み込みしてください'))});
