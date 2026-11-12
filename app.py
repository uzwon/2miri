import json
import math

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="함수로 조종하는 플래피 버드", page_icon="🐤", layout="wide")
st.title("🐤 함수로 조종하는 플래피 버드")
st.caption("함수의 계수를 바꾸어 새의 비행 경로를 설계하고, 파이프를 통과해 보세요!")

with st.sidebar:
    st.header("🎛️ 비행 경로 설계")
    mode = st.radio("함수 종류", ["사인함수", "이차함수"])
    st.subheader("함수 계수")
    if mode == "사인함수":
        a = st.slider("A · 진폭", 10, 100, 42, 1)
        b = st.slider("B · 진동수 계수", 0.005, 0.050, 0.016, 0.001, format="%.3f")
        c = st.slider("C · 위상(라디안)", -3.14, 3.14, 0.0, 0.05)
        d = st.slider("D · 중심 높이", 65, 285, 175, 5)
        formula = f"y = {a}sin({b:.3f}x {c:+.2f}) + {d}"
        params = {"a": a, "b": b, "c": c, "d": d}
    else:
        a = st.slider("a · 곡률", 0.0005, 0.0070, 0.0020, 0.0005, format="%.4f")
        h = st.slider("h · 꼭짓점의 x좌표", 100, 650, 370, 10)
        k = st.slider("k · 꼭짓점 높이", 40, 310, 90, 5)
        formula = f"y = {a:.4f}(x - {h})² + {k}"
        params = {"a": a, "h": h, "k": k}

    stage = st.select_slider("스테이지", options=[1, 2, 3], value=1)
    speed = st.slider("재생 속도", 1, 5, 2)
    show_preview = st.checkbox("예상 경로 표시", value=True)

st.markdown(f"**현재 설정:** `{formula}`")
st.info("📌 화면 좌표는 아래 방향으로 y가 증가합니다. 사인함수는 중심 높이와 진폭을, 이차함수는 곡률과 꼭짓점을 조절해 보세요.")

cfg = {
    "mode": "sin" if mode == "사인함수" else "quad",
    "params": params,
    "stage": stage,
    "speed": speed,
    "preview": show_preview,
}

