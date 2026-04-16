from flask import Flask, render_template_string, redirect, request
from pathlib import Path
import json, os, re, subprocess, threading
from dotenv import load_dotenv
from scoute.agents.ghostwriter import SAMPLE_CURATORS
load_dotenv()

app = Flask(__name__)

ARB_PATH   = Path("scoute/data/arbitrage_results.json")
SCOUT_PATH = Path("scoute/data/scout_results.json")
EMAILS_DIR = Path("scoute/outputs/emails")

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SCOUTE — {{ page_title }}</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Space Grotesk',sans-serif;background:#080812;color:#e2e8f0;min-height:100vh;overflow-x:hidden}
canvas#bg{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}
.app{position:relative;z-index:1}
nav{display:flex;align-items:center;gap:2rem;padding:1rem 2rem;background:rgba(8,8,18,0.85);backdrop-filter:blur(20px);border-bottom:1px solid rgba(168,85,247,0.2);position:sticky;top:0;z-index:100}
.logo{font-size:18px;font-weight:700;background:linear-gradient(135deg,#a855f7,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.5px;text-decoration:none}
.logo-dot{display:inline-block;width:8px;height:8px;background:#a855f7;border-radius:2px;margin-right:6px;box-shadow:0 0 8px #a855f7;vertical-align:middle}
.nav-links{display:flex;gap:1.5rem}
.nav-link{color:#94a3b8;font-size:14px;padding-bottom:2px;border-bottom:2px solid transparent;transition:all 0.2s;text-decoration:none}
.nav-link:hover,.nav-link.active{color:#e2e8f0;border-bottom-color:#a855f7}
.live-badge{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:12px;color:#22d3ee;letter-spacing:1px}
.live-dot{width:6px;height:6px;background:#22d3ee;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.4;transform:scale(1.4)}}
@keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.hero{padding:3rem 2rem 2rem;animation:fadeUp 0.6s ease}
.hero-eye{font-size:12px;color:#a855f7;letter-spacing:2px;text-transform:uppercase;margin-bottom:1rem}
.hero-title{font-size:44px;font-weight:700;line-height:1.1;margin-bottom:0.75rem}
.gradient-text{background:linear-gradient(135deg,#a855f7,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero-sub{color:#64748b;font-size:16px;margin-bottom:2rem}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:2.5rem}
.stat-card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:1.25rem;transition:all 0.3s;animation:fadeUp 0.6s ease both}
.stat-card:hover{border-color:rgba(168,85,247,0.5);box-shadow:0 0 24px rgba(168,85,247,0.15);transform:translateY(-3px)}
.stat-num{font-size:34px;font-weight:700;background:linear-gradient(135deg,#a855f7,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stat-label{font-size:11px;color:#475569;letter-spacing:1.5px;text-transform:uppercase;margin-top:6px}
.section{padding:0 2rem 3rem;animation:fadeUp 0.7s ease both}
.section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.25rem}
.section-title{font-size:18px;font-weight:600;color:#e2e8f0}
.btn-run{background:linear-gradient(135deg,#a855f7,#7c3aed);color:white;border:none;padding:9px 20px;border-radius:9px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:6px;transition:all 0.2s;font-family:'Space Grotesk',sans-serif;text-decoration:none}
.btn-run:hover{transform:scale(1.04);box-shadow:0 0 24px rgba(168,85,247,0.5)}
.btn-back{background:rgba(255,255,255,0.05);color:#94a3b8;border:1px solid rgba(255,255,255,0.1);padding:8px 16px;border-radius:9px;font-size:13px;font-weight:500;cursor:pointer;text-decoration:none;transition:all 0.2s;font-family:'Space Grotesk',sans-serif}
.btn-back:hover{background:rgba(255,255,255,0.08);color:#e2e8f0}
.table-wrap{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:16px;overflow:hidden}
.arb-table{width:100%;border-collapse:collapse}
.arb-table th{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#475569;padding:12px 16px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.06);cursor:pointer;user-select:none;white-space:nowrap}
.arb-table th:hover{color:#a855f7}
.sort-ind{margin-left:4px;opacity:0.5;font-size:10px}
.sort-ind.active{opacity:1;color:#a855f7}
.arb-row{border-bottom:1px solid rgba(255,255,255,0.04);transition:opacity 0.3s ease,background 0.2s,box-shadow 0.2s}
.arb-row.filtered-out{opacity:0.06;pointer-events:none}
.arb-row:last-child{border-bottom:none}
.arb-row:hover{background:rgba(34,211,238,0.04);box-shadow:inset 3px 0 0 #a855f7}
.arb-row td{padding:14px 16px;font-size:14px;vertical-align:middle}
.rank-badge{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700}
.rank-1{background:rgba(234,179,8,0.12);color:#eab308;border:1px solid rgba(234,179,8,0.3)}
.rank-2,.rank-3,.rank-n{background:rgba(255,255,255,0.04);color:#475569;border:1px solid rgba(255,255,255,0.08)}
.artist-name{font-weight:600;color:#e2e8f0;font-size:15px}
.sub-pill{display:inline-block;background:rgba(168,85,247,0.12);color:#a855f7;border:1px solid rgba(168,85,247,0.2);border-radius:6px;padding:2px 9px;font-size:11px}
.score-bar-wrap{display:flex;align-items:center;gap:10px}
.score-bar{height:6px;background:rgba(255,255,255,0.06);border-radius:3px;flex:1;overflow:hidden;min-width:80px}
.score-fill{height:100%;border-radius:3px;width:0%;transition:width 1.2s cubic-bezier(0.4,0,0.2,1)}
.score-val{font-size:13px;font-weight:600;min-width:38px;text-align:right}
.score-high{color:#22d3ee}.score-mid{color:#a855f7}.score-low{color:#64748b}
.meta-val{color:#94a3b8;font-size:13px}
.link-btn{display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:500;text-decoration:none;transition:all 0.2s;white-space:nowrap;line-height:1}
.link-yt{background:rgba(34,211,238,0.08);color:#22d3ee;border:1px solid rgba(34,211,238,0.2)}
.link-yt:hover{background:rgba(34,211,238,0.18)}
.link-sp{background:rgba(34,197,94,0.08);color:#22c55e;border:1px solid rgba(34,197,94,0.2)}
.link-sp:hover{background:rgba(34,197,94,0.18)}
.track-list{display:flex;flex-direction:column;gap:8px}
.track-row{display:flex;align-items:center;gap:1rem;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:1rem;transition:all 0.2s}
.track-row:hover{border-color:rgba(168,85,247,0.3);box-shadow:0 0 16px rgba(168,85,247,0.1)}
.track-num{width:28px;height:28px;border-radius:7px;background:rgba(255,255,255,0.05);display:flex;align-items:center;justify-content:center;font-size:12px;color:#64748b;flex-shrink:0}
.track-info{flex:1;min-width:0}
.track-artist{font-weight:600;color:#e2e8f0;font-size:14px}
.track-song{color:#64748b;font-size:13px;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.track-right{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.pill{display:inline-block;padding:3px 9px;border-radius:6px;font-size:11px;font-weight:500}
.pill-p{background:rgba(168,85,247,0.12);color:#a855f7;border:1px solid rgba(168,85,247,0.2)}
.pill-c{background:rgba(34,211,238,0.1);color:#22d3ee;border:1px solid rgba(34,211,238,0.2)}
.pill{background:rgba(255,255,255,0.05);color:#94a3b8;border:1px solid rgba(255,255,255,0.08)}
.email-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem}
.email-card{display:block;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:1.25rem;text-decoration:none;transition:all 0.25s}
.email-card:hover{border-color:rgba(168,85,247,0.4);box-shadow:0 0 24px rgba(168,85,247,0.12);transform:translateY(-3px)}
.email-icon{font-size:24px;margin-bottom:0.75rem}
.email-title{font-size:15px;font-weight:600;color:#e2e8f0;margin-bottom:4px}
.email-sub{font-size:13px;color:#64748b;margin-bottom:0.75rem}
.email-foot{display:flex;gap:6px;flex-wrap:wrap}
.page-head{display:flex;align-items:flex-start;justify-content:space-between;padding:2rem 2rem 1.5rem;flex-wrap:wrap;gap:1rem}
.page-head h1{font-size:28px;font-weight:700;color:#e2e8f0}
.page-head p{color:#64748b;font-size:14px;margin-top:4px}
.reader-wrap{padding:0 2rem 3rem}
.reader-card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:2rem;max-width:700px;line-height:1.8;color:#cbd5e1;font-size:15px}
.reader-card h1{font-size:22px;color:#e2e8f0;margin-bottom:1rem}
.reader-card hr{border:none;border-top:1px solid rgba(255,255,255,0.08);margin:1.5rem 0}
.reader-card strong{color:#e2e8f0}
.reader-card a{color:#22d3ee;text-decoration:none}
.empty{text-align:center;padding:4rem 2rem;color:#475569;font-size:15px}
.empty-icon{font-size:32px;display:block;margin-bottom:1rem}
.filter-card{background:rgba(255,255,255,0.04);border:1px solid rgba(168,85,247,0.2);border-radius:16px;padding:1.5rem;margin-bottom:1.25rem;backdrop-filter:blur(10px)}
.filter-grid{display:grid;grid-template-columns:2fr 1fr 1.5fr 1.5fr;gap:1rem;align-items:end}
.filter-group{display:flex;flex-direction:column;gap:6px}
.filter-label{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#a855f7;font-weight:600}
.filter-input{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:9px;color:#e2e8f0;padding:8px 12px;font-size:13px;font-family:'Space Grotesk',sans-serif;outline:none;transition:border-color 0.2s;width:100%}
.filter-input:focus{border-color:rgba(168,85,247,0.5)}
.filter-select{-webkit-appearance:none;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='7' viewBox='0 0 10 7'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23475569' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 10px center;background-color:rgba(255,255,255,0.06);padding-right:28px;cursor:pointer}
.filter-select option{background:#0f0f1f;color:#e2e8f0}
.filter-range{-webkit-appearance:none;appearance:none;width:100%;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;outline:none;cursor:pointer;margin-top:6px}
.filter-range::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:linear-gradient(135deg,#a855f7,#22d3ee);cursor:pointer;box-shadow:0 0 8px rgba(168,85,247,0.5)}
.filter-range::-moz-range-thumb{width:16px;height:16px;border:none;border-radius:50%;background:linear-gradient(135deg,#a855f7,#22d3ee);cursor:pointer}
.fan-range{display:flex;align-items:center;gap:6px}
.fan-sep{color:#475569;font-size:13px;flex-shrink:0}
.filter-footer{display:flex;align-items:center;justify-content:space-between;margin-top:1.25rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,0.06)}
.count-text{font-size:13px;color:#64748b}
.count-text b{color:#a855f7;font-weight:600}
.btn-reset{background:transparent;border:1px solid rgba(255,255,255,0.1);color:#64748b;padding:6px 14px;border-radius:8px;font-size:12px;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s}
.btn-reset:hover{border-color:rgba(168,85,247,0.4);color:#a855f7}
@media(max-width:768px){.filter-grid{grid-template-columns:1fr}.fan-range{flex-direction:column;align-items:stretch}.fan-sep{display:none}}
/* Stars */
.stars-filled{color:#eab308;letter-spacing:1px;font-size:15px}
.stars-empty{color:#1e293b;letter-spacing:1px;font-size:15px}
/* Match Curators button */
.btn-pitch{background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.25);color:#a855f7;padding:5px 12px;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;white-space:nowrap}
.btn-pitch:hover{background:rgba(168,85,247,0.22);box-shadow:0 0 12px rgba(168,85,247,0.25)}
/* Modal */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.72);backdrop-filter:blur(6px);z-index:1000;display:flex;align-items:center;justify-content:center;padding:1rem}
.modal-card{background:#0d0d1e;border:1px solid rgba(168,85,247,0.3);border-radius:20px;width:100%;max-width:460px;overflow:hidden;box-shadow:0 0 60px rgba(168,85,247,0.18)}
.modal-header{display:flex;align-items:flex-start;justify-content:space-between;padding:1.5rem;border-bottom:1px solid rgba(255,255,255,0.07)}
.modal-title{font-size:16px;font-weight:700;color:#e2e8f0}
.modal-sub{font-size:13px;color:#64748b;margin-top:3px}
.modal-close{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);color:#94a3b8;width:30px;height:30px;border-radius:8px;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all 0.2s;font-family:sans-serif}
.modal-close:hover{background:rgba(255,255,255,0.12);color:#e2e8f0}
.curator-match{display:flex;align-items:center;gap:12px;padding:1rem 1.5rem;border-bottom:1px solid rgba(255,255,255,0.05)}
.curator-match:last-child{border-bottom:none}
.match-info{flex:1;min-width:0}
.match-name{font-size:14px;font-weight:600;color:#e2e8f0}
.match-curator{font-size:12px;color:#64748b;margin-top:2px}
.match-followers{font-size:12px;color:#a855f7;font-weight:600;white-space:nowrap}
.btn-generate{background:linear-gradient(135deg,#a855f7,#7c3aed);color:#fff;border:none;padding:6px 12px;border-radius:7px;font-size:11px;font-weight:600;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;white-space:nowrap;margin-left:6px}
.btn-generate:disabled{opacity:0.35;cursor:not-allowed}
.btn-generate:not(:disabled):hover{transform:scale(1.04);box-shadow:0 0 12px rgba(168,85,247,0.4)}
.modal-no-match{padding:2rem 1.5rem;text-align:center;color:#475569;font-size:14px}
/* Waitlist */
.waitlist-wrap{max-width:540px;margin:3rem auto;padding:0 2rem}
.waitlist-card{background:rgba(255,255,255,0.03);border:1px solid rgba(168,85,247,0.25);border-radius:20px;padding:2.5rem;text-align:center}
.waitlist-icon{font-size:36px;margin-bottom:1rem}
.waitlist-title{font-size:26px;font-weight:700;color:#e2e8f0;margin-bottom:0.75rem}
.waitlist-sub{color:#64748b;font-size:15px;line-height:1.6;margin-bottom:2rem}
.waitlist-form{display:flex;flex-direction:column;gap:12px;text-align:left}
.waitlist-input{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:10px;color:#e2e8f0;padding:11px 14px;font-size:14px;font-family:'Space Grotesk',sans-serif;outline:none;transition:border-color 0.2s;width:100%}
.waitlist-input:focus{border-color:rgba(168,85,247,0.5)}
.waitlist-submit{background:linear-gradient(135deg,#a855f7,#7c3aed);color:#fff;border:none;padding:12px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;margin-top:4px}
.waitlist-submit:hover{transform:scale(1.02);box-shadow:0 0 24px rgba(168,85,247,0.4)}
.waitlist-success{background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.25);border-radius:12px;padding:1rem 1.25rem;color:#22c55e;font-size:14px;font-weight:500;margin-top:1rem;display:none}
/* Waitlist modal inside pitch modal */
.waitlist-mini{padding:1.25rem 1.5rem;border-top:2px solid rgba(168,85,247,0.2);margin-top:4px}
.waitlist-mini-title{font-size:14px;font-weight:700;color:#e2e8f0;margin-bottom:4px}
.waitlist-mini-sub{font-size:12px;color:#64748b;margin-bottom:12px}
.waitlist-mini-row{display:flex;flex-direction:column;gap:8px}
.waitlist-mini-input{width:100%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:10px;color:#e2e8f0;padding:10px 11px;font-size:13px;font-family:'Space Grotesk',sans-serif;outline:none;box-sizing:border-box}
.waitlist-mini-input:focus{border-color:rgba(168,85,247,0.4)}
.waitlist-mini-btn{width:100%;background:#a855f7;color:#fff;border:none;padding:10px 16px;border-radius:10px;font-size:12px;font-weight:600;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:background 0.2s}
.waitlist-mini-btn:hover{background:#9333ea}
.waitlist-mini-success{font-size:13px;color:#22c55e;margin-top:10px;display:none;font-weight:500}
/* Admin waitlist table */
.admin-table{width:100%;border-collapse:collapse;font-size:14px}
.admin-table th{text-align:left;padding:10px 14px;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#475569;border-bottom:1px solid rgba(255,255,255,0.08)}
.admin-table td{padding:12px 14px;border-bottom:1px solid rgba(255,255,255,0.04);color:#cbd5e1}
.admin-table tr:last-child td{border-bottom:none}
</style>
</head>
<body>
<canvas id="bg"></canvas>
<div class="app">
  <nav>
    <a href="/" class="logo"><span class="logo-dot"></span>SCOUTE</a>
    <div class="nav-links">
      <a href="/" class="nav-link {{ 'active' if active=='home' else '' }}">Home</a>
      <a href="/scout" class="nav-link {{ 'active' if active=='scout' else '' }}">Scout</a>
      <a href="/emails" class="nav-link {{ 'active' if active=='emails' else '' }}">Emails</a>
    </div>
    <div class="live-badge"><div class="live-dot"></div>LIVE</div>
  </nav>
  {{ body | safe }}
</div>
<canvas id="bg"></canvas>
<script>
const canvas=document.getElementById('bg');
const ctx=canvas.getContext('2d');
let W,H,dots=[];
function resize(){W=canvas.width=window.innerWidth;H=canvas.height=window.innerHeight;}
resize();window.addEventListener('resize',resize);
for(let i=0;i<70;i++)dots.push({x:Math.random()*3000,y:Math.random()*2000,r:Math.random()*1.5+0.3,vx:(Math.random()-0.5)*0.25,vy:(Math.random()-0.5)*0.25,o:Math.random()*0.35+0.05});
function draw(){ctx.clearRect(0,0,W,H);dots.forEach(d=>{d.x+=d.vx;d.y+=d.vy;if(d.x<0||d.x>W)d.vx*=-1;if(d.y<0||d.y>H)d.vy*=-1;ctx.beginPath();ctx.arc(d.x,d.y,d.r,0,Math.PI*2);ctx.fillStyle=`rgba(168,85,247,${d.o})`;ctx.fill();});requestAnimationFrame(draw);}
draw();
function animateCounter(el,target,isFloat){let count=0;const step=target/60;const t=setInterval(()=>{count+=step;if(count>=target){count=target;clearInterval(t);}el.textContent=isFloat?count.toFixed(2):Math.floor(count);},16);}
function applyFilters(){
  const artist=(document.getElementById('f-artist')||{value:''}).value.toLowerCase();
  const sub=(document.getElementById('f-sub')||{value:''}).value;
  const scoreMin=parseFloat((document.getElementById('f-score')||{value:0}).value)||0;
  const fansMinVal=(document.getElementById('f-fans-min')||{value:''}).value;
  const fansMaxVal=(document.getElementById('f-fans-max')||{value:''}).value;
  const fansMin=fansMinVal?parseInt(fansMinVal):0;
  const fansMax=fansMaxVal?parseInt(fansMaxVal):Infinity;
  const rows=document.querySelectorAll('.arb-row');
  let shown=0;
  rows.forEach(row=>{
    const match=
      row.dataset.artist.toLowerCase().includes(artist)&&
      (!sub||row.dataset.sub===sub)&&
      parseFloat(row.dataset.score)>=scoreMin&&
      parseInt(row.dataset.fans)>=fansMin&&
      parseInt(row.dataset.fans)<=fansMax;
    if(match){
      if(row._hideTimer){clearTimeout(row._hideTimer);row._hideTimer=null;}
      row.style.display='';
      requestAnimationFrame(()=>row.classList.remove('filtered-out'));
      shown++;
    }else{
      if(!row.classList.contains('filtered-out')){
        row.classList.add('filtered-out');
        row._hideTimer=setTimeout(()=>{if(row.classList.contains('filtered-out'))row.style.display='none';},310);
      }
    }
  });
  const countEl=document.getElementById('f-count');
  if(countEl)countEl.textContent=shown;
}
function resetFilters(){
  const fa=document.getElementById('f-artist');if(fa)fa.value='';
  const fs=document.getElementById('f-sub');if(fs)fs.value='';
  const fsc=document.getElementById('f-score');if(fsc){fsc.value=0;const sv=document.getElementById('f-score-val');if(sv)sv.textContent='0.00';}
  const fmin=document.getElementById('f-fans-min');if(fmin)fmin.value='';
  const fmax=document.getElementById('f-fans-max');if(fmax)fmax.value='';
  applyFilters();
}
document.addEventListener('DOMContentLoaded',()=>{
  const fa=document.getElementById('f-artist');
  const fs=document.getElementById('f-sub');
  const fsc=document.getElementById('f-score');
  const fmin=document.getElementById('f-fans-min');
  const fmax=document.getElementById('f-fans-max');
  if(fa)fa.addEventListener('input',applyFilters);
  if(fs)fs.addEventListener('change',applyFilters);
  if(fsc)fsc.addEventListener('input',function(){const sv=document.getElementById('f-score-val');if(sv)sv.textContent=parseFloat(this.value).toFixed(2);applyFilters();});
  if(fmin)fmin.addEventListener('input',applyFilters);
  if(fmax)fmax.addEventListener('input',applyFilters);
});
// ── Curator data (12 real Spotify playlists — auto-generated 2026-04-16, Indian music) ────
const CURATORS=[
  {name:"Travel Songs (Hindi) | Bollywood Roadtrip Hindi | Indie Travels",curator:"Aesthetic Gaane",followers:223089,genres:["hindi indie","bollywood","indian indie"]},
  {name:"\ud83c\uddee\ud83c\uddf3Indian remix\ud83c\uddee\ud83c\uddf3",curator:"Bertram O'Reilly Poulsen",followers:177658,genres:["indian rap","bollywood remix","desi beats"]},
  {name:"Desi songs which make you wanna chammak challo",curator:"Moxie",followers:79305,genres:["desi beats","bollywood","indian pop"]},
  {name:"Indian meme music",curator:"Aksel",followers:54514,genres:["indian rap","desi hip hop","indian pop"]},
  {name:"Hindi Pop Songs",curator:"mahimarajvirsingh",followers:44237,genres:["hindi pop","bollywood","hindi indie"]},
  {name:"Best Hindi Songs of All Time 2025",curator:"Rohit",followers:28439,genres:["bollywood","hindi pop","indian indie"]},
  {name:"Famous Indian Song",curator:"Carlo.Chua",followers:25198,genres:["indian indie","bollywood","indian pop"]},
  {name:"hIndie",curator:"Rajanand Lonkar",followers:21979,genres:["hindi indie","indian indie","indie pop"]},
  {name:"Trending Hindi Rap Songs 2026",curator:"i lovemusic",followers:21549,genres:["indian hip hop","hindi rap","desi rap"]},
  {name:"INDIAN PARTY HITS",curator:"Aliyah",followers:17384,genres:["indian pop","bollywood","desi rap"]},
  {name:"EK Number Hip Hop (Indian Hip Hop Hits)",curator:"Radial India",followers:13310,genres:["indian hip hop","desi hip hop","hip hop"]},
  {name:"Desi Party",curator:"shenaeze",followers:12356,genres:["desi beats","bhangra","bollywood"]},
];
const SUB_GENRES={
  hiphopheads:["hip hop","rap"],indieheads:["indie pop","indie rock"],
  listentothis:["indie","bedroom pop","lo-fi"],rnb:["r&b","soul","neo soul"],
  electronicmusic:["electronic","house","techno","dance"],
  undergroundhiphop:["hip hop","underground hip hop","rap"],
  chicagorap:["hip hop","rap","trap"],ukdrill:["uk drill","trap"],
  afrobeats:["afrobeats","afro house"],latin:["latin","latin house"],
  kpop:["k-pop","k-indie","k-r&b"],jmusic:["j-pop","city pop","j-rock","japanese indie"],
  bedroom_pop:["bedroom pop","indie pop","lo-fi","dream pop"],
  poppunkers:["pop punk","punk","emo"],emo:["emo","post-hardcore","indie rock"],
  metalcore:["metalcore","post-hardcore","hardcore"],DJs:["electronic","house","techno","dance"],
  funk:["funk","soul","jazz funk"],soul:["soul","r&b","gospel soul"],
  jazz:["jazz","jazz rap","jazz funk"],futurebeats:["future beats","electronic","downtempo","ambient"],
  IndianHipHop:["indian hip hop","desi rap","hindi rap","desi hip hop"],
  hindimusic:["hindi pop","bollywood","hindi indie","indian indie"],
  IndianaMusic:["hindi pop","bollywood","indian indie","indian pop"],
  bollywood:["bollywood","hindi pop","indian pop","desi beats"],
  IndieIndia:["indian indie","hindi indie","indie pop","bollywood"],
  sangheats:["desi beats","bhangra","bollywood","indian pop"],
  desirap:["desi rap","indian hip hop","hindi rap","desi hip hop"],
};
// ── Curator modal ─────────────────────────────────────────────────────────────
function openPitchModal(btn){
  const row=btn.closest('.arb-row');
  const artistName=row.dataset.artist;
  const subreddit=row.dataset.sub;
  document.getElementById('modal-artist-name').textContent=artistName+' \u2014 '+subreddit;
  document.getElementById('modal-waitlist-artist').value=artistName;
  document.getElementById('modal-waitlist-success').style.display='none';
  document.getElementById('modal-waitlist-name').value='';
  document.getElementById('modal-waitlist-email').value='';
  const artistGenres=(SUB_GENRES[subreddit]||[]);
  const matches=CURATORS.map(c=>({
    ...c,
    score:c.genres.filter(g=>artistGenres.some(ag=>g.includes(ag)||ag.includes(g))).length
  })).filter(c=>c.score>0).sort((a,b)=>b.score-a.score||b.followers-a.followers).slice(0,3);
  const html=matches.length?matches.map((c,i)=>`
    <div class="curator-match">
      <div style="width:22px;height:22px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;${i===0?'background:rgba(234,179,8,0.12);color:#eab308;border:1px solid rgba(234,179,8,0.3)':i===1?'background:rgba(148,163,184,0.12);color:#94a3b8;border:1px solid rgba(148,163,184,0.3)':'background:rgba(180,120,60,0.12);color:#cd8a4a;border:1px solid rgba(180,120,60,0.3)'}">${i+1}</div>
      <div class="match-info"><div class="match-name">${c.name}</div><div class="match-curator">${c.curator}</div></div>
      <span class="match-followers">${c.followers.toLocaleString()}</span>
    </div>`).join(''):'<div class="modal-no-match">No genre matches found for this subreddit.</div>';
  document.getElementById('modal-matches').innerHTML=html;
  document.getElementById('pitch-modal').style.display='flex';
  document.body.style.overflow='hidden';
}
function closePitchModal(){
  document.getElementById('pitch-modal').style.display='none';
  document.body.style.overflow='';
}
async function submitWaitlistMini(){
  const name=document.getElementById('modal-waitlist-name').value.trim();
  const email=document.getElementById('modal-waitlist-email').value.trim();
  const artist=document.getElementById('modal-waitlist-artist').value;
  if(!name||!email)return;
  await fetch('/waitlist/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,email,source:'pitch_modal',artist})});
  document.getElementById('modal-waitlist-success').style.display='block';
  document.getElementById('modal-waitlist-name').value='';
  document.getElementById('modal-waitlist-email').value='';
}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closePitchModal();});
// ── Table sorting ─────────────────────────────────────────────────────────────
let _sortCol=3,_sortAsc=false;
function sortTable(col,type){
  const tbody=document.querySelector('#arb-table tbody');
  if(!tbody)return;
  const rows=[...tbody.querySelectorAll('tr')];
  if(_sortCol===col){_sortAsc=!_sortAsc;}else{_sortCol=col;_sortAsc=false;}
  rows.sort((a,b)=>{
    const ac=a.cells[col],bc=b.cells[col];
    if(!ac||!bc)return 0;
    const av=ac.dataset.sort!==undefined?ac.dataset.sort:ac.textContent.trim();
    const bv=bc.dataset.sort!==undefined?bc.dataset.sort:bc.textContent.trim();
    let cmp=0;
    if(type==='float')cmp=parseFloat(av||0)-parseFloat(bv||0);
    else if(type==='int')cmp=parseInt(av||0)-parseInt(bv||0);
    else cmp=av.localeCompare(bv);
    return _sortAsc?cmp:-cmp;
  });
  rows.forEach(r=>tbody.appendChild(r));
  document.querySelectorAll('.sort-ind').forEach(el=>{el.textContent='';el.classList.remove('active');});
  const si=document.getElementById('si'+col);
  if(si){si.textContent=_sortAsc?'\u2193':'\u2191';si.classList.add('active');}
}
window.addEventListener('load',()=>{
  const c1=document.getElementById('c1');
  const c2=document.getElementById('c2');
  const c3=document.getElementById('c3');
  const c4=document.getElementById('c4');
  if(c1)animateCounter(c1,parseInt(c1.dataset.val),false);
  if(c2)animateCounter(c2,parseInt(c2.dataset.val),false);
  if(c3)animateCounter(c3,parseInt(c3.dataset.val),false);
  if(c4)animateCounter(c4,parseFloat(c4.dataset.val),true);
  setTimeout(()=>{document.querySelectorAll('.score-fill').forEach(b=>{b.style.width=b.dataset.pct+'%';});},200);
});
</script>
</body>
</html>"""

def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    except:
        return []

def load_data(path: Path, bin_name: str) -> list:
    """
    Pull from JSONbin when JSONBIN_KEY is set, fall back to local file.
    Bin IDs are read from .jsonbin_ids.json (written by the local pipeline).
    """
    if os.environ.get("JSONBIN_KEY"):
        try:
            from scoute.storage import pull_from_jsonbin
            data = pull_from_jsonbin(bin_name)
            if data is not None:
                return data
        except Exception:
            pass
    return load_json(path)

def yt_url(name): return f"https://music.youtube.com/search?q={name.replace(' ','+')}"
def sp_url(name): return f"https://open.spotify.com/search/{name.replace(' ','%20')}"

def star_html(score):
    n = 5 if score > 1.0 else 4 if score > 0.7 else 3 if score > 0.5 else 2 if score > 0.3 else 1
    return f'<span class="stars-filled">{"&#9733;"*n}</span><span class="stars-empty">{"&#9733;"*(5-n)}</span>'


@app.route("/")
def home():
    arb = load_data(ARB_PATH, "arbitrage_results")
    scout = load_data(SCOUT_PATH, "scout_results")
    top_score = arb[0]['arbitrage_score'] if arb else 0

    stats = f"""<div class="stats">
<div class="stat-card"><div class="stat-num" id="c1" data-val="{len(scout)}">0</div><div class="stat-label">Trending Tracks</div></div>
<div class="stat-card"><div class="stat-num" id="c2" data-val="{len(arb)}">0</div><div class="stat-label">Artists Ranked</div></div>
<div class="stat-card"><div class="stat-num" id="c3" data-val="{len(SAMPLE_CURATORS)}">0</div><div class="stat-label">Playlist Curators</div></div>
<div class="stat-card"><div class="stat-num" id="c4" data-val="{top_score:.2f}">0</div><div class="stat-label">Top Breakout Score</div></div>
</div>"""

    max_score = arb[0]['arbitrage_score'] if arb else 1
    rows = ""
    for i, a in enumerate(arb):
        rank = i+1
        rclass = {1:'rank-1',2:'rank-2',3:'rank-3'}.get(rank,'rank-n')
        score = a.get('arbitrage_score',0)
        fans = a.get('deezer_fans',0)
        reddit = a.get('reddit_score',0)
        name = a.get('artist','')
        sub = a.get('subreddit','')
        pct = min(100, score/max_score*100)
        sclass = 'score-high' if score>=1.0 else 'score-mid' if score>=0.5 else 'score-low'
        bar_bg = 'linear-gradient(90deg,#a855f7,#22d3ee)' if score>=1.0 else 'linear-gradient(90deg,#7c3aed,#a855f7)' if score>=0.5 else 'linear-gradient(90deg,#334155,#475569)'
        safe_name = name.replace('"', '&quot;')
        n_stars = 5 if score > 1.0 else 4 if score > 0.7 else 3 if score > 0.5 else 2 if score > 0.3 else 1
        rows += f"""<tr class="arb-row" data-artist="{safe_name}" data-sub="{sub}" data-score="{score}" data-fans="{fans}">
<td data-sort="{rank}"><div class="rank-badge {rclass}">{rank}</div></td>
<td><div class="artist-name">{name}</div></td>
<td><span class="sub-pill">{sub}</span></td>
<td data-sort="{score}"><div class="score-bar-wrap"><div class="score-bar"><div class="score-fill" data-pct="{pct:.1f}" style="background:{bar_bg}"></div></div><span class="score-val {sclass}">{score:.2f}</span></div></td>
<td data-sort="{fans}"><span class="meta-val">{fans:,}</span></td>
<td data-sort="{reddit}"><span class="meta-val">{reddit:,}</span></td>
<td><div style="display:flex;flex-direction:row;gap:6px;align-items:center;flex-wrap:nowrap;"><a href="{yt_url(name)}" target="_blank" class="link-btn link-yt">▶ YouTube</a><a href="{sp_url(name)}" target="_blank" class="link-btn link-sp">Spotify</a></div></td>
<td data-sort="{n_stars}">{star_html(score)}</td>
<td><button class="btn-pitch" onclick="openPitchModal(this)">Match Curators</button></td>
</tr>"""

    subs = sorted({a.get('subreddit','') for a in arb if a.get('subreddit','')})
    sub_opts = ''.join(f'<option value="{s}">{s}</option>' for s in subs)
    total = len(arb)

    filter_card = f"""<div class="filter-card">
<div class="filter-grid">
  <div class="filter-group">
    <label class="filter-label">Search Artist</label>
    <input type="text" id="f-artist" class="filter-input" placeholder="Type an artist name...">
  </div>
  <div class="filter-group">
    <label class="filter-label">Subreddit</label>
    <select id="f-sub" class="filter-input filter-select">
      <option value="">All subreddits</option>
      {sub_opts}
    </select>
  </div>
  <div class="filter-group">
    <label class="filter-label">Min Breakout Score: <span id="f-score-val">0.00</span></label>
    <input type="range" id="f-score" class="filter-range" min="0" max="2" step="0.01" value="0">
  </div>
  <div class="filter-group">
    <label class="filter-label">Deezer Fans</label>
    <div class="fan-range">
      <input type="number" id="f-fans-min" class="filter-input" placeholder="Min" min="0" style="flex:1;min-width:0">
      <span class="fan-sep">&#8211;</span>
      <input type="number" id="f-fans-max" class="filter-input" placeholder="Max" min="0" style="flex:1;min-width:0">
    </div>
  </div>
</div>
<div class="filter-footer">
  <span class="count-text">Showing <b id="f-count">{total}</b> of <b>{total}</b> artists</span>
  <button class="btn-reset" onclick="resetFilters()">Reset filters</button>
</div>
</div>""" if arb else ""

    table = f'{filter_card}<div class="table-wrap"><table class="arb-table" id="arb-table"><thead><tr><th onclick="sortTable(0,\'int\')">#<span class="sort-ind" id="si0"></span></th><th onclick="sortTable(1,\'str\')">Artist<span class="sort-ind" id="si1"></span></th><th onclick="sortTable(2,\'str\')">Subreddit<span class="sort-ind" id="si2"></span></th><th onclick="sortTable(3,\'float\')" class="sort-active">Breakout Score<span class="sort-ind active" id="si3">&#8593;</span></th><th onclick="sortTable(4,\'int\')">Deezer Fans<span class="sort-ind" id="si4"></span></th><th onclick="sortTable(5,\'int\')">Reddit Score<span class="sort-ind" id="si5"></span></th><th>Listen</th><th onclick="sortTable(7,\'int\')">Potential<span class="sort-ind" id="si7"></span></th><th>Match Curators</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else '<div class="empty"><span class="empty-icon">🎵</span>No data yet — run the pipeline.</div>'

    modal = """<div id="pitch-modal" class="modal-overlay" style="display:none" onclick="if(event.target===this)closePitchModal()">
<div class="modal-card">
<div class="modal-header">
  <div><div class="modal-title">Top Curator Matches</div><div class="modal-sub" id="modal-artist-name"></div></div>
  <button class="modal-close" onclick="closePitchModal()">&#215;</button>
</div>
<div id="modal-matches"></div>
<div class="waitlist-mini">
  <div class="waitlist-mini-title">&#10024; Want these emails written automatically?</div>
  <div class="waitlist-mini-sub">Join the waitlist — first 50 get 3 months free</div>
  <input type="hidden" id="modal-waitlist-artist" value="">
  <div class="waitlist-mini-row">
    <input class="waitlist-mini-input" id="modal-waitlist-name" type="text" placeholder="Your name">
    <input class="waitlist-mini-input" id="modal-waitlist-email" type="email" placeholder="Email address">
    <button class="waitlist-mini-btn" onclick="submitWaitlistMini()">Join</button>
  </div>
  <div class="waitlist-mini-success" id="modal-waitlist-success">&#127881; You're on the list! We'll email you at launch.</div>
</div>
</div>
</div>"""

    on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))
    use_jsonbin = bool(os.environ.get("JSONBIN_KEY"))
    run_btn = (
        '<form method="POST" action="/run" style="margin:0"><button type="submit" class="btn-run">&#8635; Refresh Data</button></form>'
        if use_jsonbin else
        '<form method="POST" action="/run" style="margin:0"><button type="submit" class="btn-run">&#9654; Run Pipeline</button></form>'
    )
    body = f"""<div class="hero">
<div class="hero-eye">&#9670; AI Music Intelligence — India</div>
<h1 class="hero-title">Discover Artists<br><span class="gradient-text">Before They Blow Up</span></h1>
<p class="hero-sub">India's first AI music intelligence platform. Find Indian artists before they blow up.</p>
{stats}</div>
<div class="section">
<div class="section-header"><div class="section-title">Arbitrage Opportunities</div>
{run_btn}</div>
{table}
</div>
{modal}"""
    return render_template_string(HTML, page_title="Home", active="home", body=body)

@app.route("/scout")
def scout():
    data = load_data(SCOUT_PATH, "scout_results")
    rows = ""
    for i,t in enumerate(data):
        artist=t.get('artist',''); song=t.get('song',''); sub=t.get('subreddit','')
        url=t.get('url',''); rurl=t.get('reddit_url',''); ups=t.get('upvotes',t.get('score',0)); cmts=t.get('comments',0)
        song_html = f'<a href="{url}" target="_blank" style="color:#22d3ee;text-decoration:none">{song}</a>' if url else song or '—'
        thread = f'<a href="{rurl}" target="_blank" class="pill pill-c">Thread ↗</a>' if rurl else ''
        rows += f"""<div class="track-row">
<div class="track-num">{i+1}</div>
<div class="track-info"><div class="track-artist">{artist}</div><div class="track-song">{song_html}</div></div>
<div class="track-right"><span class="pill pill-p">{sub}</span><span class="pill">{ups:,} ↑</span><span class="pill">{cmts:,} 💬</span>{thread}</div>
</div>"""
    if not rows: rows = '<div class="empty"><span class="empty-icon">🔍</span>No tracks yet. Run the pipeline.</div>'
    body = f"""<div class="page-head"><div><h1>Scout Results</h1><p>{len(data)} trending tracks found across Reddit</p></div><a href="/" class="btn-back">← Home</a></div>
<div class="section"><div class="track-list">{rows}</div></div>"""
    return render_template_string(HTML, page_title="Scout", active="scout", body=body)

@app.route("/emails")
def emails():
    signup_success = request.args.get("joined") == "1"
    success_msg = '<div class="waitlist-success" style="display:block">&#10003; You\'re on the list! We\'ll be in touch soon.</div>' if signup_success else ''
    body = f"""<div class="waitlist-wrap">
<div class="waitlist-card">
<div class="waitlist-icon">&#9993;</div>
<h1 class="waitlist-title">AI Pitch Emails — Coming Soon</h1>
<p class="waitlist-sub">AI-powered pitch emails are coming soon. Join the waitlist to get early access and <strong style="color:#a855f7">3 months free</strong>.</p>
<form class="waitlist-form" method="POST" action="/waitlist/signup-form">
  <input class="waitlist-input" type="text" name="name" placeholder="Your name" required>
  <input class="waitlist-input" type="email" name="email" placeholder="Email address" required>
  <button type="submit" class="waitlist-submit">Join the Waitlist &#8594;</button>
</form>
{success_msg}
</div>
</div>"""
    return render_template_string(HTML, page_title="Emails — Coming Soon", active="emails", body=body)

def _save_signup(name: str, email: str, source: str = "emails_page", artist: str = "") -> bool:
    """Append a waitlist signup to JSONbin."""
    try:
        from scoute.storage import pull_from_jsonbin, push_to_jsonbin
        existing = pull_from_jsonbin("waitlist") or []
        existing.append({
            "name": name,
            "email": email,
            "source": source,
            "artist": artist,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        })
        push_to_jsonbin(existing, "waitlist")
        return True
    except Exception:
        return False

@app.route("/waitlist/signup", methods=["POST"])
def waitlist_signup_json():
    """JSON endpoint used by the Pitch Me modal."""
    data = request.get_json(silent=True) or {}
    name = data.get("name","").strip()
    email = data.get("email","").strip()
    if name and email:
        _save_signup(name, email, source=data.get("source","modal"), artist=data.get("artist",""))
    return {"ok": True}

@app.route("/waitlist/signup-form", methods=["POST"])
def waitlist_signup_form():
    """Form POST endpoint used by the emails Coming Soon page."""
    name = request.form.get("name","").strip()
    email = request.form.get("email","").strip()
    if name and email:
        _save_signup(name, email, source="emails_page")
    return redirect("/emails?joined=1")

@app.route("/waitlist")
def waitlist_admin():
    """Admin view of all waitlist signups — password protected."""
    pwd = request.args.get("password","")
    admin_pwd = os.environ.get("ADMIN_PASSWORD","")
    if not admin_pwd or pwd != admin_pwd:
        return """<html><body style="background:#080812;color:#e2e8f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<form method="GET" style="background:rgba(255,255,255,0.04);border:1px solid rgba(168,85,247,0.25);border-radius:16px;padding:2rem;display:flex;flex-direction:column;gap:12px;min-width:280px">
<div style="font-size:18px;font-weight:700;margin-bottom:4px">Waitlist Admin</div>
<input name="password" type="password" placeholder="Admin password" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:8px;color:#e2e8f0;padding:10px 12px;font-size:14px;outline:none">
<button type="submit" style="background:linear-gradient(135deg,#a855f7,#7c3aed);color:#fff;border:none;padding:10px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer">View Signups</button>
</form></body></html>"""
    try:
        from scoute.storage import pull_from_jsonbin
        signups = pull_from_jsonbin("waitlist") or []
    except Exception:
        signups = []
    rows = "".join(
        f'<tr><td>{i+1}</td><td>{s.get("name","")}</td><td>{s.get("email","")}</td><td>{s.get("source","")}</td><td>{s.get("artist","")}</td><td>{s.get("timestamp","")}</td></tr>'
        for i, s in enumerate(signups)
    )
    return f"""<html><body style="background:#080812;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;padding:2rem">
<h1 style="margin-bottom:1.5rem;font-size:22px">Waitlist Signups <span style="font-size:14px;color:#a855f7;font-weight:400">({len(signups)} total)</span></h1>
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:14px;overflow:hidden">
<table class="admin-table" style="width:100%;border-collapse:collapse;font-size:14px">
<thead><tr style="border-bottom:1px solid rgba(255,255,255,0.08)"><th style="padding:12px 16px;text-align:left;color:#475569;font-size:11px;letter-spacing:1.5px;text-transform:uppercase">#</th><th style="padding:12px 16px;text-align:left;color:#475569;font-size:11px;letter-spacing:1.5px;text-transform:uppercase">Name</th><th style="padding:12px 16px;text-align:left;color:#475569;font-size:11px;letter-spacing:1.5px;text-transform:uppercase">Email</th><th style="padding:12px 16px;text-align:left;color:#475569;font-size:11px;letter-spacing:1.5px;text-transform:uppercase">Source</th><th style="padding:12px 16px;text-align:left;color:#475569;font-size:11px;letter-spacing:1.5px;text-transform:uppercase">Artist</th><th style="padding:12px 16px;text-align:left;color:#475569;font-size:11px;letter-spacing:1.5px;text-transform:uppercase">Time</th></tr></thead>
<tbody style="color:#cbd5e1">{rows if rows else '<tr><td colspan="6" style="padding:2rem;text-align:center;color:#475569">No signups yet.</td></tr>'}</tbody>
</table></div></body></html>"""

@app.route("/run", methods=["POST"])
def run_pipeline():
    if os.environ.get("JSONBIN_KEY"):
        # Pull fresh data from JSONbin and save to local files
        try:
            from scoute.storage import pull_from_jsonbin
            scout_data = pull_from_jsonbin("scout_results")
            arb_data = pull_from_jsonbin("arbitrage_results")
            if scout_data is not None:
                SCOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
                SCOUT_PATH.write_text(json.dumps(scout_data, indent=2), encoding="utf-8")
            if arb_data is not None:
                ARB_PATH.parent.mkdir(parents=True, exist_ok=True)
                ARB_PATH.write_text(json.dumps(arb_data, indent=2), encoding="utf-8")
        except Exception:
            pass
        return redirect("/")
    # Local dev: run the full pipeline in a background thread
    def _run():
        try: subprocess.run(["python","main.py"], cwd=Path(__file__).parent, timeout=300)
        except: pass
    threading.Thread(target=_run, daemon=True).start()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
