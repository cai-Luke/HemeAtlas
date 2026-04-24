# Future SharePoint Plans — Archived Code

This file preserves logic from admin.html that was removed during the
Antigravity refactor (agent-centric workflow). These blocks are preserved
for the future transition to a SharePoint list architecture.

Do not re-integrate this code without reviewing the full SharePoint migration plan.

## Batch Import Panel HTML
```html
<!-- BATCH IMPORT PANEL -->
<div class="batch-overlay hidden" id="batch-overlay" onclick="closeBatchIfBg(event)">
  <div class="batch-panel">
    <div class="batch-header">
      <div class="batch-title">⚡ Batch Import</div>
      <button class="dp-close" onclick="hideBatchPanel()">✕</button>
    </div>
    <div class="batch-body">
      <div class="batch-step">
        <div class="batch-step-num">1</div>
        <div class="batch-step-body">
          <div class="batch-step-label">Load image folder</div>
          <div class="batch-controls">
            <button class="batch-load-btn" onclick="document.getElementById('batch-folder-input').click()">📁 Select Folder</button>
            <span class="batch-loaded hidden" id="batch-loaded-msg"></span>
          </div>
        </div>
      </div>
      <div class="batch-step">
        <div class="batch-step-num">2</div>
        <div class="batch-step-body">
          <div class="batch-step-label">Assign cell type</div>
          <div class="batch-controls">
            <select class="dp-select" id="batch-cell-select" style="width:auto;min-width:180px" onchange="updateBatchSummary()">
              <option value="">— Select cell type —</option>
            </select>
            <div style="display:flex;align-items:center;gap:6px">
              <label style="font-size:12px;font-weight:600;color:var(--text3)">Case Tag</label>
              <input class="dp-edit-input" id="batch-case-tag" placeholder="optional" style="width:120px" />
            </div>
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
              <label style="font-size:12px;font-weight:600;color:var(--text3)">Tags</label>
              <input class="dp-edit-input" id="batch-tags" placeholder="e.g. aberration, pelger-huet" style="width:240px" />
              <span style="font-size:11px;color:var(--text3)">Add <strong>aberration</strong> to route to the Aberrations library</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px">
              <label style="font-size:12px;font-weight:600;color:var(--text3)">Your Name</label>
              <input class="dp-edit-input" id="batch-user" placeholder="for audit trail" style="width:140px" />
            </div>
          </div>
        </div>
      </div>
      <div class="batch-step">
        <div class="batch-step-num">3</div>
        <div class="batch-step-body">
          <div class="batch-step-label">Review — click any cell to exclude it</div>
          <div class="batch-preview-grid hidden" id="batch-preview-grid"></div>
          <div class="batch-excluded-hint hidden" id="batch-excluded-hint"></div>
        </div>
      </div>
      <div class="batch-summary hidden" id="batch-summary"></div>
    </div>
    <div class="batch-footer">
      <span style="font-size:12px;color:var(--text3);flex:1" id="batch-skip-msg"></span>
      <button class="btn" onclick="hideBatchPanel()">Cancel</button>
      <button class="batch-commit-btn" id="batch-commit-btn" onclick="commitBatch()" disabled>⚡ Finalize All</button>
    </div>
  </div>
</div>
```

