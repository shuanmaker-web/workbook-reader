/* Workbook 隨身讀 — app.js
   Data model (data.js → window.EXAM): books[{id,title,english,sub,plan[]}], units[{id,book,...}], sections[{id,unit,title,english,range,pages,overview,items[]}]
   items: group | entries | bank | passage | q   (q.type: choice | multi | bank | fill | trans)
   Translation (trans) questions: students answer on paper; the app only offers a "看參考答案" button,
   controlled by a teacher switch (state.transOn, remembered in localStorage). */
const CACHE='workbook-reader-v3'; // keep in sync with sw.js
const STORE='workbook-reader-v1';
const exam=window.EXAM,dict=window.DICTIONARY||{};
const $=s=>document.querySelector(s),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const readStore=(k,def)=>{try{return JSON.parse(localStorage.getItem(k))??def}catch{return def}};
const writeStore=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch{toast('儲存空間不足，這次閱讀仍可繼續。')}};
let state={section:'',book:'',bookSection:{},picks:{},drafts:{},revealed:{},positions:{},font:18,dark:false,words:{},transOn:true,...readStore(STORE,{})};
let mode='home',section,book,showAll=false,wordFilter='all',search='',tipTimer,toastTimer,scrollTimer,installPrompt;
function persist(){writeStore(STORE,state)}
function toast(t){const el=$('#toast');el.textContent=t;el.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.hidden=true,2400)}

