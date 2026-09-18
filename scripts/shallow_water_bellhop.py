#!/usr/bin/env python
"""浅海 BELLHOP 仿真实验：Pekeris 波导 + 温跃层（负梯度）对比。

场景 1（基准，Pekeris 波导）
    水深 100 m，等声速 1500 m/s，沙底 (c=1700 m/s, rho=1.8 g/cm^3,
    alpha=0.5 dB/lambda)，频率 300 Hz，声源 50 m。
    输出：本征声线、到达结构、传播损失曲线与 TL(r,z) 伪彩图。

场景 2（温跃层，负声速梯度）
    水面 1502 m/s 线性降到 100 m 处 1478 m/s，声线向下折射，
    与场景 1 对比接收深度 90 m 处的传播损失差异。

运行：
    python scripts\\shallow_water_bellhop.py

输出：
    output/figures/*.png   图
    output/data/*.csv      数据
    output/data/summary.json 关键数字
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bellhop_runtime  # noqa: E402  (必须先于 arlpy 导入)

_bellhop_runtime.prepare(verbose=True)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
import arlpy.uwapm as pm  # noqa: E402

# --------------------------------------------------------------------------
# 场景参数
# --------------------------------------------------------------------------
FREQ = 300.0            # Hz
WATER_DEPTH = 100.0     # m
TX_DEPTH = 50.0         # m
RX_DEPTH = 50.0         # m（场景 1 接收深度）
BOTTOM_C = 1700.0       # m/s
BOTTOM_RHO = 1800.0     # kg/m^3 (1.8 g/cm^3)
BOTTOM_ALPHA = 0.5      # dB/lambda
MAX_ANGLE = 80.0        # deg

R_MIN, R_MAX, R_STEP = 200.0, 10_000.0, 50.0
RANGES = np.arange(R_MIN, R_MAX + R_STEP / 2, R_STEP)
ARRIVAL_RANGE = 5000.0

SSP_ISO = 1500.0
SSP_THERMOCLINE = np.array([
    [0.0, 1502.0],
    [20.0, 1500.0],
    [40.0, 1490.0],
    [60.0, 1480.0],
    [100.0, 1478.0],
])

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = PROJECT_ROOT / "output" / "figures"
DATA_DIR = PROJECT_ROOT / "output" / "data"

for d in (FIG_DIR, DATA_DIR):
    d.mkdir(parents=True, exist_ok=True)

# 中文字体（Windows 自带雅黑）；找不到就用英文标签
_win_fonts = Path("C:/Windows/Fonts")
CJK = (_win_fonts / "msyh.ttc").is_file()
if CJK:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def L(zh: str, en: str) -> str:
    """按字体可用性选择中文或英文标签。"""
    return zh if CJK else en


def make_env(name, soundspeed, rx_depth, rx_range, tx_depth=TX_DEPTH):
    """构造 2D 环境（bottom_density 单位 kg/m^3，rlpy 内部会换算）。"""
    return pm.create_env2d(
        name=name,
        frequency=FREQ,
        depth=WATER_DEPTH,
        soundspeed=soundspeed,
        bottom_soundspeed=BOTTOM_C,
        bottom_density=BOTTOM_RHO,
        bottom_absorption=BOTTOM_ALPHA,
        bottom_roughness=0.0,
        tx_depth=tx_depth,
        rx_depth=rx_depth,
        rx_range=rx_range,
        max_angle=MAX_ANGLE,
    )


def tl_db(pressure: np.ndarray) -> np.ndarray:
    """复声压 -> 传播损失 TL = -20*log10|p| (dB, 参考 1 m)。

    注：arlpy/aubellhop 返回的是复声压（不是 dB），BELLHOP 中 |p|=1 对应
    声源 1 m 处，因此可直接换算为传播损失。
    """
    return -20.0 * np.log10(np.maximum(np.abs(pressure), 1e-12))


def tl_curve(env, mode: str):
    """返回 (range_m, tl_db) 一维曲线（单接收深度）。"""
    field = pm.compute_transmission_loss(env, mode=mode)
    if field is None:
        raise RuntimeError(f"BELLHOP 未返回 {mode} 结果")
    field = field.sort_index()
    ranges = np.asarray(field.columns, dtype=float)
    depth_axis = np.asarray(field.index, dtype=float)
    p = field.to_numpy().reshape(len(depth_axis), len(ranges))
    return ranges, tl_db(p[0, :])


def stamped(msg: str) -> float:
    t0 = time.perf_counter()
    print(f"[run] {msg}", flush=True)
    return t0


# --------------------------------------------------------------------------
# 场景 1
# --------------------------------------------------------------------------
def experiment_1():
    print("\n=== 场景 1：浅海 Pekeris 波导（等声速） ===")
    summary = {}

    # --- 1.1 声线 ---
    stamped("计算本征声线 (run type R)")
    ray_ranges = np.arange(200.0, 5000.0 + 1, 200.0)
    env_ray = make_env("pekeris_rays", SSP_ISO, RX_DEPTH, ray_ranges)
    rays = pm.compute_rays(env_ray)
    print(f"      声线条数: {len(rays)}")

    # --- 1.2 到达结构 ---
    stamped(f"计算 {ARRIVAL_RANGE/1000:.0f} km 处到达结构 (run type A)")
    env_arr = make_env("pekeris_arrivals", SSP_ISO, RX_DEPTH, ARRIVAL_RANGE)
    arrivals = pm.compute_arrivals(env_arr)
    n_arr = len(arrivals)
    amp_db = 20.0 * np.log10(np.maximum(np.abs(arrivals["arrival_amplitude"].to_numpy()), 1e-12))
    t_arr = arrivals["time_of_arrival"].to_numpy(dtype=float)
    spread = float(t_arr.max() - t_arr.min())
    print(f"      到达路径: {n_arr} 条, 时延展宽: {spread*1e3:.1f} ms")

    arrivals_out = pd.DataFrame({
        "time_of_arrival_s": t_arr,
        "amplitude_abs": np.abs(arrivals["arrival_amplitude"].to_numpy()),
        "amplitude_dB_abs": amp_db,
        "amplitude_dB_rel_to_max": amp_db - amp_db.max(),
        "angle_of_arrival_deg": arrivals["angle_of_arrival"].to_numpy(dtype=float),
        "angle_of_departure_deg": arrivals["angle_of_departure"].to_numpy(dtype=float),
        "surface_bounces": arrivals["surface_bounces"].to_numpy(),
        "bottom_bounces": arrivals["bottom_bounces"].to_numpy(),
    }).sort_values("time_of_arrival_s")
    arrivals_out.to_csv(DATA_DIR / "arrivals_5km.csv", index=False)

    # --- 1.3 传播损失曲线 ---
    stamped("计算相干/非相干传播损失 (run type C / I)")
    env_tl = make_env("pekeris_tl", SSP_ISO, RX_DEPTH, RANGES)
    rng, tl_coh = tl_curve(env_tl, "coherent")
    _, tl_inc = tl_curve(env_tl, "incoherent")
    pd.DataFrame({
        "range_m": rng,
        "TL_coherent_dB": tl_coh,
        "TL_incoherent_dB": tl_inc,
    }).to_csv(DATA_DIR / "tl_vs_range_pekeris.csv", index=False)

    def at(r_km):
        idx = int(np.argmin(np.abs(rng - r_km * 1000)))
        return float(tl_coh[idx]), float(tl_inc[idx])

    for r_km in (1, 5, 10):
        c, i = at(r_km)
        print(f"      {r_km:>2} km: 相干 {c:6.1f} dB / 非相干 {i:6.1f} dB")
        summary[f"TL_coherent_{r_km}km_dB"] = round(c, 2)
        summary[f"TL_incoherent_{r_km}km_dB"] = round(i, 2)

    # --- 1.4 TL(r, z) 场：非相干全景 + 相干局部 ---
    stamped("计算非相干 TL(r,z) 场（0.2-10 km）")
    rx_depths = np.arange(2.0, 100.0, 2.0)
    env_map = make_env("pekeris_map", SSP_ISO, rx_depths, RANGES)
    field_map = pm.compute_transmission_loss(env_map, mode="incoherent")
    field_map = field_map.sort_index()
    dep_axis = np.asarray(field_map.index, dtype=float)
    rng_axis = np.asarray(field_map.columns, dtype=float)
    tl_map = tl_db(field_map.to_numpy().reshape(len(dep_axis), len(rng_axis)))
    pd.DataFrame(tl_map, index=dep_axis, columns=rng_axis).to_csv(
        DATA_DIR / "tl_map_pekeris.csv", float_format="%.2f")

    stamped("计算相干 TL(r,z) 局部场（0.3-2 km，步长 5 m）")
    zoom_ranges = np.arange(300.0, 2000.0 + 1, 5.0)
    env_zoom = make_env("pekeris_zoom", SSP_ISO, rx_depths, zoom_ranges)
    field_zoom = pm.compute_transmission_loss(env_zoom, mode="coherent").sort_index()
    dep_zoom = np.asarray(field_zoom.index, dtype=float)
    rng_zoom = np.asarray(field_zoom.columns, dtype=float)
    tl_zoom = tl_db(field_zoom.to_numpy().reshape(len(dep_zoom), len(rng_zoom)))
    pd.DataFrame(tl_zoom, index=dep_zoom, columns=rng_zoom).to_csv(
        DATA_DIR / "tl_map_pekeris_zoom_coherent.csv", float_format="%.2f")

    # ------------------------------------------------------------------
    # 绘图：场景 1 总览
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.0))
    fig.suptitle(L(f"浅海 BELLHOP 实验 1：Pekeris 波导（{FREQ:.0f} Hz，水深 {WATER_DEPTH:.0f} m，声源/接收 {TX_DEPTH:.0f} m）",
                   f"Shallow-water BELLHOP #1: Pekeris waveguide ({FREQ:.0f} Hz, {WATER_DEPTH:.0f} m, src/rx {TX_DEPTH:.0f} m)"),
                 fontsize=13)

    # (a) 声速剖面
    ax = axes[0, 0]
    ax.axhspan(WATER_DEPTH, 132, color="navajowhite", alpha=0.55)
    ax.plot([SSP_ISO, SSP_ISO], [0, WATER_DEPTH], "b-", lw=2, label=L("海水 (等声速)", "water"))
    ax.plot([BOTTOM_C, BOTTOM_C], [WATER_DEPTH, 130], color="peru", lw=2,
            label=L("沙底 c=1700 m/s", "sand bottom"))
    ax.axhline(WATER_DEPTH, color="k", lw=0.8, ls="--")
    ax.plot(SSP_ISO, TX_DEPTH, "r*", ms=14, label=L("声源", "source"))
    ax.plot(SSP_ISO, RX_DEPTH, "kv", ms=7, label=L("接收", "receiver"))
    ax.text(BOTTOM_C - 6, 118, L(r"$\rho$=1.8 g/cm$^3$, $\alpha$=0.5 dB/$\lambda$",
                                 r"$\rho$=1.8 g/cm$^3$, $\alpha$=0.5 dB/$\lambda$"),
            fontsize=8, ha="right", color="saddlebrown")
    ax.set_xlabel(L("声速 (m/s)", "sound speed (m/s)"))
    ax.set_ylabel(L("深度 (m)", "depth (m)"))
    ax.set_ylim(132, -3)
    ax.set_xlim(1460, BOTTOM_C + 40)
    ax.set_title(L("(a) 声速剖面", "(a) sound-speed profile"))
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower left")

    # (b) 本征声线
    ax = axes[0, 1]
    for _, row in rays.iterrows():
        path = np.asarray(row["ray"], dtype=float)
        ax.plot(path[:, 0] / 1000.0, path[:, 1], lw=0.6, alpha=0.65)
    ax.axhline(WATER_DEPTH, color="peru", lw=2)
    ax.axhline(0.0, color="deepskyblue", lw=1.5)
    ax.plot(0.0, TX_DEPTH, "r*", ms=14)
    ax.plot(ray_ranges / 1000.0, np.full_like(ray_ranges, RX_DEPTH), "kv", ms=4)
    ax.set_xlabel(L("距离 (km)", "range (km)"))
    ax.set_ylabel(L("深度 (m)", "depth (m)"))
    ax.set_ylim(WATER_DEPTH + 20, -3)
    ax.set_title(L(f"(b) 本征声线（{len(rays)} 条，发射角 ±80°）",
                   f"(b) eigenrays ({len(rays)}, ±80°)"))
    ax.grid(alpha=0.3)

    # (c) 传播损失曲线
    ax = axes[1, 0]
    r_km = rng / 1000.0
    ax.plot(r_km, tl_coh, lw=1.1, color="crimson", label=L("相干 TL", "coherent"))
    ax.plot(r_km, tl_inc, lw=1.6, color="navy", label=L("非相干 TL", "incoherent"))
    ax.plot(r_km, 20 * np.log10(np.maximum(r_km * 1000, 1.0)),
            "k--", lw=1.0, label=L("球面扩展 20log r", "spherical 20log r"))
    ax.set_xlabel(L("距离 (km)", "range (km)"))
    ax.set_ylabel(L("传播损失 (dB)", "transmission loss (dB)"))
    ax.set_xlim(0, 10)
    ax.set_title(L(f"(c) 接收深度 {RX_DEPTH:.0f} m 处传播损失", f"(c) TL at {RX_DEPTH:.0f} m"))
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)

    # (d) 到达结构
    ax = axes[1, 1]
    order = np.argsort(t_arr)
    rel_db = amp_db[order] - amp_db.max()
    ax.stem((t_arr[order] - t_arr[order].min()) * 1e3, rel_db,
            linefmt="C0-", markerfmt="C0o", basefmt=" ", bottom=-140.0)
    ax.set_ylim(-140.0, 5.0)
    ax.set_xlabel(L("相对时延 (ms)", "relative delay (ms)"))
    ax.set_ylabel(L("相对幅度 (dB)", "relative amplitude (dB)"))
    ax.set_title(L(f"(d) {ARRIVAL_RANGE/1000:.0f} km 处到达结构（{n_arr} 条路径）",
                   f"(d) arrivals at {ARRIVAL_RANGE/1000:.0f} km ({n_arr} paths)"))
    ax.grid(alpha=0.3)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG_DIR / "exp1_pekeris_overview.png", dpi=150)
    plt.close(fig)

    # 单独的 TL 伪彩图（左：非相干全景；右：相干局部）
    fig, axes = plt.subplots(1, 2, figsize=(15.0, 5.0))
    vmin, vmax = (float(v) for v in np.percentile(tl_map, [2, 98]))
    cmap = LinearSegmentedColormap.from_list("tl", ["#12285c", "#1f7ac0", "#41b6c4", "#ffffbf", "#fdae61", "#d7191c"])

    ax = axes[0]
    mesh = ax.pcolormesh(rng_axis / 1000.0, dep_axis, np.clip(tl_map, vmin, vmax),
                         cmap=cmap, vmin=vmin, vmax=vmax, shading="auto")
    ax.plot(0.0, TX_DEPTH, "w*", ms=16, mec="k")
    ax.set_xlabel(L("距离 (km)", "range (km)"))
    ax.set_ylabel(L("深度 (m)", "depth (m)"))
    ax.set_title(L("(a) 非相干 TL(r,z)：0.2–10 km 全景", "(a) incoherent TL(r,z): 0.2–10 km"))
    ax.invert_yaxis()
    cb = fig.colorbar(mesh, ax=ax)
    cb.set_label(L("传播损失 (dB)", "transmission loss (dB)"))

    ax = axes[1]
    mesh2 = ax.pcolormesh(rng_zoom / 1000.0, dep_zoom, np.clip(tl_zoom, 35, 95),
                          cmap=cmap, vmin=35, vmax=95, shading="auto")
    ax.plot(0.0, TX_DEPTH, "w*", ms=16, mec="k")
    ax.set_xlabel(L("距离 (km)", "range (km)"))
    ax.set_ylabel(L("深度 (m)", "depth (m)"))
    ax.set_title(L("(b) 相干 TL(r,z)：0.3–2 km 局部（步长 5 m，可见干涉条纹）",
                   "(b) coherent TL(r,z): 0.3–2 km zoom (5 m step)"))
    ax.invert_yaxis()
    cb2 = fig.colorbar(mesh2, ax=ax)
    cb2.set_label(L("传播损失 (dB)", "transmission loss (dB)"))

    fig.suptitle(L(f"浅海 Pekeris 波导传播损失，{FREQ:.0f} Hz，水深 {WATER_DEPTH:.0f} m",
                   f"Pekeris waveguide TL, {FREQ:.0f} Hz, {WATER_DEPTH:.0f} m"), fontsize=13)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "exp1_tl_map.png", dpi=150)
    plt.close(fig)

    summary.update({
        "n_eigenrays": int(len(rays)),
        "n_arrivals_5km": int(n_arr),
        "delay_spread_ms": round(spread * 1e3, 2),
        "tl_map_depth_range_m": [float(dep_axis.min()), float(dep_axis.max())],
    })
    return summary


# --------------------------------------------------------------------------
# 场景 2：温跃层对比
# --------------------------------------------------------------------------
def experiment_2():
    print("\n=== 场景 2：温跃层（负声速梯度）对比 ===")
    summary = {}
    rx_shallow = 10.0
    rx_deep = 90.0

    stamped(f"计算等声速剖面的 TL ({rx_shallow:.0f} m / {rx_deep:.0f} m)")
    env_iso = make_env("iso_2d", SSP_ISO, [rx_shallow, rx_deep], RANGES)
    fields_iso = pm.compute_transmission_loss(env_iso, mode="incoherent").sort_index()
    rng = np.asarray(fields_iso.columns, dtype=float)
    dep = np.asarray(fields_iso.index, dtype=float)
    tl_iso_s = tl_db(fields_iso.to_numpy().reshape(len(dep), len(rng))[0, :])
    tl_iso_d = tl_db(fields_iso.to_numpy().reshape(len(dep), len(rng))[1, :])

    stamped(f"计算温跃层剖面的 TL ({rx_shallow:.0f} m / {rx_deep:.0f} m)")
    env_thermo = make_env("thermo_2d", SSP_THERMOCLINE, [rx_shallow, rx_deep], RANGES)
    fields_th = pm.compute_transmission_loss(env_thermo, mode="incoherent").sort_index()
    tl_th_s = tl_db(fields_th.to_numpy().reshape(len(dep), len(rng))[0, :])
    tl_th_d = tl_db(fields_th.to_numpy().reshape(len(dep), len(rng))[1, :])

    pd.DataFrame({
        "range_m": rng,
        f"TL_isovelocity_{rx_deep:.0f}m_dB": tl_iso_d,
        f"TL_thermocline_{rx_deep:.0f}m_dB": tl_th_d,
        f"TL_isovelocity_{rx_shallow:.0f}m_dB": tl_iso_s,
        f"TL_thermocline_{rx_shallow:.0f}m_dB": tl_th_s,
    }).to_csv(DATA_DIR / "tl_thermocline_vs_iso.csv", index=False)

    for r_km in (2, 5, 10):
        idx = int(np.argmin(np.abs(rng - r_km * 1000)))
        print(f"      {r_km:>2} km：浅层 {rx_shallow:.0f} m 差值 "
              f"{tl_th_s[idx]-tl_iso_s[idx]:+5.1f} dB；深层 {rx_deep:.0f} m 差值 "
              f"{tl_th_d[idx]-tl_iso_d[idx]:+5.1f} dB （正=温跃层更差）")
        summary[f"dTL_thermocline_shallow_{r_km}km_dB"] = round(float(tl_th_s[idx] - tl_iso_s[idx]), 2)
        summary[f"dTL_thermocline_deep_{r_km}km_dB"] = round(float(tl_th_d[idx] - tl_iso_d[idx]), 2)

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.8))
    ax = axes[0]
    z = np.linspace(0, WATER_DEPTH, 200)
    ax.plot(np.full_like(z, SSP_ISO), z, "b-", lw=2, label=L("等声速 1500 m/s", "isovelocity"))
    ax.plot(PchipInterpolator(SSP_THERMOCLINE[:, 0], SSP_THERMOCLINE[:, 1])(z), z, "g-", lw=2,
            label=L("温跃层（负梯度）", "thermocline (negative gradient)"))
    ax.axhline(WATER_DEPTH, color="k", ls="--", lw=0.8)
    ax.plot(SSP_ISO, TX_DEPTH, "r*", ms=14)
    ax.plot(1500.0, rx_deep, "kv", ms=7)
    ax.plot(1500.0, rx_shallow, "k^", ms=7)
    ax.set_xlabel(L("声速 (m/s)", "sound speed (m/s)"))
    ax.set_ylabel(L("深度 (m)", "depth (m)"))
    ax.set_ylim(WATER_DEPTH + 3, -3)
    ax.set_title(L("(a) 两种声速剖面", "(a) two sound-speed profiles"))
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)

    ax = axes[1]
    ax.plot(rng / 1000.0, tl_iso_s, "b-", lw=1.6, label=L("等声速", "isovelocity"))
    ax.plot(rng / 1000.0, tl_th_s, "g-", lw=1.6, label=L("温跃层", "thermocline"))
    ax.set_xlabel(L("距离 (km)", "range (km)"))
    ax.set_ylabel(L("非相干传播损失 (dB)", "incoherent TL (dB)"))
    ax.set_title(L(f"(b) 接收深度 {rx_shallow:.0f} m（温跃层上方：损失增大）",
                   f"(b) TL at {rx_shallow:.0f} m (above thermocline)"))
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    ax.set_xlim(0, 10)

    ax = axes[2]
    ax.plot(rng / 1000.0, tl_iso_d, "b-", lw=1.6, label=L("等声速", "isovelocity"))
    ax.plot(rng / 1000.0, tl_th_d, "g-", lw=1.6, label=L("温跃层", "thermocline"))
    ax.set_xlabel(L("距离 (km)", "range (km)"))
    ax.set_ylabel(L("非相干传播损失 (dB)", "incoherent TL (dB)"))
    ax.set_title(L(f"(c) 接收深度 {rx_deep:.0f} m（温跃层下方）",
                   f"(c) TL at {rx_deep:.0f} m (below thermocline)"))
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    ax.set_xlim(0, 10)

    fig.suptitle(L("浅海 BELLHOP 实验 2：负声速梯度（温跃层）使声能向下折射，浅层传播损失增大",
                   "BELLHOP #2: negative gradient refracts energy downward, raising loss near the surface"),
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG_DIR / "exp2_thermocline.png", dpi=150)
    plt.close(fig)
    return summary


def main():
    t_start = time.perf_counter()
    summary = {
        "environment": {
            "env_root": str(_bellhop_runtime.ENV_ROOT),
            "frequency_Hz": FREQ,
            "water_depth_m": WATER_DEPTH,
            "source_depth_m": TX_DEPTH,
            "bottom_soundspeed_m_s": BOTTOM_C,
            "bottom_density_kg_m3": BOTTOM_RHO,
            "bottom_absorption_dB_per_lambda": BOTTOM_ALPHA,
            "range_m": [R_MIN, R_MAX],
        }
    }
    summary.update(experiment_1())
    summary.update(experiment_2())
    summary["runtime_s"] = round(time.perf_counter() - t_start, 1)

    with open(DATA_DIR / "summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print("\n=== 完成 ===")
    for k, v in summary.items():
        if not isinstance(v, dict):
            print(f"  {k}: {v}")
    print(f"  总耗时: {summary['runtime_s']} s")
    print(f"  图: {FIG_DIR}")
    print(f"  数据: {DATA_DIR}")


if __name__ == "__main__":
    main()
