"""FLOW LAB — 수평 관의 이상 유체 흐름 시뮬레이터.

실행: streamlit run main.py
모형: 비압축성·비점성·정상 흐름, 수평 관, 동일 유선의 베르누이 방정식.
주의: 실제 배관 설계나 안전성 판단에 사용하지 마세요.
"""

from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="FLOW LAB | 유체역학 가상 실험실", page_icon="🌊", layout="wide")

# 기본 계산 상수
PIPE_LENGTH = 3.0  # m
INLET_DIAMETER = 0.10  # m
POINTS = 301


@st.cache_data(show_spinner=False)
def make_pipe_profile(throat_ratio: float, exit_ratio: float, n: int = POINTS):
    """부드러운 축소·확대 구간을 가진 관의 지름 배열을 생성한다.

    throat_ratio, exit_ratio는 '지름 비율'이며 단면적 비율이 아니다.
    """
    x = np.linspace(0.0, PIPE_LENGTH, n)
    d = np.full_like(x, INLET_DIAMETER)
    throat_d = INLET_DIAMETER * throat_ratio
    exit_d = INLET_DIAMETER * exit_ratio

    # 0.6~1.3 m: 입구 지름에서 목 지름으로 축소
    mask = (x >= 0.6) & (x < 1.3)
    t = (x[mask] - 0.6) / 0.7
    smooth = (1 - np.cos(np.pi * t)) / 2
    d[mask] = INLET_DIAMETER + (throat_d - INLET_DIAMETER) * smooth

    # 1.3~1.7 m: 목 구간
    d[(x >= 1.3) & (x <= 1.7)] = throat_d

    # 1.7~2.4 m: 출구 지름으로 확대
    mask = (x > 1.7) & (x <= 2.4)
    t = (x[mask] - 1.7) / 0.7
    smooth = (1 - np.cos(np.pi * t)) / 2
    d[mask] = throat_d + (exit_d - throat_d) * smooth
    d[x > 2.4] = exit_d
    return x, d


def calculate_flow(throat_ratio: float, exit_ratio: float, q_lps: float,
                   density: float, inlet_pressure_kpa: float) -> pd.DataFrame:
    """연속 방정식과 베르누이 방정식으로 위치별 평균 유속·정압을 구한다."""
    x, diameter = make_pipe_profile(throat_ratio, exit_ratio)
    area = np.pi * (diameter ** 2) / 4
    q_m3s = q_lps / 1000.0
    velocity = q_m3s / area
    v_inlet = velocity[0]
    # 수평 이상 유체: P + (1/2) rho v² = 일정
    pressure_pa = inlet_pressure_kpa * 1000 + 0.5 * density * (v_inlet**2 - velocity**2)
    return pd.DataFrame({
        "위치(m)": x,
        "관 지름(m)": diameter,
        "단면적(m²)": area,
        "유속(m/s)": velocity,
        "정압(kPa)": pressure_pa / 1000,
    })


def plot_pipe(df: pd.DataFrame):
    """관 단면의 모식도를 위치별 평균 유속에 따라 색으로 표현한다."""
    x = df["위치(m)"].to_numpy()
    r = df["관 지름(m)"].to_numpy() / 2
    velocity = df["유속(m/s)"].to_numpy()
    fig, ax = plt.subplots(figsize=(11, 3.4), constrained_layout=True)
    fig.patch.set_facecolor("#f8fbff")
    ax.set_facecolor("#f8fbff")
    verts = [
        [(x[i], -r[i]), (x[i+1], -r[i+1]),
         (x[i+1], r[i+1]), (x[i], r[i])]
        for i in range(len(x) - 1)
    ]
    cmap = plt.get_cmap("turbo")
    norm = Normalize(vmin=max(0, float(velocity.min()) * 0.8), vmax=max(float(velocity.max()), 0.01))
    polygons = PolyCollection(verts, array=(velocity[:-1]+velocity[1:])/2,
                              cmap=cmap, norm=norm, edgecolors="none")
    ax.add_collection(polygons)
    ax.plot(x, r, color="#16416b", linewidth=2)
    ax.plot(x, -r, color="#16416b", linewidth=2)
    # 중심선의 흐름 방향 표시. 실제 입자 추적 결과가 아닌 모식도임.
    for xi in (0.35, 0.95, 1.5, 2.1, 2.75):
        ax.annotate("", xy=(xi + 0.13, 0), xytext=(xi - 0.09, 0),
                    arrowprops=dict(arrowstyle="->", color="white", lw=1.7))
    ax.set_xlim(0, PIPE_LENGTH)
    ax.set_ylim(-0.075, 0.075)
    ax.set_xlabel("Pipe position (m)")
    ax.set_ylabel("Radial position (m)")
    ax.set_title("Pipe profile and mean-flow speed (schematic)", fontweight="bold")
    ax.grid(alpha=0.14, axis="x")
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, label="Mean speed (m/s)", pad=0.01)
    return fig