/* ---------- indexes & helpers ---------- */
const questions=s=>s.items.filter(i=>i.t==='q');
const qkey=(s,q)=>`${s.id}-${q.n}`;
const qIndex={},entryIndex={};
exam.sections.forEach(s=>{questions(s).forEach(q=>{qIndex[qkey(s,q)]={s,q}});s.items.forEach(it=>{if(it.t==='entries')it.list.forEach(e=>{entryIndex[e.w.toLowerCase()]=e})})});
const isTrans=q=>q.type==='trans';
const hasTrans=s=>questions(s).some(isTrans);
const canSee=q=>!isTrans(q)||state.transOn;
const isRevealed=(s,q)=>canSee(q)&&(showAll||!!state.revealed[qkey(s,q)]);
const qLabel=q=>/^(類題|試題演練) \d+/.test(q.src)?q.src:`第 ${q.n} 題 · ${q.src}`;
const altList=a=>a.split('|').map(x=>x.trim()).filter(Boolean);
const normFill=s=>s.toLowerCase().replace(/\s+/g,' ').replace(/[.。]+$/,'').trim();
const numSet=s=>(String(s).match(/\d+/g)||[]).map(Number).sort((a,b)=>a-b).join(',');
function fillCorrect(q,val){if(!String(val||'').trim())return false;if(/^[\d\s,，、]+$/.test(q.ans))return numSet(val)===numSet(q.ans);return altList(q.ans).some(a=>normFill(a)===normFill(val))}
function answerText(q){if(q.type==='choice'||q.type==='bank')return q.opts[q.ans.charCodeAt(0)-65];if(q.type==='multi')return q.ans.split('').map(l=>q.opts[l.charCodeAt(0)-65]).join(' / ');return altList(q.ans)[0]}
function lookup(word){const k=word.toLowerCase().replaceAll('’',"'");let d=dict[k];if(!d&&k.endsWith("'s"))d=dict[k.slice(0,-2)];return d??{meaning:'專有名稱或外語詞，請參照原文語境。',phonetic:''}}
function wordify(t){return String(t).replace(/([A-Za-z]+(?:['’][A-Za-z]+)?)|([^A-Za-z]+)/g,(m,w,o)=>w?`<span class="word" data-word="${esc(w)}">${esc(w)}</span>`:esc(o))}
function text(t,s=null,fill=false){return String(t).split(/(\[\[\d+\]\])/).map(ch=>{const m=ch.match(/^\[\[(\d+)\]\]$/);if(!m)return wordify(ch);const q=s&&questions(s).find(x=>x.n===+m[1]);if(!q)return esc(ch);if(fill&&isRevealed(s,q))return `<span class="gap-answer">${wordify(answerText(q))}</span>`;return `<a class="blank" href="#q-${s.id}-${q.n}" data-gap="${q.n}" aria-label="前往第 ${q.show} 題">${q.show}</a>`}).join('')}
function blankContext(s,q){for(const it of s.items){if(it.t!=='passage')continue;for(const p of it.paras){if(!p.includes(`[[${q.n}]]`))continue;const sent=p.split(/(?<=[.!?。])\s+/).find(x=>x.includes(`[[${q.n}]]`))||p;return sent.replace(/\[\[(\d+)\]\]/g,(m,n)=>+n===q.n?'______':'___')}}return ''}
const unitOf=id=>exam.units.find(u=>u.id===id);
const books=exam.books&&exam.books.length?exam.books:[{id:'dmg',title:'大滿貫',english:'Grand Slam',sub:'',plan:[]}];
const bookById=id=>books.find(b=>b.id===id);
const bookOf=s=>bookById((unitOf(s.unit)||{}).book)||books[0];
const bookUnits=b=>exam.units.filter(u=>(u.book||books[0].id)===b.id);
const bookSections=b=>exam.sections.filter(s=>bookOf(s)===b);
const lastSection=b=>{const secs=bookSections(b);return secs.find(s=>s.id===state.bookSection[b.id])||secs[0]};
const isLesson=()=>mode==='read'||mode==='analysis';

/* ---------- section chrome ---------- */
function chapterSelect(){const opts=bookUnits(book).map(u=>{const secs=exam.sections.filter(s=>s.unit===u.id);if(!secs.length)return '';return `<optgroup label="${esc(u.title)}">${secs.map(s=>`<option value="${s.id}" ${s.id===section.id?'selected':''}>${esc(s.title)}　${esc(s.range)}</option>`).join('')}</optgroup>`}).join('');return `<select class="mobile-chapters" id="chapterSelect" aria-label="選擇單元">${opts}</select>`}
function hero(analysis=false){const nq=questions(section).length,ne=section.items.filter(i=>i.t==='entries').reduce((n,i)=>n+i.list.length,0);return `<section class="hero"><div class="eyebrow">${esc(book.title)} · ${analysis?'TEACHER’S DESK / 解析備課':esc((unitOf(section.unit)||{}).title||'WORKBOOK').toUpperCase()}</div><h1>${esc(section.english)}</h1><p>${analysis?'從答案走回線索。逐題看文意、搭配詞和句型，準備明天的課。':'點一下英文單字，詞義停留 2 秒。<br>上課時直接帶學生讀題、作答、對答案。'}</p><div class="pillrow"><span class="pill">${esc(section.title)}</span><span class="pill">${esc(section.range)}</span>${nq?`<span class="pill">${nq} 題</span>`:''}${ne?`<span class="pill">${ne} 個單字／片語</span>`:''}</div></section>${chapterSelect()}`}
function navrow(){const secs=bookSections(book),i=secs.indexOf(section),prev=secs[i-1],next=secs[i+1];return `<div class="navrow">${prev?`<a href="#${mode}/${prev.id}">← ${esc(prev.title)}</a>`:`<a href="#book/${book.id}">← ${esc(book.title)} 目錄</a>`}${next?`<a href="#${mode}/${next.id}">${esc(next.title)} →</a>`:'<a href="#home">回到首頁，換一本書 →</a>'}</div>`}
function transSwitch(){return hasTrans(section)?`<div class="trans-switch"><span class="hint">老師可在這裡決定要不要顯示翻譯參考答案。</span><label class="switch"><input type="checkbox" id="transToggle" ${state.transOn?'checked':''}>顯示翻譯答案</label></div>`:''}

/* ---------- items ---------- */
function renderEntry(e){const key=e.w.toLowerCase(),starred=!!state.words[key]?.star;return `<article class="entry"><div class="entry-head"><h3>${wordify(e.w)}</h3><button class="starbtn" data-entry-star="${esc(key)}" aria-pressed="${starred}" aria-label="${starred?'取消收藏':'收藏'} ${esc(e.w)}">${starred?'★':'☆'}</button></div>`
 +e.s.map(x=>`<p class="sense">${wordify(x)}</p>`).join('')
 +(e.p.length?`<ul class="phrases">${e.p.map(p=>`<li><b>${wordify(p[0])}</b>　${esc(p[1])}</li>`).join('')}</ul>`:'')
 +e.n.map(n=>`<p class="note"><span class="note-tag">${esc(n[0])}</span>${wordify(n[1])}</p>`).join('')
 +e.e.map(x=>`<p class="ex">${wordify(x[0])}${x[1]?`<br><span class="zh">${esc(x[1])}</span>`:''}</p>`).join('')
 +e.b.map(b=>`<p class="boxed"><span class="src">${esc(b[0])}</span>${wordify(b[1])}<br><span class="zh">${esc(b[2])}</span></p>`).join('')+`</article>`}
function renderBank(b){const words=b.opts.every(o=>o.length<=24);return `<details class="reading-card bank-card" open><summary>${words?'單字庫':'句庫'}（${b.opts.length} 個選項）</summary><div class="bank-list">${b.opts.map((o,i)=>`<div><b>${String.fromCharCode(65+i)}</b><span>${wordify(o)}</span></div>`).join('')}</div></details>`}
function altsHtml(q){const alts=q.an.filter(a=>a.l==='替換'),extra=q.an.filter(a=>a.l!=='替換');
 return (alts.length?`<div class="alts-title">可替換的說法</div><ul class="alts">${alts.map(a=>{const i=a.t.indexOf(':');return i<0?`<li>${wordify(a.t)}</li>`:`<li><b>${wordify(a.t.slice(0,i))}</b> → ${wordify(a.t.slice(i+1).trim())}</li>`}).join('')}</ul>`:'')
  +extra.map(a=>`<p class="tn">${a.l?`<span class="exp-tag">${esc(a.l)}</span>`:''}${a.d?'<span class="tag-derived">推導</span>':''}${wordify(a.t)}</p>`).join('')}
function renderQuestion(q){const s=section,key=qkey(s,q),revealed=isRevealed(s,q),pick=state.picks[key]??'',draft=state.drafts[key]??'';let body='',tag='';
 if(q.type==='choice'||q.type==='multi'||q.type==='bank'){
  const chips=q.type==='bank'&&q.opts.every(o=>o.length<=24);
  const btn=(o,i)=>{const L=String.fromCharCode(65+i),sel=q.type==='multi'?pick.includes(L):pick===L,ok=revealed&&q.ans.includes(L);return `<button type="button" class="${chips?'chip':'option'} ${sel?'selected':''} ${ok?'correct':''} ${revealed&&sel&&!ok?'wrong':''}" data-choice="${key}" data-letter="${L}" aria-pressed="${sel}"><span class="letter">${L}</span>${chips?`<span>${wordify(o)}</span>`:`<span>${text(o)}</span>`}</button>`};
  body=`<div class="${chips?'chips':'options'}">${q.opts.map(btn).join('')}</div>`;
  if(revealed)tag=`答案 ${q.ans.split('').join('、')}`;
 }else if(q.type==='fill'){
  body=`<input class="response" data-draft="${key}" value="${esc(draft)}" placeholder="輸入你的答案…" autocomplete="off" autocapitalize="none" spellcheck="false" aria-label="${esc(qLabel(q))} 作答">`;
  if(revealed){tag=fillCorrect(q,draft)?'✓ 答對了':'參考答案';body+=`<div class="text-answer">${altList(q.ans).map(esc).join('　/　')}</div>`}
 }else if(isTrans(q)){
  body='';
  if(revealed){tag=q.an.some(a=>a.d)?'參考答案 · 推導':'參考答案';body+=`<div class="text-answer trans-answer">${wordify(q.ans)}${altsHtml(q)}<p class="tn">這題的英文說法不只一種，以上僅供參考。</p></div>`}
 }
 const showBtn=canSee(q);
 return `<article class="qcard" id="q-${key}"><div class="qtop"><span class="qnum">${esc(qLabel(q))}</span>${tag?`<span class="answer-tag">${esc(tag)}</span>`:''}</div><div class="qstem">${text(q.stem,s)}</div>${q.type==='multi'?'<p class="hint">本題為多選。</p>':''}${body}<div class="qactions">${showBtn?`<button class="reveal" data-reveal="${key}">${revealed?'收起答案 ↑':isTrans(q)?'看參考答案 ↓':'顯示答案 ↓'}</button>`:'<span class="hint">翻譯答案已關閉</span>'}${showBtn&&!isTrans(q)?`<a class="to-analysis" href="#analysis/${s.id}/${q.n}">查看解析 ↗</a>`:'<span></span>'}</div></article>`}
function renderItem(it){switch(it.t){case 'group':return `<div class="sectionbar groupbar"><h2>${esc(it.title)}</h2></div>`;case 'entries':return it.list.map(renderEntry).join('');case 'bank':return renderBank(it);case 'passage':return `<div class="reading-card"><div class="article-label">THE PASSAGE / 文章</div><div class="passage">${it.paras.map(p=>`<p>${text(p,section,true)}</p>`).join('')}</div></div>`;case 'q':return renderQuestion(it)}return ''}
function answeredCount(s){return questions(s).filter(q=>{const k=qkey(s,q);return q.type==='fill'?(state.drafts[k]||'').trim():state.picks[k]}).length}
function renderRead(){const nq=questions(section).length,done=answeredCount(section);return `${hero()}<div class="toolbar"><span class="hint">✦ 點單字查義 · 點選項作答</span>${nq?`<label class="switch"><input type="checkbox" id="showAll" ${showAll?'checked':''}>顯示全部答案</label>`:''}</div>${transSwitch()}${section.overview?`<div class="overview">${esc(section.overview)}</div>`:''}${section.pages&&section.pages.length?`<div class="sectionbar"><span></span><button class="sourcebtn" id="openSource">原書頁面核對 ↗</button></div>`:''}${nq?`<div class="progress-label">已作答 ${done} / ${questions(section).filter(q=>!isTrans(q)).length} 題</div>`:''}${section.items.map(renderItem).join('')}${navrow()}<div class="notebox">${esc(exam.notice||'')}</div>`}

/* ---------- analysis ---------- */
function renderAnalysisQ(q){const s=section,key=qkey(s,q),hide=isTrans(q)&&!state.transOn;let ctx=q.type==='bank'||/^（第/.test(q.stem)?blankContext(s,q):'';const excerpt=ctx?wordify(ctx):text(q.stem,s);
 let full='';if(!hide){full=q.type==='choice'||q.type==='bank'?`${q.ans}. ${answerText(q)}`:q.type==='multi'?q.ans.split('').map(l=>`${l}. ${q.opts[l.charCodeAt(0)-65]}`).join('\n'):isTrans(q)?q.ans:altList(q.ans).join('　/　')}
 const lines=isTrans(q)?'':q.an.map(a=>`<p class="exp-line">${a.l?`<span class="exp-tag">${esc(a.l)}</span>`:''}${a.d?'<span class="tag-derived">推導</span>':''}${wordify(a.t)}</p>`).join('');
 const body=hide?`<div class="lock-note">翻譯答案目前已關閉。可到「設定」或該課頂端的開關開啟。</div>`:`<div class="answer-full">${wordify(full)}</div>${isTrans(q)?`<div class="trans-answer">${altsHtml(q)}</div>`:`<div class="explain">${lines}</div>`}`;
 return `<article class="analysis-card" id="a-${key}"><h3><span class="qnum">${esc(qLabel(q))}</span>${!hide&&q.type!=='fill'&&!isTrans(q)?`<span class="answer-tag">${q.ans.split('').join('、')}</span>`:''}</h3><div class="qexcerpt">${excerpt}</div>${body}<div class="qactions"><a class="to-analysis" href="#read/${s.id}/${q.n}">回到題目 ↗</a></div></article>`}
function renderAnalysis(){return `${hero(true)}${transSwitch()}<div class="sectionbar"><h2>單元導讀</h2>${section.pages&&section.pages.length?'<button class="sourcebtn" id="openSource">原書頁面核對 ↗</button>':''}</div><div class="overview">${esc(section.overview||'')}</div>${section.items.map(it=>it.t==='q'?renderAnalysisQ(it):it.t==='group'||it.t==='entries'?renderItem(it):'').join('')}${navrow()}<div class="notebox">${esc(exam.notice||'')}</div>`}

/* ---------- home & book contents ---------- */
const qCount=secs=>secs.reduce((n,s)=>n+questions(s).length,0);
function renderHome(){const total=exam.sections.length;return `<section class="hero"><div class="eyebrow">TUTOR’S BAG / 隨身教材</div><h1>今天上哪一本？</h1><p>一台 iPad 帶齊上課教材。選一本書開始上課，<br>點英文單字可查詞義，題目、答案、解析都在裡面。</p><div class="pillrow"><span class="pill">${books.length} 本書</span><span class="pill">${total} 個單元</span><span class="pill">${qCount(exam.sections)} 題</span></div></section><div class="book-grid">${books.map((b,i)=>{const secs=bookSections(b),last=secs.length&&lastSection(b),resumed=last&&state.bookSection[b.id];return `<a class="book-card ${secs.length?'':'is-empty'}" href="#book/${b.id}"><span class="book-num">${String(i+1).padStart(2,'0')}</span><span class="book-body"><b>${esc(b.title)}</b><small class="book-en">${esc(b.english||'')}</small><span class="book-sub">${esc(b.sub||'')}</span><span class="book-meta">${secs.length?`${bookUnits(b).filter(u=>secs.some(s=>s.unit===u.id)).length} 個部分 · ${secs.length} 個單元 · ${qCount(secs)} 題`:'內容準備中'}</span>${resumed?`<span class="book-resume">上次：${esc(last.title)}（${esc((unitOf(last.unit)||{}).title||'')}）</span>`:''}</span><span class="book-go">→</span></a>`}).join('')}</div><div class="notebox">${esc(exam.notice||'')}</div>`}
function renderBook(){const secs=bookSections(book),last=secs.length&&lastSection(book),resumed=last&&state.bookSection[book.id];
 const head=`<section class="hero"><div class="eyebrow">BOOK / 教材</div><h1>${esc(book.title)}</h1><p>${esc(book.english||'')}${book.sub?`<br>${esc(book.sub)}`:''}</p><div class="pillrow"><span class="pill">${esc(book.title)}</span>${secs.length?`<span class="pill">${secs.length} 個單元</span><span class="pill">${qCount(secs)} 題</span>`:'<span class="pill">內容準備中</span>'}</div></section>`;
 if(!secs.length)return `${head}<div class="empty book-empty">這本書的內容還沒有加入。${book.plan&&book.plan.length?`<div class="plan-list">${book.plan.map(p=>`<span>${esc(p)}</span>`).join('')}</div>`:''}<small>把教材頁面拍照或掃描給 Claude，就能整理成和「大滿貫」一樣的題目、答案與解析。</small></div><div class="navrow"><a href="#home">← 回到首頁</a><span></span></div>`;
 return `${head}${resumed?`<a class="resume-card" href="#read/${last.id}"><span>繼續上次的進度</span><b>${esc(last.title)}　${esc(last.range)}</b><small>${esc((unitOf(last.unit)||{}).title||'')} →</small></a>`:''}${bookUnits(book).map(u=>{const us=secs.filter(s=>s.unit===u.id);if(!us.length)return '';return `<div class="sectionbar groupbar"><h2>${esc(u.title)}</h2><span class="hint">${esc(u.sub||'')}</span></div><div class="toc">${us.map(s=>{const nq=questions(s).length;return `<div class="toc-row"><a class="toc-main" href="#read/${s.id}"><b>${esc(s.title)}</b><small>${esc(s.range)} · ${esc(s.english)}${nq?` · ${nq} 題`:''}</small></a>${nq?`<a class="toc-side" href="#analysis/${s.id}">解析 ↗</a>`:''}</div>`}).join('')}</div>`}).join('')}<div class="navrow"><a href="#home">← 回到首頁</a><span></span></div>`}

/* ---------- my words ---------- */
function renderWords(){const all=Object.values(state.words),starred=all.filter(w=>w.star).length;return `<section class="hero"><div class="eyebrow">YOUR WORDS / 通勤的累積</div><h1>每次點一下，<br>就多記住一點。</h1><p>查過的單字都在這裡。點星號留下重點，通勤時再看一眼。</p><div class="pillrow"><span class="pill">${all.length} 個查過的字</span><span class="pill">${starred} 個收藏</span></div></section><input class="search" id="wordSearch" placeholder="搜尋英文或繁中詞義…" aria-label="搜尋單字" value="${esc(search)}"><div class="filters"><button data-filter="all" class="${wordFilter==='all'?'active':''}">全部</button><button data-filter="star" class="${wordFilter==='star'?'active':''}">★ 收藏</button><button id="exportWords">匯出單字</button></div><div id="wordList">${wordRows()}</div>`}
function wordRows(){const list=Object.values(state.words).filter(w=>(wordFilter!=='star'||w.star)&&(!search||`${w.word} ${w.meaning}`.toLowerCase().includes(search.toLowerCase()))).sort((a,b)=>b.time-a.time);return list.length?list.map(w=>`<article class="word-row"><div><h3>${text(w.word)}</h3><p>${esc(w.meaning)}</p></div><button class="starbtn" data-star="${esc(w.word.toLowerCase())}" aria-label="${w.star?'取消收藏':'收藏'} ${esc(w.word)}" aria-pressed="${!!w.star}">${w.star?'★':'☆'}</button></article>`).join(''):`<div class="empty">${wordFilter==='star'?'還沒有收藏單字。<br>點單字旁的 ☆ 就能留下重點。':'讓第一個單字，成為這趟路的起點。<br>到題目頁點一下任何英文單字，詞義會停留 2 秒，並自動收進這裡。'}</div>`}

/* ---------- routing / render ---------- */
function sidebar(){if(mode==='home')return `<div class="unit-caption">BOOKS / 教材</div>`+books.map((b,i)=>`<a class="chapter" href="#book/${b.id}"><span class="num">${String(i+1).padStart(2,'0')}</span><span><b>${esc(b.title)}</b><small>${esc(b.sub||b.english||'')}</small></span></a>`).join('');
 let n=0;return `<a class="chapter back-books" href="#home"><span class="num">⌂</span><span><b>全部書本</b><small>回到首頁換一本</small></span></a><a class="chapter book-title ${mode==='book'?'active':''}" href="#book/${book.id}"><span class="num">▤</span><span><b>${esc(book.title)}</b><small>目錄</small></span></a>`+bookUnits(book).map(u=>{const secs=bookSections(book).filter(s=>s.unit===u.id);if(!secs.length)return '';return `<div class="unit-caption">${esc(u.title).toUpperCase()}</div>`+secs.map(s=>{n++;return `<a class="chapter ${s===section&&isLesson()?'active':''}" href="#${mode==='analysis'?'analysis':'read'}/${s.id}"><span class="num">${String(n).padStart(2,'0')}</span><span><b>${esc(s.title)}</b><small>${esc(s.range)} · ${esc(s.english)}</small></span></a>`}).join('')}).join('')}
function render(){const parts=location.hash.slice(1).split('/');const r=parts[0];
 mode=['read','analysis','words','book'].includes(r)?r:'home';
 if(mode==='book'){book=bookById(parts[1])||bookById(state.book)||books[0];section=lastSection(book)}
 else if(isLesson()){book=bookById(state.book)||books[0];section=exam.sections.find(s=>s.id===parts[1])||lastSection(book)||exam.sections[0];book=bookOf(section)}
 else{book=bookById(state.book)||books[0];section=lastSection(book)}
 state.book=book.id;if(isLesson()){state.section=section.id;state.bookSection[book.id]=section.id}persist();
 $('#main').innerHTML=mode==='home'?renderHome():mode==='book'?renderBook():mode==='words'?renderWords():mode==='analysis'?renderAnalysis():renderRead();
 $('#chapterList').innerHTML=sidebar();
 document.querySelectorAll('[data-nav]').forEach(a=>{const nav=a.dataset.nav;a.classList.toggle('active',nav===mode||(nav==='home'&&mode==='book'));if(nav==='read'||nav==='analysis')a.href=section?'#'+nav+'/'+section.id:'#book/'+book.id});
 document.title=`${mode==='home'?'首頁':mode==='book'?book.title+' · 目錄':mode==='words'?'我的單字':section.title+' · '+(mode==='analysis'?'解析備課':'題目閱讀')}｜Workbook 隨身讀`;
 requestAnimationFrame(()=>{if(isLesson()&&parts[2]){document.getElementById((mode==='analysis'?'a-':'q-')+section.id+'-'+parts[2])?.scrollIntoView()}else window.scrollTo(0,isLesson()?state.positions[mode+'/'+section.id]||0:0)})}
function rerenderHere(){const y=scrollY;$('#main').innerHTML=mode==='home'?renderHome():mode==='book'?renderBook():mode==='read'?renderRead():mode==='words'?renderWords():renderAnalysis();window.scrollTo(0,y)}
function chooseSection(id){state.section=id;persist();location.hash=mode+'/'+id}
function setTrans(on){state.transOn=on;persist();applySettings();if(isLesson())rerenderHere()}

/* ---------- events ---------- */
document.addEventListener('click',e=>{
 const word=e.target.closest('.word');if(word){e.preventDefault();e.stopPropagation();const raw=word.dataset.word.replaceAll('’',"'"),key=raw.toLowerCase(),d=lookup(raw);clearTimeout(tipTimer);document.querySelector('.word.tapped')?.classList.remove('tapped');word.classList.add('tapped');const tip=$('#wordTip');tip.innerHTML=`<strong>${esc(raw)}${d.phonetic?`<small>/${esc(d.phonetic)}/</small>`:''}</strong>${esc(d.meaning)}`;tip.hidden=false;const rect=word.getBoundingClientRect(),w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=Math.max(14,Math.min(rect.left,innerWidth-w-14))+'px';tip.style.top=Math.max(10,rect.top>h+20?rect.top-h-9:Math.min(innerHeight-h-90,rect.bottom+9))+'px';tipTimer=setTimeout(()=>{tip.hidden=true;word.classList.remove('tapped')},2000);state.words[key]={word:key,...d,star:state.words[key]?.star||false,time:Date.now()};persist();return}
 const gap=e.target.closest('[data-gap]');if(gap){e.preventDefault();document.getElementById(`q-${section.id}-${gap.dataset.gap}`)?.scrollIntoView({behavior:'smooth'});return}
 const opt=e.target.closest('[data-choice]');if(opt){const k=opt.dataset.choice,{q}=qIndex[k],l=opt.dataset.letter;if(q.type==='multi'){const val=state.picks[k]??'';state.picks[k]=(val.includes(l)?val.replace(l,''):val+l).split('').sort().join('')}else state.picks[k]=l;persist();rerenderHere();return}
 const reveal=e.target.closest('[data-reveal]');if(reveal){const k=reveal.dataset.reveal;if(showAll){showAll=false;state.revealed[k]=false}else state.revealed[k]=!state.revealed[k];persist();rerenderHere();return}
 const es=e.target.closest('[data-entry-star]');if(es){const key=es.dataset.entryStar,ent=entryIndex[key],cur=state.words[key];state.words[key]={word:ent.w,meaning:ent.s.join(' ｜ ')||ent.p.map(p=>p[1]).join('；')||ent.n.map(n=>n[1]).join('；'),phonetic:cur?.phonetic||'',star:!cur?.star,time:Date.now()};persist();rerenderHere();return}
 const star=e.target.closest('[data-star]');if(star){const w=state.words[star.dataset.star];if(w){w.star=!w.star;persist();$('#wordList').innerHTML=wordRows()}return}
 const filter=e.target.closest('[data-filter]');if(filter){wordFilter=filter.dataset.filter;rerenderHere();return}
 const close=e.target.closest('[data-close]');if(close){$('#'+close.dataset.close).close();return}
 if(e.target.closest('#openSource')){$('#sourcePages').innerHTML=section.pages.map(n=>{const p=String(n).padStart(2,'0');return `<h3>第 ${n} 頁</h3><img src="assets/page-${n}.jpg" alt="原書第 ${n} 頁掃描" onerror="this.onerror=null;this.src='assets/page-${p}.jpg'">`}).join('');$('#source').showModal()}
 if(e.target.closest('#exportWords')){const lines=Object.values(state.words).map(w=>`${w.star?'★ ':''}${w.word}\t${w.meaning}`).join('\n');if(!lines)return toast('先查幾個單字，再匯出吧。');const blob=new Blob(['Workbook 我的單字\n\n'+lines],{type:'text/plain;charset=utf-8'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='Workbook_My_Words.txt';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}});
document.addEventListener('change',e=>{const id=e.target.id;if(id==='chapterSelect')chooseSection(e.target.value);if(id==='showAll'){showAll=e.target.checked;rerenderHere()}if(id==='darkToggle'){state.dark=e.target.checked;applySettings();persist()}if(id==='transToggle'||id==='transToggle2')setTrans(e.target.checked)});
document.addEventListener('input',e=>{if(e.target.dataset.draft){state.drafts[e.target.dataset.draft]=e.target.value;persist()}if(e.target.id==='wordSearch'){search=e.target.value;$('#wordList').innerHTML=wordRows()}});
function applySettings(){document.documentElement.style.setProperty('--reading',state.font+'px');document.body.classList.toggle('dark',state.dark);$('#fontValue').textContent=state.font+' px';$('#darkToggle').checked=state.dark;$('#transToggle2').checked=state.transOn}
$('#fontDown').onclick=()=>{state.font=Math.max(16,state.font-1);applySettings();persist()};$('#fontUp').onclick=()=>{state.font=Math.min(26,state.font+1);applySettings();persist()};$('#settingsBtn').onclick=()=>$('#settings').showModal();
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e});$('#installBtn').onclick=async()=>{if(installPrompt){await installPrompt.prompt();installPrompt=null}else{$('#installHelp').style.background='var(--wash)';toast('請依下方說明，從瀏覽器加入主畫面。')}};
window.addEventListener('hashchange',render);window.addEventListener('scroll',()=>{clearTimeout(scrollTimer);scrollTimer=setTimeout(()=>{if(section&&isLesson()){state.positions[mode+'/'+section.id]=scrollY;persist()}},200)},{passive:true});
function offlineStatus(ready=false){const el=$('#offlineState');el.textContent=ready?'可離線閱讀':navigator.onLine?'正在準備離線…':'目前離線';el.classList.toggle('ready',ready)}
if('serviceWorker'in navigator){navigator.serviceWorker.addEventListener('message',e=>{if(e.data==='offline-ready')offlineStatus(true);if(e.data==='offline-error'){$('#offlineState').textContent='離線快取待重試'}});navigator.serviceWorker.register('sw.js').then(async()=>{await navigator.serviceWorker.ready;const cache=await caches.open(CACHE);offlineStatus(!!(await cache.match(new URL('offline-ready',location.href).href)))}).catch(()=>{$('#offlineState').textContent='僅線上閱讀'})}else $('#offlineState').textContent='僅線上閱讀';
applySettings();render();
