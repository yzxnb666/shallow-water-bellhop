#!/usr/bin/env python
"""生成实验报告用的插图与公式图片。

报告插图按"接近正文宽度插入"来设计：图片物理宽度不超过 10.5 英寸，字号放大到
15 至 16 pt，插入到 15.5 cm 宽的正文里后，图内文字约为 9 pt，与正文 10.5 pt
搭配清晰可读。

输出：output/report/assets/
运行：python scripts/report_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bellhop_runtime  # noqa: E402

_bellhop_runtime.prepare(verbose=False)
import arlpy.uwapm as pm  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "output" / "data"
OUT = PROJECT / "output" / "report" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

if (Path("C:/Windows/Fonts") / "msyh.ttc").is_file():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({
    "font.size": 15,
    "axes.titlesize": 16,
    "axes.labelsize": 15,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "legend.fontsize": 12,
})


def save(fig, name):
    p = OUT / name
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("written:", p)


# ----------------------------------------------------------------------
# 图 1 原理示意
# ----------------------------------------------------------------------
def fig_principles():
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5))

    z = np.linspace(0, 100, 200)
    ax = axes[0]
    ax.plot(np.full_like(z, 1500.0), z, "k-", lw=2.2, label="等声速")
    ax.plot(1502.0 - 0.24 * z, z, "g-", lw=2.2, label="负梯度")
    ax.plot(1480.0 + 0.22 * z, z, "b-", lw=2.2, label="正梯度")
    ax.set_xlabel("声速 (m/s)")
    ax.set_ylabel("深度 (m)")
    ax.set_title("(a) 三种典型声速剖面")
    ax.invert_yaxis()
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right")

    def trace_ray(c0, g, theta0_deg, z0=5.0, smax=6000.0, n=6000):
        """射线方程: dx/ds=cos(theta), dz/ds=sin(theta), dtheta/ds=-(dc/dz)cos(theta)/c"""
        ds = smax / n
        x, zz, th = 0.0, z0, np.deg2rad(theta0_deg)
        xs, zs = [x], [zz]
        for _ in range(n):
            c = c0 + g * zz
            x += np.cos(th) * ds
            zz += np.sin(th) * ds
            th -= (g * np.cos(th) / c) * ds
            if zz < 0.0 or zz > 100.0:
                xs.append(x)
                zs.append(float(np.clip(zz, 0.0, 100.0)))
                break
            xs.append(x)
            zs.append(zz)
        return np.asarray(xs), np.asarray(zs)

    ax = axes[1]
    x, zz = trace_ray(1500.0, 0.0, 8.0)
    ax.plot(x / 1000.0, zz, "k-", lw=2.2, label="等声速")
    x, zz = trace_ray(1490.0, -0.12, 8.0)
    ax.plot(x / 1000.0, zz, "g-", lw=2.2, label="负梯度")
    x, zz = trace_ray(1500.0, 0.22, 3.0)
    ax.plot(x / 1000.0, zz, "b-", lw=2.2, label="正梯度")
    ax.axhline(0.0, color="deepskyblue", lw=1.5)
    ax.axhline(100.0, color="peru", lw=2.5)
    ax.plot(0.0, 5.0, "r*", ms=16)
    ax.set_xlabel("距离 (km)")
    ax.set_ylabel("深度 (m)")
    ax.set_title("(b) 声线为什么会弯曲")
    ax.set_ylim(105, -3)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right")

    ax = axes[2]
    r = np.linspace(200.0, 10000.0, 400)
    ax.plot(r / 1000, 20 * np.log10(r), "k--", lw=1.8, label="球面 20log r")
    ax.plot(r / 1000, 15 * np.log10(r), "b-.", lw=1.8, label="浅海 15log r")
    ax.plot(r / 1000, 10 * np.log10(r), "gray", lw=1.8, label="柱面 10log r")
    tl = pd.read_csv(DATA / "tl_vs_range_pekeris.csv")
    ax.plot(tl["range_m"] / 1000, tl["TL_incoherent_dB"], "r-", lw=2.6,
            label="本次实验")
    ax.set_xlabel("距离 (km)")
    ax.set_ylabel("传播损失 (dB)")
    ax.set_xlim(0, 10)
    ax.set_title("(c) 传播损失随距离增长")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save(fig, "fig_principles.png")


# ----------------------------------------------------------------------
# 图 2 声速剖面与声线
# ----------------------------------------------------------------------
def fig_ssp_rays():
    FREQ, DEPTH, TX_DEPTH, RX_DEPTH = 300.0, 100.0, 50.0, 50.0
    env = pm.create_env2d(
        name="report_rays", frequency=FREQ, depth=DEPTH, soundspeed=1500.0,
        bottom_soundspeed=1700.0, bottom_density=1800.0, bottom_absorption=0.5,
        tx_depth=TX_DEPTH, rx_depth=RX_DEPTH,
        rx_range=np.arange(200.0, 5001.0, 200.0), max_angle=80.0)
    rays = pm.compute_rays(env)

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 3.6))

    ax = axes[0]
    ax.axhspan(DEPTH, 132, color="navajowhite", alpha=0.6)
    ax.plot([1500.0, 1500.0], [0, DEPTH], "b-", lw=2.5, label="海水 1500 m/s")
    ax.plot([1700.0, 1700.0], [DEPTH, 130], color="peru", lw=2.5,
            label="沙底 1700 m/s")
    ax.axhline(DEPTH, color="k", lw=0.9, ls="--")
    ax.plot(1500.0, TX_DEPTH, "r*", ms=16, label="声源 / 接收")
    ax.plot(1500.0, RX_DEPTH, "kv", ms=8)
    ax.set_xlabel("声速 (m/s)")
    ax.set_ylabel("深度 (m)")
    ax.set_ylim(132, -3)
    ax.set_xlim(1460, 1745)
    ax.set_title("(a) 声速剖面")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left")

    ax = axes[1]
    for _, row in rays.iterrows():
        path = np.asarray(row["ray"], dtype=float)
        ax.plot(path[:, 0] / 1000.0, path[:, 1], lw=0.7, alpha=0.65)
    ax.axhline(0.0, color="deepskyblue", lw=1.5)
    ax.axhline(DEPTH, color="peru", lw=2.5)
    ax.plot(0.0, TX_DEPTH, "r*", ms=16)
    ax.set_xlabel("距离 (km)")
    ax.set_ylabel("深度 (m)")
    ax.set_ylim(DEPTH + 12, -3)
    ax.set_xlim(0, 5)
    ax.set_title(f"(b) 本征声线（{len(rays)} 条）")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    save(fig, "fig_ssp_rays.png")


# ----------------------------------------------------------------------
# 图 3 到达结构 / 图 4 到达统计
# ----------------------------------------------------------------------
def fig_arrivals():
    arr = pd.read_csv(DATA / "arrivals_5km.csv")
    t = arr["time_of_arrival_s"].to_numpy() - arr["time_of_arrival_s"].min()
    rel = arr["amplitude_dB_rel_to_max"].to_numpy()

    fig, axes = plt.subplots(1, 3, figsize=(10.8, 3.3))

    ax = axes[0]
    ax.stem(t * 1e3, rel, linefmt="C0-", markerfmt="C0o", basefmt=" ", bottom=-140.0)
    ax.set_ylim(-140, 5)
    ax.set_xlabel("相对时延 (ms)")
    ax.set_ylabel("相对幅度 (dB)")
    ax.set_title(f"(a) 到达结构（{len(arr)} 条）")
    ax.grid(alpha=0.3)

    ax = axes[1]
    sc = ax.scatter(t * 1e3, arr["angle_of_departure_deg"], c=rel,
                    s=18 + 4 * arr["bottom_bounces"], cmap="viridis",
                    vmin=-60, vmax=0, edgecolors="k", linewidths=0.3)
    ax.set_xlabel("相对时延 (ms)")
    ax.set_ylabel("发射角 (deg)")
    ax.set_title("(b) 时延与发射角")
    ax.grid(alpha=0.3)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("相对幅度 (dB)", fontsize=11)

    ax = axes[2]
    bins = np.arange(-0.5, arr["bottom_bounces"].max() + 1.5, 1.0)
    ax.hist([arr["surface_bounces"], arr["bottom_bounces"]], bins=bins,
            label=["海面反射", "海底反射"], color=["#4C72B0", "#DD8452"])
    ax.set_xlabel("反射次数")
    ax.set_ylabel("路径条数")
    ax.set_title("(c) 反射次数分布")
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=11)

    fig.tight_layout()
    save(fig, "fig_arrivals.png")


# ----------------------------------------------------------------------
# 图 4 传播损失曲线 / 图 5 传播损失场
# ----------------------------------------------------------------------
def fig_tl_curve():
    tl = pd.read_csv(DATA / "tl_vs_range_pekeris.csv")
    r_km = tl["range_m"] / 1000.0

    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.plot(r_km, tl["TL_coherent_dB"], lw=1.2, color="crimson", label="相干")
    ax.plot(r_km, tl["TL_incoherent_dB"], lw=2.4, color="navy", label="非相干")
    ax.plot(r_km, 20 * np.log10(tl["range_m"]), "k--", lw=1.6, label="球面 20log r")
    ax.plot(r_km, 10 * np.log10(tl["range_m"]), color="gray", lw=1.6,
            label="柱面 10log r")
    ax.set_xlabel("距离 (km)")
    ax.set_ylabel("传播损失 (dB)")
    ax.set_xlim(0, 10)
    ax.grid(alpha=0.3)
    ax.legend(ncol=2)
    ax.set_title("接收深度 50 m 处的传播损失")
    fig.tight_layout()
    save(fig, "fig_tl_curve.png")


def fig_tl_map():
    inc = pd.read_csv(DATA / "tl_map_pekeris.csv", index_col=0)
    coh = pd.read_csv(DATA / "tl_map_pekeris_zoom_coherent.csv", index_col=0)
    dep1 = inc.index.to_numpy(dtype=float)
    rng1 = inc.columns.to_numpy(dtype=float)
    tl1 = inc.to_numpy()
    dep2 = coh.index.to_numpy(dtype=float)
    rng2 = coh.columns.to_numpy(dtype=float)
    tl2 = coh.to_numpy()

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.0))
    vmin, vmax = np.percentile(tl1, [2, 98])
    ax = axes[0]
    m = ax.pcolormesh(rng1 / 1000, dep1, tl1, cmap="turbo", vmin=vmin, vmax=vmax,
                      shading="auto")
    ax.plot(0.0, 50.0, "w*", ms=16, mec="k")
    ax.set_xlabel("距离 (km)")
    ax.set_ylabel("深度 (m)")
    ax.set_title("(a) 非相干 TL 场")
    ax.invert_yaxis()
    fig.colorbar(m, ax=ax, label="TL (dB)")

    ax = axes[1]
    m2 = ax.pcolormesh(rng2 / 1000, dep2, tl2, cmap="turbo", vmin=35, vmax=95,
                       shading="auto")
    ax.plot(0.0, 50.0, "w*", ms=16, mec="k")
    ax.set_xlabel("距离 (km)")
    ax.set_ylabel("深度 (m)")
    ax.set_title("(b) 相干 TL 场（局部）")
    ax.invert_yaxis()
    fig.colorbar(m2, ax=ax, label="TL (dB)")

    fig.tight_layout()
    save(fig, "fig_tl_map.png")


# ----------------------------------------------------------------------
# 图 7 温跃层对比
# ----------------------------------------------------------------------
def fig_thermocline():
    cmp = pd.read_csv(DATA / "tl_thermocline_vs_iso.csv")
    r_km = cmp["range_m"] / 1000.0

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 3.5))

    ax = axes[0]
    z = np.linspace(0, 100, 200)
    ax.plot(np.full_like(z, 1500.0), z, "b-", lw=2.4, label="等声速")
    ssp = np.array([[0.0, 1502.0], [20.0, 1500.0], [40.0, 1490.0],
                    [60.0, 1480.0], [100.0, 1478.0]])
    ax.plot(np.interp(z, ssp[:, 0], ssp[:, 1]), z, "g-", lw=2.4, label="温跃层")
    ax.axhline(100.0, color="k", ls="--", lw=0.9)
    ax.plot(1500.0, 50.0, "r*", ms=16)
    ax.plot(1500.0, 10.0, "k^", ms=8)
    ax.plot(1500.0, 90.0, "kv", ms=8)
    ax.set_xlabel("声速 (m/s)")
    ax.set_ylabel("深度 (m)")
    ax.set_title("(a) 两种声速剖面")
    ax.set_ylim(103, -3)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left")

    ax = axes[1]
    ax.plot(r_km, cmp["TL_isovelocity_10m_dB"], "b-", lw=2.0, label="等声速 10 m")
    ax.plot(r_km, cmp["TL_thermocline_10m_dB"], "g-", lw=2.0, label="温跃层 10 m")
    ax.plot(r_km, cmp["TL_isovelocity_90m_dB"], "b--", lw=2.0, label="等声速 90 m")
    ax.plot(r_km, cmp["TL_thermocline_90m_dB"], "g--", lw=2.0, label="温跃层 90 m")
    ax.set_xlabel("距离 (km)")
    ax.set_ylabel("非相干传播损失 (dB)")
    ax.set_xlim(0, 10)
    ax.set_title("(b) 浅层与深层的传播损失")
    ax.grid(alpha=0.3)
    ax.legend()

    fig.tight_layout()
    save(fig, "fig_thermocline.png")


# ----------------------------------------------------------------------
# 公式图片：透明背景、紧凑裁剪；渲染 20 pt，插入时按比例缩到约 11 pt
# ----------------------------------------------------------------------
EQUATIONS = {
    "eq_speed": r"$c\;\approx\;1449\;+\;4.6T\;-\;0.055T^{2}\;+\;0.016D$",
    "eq_snell": r"$\dfrac{\cos\theta_1}{c_1}\;=\;\dfrac{\cos\theta_2}{c_2}\;=\;\mathrm{constant}$",
    "eq_tl": r"$\mathrm{TL}(r,z)\;=\;-20\,\log_{10}\left|\,p(r,z)\,\right|$",
    "eq_spread": r"$\mathrm{TL}_{\mathrm{sph}}=20\log_{10}r,\qquad \mathrm{TL}_{\mathrm{cyl}}=10\log_{10}r$",
    "eq_coherent": r"$p(r,z)\;=\;\sum_i a_i\,e^{-j\,2\pi f\tau_i}$",
    "eq_delay": r"$\Delta\tau\;=\;\tau_{\max}-\tau_{\min}$",
}


def equations():
    plt.rcParams["mathtext.fontset"] = "stix"
    for name, tex in EQUATIONS.items():
        fig = plt.figure(figsize=(6.0, 1.0), dpi=300)
        fig.text(0.5, 0.5, tex, ha="center", va="center", fontsize=20, color="black")
        p = OUT / f"{name}.png"
        fig.savefig(p, transparent=True, bbox_inches="tight", pad_inches=0.06)
        plt.close(fig)
        print("written:", p)


# ----------------------------------------------------------------------
# 报告引用的统计数字
# ----------------------------------------------------------------------
def stats():
    arr = pd.read_csv(DATA / "arrivals_5km.csv")
    tl = pd.read_csv(DATA / "tl_vs_range_pekeris.csv")
    print("\n===== 报告中引用的统计数字 =====")
    print("到达路径条数:", len(arr))
    print("时延展宽 (ms): %.1f" % ((arr["time_of_arrival_s"].max() - arr["time_of_arrival_s"].min()) * 1e3))
    print("最早 / 最晚到达 (s): %.4f / %.4f" % (arr["time_of_arrival_s"].min(), arr["time_of_arrival_s"].max()))
    print("发射角范围 (deg): %.1f ~ %.1f" % (arr["angle_of_departure_deg"].min(), arr["angle_of_departure_deg"].max()))
    print("海底反射次数:", arr["bottom_bounces"].min(), "~", arr["bottom_bounces"].max())
    print("海面反射次数:", arr["surface_bounces"].min(), "~", arr["surface_bounces"].max())
    print("相对幅度 > -20 dB 的路径数:", int((arr["amplitude_dB_rel_to_max"] > -20).sum()))
    print("相对幅度 > -40 dB 的路径数:", int((arr["amplitude_dB_rel_to_max"] > -40).sum()))
    for r in (200, 1000, 5000, 10000):
        i = int(np.argmin(np.abs(tl["range_m"] - r)))
        print("TL @ %5d m: 相干 %6.1f dB, 非相干 %6.1f dB" %
              (r, tl["TL_coherent_dB"][i], tl["TL_incoherent_dB"][i]))
    i1 = int(np.argmin(np.abs(tl["range_m"] - 1000)))
    i2 = int(np.argmin(np.abs(tl["range_m"] - 10000)))
    print("1-10 km 等效扩展指数: %.1f log r" %
          (tl["TL_incoherent_dB"][i2] - tl["TL_incoherent_dB"][i1]))
    coh = tl["TL_coherent_dB"].to_numpy()
    inc = tl["TL_incoherent_dB"].to_numpy()
    print("相干起伏标准差: %.1f dB" % np.std(coh - inc))
    print("相干 TL 极值: %.1f / %.1f dB" % (coh.max(), coh.min()))


if __name__ == "__main__":
    fig_principles()
    fig_ssp_rays()
    fig_arrivals()
    fig_tl_curve()
    fig_tl_map()
    fig_thermocline()
    equations()
    stats()
    print("\nassets ->", OUT)