## Batch Import CSS
```css
/* ── BATCH IMPORT PANEL ── */
  .batch-overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:600;display:flex;align-items:center;justify-content:center;padding:20px}
  .batch-panel{background:#ffffff;border-radius:var(--radius-xl);box-shadow:0 20px 60px rgba(0,0,0,.35);width:820px;max-width:calc(100vw - 40px);max-height:88vh;overflow:hidden;display:flex;flex-direction:column;position:relative;z-index:601}
  .batch-header{padding:18px 22px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;flex-shrink:0}
  .batch-title{font-size:16px;font-weight:700;flex:1}
  .batch-body{overflow-y:auto;padding:20px 22px;flex:1;display:flex;flex-direction:column;gap:16px}
  .batch-step{display:flex;align-items:flex-start;gap:14px}
  .batch-step-num{width:24px;height:24px;border-radius:50%;background:var(--accent);color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px}
  .batch-step-body{flex:1}
  .batch-step-label{font-size:12px;font-weight:700;color:var(--text);margin-bottom:6px;text-transform:uppercase;letter-spacing:.4px}
  .batch-controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  .batch-load-btn{padding:8px 16px;border-radius:var(--radius);font-size:13px;font-weight:600;cursor:pointer;border:1.5px solid var(--accent);background:#fff;color:var(--accent);transition:all .15s}
  .batch-load-btn:hover{background:var(--accent);color:#fff}
  .batch-loaded{font-size:12px;color:var(--green);font-weight:600}
  .batch-preview-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:8px;max-height:280px;overflow-y:auto;padding:4px;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg)}
  .batch-thumb{position:relative;border-radius:6px;overflow:hidden;border:2px solid var(--border);background:var(--surface2);cursor:pointer;transition:border-color .15s}
  .batch-thumb.excluded{opacity:.35;border-color:var(--red)}
  .batch-thumb:hover{border-color:var(--accent)}
  .batch-thumb img{width:100%;aspect-ratio:1;object-fit:cover;display:block}
  .batch-thumb .bt-name{font-size:8px;color:var(--text3);padding:2px 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;background:#fff}
  .batch-thumb .bt-exclude{position:absolute;top:2px;right:2px;width:16px;height:16px;border-radius:50%;background:rgba(0,0,0,.5);color:#fff;font-size:9px;display:flex;align-items:center;justify-content:center;font-weight:700}
  .batch-excluded-hint{font-size:11px;color:var(--text3);margin-top:4px}
  .batch-summary{padding:12px 16px;background:var(--accent-light);border:1px solid #93c5fd;border-radius:var(--radius);font-size:13px;color:var(--accent);font-weight:600}
  .batch-footer{padding:14px 22px;border-top:1px solid var(--border);background:#fafbfc;display:flex;align-items:center;gap:10px;flex-shrink:0}
  .batch-commit-btn{padding:9px 20px;border-radius:var(--radius);font-size:13px;font-weight:700;cursor:pointer;border:none;background:var(--green);color:#fff;transition:background .15s}
  .batch-commit-btn:hover{background:#15803d}
  .batch-commit-btn:disabled{opacity:.4;cursor:not-allowed}
  .zoom-overlay{position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:900;display:flex;align-items:center;justify-content:center;cursor:zoom-out}
  .zoom-img{max-width:90vw;max-height:90vh;object-fit:contain;border-radius:var(--radius-lg);box-shadow:0 0 60px rgba(0,0,0,.8);transition:transform .1s ease;transform-origin:center center}
  .zoom-close{position:fixed;top:20px;right:24px;color:#fff;font-size:28px;cursor:pointer;opacity:.7;transition:opacity .15s;z-index:901;background:none;border:none;line-height:1}
  .zoom-close:hover{opacity:1}
  .zoom-hint{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);color:rgba(255,255,255,.5);font-size:12px;pointer-events:none}

  /* ── SELECTION MODE ── */
```

