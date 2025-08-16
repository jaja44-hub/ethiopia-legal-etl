const el = (id)=>document.getElementById(id);
const pulse = (msg, cls='') => { const p=el('pulse'); p.textContent=msg; p.className='pulse '+cls; };
const log = (s)=>{ const L=el('log'); L.textContent += s + '\n'; L.scrollTop=L.scrollHeight; };

const templates = [
  { name: "Deploy React → Render (demo)", intent: "Deploy React app to Render with Firebase backend" },
  { name: "Daily scrape → Firestore (demo)", intent: "Scrape example.com daily and store titles in Firestore" },
  { name: "PDF → JSON (demo)", intent: "Convert sample.pdf into structured JSON and index for search" }
];

function renderTemplates(){
  const ul = el('templates');
  ul.innerHTML = '';
  templates.forEach(t=>{
    const li = document.createElement('li');
    const a = document.createElement('a'); a.href="#"; a.textContent = t.name;
    a.onclick = (e)=>{ e.preventDefault(); el('intent').value=t.intent; };
    li.appendChild(a); ul.appendChild(li);
  });
}

function demoRun(intent){
  pulse('Planning in demo mode…','warn');
  log('Intent: ' + intent);
  setTimeout(()=>{ log('• Plan created (mock)'); }, 400);
  setTimeout(()=>{ log('• Executing steps (mock)'); }, 900);
  setTimeout(()=>{ log('• All steps succeeded (mock)'); pulse('Demo completed — UI is live.','ok'); }, 1600);
}

window.addEventListener('DOMContentLoaded', ()=>{
  renderTemplates();
  el('run').addEventListener('click', ()=>{
    const intent = el('intent').value.trim();
    if(!intent){ pulse('Enter an intent to run the demo.','warn'); return; }
    el('log').textContent=''; demoRun(intent);
  });
  pulse('Ready — demo mode');
});
