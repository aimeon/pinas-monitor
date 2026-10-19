#!/usr/bin/env python3
"""Private, read-only SMART dashboard for PiNAS."""
import csv
import os
from pathlib import Path

from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
CSV_PATH = Path(os.environ.get("PINAS_CSV", "/var/log/pinas-smart/history.csv"))

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#10171b">
<title>PiNAS | Disk monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js" defer></script>
<style>
:root{color-scheme:dark;font-family:Inter,"IBM Plex Sans",system-ui,-apple-system,sans-serif;
  background:#10171b;color:#e5ecee;font-synthesis:none}
*{box-sizing:border-box}
body{margin:0;min-width:320px}
.shell{max-width:1180px;margin:auto;padding:0 32px 48px}
header{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:28px 0 24px;border-bottom:1px solid #2b393e}
.identity{display:flex;align-items:center;gap:14px}
.logo{width:38px;height:38px;border:1px solid #456d70;display:grid;place-items:center;color:#9dd0cf;
  font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:18px;font-weight:700;border-radius:6px}
h1{font-size:19px;letter-spacing:-.035em;font-weight:650;margin:0;line-height:1.3}
.subtitle{margin:3px 0 0;color:#91a3aa;font-size:12px}
.header-right{text-align:right}
.live{display:inline-flex;align-items:center;gap:8px;font-size:12px;color:#c2d0d3}
.dot{width:7px;height:7px;border-radius:50%;background:#7bbf9c;box-shadow:0 0 0 3px #7bbf9c15}
.dot.stale{background:#dfac68;box-shadow:none}.dot.error{background:#e0837c;box-shadow:none}
#updated{display:block;margin-top:7px;color:#91a3aa;font-size:11px;font-variant-numeric:tabular-nums}
.intro{display:flex;justify-content:space-between;align-items:baseline;gap:16px;margin:35px 0 17px}
h2{font-size:15px;font-weight:620;letter-spacing:-.015em;margin:0}
.eyebrow{font:10px ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.13em;text-transform:uppercase;color:#8299a1}
#drive-count{color:#90a3aa;font-size:12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,350px),1fr));gap:14px}
.card,.graph{border:1px solid #2b3a40;background:#182227;border-radius:7px;min-width:0}
.card{padding:23px 24px 18px}
.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:23px}
.drive-name{font-weight:640;font-size:17px;line-height:1.4;overflow-wrap:anywhere}
.drive-label{font-size:10px;color:#8ba0a8;text-transform:uppercase;letter-spacing:.12em;margin-bottom:6px}
.badge{font-size:10px;font-weight:650;letter-spacing:.045em;padding:5px 8px;border:1px solid #79583a;color:#e9bd84;border-radius:4px;white-space:nowrap}
.badge.ok{border-color:#376252;color:#93c7af}.badge.unknown{border-color:#53616a;color:#a4b2b9}
.hero{display:flex;align-items:baseline;gap:8px;padding-bottom:23px;border-bottom:1px solid #2b393e}
.hero .value{font-size:43px;letter-spacing:-.055em;font-weight:540;line-height:1;font-variant-numeric:tabular-nums}
.hero .unit{color:#a3b5bb;font-size:15px}.hero .hint{font-size:11px;color:#8ea1a8;margin-left:auto}
.metrics{display:grid;grid-template-columns:1fr 1fr;column-gap:18px;row-gap:23px;padding-top:23px}
.metric-label{font-size:11px;color:#91a5ac;margin-bottom:7px}.metric-value{font-size:20px;line-height:1.2;font-weight:560;font-variant-numeric:tabular-nums;letter-spacing:-.025em}
.metric-value small{font-size:11px;color:#91a5ac;font-weight:400;margin-left:3px}
.section-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:34px 0 17px}
.graphs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.graph{padding:22px 23px 17px}.graph-head{margin-bottom:20px}.graph-title{font-size:13px;font-weight:600}
.graph-subtitle{font-size:11px;color:#91a5ac;margin-top:5px}
.chart-box{position:relative;height:245px}
canvas{display:block;width:100%!important;height:100%!important}
.chart-fallback{color:#9aaeb4;font-size:12px;display:none;padding:15px 0}
#error{color:#f0b2a3;font-size:12px;margin-top:15px;min-height:0}
footer{margin-top:31px;padding-top:16px;border-top:1px solid #2b393e;color:#8ea0a6;font-size:11px;line-height:1.7}
.empty{color:#9fb0b7;padding:30px 24px;border:1px dashed #3a4c52;border-radius:7px;grid-column:1/-1}
@media(max-width:760px){.shell{padding:0 16px 32px}header{padding:20px 0}.graphs{grid-template-columns:1fr}.intro{margin-top:27px}}
@media(max-width:480px){.header-right{max-width:46%}.logo{width:33px;height:33px}.card{padding:20px}.hero .value{font-size:38px}.graph{padding:18px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;animation:none!important;transition:none!important}}
</style>
</head>
<body><main class="shell">
<header>
  <div class="identity"><div class="logo" aria-hidden="true">P/</div><div><h1>PiNAS Monitor</h1><p class="subtitle">Disk health / SMART telemetry</p></div></div>
  <div class="header-right"><div class="live"><span class="dot" id="indicator"></span><span id="connection">Connecting</span></div><time id="updated">Waiting for first reading</time></div>
</header>
<div id="error" role="alert"></div>
<section aria-labelledby="drives-heading">
  <div class="intro"><div><div class="eyebrow">01 / Hardware</div><h2 id="drives-heading" style="margin-top:6px">Storage devices</h2></div><span id="drive-count"></span></div>
  <div class="cards" id="cards"><div class="empty">Loading SMART records…</div></div>
</section>
<section aria-labelledby="history-heading">
  <div class="section-head"><div><div class="eyebrow">02 / History</div><h2 id="history-heading" style="margin-top:6px">Recorded trends</h2></div><span class="eyebrow">Latest 4,000 records</span></div>
  <div class="graphs">
    <article class="graph"><div class="graph-head"><div class="graph-title">Temperature</div><div class="graph-subtitle">Degrees Celsius</div></div><div class="chart-box"><canvas id="temp" role="img" aria-label="Disk temperature history"></canvas></div><div class="chart-fallback" id="temp-fallback"></div></article>
    <article class="graph"><div class="graph-head"><div class="graph-title">Available capacity</div><div class="graph-subtitle">Free space, GB</div></div><div class="chart-box"><canvas id="space" role="img" aria-label="Disk free space history"></canvas></div><div class="chart-fallback" id="space-fallback"></div></article>
  </div>
</section>
<footer>Source: smartctl / PiNAS collector · Refreshes every 60 seconds · SMART health is not a substitute for backups.<br>Values are shown as reported by the collector. Total drive capacity is not inferred from free space.</footer>
</main>
<script>
'use strict';
let charts=[];
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=value=>{if(value===null||value===undefined||String(value).trim()==='')return null;const n=Number(value);return Number.isFinite(n)?n:null};
const show=value=>value===null||value===undefined||String(value).trim()===''?'—':esc(value);
const displayNum=value=>{const n=num(value);return n===null?'—':n.toLocaleString(undefined,{maximumFractionDigits:2})};
const timestamp=value=>{const t=Date.parse(value);return Number.isFinite(t)?t:null};
function metric(label,value,unit=''){
  return `<div><div class="metric-label">${label}</div><div class="metric-value">${displayNum(value)}${num(value)!==null&&unit?`<small>${unit}</small>`:''}</div></div>`;
}
function statusClass(status){const s=String(status||'').trim().toUpperCase();return s==='OK'||s==='PASSED'||s==='HEALTHY'?'ok':!s||s==='UNKNOWN'||s==='N/A'?'unknown':''}
function card(x){
  const state=String(x.status||'UNKNOWN').trim()||'UNKNOWN';
  return `<article class="card"><div class="card-head"><div><div class="drive-label">Storage device</div><div class="drive-name">${esc(x.drive||'Unnamed device')}</div></div><span class="badge ${statusClass(state)}">${esc(state)}</span></div>
    <div class="drive-label" style="margin-bottom:10px">Drive temperature</div>
    <div class="hero"><span class="value">${displayNum(x.temperature_c)}</span><span class="unit">${num(x.temperature_c)!==null?'°C':''}</span><span class="hint">Latest reading</span></div>
    <div class="metrics">${metric('Free space',x.free_gb,'GB')}${metric('SSD wear',x.wear_pct,'%')}${metric('Power-on time',x.power_on_hours,'h')}${metric('Media errors',x.media_errors)}${metric('Unsafe shutdowns',x.unsafe_shutdowns)}</div></article>`;
}
function renderChart(id,rows,field){
 const fallback=$(id+'-fallback');fallback.style.display='none';
 if(typeof Chart==='undefined'){fallback.textContent='Charts unavailable. Chart.js needs an internet connection.';fallback.style.display='block';return;}
 const grouped=new Map();
 for(const r of rows){const n=num(r[field]),t=timestamp(r.timestamp);if(n===null||t===null)continue;const name=String(r.drive||'Unknown');if(!grouped.has(name))grouped.set(name,[]);grouped.get(name).push({x:t,y:n});}
 const palette=['#83c7c4','#e6b17d','#a7b6e6','#d7a3c4','#afc889'];
 const datasets=[...grouped].map(([name,values],i)=>({label:name,data:values.sort((a,b)=>a.x-b.x),borderColor:palette[i%palette.length],backgroundColor:palette[i%palette.length],pointRadius:0,pointHoverRadius:4,borderWidth:2,tension:.15,spanGaps:false}));
 if(!datasets.length){fallback.textContent='No numeric measurements available yet.';fallback.style.display='block';return;}
 const chart=new Chart($(id),{type:'line',data:{datasets},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'nearest',intersect:false},plugins:{legend:{position:'bottom',labels:{color:'#b5c4c9',boxWidth:9,boxHeight:9,padding:16,font:{size:11}}},tooltip:{callbacks:{title:items=>items.length?new Date(items[0].parsed.x).toLocaleString():''}}},scales:{x:{type:'linear',grid:{color:'#26353b'},border:{display:false},ticks:{color:'#81969f',maxTicksLimit:5,font:{size:10},callback:v=>new Date(v).toLocaleDateString(undefined,{month:'short',day:'numeric'})}},y:{grid:{color:'#304047'},border:{display:false},ticks:{color:'#81969f',maxTicksLimit:5,font:{size:10}}}}}});
 charts.push(chart);
}
async function load(){
 try{
  const response=await fetch('/api/history',{cache:'no-store'});
  if(!response.ok){let detail='';try{detail=(await response.json()).error||''}catch(_){}throw Error(detail||`HTTP ${response.status}`)}
  const data=await response.json();if(!Array.isArray(data)||!data.length)throw Error('No SMART records yet. Check that the collector has written history.csv.');
  const rows=data.filter(r=>r&&typeof r==='object').sort((a,b)=>(timestamp(a.timestamp)??0)-(timestamp(b.timestamp)??0));
  const last=new Map();for(const r of rows)last.set(String(r.drive||'Unknown'),r);
  $('cards').innerHTML=[...last.values()].map(card).join('')||'<div class="empty">No drives found.</div>';
  $('drive-count').textContent=`${last.size} ${last.size===1?'device':'devices'}`;
  const latest=rows.reduce((m,r)=>Math.max(m,timestamp(r.timestamp)??0),0);
  $('updated').textContent=latest?'Last reading · '+new Date(latest).toLocaleString():'Reading time unavailable';
  const stale=!latest||Date.now()-latest>2*60*60*1000;
  $('indicator').className='dot'+(stale?' stale':'');$('connection').textContent=stale?'Data may be stale':'Collector data available';
  charts.forEach(c=>c.destroy());charts=[];
  renderChart('temp',rows,'temperature_c');renderChart('space',rows,'free_gb');
  $('error').textContent='';
 }catch(error){$('error').textContent=error.message;$('indicator').className='dot error';$('connection').textContent='Data unavailable';}
}
load();setInterval(load,60000);
</script>
</body></html>'''


@app.get("/")
def index():
    return render_template_string(HTML)


@app.get("/api/history")
def history():
    if not CSV_PATH.is_file():
        return jsonify(error="SMART history unavailable"), 503
    try:
        with CSV_PATH.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except (OSError, UnicodeError, csv.Error):
        app.logger.exception("Unable to read SMART history")
        return jsonify(error="Unable to read SMART history"), 503
    return jsonify(rows[-4000:])


if __name__ == "__main__":
    app.run(
        host=os.environ.get("PINAS_HOST", "127.0.0.1"),
        port=int(os.environ.get("PINAS_PORT", "8765")),
        debug=False,
    )
