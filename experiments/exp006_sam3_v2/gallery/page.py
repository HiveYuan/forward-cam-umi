"""index.html for the v1 | v2 gallery. usage: page.py <out dir> <stats.json>"""
import json, sys
from pathlib import Path
out = Path(sys.argv[1]); st = json.load(open(sys.argv[2])); rows = json.load(open(out / 'rows.json'))
def f(x, d=3): return '–' if x is None else f'{x:.{d}f}'
figs = []
for r in sorted(rows, key=lambda r: (r['segment'], r['kind'] != 'even', r['i'])):
    kind = 'typical' if r['kind'] == 'even' else 'worst-v1'
    better = r['iou_v2'] - r['iou_v1']
    figs.append(f'<figure class="shot" data-seg="{r["segment"]}" data-kind="{kind}" data-gain="{better:.4f}" data-iou="{r["iou_v2"]:.4f}">'
                f'<img src="{r["src"]}" width="{r["w"]}" height="{r["h"]}" loading="lazy" alt="{r["segment"]} frame {r["i"]}: v1 and v2 masks against SAM2">'
                f'<figcaption><span class="seg">{r["segment"]}</span><span>frame {r["i"]}</span>'
                f'<span>IoU v1 {r["iou_v1"]:.2f} → v2 {r["iou_v2"]:.2f}</span><span class="kind">{kind}</span></figcaption></figure>')
