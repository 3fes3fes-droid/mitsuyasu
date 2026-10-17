(async () => {
  const FAV_KEY="public_actress_directory_favorites_v1";
  const BATCH=220;
  const collator=new Intl.Collator("ja",{numeric:true,sensitivity:"base"});
  const response=await fetch("directory-index.json");if(!response.ok)throw Error("data");const manifest=await response.json();
  const parts=await Promise.all(manifest.parts.map(async p=>{const r=await fetch(p);if(!r.ok)throw Error("data");return r.json()}));
  const items=parts.flat();if(items.length!==manifest.total)throw Error("data count");

  const app=document.getElementById("app");
  const toggleList=document.getElementById("toggleList");
  const searchInput=document.getElementById("searchInput");
  const favGrid=document.getElementById("favGrid");
  const allGrid=document.getElementById("allGrid");
  const allScroll=document.getElementById("allScroll");
  const sentinel=document.getElementById("sentinel");
  const favRandom=document.getElementById("favRandom");
  const favKana=document.getElementById("favKana");
  const allRandom=document.getElementById("allRandom");
  const allKana=document.getElementById("allKana");

  let favorites=new Set(JSON.parse(localStorage.getItem(FAV_KEY)||"[]"));
  let allMode="random",favMode="random",listVisible=true,allView=[],rendered=0;

  const norm=s=>(s||"").normalize("NFKC").toLowerCase().replace(/\s+/g,"");
  const hira=s=>norm(s).replace(/[\u30a1-\u30f6]/g,c=>String.fromCharCode(c.charCodeAt(0)-0x60));

  function shuffle(arr){
    const a=arr.slice();
    for(let i=a.length-1;i>0;i--){
      const j=Math.floor(Math.random()*(i+1));
      [a[i],a[j]]=[a[j],a[i]];
    }
    return a;
  }
  function sort50(arr){
    return arr.slice().sort((a,b)=>
      collator.compare(a.ruby||a.name,b.ruby||b.name) || collator.compare(a.name,b.name)
    );
  }
  function yt(n){return "https://www.youtube.com/results?search_query="+encodeURIComponent(n)}
  function google(n){return "https://www.google.com/search?q="+encodeURIComponent(n)}

  function card(item){
    const el=document.createElement("article");
    el.className="card";
    el.dataset.name=item.name;

    const pic=document.createElement("a");
    pic.className="thumb";
    pic.href=yt(item.name);
    pic.target="_blank";
    pic.rel="noopener noreferrer";

    if(item.image){
      const img=document.createElement("img");
      img.loading="lazy";
      img.decoding="async";
      img.alt=item.name;
      img.src=item.image;
      pic.appendChild(img);
    }else{
      const blank=document.createElement("div");
      blank.className="missing";
      pic.appendChild(blank);
    }

    const meta=document.createElement("div");
    meta.className="meta";

    const cb=document.createElement("input");
    cb.type="checkbox";
    cb.className="check";
    cb.checked=favorites.has(item.name);
    cb.addEventListener("change",()=>setFavorite(item.name,cb.checked));

    const name=document.createElement("a");
    name.className="name";
    name.href=google(item.name);
    name.target="_blank";
    name.rel="noopener noreferrer";
    name.textContent=item.name;

    meta.append(cb,name);
    el.append(pic,meta);
    return el;
  }

  function save(){localStorage.setItem(FAV_KEY,JSON.stringify([...favorites]))}

  function setFavorite(name,on){
    if(on) favorites.add(name); else favorites.delete(name);
    save();
    document.querySelectorAll(".card").forEach(c=>{
      if(c.dataset.name===name){
        const box=c.querySelector(".check");
        if(box) box.checked=on;
      }
    });
    renderFavs();
  }

  function filterItems(){
    const q=norm(searchInput.value);
    const qh=hira(searchInput.value);
    if(!q) return items.slice();
    return items.filter(x=>
      norm(x.name).includes(q) ||
      hira(x.ruby).includes(qh) ||
      hira(x.name).includes(qh)
    );
  }

  function rebuildAll(){
    const base=filterItems();
    allView=allMode==="kana"?sort50(base):shuffle(base);
    rendered=0;
    allGrid.textContent="";
    allScroll.scrollTop=0;
    appendBatch();
  }

  function appendBatch(){
    if(rendered>=allView.length)return;
    const end=Math.min(rendered+BATCH,allView.length);
    const frag=document.createDocumentFragment();
    for(let i=rendered;i<end;i++)frag.appendChild(card(allView[i]));
    allGrid.appendChild(frag);
    rendered=end;
  }

  function renderFavs(){
    let base=items.filter(x=>favorites.has(x.name));
    base=favMode==="kana"?sort50(base):shuffle(base);
    favGrid.textContent="";
    const frag=document.createDocumentFragment();
    base.forEach(x=>frag.appendChild(card(x)));
    favGrid.appendChild(frag);
  }

  function setMode(side,mode){
    if(side==="fav"){
      favMode=mode;
      favRandom.classList.toggle("active",mode==="random");
      favKana.classList.toggle("active",mode==="kana");
      renderFavs();
    }else{
      allMode=mode;
      allRandom.classList.toggle("active",mode==="random");
      allKana.classList.toggle("active",mode==="kana");
      rebuildAll();
    }
  }

  toggleList.addEventListener("click",()=>{
    listVisible=!listVisible;
    app.classList.toggle("list-hidden",!listVisible);
    toggleList.classList.toggle("active",listVisible);
  });

  let timer;
  searchInput.addEventListener("input",()=>{
    clearTimeout(timer);
    timer=setTimeout(rebuildAll,80);
  });

  favRandom.addEventListener("click",()=>setMode("fav","random"));
  favKana.addEventListener("click",()=>setMode("fav","kana"));
  allRandom.addEventListener("click",()=>setMode("all","random"));
  allKana.addEventListener("click",()=>setMode("all","kana"));

  new IntersectionObserver(es=>{
    if(es.some(e=>e.isIntersecting))appendBatch();
  },{root:allScroll,rootMargin:"900px 0px"}).observe(sentinel);

  rebuildAll();
  renderFavs();
})().catch(()=>{document.getElementById("allGrid").textContent="読み込みに失敗しました。ページを再読み込みしてください。"});