def plot_results(df: pd.DataFrame, saved=None):
    """유속·정압 변화를 별도 그래프로 표시한다."""
    fig1, ax1 = plt.subplots(figsize=(7, 3.3), constrained_layout=True)
    ax1.plot(df["위치(m)"], df["유속(m/s)"], color="#087ca3", lw=2.7, label="Current")
    if saved is not None:
        ax1.plot(saved["위치(m)"], saved["유속(m/s)"], ls="--", color="#ed8a29", lw=2, label="Saved A")
    ax1.set(title="Velocity distribution", xlabel="Position (m)", ylabel="Speed (m/s)")
    ax1.grid(alpha=0.25)
    if saved is not None:
        ax1.legend()

    fig2, ax2 = plt.subplots(figsize=(7, 3.3), constrained_layout=True)
    ax2.plot(df["위치(m)"], df["정압(kPa)"], color="#6958bd", lw=2.7, label="Current")
    if saved is not None:
        ax2.plot(saved["위치(m)"], saved["정압(kPa)"], ls="--", color="#ed8a29", lw=2, label="Saved A")
    ax2.set(title="Static pressure distribution", xlabel="Position (m)", ylabel="Pressure (kPa)")
    ax2.grid(alpha=0.25)
    if saved is not None:
        ax2.legend()
    return fig1, fig2


def summarize(df: pd.DataFrame) -> dict:
    idx = df["유속(m/s)"].idxmax()
    return {
        "입구 유속(m/s)": float(df["유속(m/s)"].iloc[0]),
        "최대 유속(m/s)": float(df["유속(m/s)"].max()),
        "최소 정압(kPa)": float(df["정압(kPa)"].min()),
        "목 위치(m)": float(df.loc[idx, "위치(m)"]),
        "입구-목 정압 차(kPa)": float(df["정압(kPa)"].iloc[0] - df["정압(kPa)"].min()),
    }


st.title("🌊 FLOW LAB")
st.caption("관의 단면적 변화에 따른 유속·정압 분포 | Python·Streamlit 유체역학 가상 실험실")
st.info("**모형 가정:** 수평 관 · 정상 흐름 · 비압축성 · 비점성 · 동일 유선의 베르누이 법칙. "
        "실제 관의 마찰 손실, 펌프 특성, 난류, 공동현상 및 곡관 손실은 계산하지 않습니다.")

DEFAULTS = {
    "throat_ratio": 0.60,
    "exit_ratio": 1.00,
    "q_lps": 2.0,
    "density": 1000,
    "inlet_pressure_kpa": 250,
}
for field, default in DEFAULTS.items():
    if field not in st.session_state:
        st.session_state[field] = default


def reset_conditions():
    """실험 입력값과 비교 기록을 초기화한다."""
    for field, default in DEFAULTS.items():
        st.session_state[field] = default
    st.session_state.pop("saved_experiment", None)


with st.sidebar:
    st.header("⚙️ 실험 조건")
    st.caption("입구 지름은 0.10 m, 관 길이는 3.0 m로 고정합니다.")
    throat_ratio = st.slider("중앙(목) 지름 비율", min_value=0.40, max_value=1.00, step=0.05,
                             key="throat_ratio", help="입구 지름 대비 목 지름 비율. 단면적 비율과는 다릅니다.")
    exit_ratio = st.slider("출구 지름 비율", min_value=0.50, max_value=1.40, step=0.05,
                           key="exit_ratio", help="입구 지름 대비 출구 지름 비율")
    q_lps = st.slider("부피 유량 (L/s)", min_value=0.5, max_value=5.0, step=0.1, key="q_lps")
    density = st.slider("밀도 (kg/m³)", min_value=800, max_value=1200, step=25, key="density")
    inlet_pressure_kpa = st.slider("입구 정압 (kPa)", min_value=150, max_value=400, step=10,
                                    key="inlet_pressure_kpa", help="절대압 기준으로 입력하세요.")
    st.button("🔄 기본값으로 되돌리기", on_click=reset_conditions, use_container_width=True)
    st.markdown("---")
    st.caption("입력값을 바꾸면 계산과 그래프가 자동 갱신됩니다.")