## Batch Import JavaScript
```js
const _batchUrlCache = {};

// ── BATCH IMPORT ───────────────────────────────────────
let B = {files:[], excluded:new Set()};

function showBatchPanel(){
  // Populate cell type dropdown
  const sel=document.getElementById('batch-cell-select');
  sel.innerHTML='<option value="">— Select cell type —</option>';
  Object.keys(MATURATION).sort((a,b)=>MATURATION[a]-MATURATION[b]).forEach(k=>{
    const o=document.createElement('option');o.value=k;o.textContent=CELL_DISPLAY[k]||k;sel.appendChild(o);
  });
  // Pre-fill username if known
  document.getElementById('batch-user').value=G.userName||'';
  document.getElementById('batch-tags').value='';
  // Reset state
  B.files=[];B.excluded=new Set();
  document.getElementById('batch-loaded-msg').classList.add('hidden');
  document.getElementById('batch-preview-grid').classList.add('hidden');
  document.getElementById('batch-excluded-hint').classList.add('hidden');
  document.getElementById('batch-summary').classList.add('hidden');
  document.getElementById('batch-commit-btn').disabled=true;
  document.getElementById('batch-skip-msg').textContent='';
  document.getElementById('batch-overlay').classList.remove('hidden');
}
function hideBatchPanel(){document.getElementById('batch-overlay').classList.add('hidden');}
function closeBatchIfBg(e){if(e.target===document.getElementById('batch-overlay'))hideBatchPanel();}

function handleBatchFolder(e){
  const files=Array.from(e.target.files).filter(f=>f.type.startsWith('image/')).sort((a,b)=>a.name.localeCompare(b.name));
  if(!files.length){toast('⚠ No image files found.');return;}
  B.files=files.map(f=>({file:f,url:URL.createObjectURL(f),name:f.name}));
  B.excluded=new Set();
  document.getElementById('batch-loaded-msg').textContent=`✓ ${files.length} images loaded`;
  document.getElementById('batch-loaded-msg').classList.remove('hidden');
  renderBatchPreview();
  updateBatchSummary();
  e.target.value='';
}

function renderBatchPreview(){
  const grid=document.getElementById('batch-preview-grid');
  grid.innerHTML='';grid.classList.remove('hidden');
  B.files.forEach((img,i)=>{
    const div=document.createElement('div');
    div.className='batch-thumb'+(B.excluded.has(i)?' excluded':'');
    div.id='bt-'+i;
    div.title=img.name+'\nClick to exclude/include';
    div.onclick=()=>toggleBatchExclude(i);
    div.innerHTML=`<img src="${img.url}" loading="lazy" /><div class="bt-name">${esc(img.name)}</div>${B.excluded.has(i)?'<div class="bt-exclude">✕</div>':''}`;
    grid.appendChild(div);
  });
}

function toggleBatchExclude(i){
  if(B.excluded.has(i))B.excluded.delete(i);
  else B.excluded.add(i);
  // Update just this thumb
  const div=document.getElementById('bt-'+i);
  if(div){
    div.className='batch-thumb'+(B.excluded.has(i)?' excluded':'');
    const ex=div.querySelector('.bt-exclude');
    if(B.excluded.has(i)&&!ex){const d=document.createElement('div');d.className='bt-exclude';d.textContent='✕';div.appendChild(d);}
    else if(!B.excluded.has(i)&&ex)ex.remove();
  }
  updateBatchSummary();
}

function updateBatchSummary(){
  if(!B.files.length)return;
  const cellType=document.getElementById('batch-cell-select').value;
  const included=B.files.filter((_,i)=>!B.excluded.has(i));
  const alreadyExists=included.filter(img=>G.records[img.name]);
  const toCreate=included.filter(img=>!G.records[img.name]);
  const excCount=B.excluded.size;

  // Excluded hint
  const hint=document.getElementById('batch-excluded-hint');
  if(excCount>0){hint.textContent=`${excCount} cell${excCount===1?'':'s'} excluded — click again to re-include`;hint.classList.remove('hidden');}
  else hint.classList.add('hidden');

  // Skip message for already-existing records
  const skipMsg=document.getElementById('batch-skip-msg');
  if(alreadyExists.length>0)skipMsg.textContent=`⚠ ${alreadyExists.length} image${alreadyExists.length===1?'':'s'} already in records — will be skipped`;
  else skipMsg.textContent='';

  // Summary banner
  const summary=document.getElementById('batch-summary');
  if(cellType&&toCreate.length>0){
    summary.textContent=`Ready to finalize ${toCreate.length} cell${toCreate.length===1?'':'s'} as ${CELL_DISPLAY[cellType]||cellType}`;
    summary.classList.remove('hidden');
  } else if(cellType&&toCreate.length===0&&included.length>0){
    summary.textContent='All selected images are already in your records.';
    summary.classList.remove('hidden');
  } else {
    summary.classList.add('hidden');
  }

  // Enable commit only if we have something to do
  document.getElementById('batch-commit-btn').disabled=!(cellType&&toCreate.length>0);
}

function commitBatch(){
  const cellType=document.getElementById('batch-cell-select').value;
  const caseTag=document.getElementById('batch-case-tag').value.trim();
  const batchTags=document.getElementById('batch-tags').value.trim();
  const user=document.getElementById('batch-user').value.trim();
  if(!cellType){toast('⚠ Please select a cell type.');return;}
  if(!user){toast('⚠ Please enter your name.');return;}
  G.userName=user;

  const included=B.files.filter((_,i)=>!B.excluded.has(i));
  const toCreate=included.filter(img=>!G.records[img.name]);
  if(!toCreate.length){toast('⚠ Nothing to import.');return;}

  const ts=now();
  toCreate.forEach(img=>{
    // Cache the blob URL for display until images are pushed to repo
    if(img.url) _batchUrlCache[img.name]=img.url;
    // Create record
    const rec={
      image_id:'USR_'+Date.now()+'_'+Math.random().toString(36).slice(2,6),
      filename:img.name,case_tag:caseTag,uploaded_by:user,upload_date:ts,
      tech_label:cellType,tech_id:user,tech_date:ts,tech_status:'finalized',
      image_quality:'acceptable',tech_confidence:'classic',
      path_label:'',path_id:'',path_date:'',path_status:'unlabeled',
      path_confidence:'',path_commentary:'',tags:batchTags,
      version:1,last_modified_by:user,last_modified_date:ts,
      audit_trail:[{user,role:'tech',action:`Batch finalized as ${cellType}`,timestamp:ts,version:1}],
      discussion_flag:'false',discussion_comment:'',discussion_flagged_by:'',discussion_date:'',
      correction_label:'',correction_reason:'',correction_note:'',correction_by:'',correction_date:'',
      path_review_method:'',
    };
    G.records[img.name]=rec;
  });

  const isAbBatch=batchTags.split(',').map(t=>t.trim().toLowerCase()).includes('aberration');
  toast(`✅ ${toCreate.length} cells imported${isAbBatch?' → Aberrations library':' as '+(CELL_DISPLAY[cellType]||cellType)}`);
  hideBatchPanel();
  setView(isAbBatch?'aberrations':cellType);
  refreshAll();
}

// Handle permalink on page load
```