segs = sorted({r['segment'] for r in rows})
A = st['audit']
page = f"""<title>glove7 SAM3 v2 Masks</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: contact sheet of v1|v2 comparison frames; audit table and pooled numbers on top. */
:root {{ --bg:#f4f5f3; --surface:#fff; --fg:#1d2421; --muted:#5d6a64; --line:#d8ddd9; --accent:#1f7a68; --good:#2f7d32; --bad:#b3261e;
  --sans:"IBM Plex Sans",system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#121614; --surface:#1a1f1d; --fg:#e3e8e5; --muted:#9aa8a1; --line:#2c3431; --accent:#5cc4ad; --good:#7fcb83; --bad:#f08a80; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#121614; --surface:#1a1f1d; --fg:#e3e8e5; --muted:#9aa8a1; --line:#2c3431; --accent:#5cc4ad; --good:#7fcb83; --bad:#f08a80; color-scheme:dark }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.55 var(--sans); padding-left:max(16px,env(safe-area-inset-left,0px)); padding-right:max(16px,env(safe-area-inset-right,0px)); padding-block:24px 48px; }}
.wrap {{ max-width:1320px; margin:0 auto; display:grid; gap:20px; }}
h1 {{ font-size:1.55rem; font-weight:600; margin:0; text-wrap:balance; }} h2 {{ font-size:1.05rem; margin:0 0 8px; }}
p {{ margin:0; max-width:76ch; color:var(--muted); }}
.tablewrap {{ overflow-x:auto; background:var(--surface); border:1px solid var(--line); border-radius:6px; }}
table {{ border-collapse:collapse; width:100%; font:.86rem var(--mono); font-variant-numeric:tabular-nums; }}
th,td {{ padding:7px 10px; text-align:right; border-bottom:1px solid var(--line); white-space:nowrap; }}
th:first-child,td:first-child {{ text-align:left; }} th {{ font-family:var(--sans); font-weight:600; color:var(--muted); }}
td.v2 {{ color:var(--good); font-weight:500; }}
.legend {{ display:flex; flex-wrap:wrap; gap:8px 18px; font-size:.92rem; }}
.sw {{ display:inline-block; width:14px; height:14px; border-radius:3px; vertical-align:-2px; margin-right:6px; }}
.bar {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; position:sticky; top:env(safe-area-inset-top,0px); background:var(--bg); padding-block:8px; z-index:5; border-bottom:1px solid var(--line); }}
.chip {{ font:500 .88rem var(--sans); padding:6px 12px; border-radius:999px; border:1px solid var(--line); background:var(--surface); color:var(--fg); cursor:pointer; }}
.chip[aria-pressed="true"] {{ background:var(--accent); border-color:var(--accent); color:var(--bg); }}
.chip:focus-visible,select:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
select {{ font:.88rem var(--sans); padding:6px 10px; border-radius:6px; border:1px solid var(--line); background:var(--surface); color:var(--fg); }}
.count {{ margin-left:auto; font:.85rem var(--mono); color:var(--muted); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,620px),1fr)); gap:14px; }}
.shot {{ margin:0; background:var(--surface); border:1px solid var(--line); border-radius:6px; overflow:hidden; }}
.shot img {{ display:block; width:100%; height:auto; max-width:100%; }}
.shot figcaption {{ display:flex; flex-wrap:wrap; gap:4px 14px; padding:8px 10px; font:.82rem var(--mono); color:var(--muted); }}
.seg {{ color:var(--fg); font-weight:500; }} .kind {{ margin-left:auto; text-transform:uppercase; letter-spacing:.05em; font-size:.72rem; }}
.sr {{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); }}
</style>
<div class="wrap">
 <header style="display:grid;gap:8px"><h1>SAM3 v2 motion masks on yam_glove7, against v1 and SAM2</h1>
 <p>exp006: v2 keeps a SAM3 text detection (hand, arm, cable) only when it stays attached to the tracked wearer and does not balloon onto
 the scene; it tracks the glove rig from denser ball-pose points and the held block from a fingertip point while the gripper is closed.
 Each image shows v1 (left) and v2 (right) on the same frame, each compared with SAM2. Judge each colour by what the pixels are:
 everything that moves on its own should be masked, static things should not.</p></header>
 <div class="legend"><span><i class="sw" style="background:#28be28"></i>both the SAM3 version and SAM2</span>
  <span><i class="sw" style="background:#00e6ff"></i>SAM2 only</span><span><i class="sw" style="background:#dc00ff"></i>SAM3 version only</span></div>
 <section><h2>Region audit (154 regions judged moving or static by two reviewers, the 60 most-disagreeing frames)</h2>
 <div class="tablewrap"><table><thead><tr><th>mask set</th><th>moving regions covered</th><th>static regions covered</th><th>held block covered (4 held frames)</th></tr></thead><tbody>
 <tr><td>SAM2 (exp001)</td><td>{A['sam2'][0]} / 80</td><td>{A['sam2'][1]} / 74</td><td>{A['sam2'][2]}</td></tr>
 <tr><td>SAM3 v1 (exp002)</td><td>{A['v1'][0]} / 80</td><td>{A['v1'][1]} / 74</td><td>{A['v1'][2]}</td></tr>
 <tr><td>SAM3 v2 (exp006)</td><td class="v2">{A['v2'][0]} / 80</td><td class="v2">{A['v2'][1]} / 74</td><td class="v2">{A['v2'][2]}</td></tr></tbody></table></div></section>
 <section><h2>All 8972 frames against SAM2 (agreement, not accuracy)</h2>
 <div class="tablewrap"><table><thead><tr><th>mask set</th><th>IoU median</th><th>IoU p10</th><th>SAM2 covered</th><th>inside SAM2</th><th>DROID-cell IoU median / p10</th><th>area</th></tr></thead><tbody>
 {''.join(f"<tr><td>{n}</td><td>{f(v['iou_median'])}</td><td>{f(v['iou_p10'])}</td><td>{f(v['recall_median'])}</td><td>{f(v['precision_median'])}</td><td>{f(v['cells_median'])} / {f(v['cells_p10'])}</td><td>{100*v['area']:.1f}%</td></tr>" for n, v in st['global'].items())}
 </tbody></table></div>
 <p style="margin-top:8px">{st.get('note', '')}</p></section>
 <div class="bar" role="toolbar" aria-label="Filter frames">
  <button class="chip" aria-pressed="true" data-kind="all">All</button><button class="chip" aria-pressed="false" data-kind="typical">Typical</button>
  <button class="chip" aria-pressed="false" data-kind="worst-v1">Worst for v1</button>
  <label for="seg" class="sr">Segment</label><select id="seg"><option value="">All segments</option>{''.join(f'<option value="{s}">{s}</option>' for s in segs)}</select>
  <label for="sort" class="sr">Sort</label><select id="sort"><option value="seg">Sort by segment</option><option value="gain">Largest change v1 → v2 first</option><option value="iou">v2 lowest IoU first</option></select>
  <span class="count" id="count"></span></div>
 <section class="grid" id="grid">{''.join(figs)}</section>
</div>
<script>
const grid=document.getElementById('grid'), shots=Array.from(grid.children); let kind='all';
function apply(){{ const seg=document.getElementById('seg').value, sort=document.getElementById('sort').value; let n=0;
 const L=shots.slice().sort((a,b)=> sort==='gain'? Math.abs(b.dataset.gain)-Math.abs(a.dataset.gain) : sort==='iou'? a.dataset.iou-b.dataset.iou : a.dataset.seg.localeCompare(b.dataset.seg));
 L.forEach(el=>{{ const show=(kind==='all'||el.dataset.kind===kind)&&(!seg||el.dataset.seg===seg); el.hidden=!show; if(show)n++; grid.appendChild(el); }});
 document.getElementById('count').textContent=n+' frames'; }}
document.querySelectorAll('.chip').forEach(b=>b.addEventListener('click',()=>{{ kind=b.dataset.kind; document.querySelectorAll('.chip').forEach(c=>c.setAttribute('aria-pressed',String(c===b))); apply(); }}));
document.getElementById('seg').addEventListener('change',apply); document.getElementById('sort').addEventListener('change',apply); apply();
</script>
"""
(out / 'index.html').write_text(page); print('ok', len(figs))
