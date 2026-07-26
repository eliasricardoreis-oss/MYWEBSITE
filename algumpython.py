import gd, json, uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# Adiciona suporte a HEAD para o monitoramento da hospedagem não dar erro 405
app = FastAPI()
client = gd.Client()
saved = []
conns = []

# Aceita tanto GET quanto HEAD na rota principal
@app.api_route("/", methods=["GET", "HEAD"])
async def get(): return HTMLResponse(html)

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    conns.append(ws)
    await ws.send_text(json.dumps({"t": "init", "b": saved}))
    try:
        while True:
            d = json.loads(await ws.receive_text())
            t = d.get("t")
            if t == "+":
                saved[:] = [b for b in saved if not (b["x"] == d["x"] and b["y"] == d["y"])]
                saved.append({"id": d["id"], "x": d["x"], "y": d["y"], "r": d.get("r", 0), "s": d.get("s", 1), "o": d.get("o", 1), "c": d.get("c", None)})
                for c in conns: await c.send_text(json.dumps({"t": "+", **saved[-1]}))
            elif t == "u":
                for b in saved:
                    if b["x"] == d["x"] and b["y"] == d["y"]:
                        b["r"] = d.get("r", b["r"]); b["s"] = d.get("s", b["s"])
                        b["o"] = d.get("o", b["o"]); b["c"] = d.get("c", b["c"])
                for c in conns: await c.send_text(json.dumps({"t": "init", "b": saved}))
            elif t == "-":
                saved[:] = [b for b in saved if not (b["x"] == d["x"] and b["y"] == d["y"])]
                for c in conns: await c.send_text(json.dumps({"t": "-", "x": d["x"], "y": d["y"]}))
    except WebSocketDisconnect: conns.remove(ws)

@app.get("/export")
async def exp():
    return {"g": ";".join([f"1,{b['id']},2,{b['x']},3,{b['y']}" + (f",6,{b['r']}" if b['r'] else "") + (f",128,{b['s']}" if b['s']!=1 else "") + (f",35,{b['o']}" if b['o']!=1 else "") for b in saved]) + ";"}

html = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>GD</title>
<style>body{font:14px sans-serif;background:#111;color:#fff;text-align:center}canvas{background:#1a1a1a;border:1px solid #333;display:block;margin:10px auto;cursor:crosshair}button{background:#333;color:#fff;border:1px solid #555;padding:6px 12px;margin:3px;cursor:pointer}.active{background:#2196f3}</style>
</head><body>
    <h3>GD Editor Minimal 🛠️</h3>
    <button style="background:#ff9800" onclick="ex()">📥 Exportar .TXT</button><div id="m"></div>
    <canvas id="cv" width="900" height="420"></canvas>
<script>
    const cv=document.getElementById('cv'),ctx=cv.getContext('2d'),S=30;let id=1,bs=[],lc=null;
    const items=[{id:1,n:"Bloco",c:"#4a90e2",t:"cu"},{id:8,n:"Espinho",c:"#e24a4a",t:"sp"},{id:35,n:"Yellow Pad",c:"#ffd700",t:"ci"},{id:36,n:"Yellow Orb",c:"#ffcc00",t:"ob"},{id:1332,n:"Red Orb",c:"#ff0000",t:"ob"},{id:12,n:"P Cubo",c:"#00ffcc",t:"pt"},{id:13,n:"P Ship",c:"#ff9900",t:"pt"},{id:47,n:"P Ball",c:"#cc66ff",t:"pt"}];
    items.forEach(i=>{const b=document.createElement('button');b.innerText=i.n;if(i.id===1)b.className='active';b.onclick=()=>{id=i.id;document.querySelectorAll('#m button').forEach(x=>x.classList.remove('active'));b.classList.add('active')};document.getElementById('m').appendChild(b)});
    const ws=new WebSocket(`${window.location.protocol==='https:'?'wws':'ws'}://${window.location.host}/ws`);
    function dr(){
        ctx.clearRect(0,0,cv.width,cv.height);ctx.strokeStyle='#222';
        for(let x=0;x<cv.width;x+=S)ctx.strokeRect(x,0,1,cv.height);for(let y=0;y<cv.height;y+=S)ctx.strokeRect(0,y,cv.width,1);
        bs.forEach(b=>{
            const cfg=items.find(i=>i.id===b.id)||{c:b.c||'#fff',t:'cu'};let dy=cv.height-b.y-S;
            ctx.save();ctx.translate(b.x+S/2,dy+S/2);ctx.rotate((b.r||0)*Math.PI/180);ctx.scale(b.s||1,b.s||1);ctx.globalAlpha=b.o!==undefined?b.o:1;ctx.fillStyle=b.c||cfg.c;
            if(cfg.t==="cu")ctx.fillRect(-S/2,-S/2,S,S);
            else if(cfg.t==="sp"){ctx.beginPath();ctx.moveTo(-S/2,S/2);ctx.lineTo(0,-S/2);ctx.lineTo(S/2,S/2);ctx.fill()}
            else if(cfg.t==="ci")ctx.fillRect(-S/2,5,S,5);
            else if(cfg.t==="ob"){ctx.beginPath();ctx.arc(0,0,8,0,Math.PI*2);ctx.fill()}
            else if(cfg.t==="pt")ctx.fillRect(-4,-S/2,8,S);
            ctx.restore()
        })
    }
    ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.t==='init')bs=d.b;else if(d.t==='+'){bs=bs.filter(b=>!(b.x===d.x&&b.y===d.y));bs.push(d)}else if(d.t==='-')bs=bs.filter(b=>!(b.x===d.x&&b.y===d.y));dr()};
    cv.addEventListener('contextmenu',e=>e.preventDefault());
    cv.addEventListener('mousedown',e=>{
        const r=cv.getBoundingClientRect(),x=Math.floor((e.clientX-r.left)/S)*S,y=Math.floor((cv.height-(e.clientY-r.top))/S)*S;
        if(e.button===0){ws.send(JSON.stringify({t:"+",id,x,y}));lc={x,y}}
        else if(e.button===2){ws.send(JSON.stringify({t:"-",x,y}));if(lc&&lc.x===x&&lc.y===y)lc=null}
    });
    window.dev={editor:{
        rotation:a=>{ws.send(JSON.stringify({t:"u",x:lc.x,y:lc.y,r:a}));return'Ok'},
        scale:s=>{ws.send(JSON.stringify({t:"u",x:lc.x,y:lc.y,s}));return'Ok'},
        opacity:o=>{ws.send(JSON.stringify({t:"u",x:lc.x,y:lc.y,o}));return'Ok'},
        color:c=>{ws.send(JSON.stringify({t:"u",x:lc.x,y:lc.y,c}));return'Ok'},
        info:()=>bs.find(b=>b.x===lc.x&&b.y===lc.y)
    }};
    function ex(){fetch('/export').then(r=>r.json()).then(d=>{const b=new Blob([d.g],{type:'text/plain'});const l=document.createElement('a');l.download='fase_gd.txt';l.href=window.URL.createObjectURL(b);document.body.appendChild(l);l.click();document.body.removeChild(l)})}
    window.onload=dr;
</script></body></html>
"""
if __name__ == "__main__": uvicorn.run(app, host="127.0.0.1", port=8000)