current = calculate_flow(throat_ratio, exit_ratio, q_lps, density, inlet_pressure_kpa)
summary = summarize(current)

st.subheader("① 관 구조와 유체 흐름")
fig_pipe = plot_pipe(current)
st.pyplot(fig_pipe, clear_figure=True)
plt.close(fig_pipe)
st.caption("색상은 각 단면에서의 **평균 유속**을 뜻합니다. 그림은 유선/입자 운동을 정밀 계산한 결과가 아닌 관 모식도입니다.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("입구 유속", f"{summary['입구 유속(m/s)']:.2f} m/s")
m2.metric("최대 유속", f"{summary['최대 유속(m/s)']:.2f} m/s")
m3.metric("최소 정압", f"{summary['최소 정압(kPa)']:.2f} kPa")
m4.metric("입구 → 목 정압 감소", f"{summary['입구-목 정압 차(kPa)']:.2f} kPa")

st.subheader("② 위치별 분석 그래프")
saved_record = st.session_state.get("saved_experiment")
saved_df = saved_record["data"] if saved_record is not None else None
fig_v, fig_p = plot_results(current, saved_df)
c1, c2 = st.columns(2)
with c1:
    st.pyplot(fig_v, clear_figure=True)
with c2:
    st.pyplot(fig_p, clear_figure=True)
plt.close(fig_v)
plt.close(fig_p)

st.subheader("③ 실험 A/B 비교")
st.write("현재 조건을 **실험 A**로 저장한 뒤 슬라이더를 변경하면, 새 조건인 **실험 B**와 그래프를 비교할 수 있어요.")
if st.button("📌 현재 조건을 실험 A로 저장", type="primary"):
    st.session_state["saved_experiment"] = {
        "data": current.copy(),
        "settings": {"목 지름 비율": throat_ratio, "출구 지름 비율": exit_ratio,
                     "유량(L/s)": q_lps, "밀도(kg/m³)": density, "입구 정압(kPa)": inlet_pressure_kpa},
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    st.rerun()

saved_record = st.session_state.get("saved_experiment")
if saved_record is None:
    st.caption("아직 저장한 실험이 없습니다.")
else:
    a = summarize(saved_record["data"])
    b = summary
    comp = pd.DataFrame([
        {"지표": k, "실험 A": round(a[k], 3), "실험 B": round(b[k], 3), "B - A": round(b[k]-a[k], 3)}
        for k in a
    ])
    st.dataframe(comp, hide_index=True, use_container_width=True)
    st.caption(f"실험 A 저장 시각: {saved_record['saved_at']}")
    if st.button("실험 A 기록 지우기"):
        st.session_state.pop("saved_experiment", None)
        st.rerun()

st.subheader("④ 계산 데이터 내려받기")
st.dataframe(current.iloc[::10].round(4), hide_index=True, use_container_width=True)
csv_bytes = current.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ 전체 위치별 계산 결과 CSV 다운로드", data=csv_bytes,
                   file_name="flow_lab_results.csv", mime="text/csv")

with st.expander("📘 물리 원리와 해석 시 주의사항", expanded=False):
    st.markdown(r"""
**연속 방정식** (비압축성 정상 흐름)

$$Q=Av,\qquad A=\frac{\pi D^2}{4}$$

**베르누이 방정식** (수평, 비점성, 동일 유선)

$$P(x)+\frac12\rho v(x)^2=P_1+\frac12\rho v_1^2$$

- 지름을 절반으로 줄이면 단면적은 1/4이 되므로, 같은 유량에서 평균 유속은 4배가 됩니다.
- 좁은 곳의 속도가 증가하면 이상 유체 모형에서 정압은 감소합니다.
- 이 프로그램은 1차원 **단면 평균 속도**만 계산하며 실제 점성 유동의 속도 프로필은 표현하지 않습니다.
- 실제 배관에서는 점성, 난류, 마찰, 곡관 손실, 펌프 조건 등이 영향을 줍니다. 또한 모델의 정압이 매우 낮아지는 조건은 실제로 공동현상 등이 발생할 수 있어 이 식만으로 해석하기 어렵습니다.
- 이 결과는 학습용 근사이며 실제 장치 안전성·설계 판단에 사용하면 안 됩니다.
""")

st.caption("FLOW LAB · 고등학교 프로그래밍 수행평가용 교육 시뮬레이터")

