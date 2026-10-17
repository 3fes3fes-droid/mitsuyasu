import{n as e}from"./rolldown-runtime-jpDsebLB.js";import{n as t,t as n}from"./jsx-runtime-B8pT2InZ.js";import{n as r}from"./shuffle-BbnpeDIt.js";var i=r(`eye`,[[`path`,{d:`M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0`,key:`1nclc0`}],[`circle`,{cx:`12`,cy:`12`,r:`3`,key:`1v7zrd`}]]),a=r(`house`,[[`path`,{d:`M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8`,key:`5wwlr5`}],[`path`,{d:`M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z`,key:`r6nss1`}]]),o=r(`utensils`,[[`path`,{d:`M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2`,key:`cjf0a3`}],[`path`,{d:`M7 2v20`,key:`1473qp`}],[`path`,{d:`M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7`,key:`j28e5`}]]),s=e(t(),1),c=n();function l({href:e,children:t,...n}){return(0,c.jsx)(`a`,{href:e,...n,children:t})}function u(e,t=!1){let n=e.replaceAll(`&`,`&amp;`).replaceAll(`<`,`&lt;`).replaceAll(`>`,`&gt;`).replaceAll(`"`,`&quot;`).slice(0,32);return`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
          <stop stop-color="#d9e2d4"/>
          <stop offset="1" stop-color="#b9c7b3"/>
        </linearGradient>
      </defs>
      <rect width="1200" height="800" fill="url(#g)"/>
      ${t?`<circle cx="600" cy="365" r="180" fill="none" stroke="#6f8a71" stroke-width="28"/><circle cx="600" cy="365" r="122" fill="#f1eee5"/><path d="M355 180v365M315 180v120q0 58 40 58t40-58V180M845 180v365M845 180q90 85 0 210" fill="none" stroke="#6f8a71" stroke-width="22" stroke-linecap="round"/>`:`<path d="M0 620Q230 510 420 610T800 560T1200 590V800H0Z" fill="#6f8a71" opacity=".5"/>`}
      <rect x="0" y="690" width="1200" height="110" fill="#173425"/>
      <text x="60" y="758" fill="#fbfaf6" font-family="sans-serif" font-size="42" font-weight="700">${n}</text>
    </svg>`}function d({query:e,alt:t,src:n,loading:r=`lazy`,kind:i=`photo`}){let a=(0,s.useMemo)(()=>`data:image/svg+xml;charset=utf-8,`+encodeURIComponent(u(e.trim().slice(0,80),i===`food`)),[i,e]),[o,l]=(0,s.useState)(!1);return(0,c.jsx)(`img`,{src:n&&!o?n:a,alt:t,loading:r,decoding:`async`,onError:()=>{n&&!o&&l(!0)}})}export{i as a,a as i,l as n,o as r,d as t};