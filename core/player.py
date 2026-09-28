from __future__ import annotations
import html
import json
from pathlib import Path
from urllib.parse import quote

def write_player(job_dir: Path, media: Path, transcript_json: Path) -> Path:
    data=json.loads(transcript_json.read_text(encoding="utf-8"))
    segments=data.get("segments",[])
    rel_media=Path("_work")/media.name
    payload=json.dumps(segments,ensure_ascii=False).replace("</","<\\/")
    title=html.escape(job_dir.name)
    src=quote(str(rel_media).replace("\\","/"))
    page=f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font:15px Segoe UI,Arial;margin:24px;background:#111;color:#eee}}video{{width:100%;max-height:65vh}}
#t{{margin-top:16px;display:grid;gap:5px}}.s{{padding:8px;border-radius:5px;background:#222;cursor:pointer}}
.active{{background:#3a4655}}small{{color:#aaa}}</style></head><body>
<h2>SS Transcribe-Translate</h2><video id="media" controls preload="metadata" src="{src}"></video>
<p><small>Click a transcript line to jump to its timestamp. The highlighted line follows playback.</small></p>
<div id="t"></div><script>
const segs={payload},v=document.getElementById('media'),box=document.getElementById('t');
function fmt(x){{const m=Math.floor(x/60),s=(x%60).toFixed(1).padStart(4,'0');return String(m).padStart(2,'0')+':'+s;}}
const els=segs.map((s,i)=>{{const e=document.createElement('div');e.className='s';e.innerHTML='<b>'+fmt(s.start)+'</b> '+(s.speaker?'['+s.speaker+'] ':'')+s.text;e.onclick=()=>v.currentTime=s.start;box.appendChild(e);return e;}});
v.ontimeupdate=()=>{{let n=0;for(let i=0;i<segs.length;i++)if(v.currentTime>=segs[i].start)n=i;els.forEach((e,i)=>e.classList.toggle('active',i===n));if(els[n])els[n].scrollIntoView({{block:'nearest'}});}};
</script></body></html>"""
    out=job_dir/"player.html"; out.write_text(page,encoding="utf-8"); return out