## CSV Export Modal HTML
```html
<!-- EXPORT MODAL -->
<div class="export-overlay hidden" id="export-overlay" onclick="closeExportIfBg(event)">
  <div class="export-panel">
    <div class="export-header">
      <div class="export-title">✅ atlas.csv exported</div>
      <button class="dp-close" onclick="closeExportModal()">✕</button>
    </div>
    <div class="export-body">
      <div class="export-desc">Run these commands to deploy the updated atlas:</div>
      <div class="export-cmd-wrap">
        <code class="export-cmd" id="export-cmd-block"></code>
        <button class="export-copy-btn" id="export-copy-btn" onclick="copyExportCmds()">Copy</button>
      </div>
    </div>
    <div class="export-footer">
      <button class="btn primary" onclick="closeExportModal()">Done</button>
    </div>
  </div>
</div>
```

## CSV Export JavaScript
```js
// ── CSV EXPORT ─────────────────────────────────────────
function exportCSV(){
  if(!Object.keys(G.records).length){toast('⚠ No data to export.');return;}
  const rows=[CSV_FIELDS.join(',')];
  Object.values(G.records).forEach(r=>{
    rows.push(CSV_FIELDS.map(f=>f==='audit_trail_json'?csvEsc(JSON.stringify(r.audit_trail||[])):csvEsc(String(r[f]??''))).join(','));
  });
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([rows.join('\n')],{type:'text/csv'}));
  a.download='atlas.csv';a.click();
  const cmds='cp ~/Downloads/atlas.csv ~/Desktop/HemeAtlas/data/atlas.csv\ncd ~/Desktop/HemeAtlas\ngit add data/atlas.csv\ngit commit -m "Curate cells"\ngit push origin main';
  document.getElementById('export-cmd-block').textContent=cmds;
  document.getElementById('export-copy-btn').textContent='Copy';
  document.getElementById('export-overlay').classList.remove('hidden');
}
function closeExportModal(){document.getElementById('export-overlay').classList.add('hidden');}
function closeExportIfBg(e){if(e.target===document.getElementById('export-overlay'))closeExportModal();}
function copyExportCmds(){
  const cmds=document.getElementById('export-cmd-block').textContent;
  navigator.clipboard.writeText(cmds).then(()=>{
    const btn=document.getElementById('export-copy-btn');
    btn.textContent='Copied!';setTimeout(()=>{btn.textContent='Copy';},2000);
  });
}

// ── BULK APPROVAL ──────────────────────────────────────
```