html = r'''
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8" />
<style>
  *{box-sizing:border-box}body{margin:0;background:transparent;font-family:system-ui,-apple-system,'Malgun Gothic',sans-serif;color:#243347}
  .wrap{max-width:1050px;margin:auto}.panel{background:#fff;border:1px solid #dce4ef;border-radius:16px;padding:14px;box-shadow:0 4px 16px #132d4810}
  canvas{display:block;width:100%;border-radius:12px;background:#cceefa;touch-action:manipulation}
  .controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px}
  button{border:0;border-radius:10px;padding:11px 17px;font-weight:750;font-size:14px;cursor:pointer;background:#2778ec;color:white}
  button.secondary{background:#e8edf6;color:#264263}
  #status{font-weight:750;margin-left:auto}#detail{font-size:13px;color:#576679;margin-top:10px;line-height:1.55}
  .legend{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:13px;color:#52677b;margin-bottom:10px}
</style></head><body><div class="wrap"><div class="panel">
<div class="legend"><strong>🐤 함수 비행 실험실</strong><span>점선: 계획한 경로 | 파이프: 통과해야 할 구간</span></div>
<canvas id="game" width="960" height="370" role="img" aria-label="함수 그래프를 따라 나는 새와 파이프 장애물"></canvas>
<div class="controls">
<button id="start">▶ 비행 시작</button><button id="reset" class="secondary">↺ 처음으로</button>
<span id="status" aria-live="polite">계수를 조절하고 비행을 시작하세요.</span>
</div><div id="detail">각 파이프를 통과할 때 새의 중심뿐 아니라 몸체 반지름까지 고려해 충돌을 판정합니다.</div>
</div></div>
<script>
const cfg = __CONFIG__;
const canvas = document.getElementById('game'), ctx = canvas.getContext('2d');
const statusEl = document.getElementById('status'), detailEl = document.getElementById('detail');
const W = canvas.width, H=canvas.height, left=35, right=930, ground=345, birdR=12;
const pipeX=[235,445,655,860];
const gaps = {1:[177,153,191,160],2:[135,200,144,207],3:[209,120,214,134]}[cfg.stage];
const gapSize={1:112,2:92,3:74}[cfg.stage];
let x=left, running=false, finished=false, lastTime=0, passed=0, raf=0;
function f(x){const p=cfg.params;return cfg.mode==='sin' ? p.a*Math.sin(p.b*x+p.c)+p.d : p.a*(x-p.h)*(x-p.h)+p.k;}
function text(t,detail=''){statusEl.textContent=t;if(detail)detailEl.textContent=detail;}
function draw(){
 ctx.clearRect(0,0,W,H);
 const sky=ctx.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#b4e7ff');sky.addColorStop(1,'#f5fbff');ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);
 ctx.fillStyle='#fff';for(const [cx,cy] of [[100,60],[370,43],[740,68]]){ctx.beginPath();ctx.ellipse(cx,cy,34,12,0,0,Math.PI*2);ctx.ellipse(cx+18,cy-8,27,14,0,0,Math.PI*2);ctx.fill();}
 ctx.fillStyle='#8fd68a';ctx.fillRect(0,ground,W,H-ground);
 ctx.fillStyle='#5ebc69';ctx.fillRect(0,ground,W,5);
 for(let i=0;i<pipeX.length;i++){
  const px=pipeX[i], center=gaps[i], top=center-gapSize/2, bottom=center+gapSize/2;
  ctx.fillStyle='#3ca84e';ctx.fillRect(px,0,48,top);ctx.fillRect(px,bottom,48,ground-bottom);
  ctx.fillStyle='#278b41';ctx.fillRect(px-5,Math.max(0,top-12),58,12);ctx.fillRect(px-5,bottom,58,12);
  ctx.fillStyle='#174b2c';ctx.font='bold 14px sans-serif';ctx.fillText(String(i+1),px+17,Math.min(ground-12,bottom+30));
 }
 if(cfg.preview){
  ctx.strokeStyle='#2365e5';ctx.lineWidth=2.5;ctx.setLineDash([6,6]);ctx.beginPath();
  for(let px=left;px<=right;px+=3){const yy=f(px);if(px===left)ctx.moveTo(px,yy);else ctx.lineTo(px,yy);}
  ctx.stroke();ctx.setLineDash([]);
 }
 const y=f(x);
 ctx.save();ctx.translate(x,y);ctx.fillStyle='#f9ca48';ctx.beginPath();ctx.arc(0,0,birdR,0,2*Math.PI);ctx.fill();
 ctx.fillStyle='#e9a927';ctx.beginPath();ctx.ellipse(-5,4,6,4,0,0,Math.PI*2);ctx.fill();
 ctx.fillStyle='#1f2c38';ctx.beginPath();ctx.arc(5,-4,2.5,0,Math.PI*2);ctx.fill();
 ctx.fillStyle='#f58933';ctx.beginPath();ctx.moveTo(10,0);ctx.lineTo(20,4);ctx.lineTo(10,7);ctx.fill();ctx.restore();
 ctx.fillStyle='#244055';ctx.font='13px sans-serif';ctx.fillText(`통과: ${passed} / ${pipeX.length}`,15,22);
}
function collision(px,py){
 if(py-birdR<0 || py+birdR>ground)return '화면 경계와 충돌했습니다.';
 for(let i=0;i<pipeX.length;i++){
  let bx=pipeX[i], cy=gaps[i], top=cy-gapSize/2, bottom=cy+gapSize/2;
  if(px+birdR>bx && px-birdR<bx+48 && (py-birdR<top || py+birdR>bottom))return `${i+1}번 파이프에 충돌했습니다.`;
 }
 return null;
}
function stop(msg){running=false;finished=true;cancelAnimationFrame(raf);text(msg,`마지막 위치 x=${x.toFixed(1)}, y=${f(x).toFixed(1)} | 통과한 파이프 ${passed}개 | 슬라이더를 수정하거나 '처음으로'를 눌러 재도전하세요.`);document.getElementById('start').textContent='▶ 다시 시작';}
function tick(t){
 if(!running)return;if(!lastTime)lastTime=t;
 const dt=Math.min((t-lastTime)/1000,0.05);lastTime=t;
 // 1px 이하로 나누어 전진해 빠른 재생에서도 장애물을 통과하지 않도록 판정합니다.
 let travel=dt*(70+cfg.speed*55);
 while(travel>0){const step=Math.min(travel,1);x+=step;travel-=step;
  const hit=collision(x,f(x));if(hit){draw();stop(`💥 실패! ${hit}`);return;}
  passed=pipeX.filter(v=>x-birdR>v+48).length;
  if(x>=right){x=right;draw();stop(passed===pipeX.length?'🏆 성공! 모든 파이프 통과!':'비행 종료');return;}
 }
 draw();raf=requestAnimationFrame(tick);
}
function reset(){running=false;finished=false;cancelAnimationFrame(raf);x=left;lastTime=0;passed=0;document.getElementById('start').textContent='▶ 비행 시작';text('계수를 조절하고 비행을 시작하세요.','장애물의 위치는 스테이지마다 고정됩니다. 화면에 보이는 파란 점선을 참고하여 안전한 경로를 만들어 보세요.');draw();}
document.getElementById('start').onclick=()=>{if(finished)reset();if(running)return;running=true;lastTime=0;text('🚀 비행 중...');raf=requestAnimationFrame(tick);};
document.getElementById('reset').onclick=reset;
reset();
</script></body></html>
'''.replace('__CONFIG__', json.dumps(cfg, ensure_ascii=False))

components.html(html, height=480, scrolling=False)

with st.expander("📘 게임 속 수학 원리"):
    st.markdown("""
    **사인함수 모드**: `y = A sin(Bx + C) + D`에서 진폭은 `|A|`, 주기는 `2π/|B|`입니다. `C`는 위상, `D`는 수직 이동을 결정합니다.

    **이차함수 모드**: `y = a(x-h)² + k`에서 `(h, k)`가 꼭짓점이며 `a`는 포물선의 굽은 정도를 결정합니다. 화면에서는 y좌표가 커질수록 아래쪽으로 이동합니다.

    **충돌 판정**: 새의 중심 좌표와 반지름을 이용해 파이프의 위쪽 및 아래쪽 경계와 겹치는지 확인합니다.

    **수학 탐구**: 스테이지를 고정하고 계수를 하나씩 바꾸면서 성공 여부, 통과 파이프 수, 충돌 위치를 비교해 보세요.
    """)

st.caption("제작: Python + Streamlit + HTML Canvas · GitHub에 app.py 하나만 올려도 실행 가능합니다.")
