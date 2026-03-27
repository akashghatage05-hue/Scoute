from flask import Flask, render_template_string, redirect
from pathlib import Path
import json, re, subprocess, threading

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
.arb-table th{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#475569;padding:12px 16px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.06)}
.arb-row{border-bottom:1px solid rgba(255,255,255,0.04);transition:all 0.2s}
.arb-row:last-child{border-bottom:none}
.arb-row:hover{background:rgba(34,211,238,0.04);box-shadow:inset 3px 0 0 #a855f7}
.arb-row td{padding:14px 16px;font-size:14px;vertical-align:middle}
.rank-badge{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700}
.rank-1{background:rgba(234,179,8,0.12);color:#eab308;border:1px solid rgba(234,179,8,0.3)}
.rank-2{background:rgba(148,163,184,0.12);color:#94a3b8;border:1px solid rgba(148,163,184,0.3)}
.rank-3{background:rgba(180,120,60,0.12);color:#cd8a4a;border:1px solid rgba(180,120,60,0.3)}
.rank-n{background:rgba(255,255,255,0.04);color:#475569;border:1px solid rgba(255,255,255,0.08)}
.artist-name{font-weight:600;color:#e2e8f0;font-size:15px}
.sub-pill{display:inline-block;background:rgba(168,85,247,0.12);color:#a855f7;border:1px solid rgba(168,85,247,0.2);border-radius:6px;padding:2px 9px;font-size:11px}
.score-bar-wrap{display:flex;align-items:center;gap:10px}
.score-bar{height:6px;background:rgba(255,255,255,0.06);border-radius:3px;flex:1;overflow:hidden;min-width:80px}
.score-fill{height:100%;border-radius:3px;width:0%;transition:width 1.2s cubic-bezier(0.4,0,0.2,1)}
.score-val{font-size:13px;font-weight:600;min-width:38px;text-align:right}
.score-high{color:#22d3ee}.score-mid{color:#a855f7}.score-low{color:#64748b}
.meta-val{color:#94a3b8;font-size:13px}
.link-btn{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:500;text-decoration:none;transition:all 0.2s;margin-right:5px}
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

def yt_url(name): return f"https://music.youtube.com/search?q={name.replace(' ','+')}"
def sp_url(name): return f"https://open.spotify.com/search/{name.replace(' ','%20')}"

@app.route("/")
def home():
    arb = load_json(ARB_PATH)
    scout = load_json(SCOUT_PATH)
    emails = list(EMAILS_DIR.glob("*.md")) if EMAILS_DIR.exists() else []
    top_score = arb[0]['arbitrage_score'] if arb else 0

    stats = f"""<div class="stats">
<div class="stat-card"><div class="stat-num" id="c1" data-val="{len(scout)}">0</div><div class="stat-label">Trending Tracks</div></div>
<div class="stat-card"><div class="stat-num" id="c2" data-val="{len(arb)}">0</div><div class="stat-label">Artists Ranked</div></div>
<div class="stat-card"><div class="stat-num" id="c3" data-val="{len(emails)}">0</div><div class="stat-label">Emails Generated</div></div>
<div class="stat-card"><div class="stat-num" id="c4" data-val="{top_score:.2f}">0</div><div class="stat-label">Top Arb Score</div></div>
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
        rows += f"""<tr class="arb-row">
<td><div class="rank-badge {rclass}">{rank}</div></td>
<td><div class="artist-name">{name}</div></td>
<td><span class="sub-pill">{sub}</span></td>
<td><div class="score-bar-wrap"><div class="score-bar"><div class="score-fill" data-pct="{pct:.1f}" style="background:{bar_bg}"></div></div><span class="score-val {sclass}">{score:.2f}</span></div></td>
<td><span class="meta-val">{fans:,}</span></td>
<td><span class="meta-val">{reddit:,}</span></td>
<td><a href="{yt_url(name)}" target="_blank" class="link-btn link-yt">▶ YouTube</a><a href="{sp_url(name)}" target="_blank" class="link-btn link-sp">Spotify</a></td>
</tr>"""

    table = f'<div class="table-wrap"><table class="arb-table"><thead><tr><th>#</th><th>Artist</th><th>Subreddit</th><th>Arb Score</th><th>Deezer Fans</th><th>Reddit Score</th><th>Listen</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else '<div class="empty"><span class="empty-icon">🎵</span>No data yet — run the pipeline.</div>'

    body = f"""<div class="hero">
<div class="hero-eye">◆ AI Music Intelligence Platform</div>
<h1 class="hero-title">Discover Artists<br><span class="gradient-text">Before They Blow Up</span></h1>
<p class="hero-sub">Real-time Reddit signals. Zero guesswork. Pure arbitrage.</p>
{stats}</div>
<div class="section">
<div class="section-header"><div class="section-title">Arbitrage Opportunities</div>
<form method="POST" action="/run" style="margin:0"><button type="submit" class="btn-run">▶ Run Pipeline</button></form></div>
{table}</div>"""
    return render_template_string(HTML, page_title="Home", active="home", body=body)

@app.route("/scout")
def scout():
    data = load_json(SCOUT_PATH)
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
    files = sorted(EMAILS_DIR.glob("*.md"), reverse=True) if EMAILS_DIR.exists() else []
    cards = ""
    for f in files:
        parts=f.stem.split("_"); artist=parts[0].replace("-"," ").title() if parts else f.stem
        curator=parts[1].replace("-"," ").title() if len(parts)>1 else ""; raw_date=parts[2] if len(parts)>2 else ""
        date_fmt=f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date)==8 else raw_date
        dp=f'<span class="pill pill-c">{date_fmt}</span>' if date_fmt else ""
        cards += f"""<a href="/emails/{f.name}" class="email-card">
<div class="email-icon">✉</div>
<div class="email-title">{artist}</div>
<div class="email-sub">{"Curator: "+curator if curator else ""}</div>
<div class="email-foot">{dp}<span class="pill">{max(1,f.stat().st_size//1024)} KB</span></div></a>"""
    if not cards: cards = '<div class="empty"><span class="empty-icon">📭</span>No emails yet. Run the Ghostwriter.</div>'
    body = f"""<div class="page-head"><div><h1>Generated Pitch Emails</h1><p>{len(files)} emails ready</p></div><a href="/" class="btn-back">← Home</a></div>
<div class="section"><div class="email-grid">{cards}</div></div>"""
    return render_template_string(HTML, page_title="Emails", active="emails", body=body)

@app.route("/emails/<filename>")
def view_email(filename):
    fp = EMAILS_DIR / Path(filename).name
    if not fp.exists(): return redirect("/emails")
    raw = fp.read_text(encoding="utf-8")
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', raw, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 style="color:#a855f7;margin:1rem 0 0.5rem">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)
    html = html.replace("\n","<br>")
    title = fp.stem.replace("-"," ").replace("_"," — ",1).title()
    body = f"""<div class="page-head"><div><h1>{title}</h1><p>{fp.name}</p></div><a href="/emails" class="btn-back">← All Emails</a></div>
<div class="reader-wrap"><div class="reader-card">{html}</div></div>"""
    return render_template_string(HTML, page_title=title, active="emails", body=body)

@app.route("/run", methods=["POST"])
def run_pipeline():
    def _run():
        try: subprocess.run(["python","main.py"], cwd=Path(__file__).parent, timeout=120)
        except: pass
    threading.Thread(target=_run, daemon=True).start()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
