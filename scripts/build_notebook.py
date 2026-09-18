#!/usr/bin/env python
"""生成"分步复现"用的 Jupyter notebook。

内容与 scripts/shallow_water_bellhop.py 一致，但拆成带讲解和检查点的分步单元。
默认输出到项目下的 notebooks/ 目录，可用参数指定其它位置。

运行：python scripts/build_notebook.py [输出路径]
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = PROJECT / "notebooks" / "01_shallow_water_bellhop.ipynb"
TARGET = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_TARGET


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip("\n"))


def code(text: str):
    return nbf.v4.new_code_cell(text.strip("\n"))


cells = [
    md(
        """
# 浅海 BELLHOP 实验 · 分步复现

用 `aubellhop` + `arlpy` 计算浅海 Pekeris 波导的**声线 / 到达结构 / 传播损失**，
最后对比温跃层（负声速梯度）的影响。

**场景**：水深 100 m，等声速 1500 m/s，沙底（1700 m/s，1.8 g/cm³，0.5 dB/λ），
频率 300 Hz，声源 50 m，接收 50 m，距离 0.2–10 km。

**用法**：从第一格开始依次按 `Shift + Enter`。每格末尾有 ✓ 检查点，
数字和注释里的预期对不上，就停下来看最后一节"排错"。

**内核**：右上角选你创建的 conda 环境对应的 Python 内核（名字里带
`underwater`）。选错了会报 `No module named arlpy`。
"""
    ),
    md(
        """
## 第 0 步 · 环境自检（必做）

为什么需要这一格：`arlpy` 是**通过 PATH 查找 `bellhop.exe`** 的，
它不会去 site-packages 里找。这里从 aubellhop 的安装位置自动定位，
并把它补进 PATH，避免在不同机器上写死路径。

预期输出：`模型 : ['bellhop']`，`BELLHOP exe : OK`。
"""
    ),
    code(
        """
import os, sys
from pathlib import Path
from importlib.metadata import version

import aubellhop

# 从 aubellhop 的安装位置定位 BELLHOP 可执行文件目录
BELLHOP_BIN = Path(aubellhop.__file__).resolve().parent / "bin"
EXE_NAME = "bellhop.exe" if os.name == "nt" else "bellhop"

# arlpy 只从 PATH 里找 bellhop.exe
if str(BELLHOP_BIN) not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = str(BELLHOP_BIN) + os.pathsep + os.environ.get("PATH", "")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import arlpy.uwapm as pm

# 中文字体（Windows 自带雅黑），并让负号正常显示
if (Path("C:/Windows/Fonts") / "msyh.ttc").is_file():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 图和数据统一存到 notebook 同目录的 output/
OUT_DIR = Path.cwd() / "output"
OUT_DIR.mkdir(exist_ok=True)

print("Python      :", sys.version.split()[0])
print("aubellhop   :", version("aubellhop"))
print("arlpy       :", version("arlpy"))
print("numpy       :", np.__version__)
print("BELLHOP exe :", "OK" if (BELLHOP_BIN / EXE_NAME).is_file() else "MISSING")
print("模型        :", pm.models())
print("结果目录    :", OUT_DIR)
"""
    ),
    md(
        """
### 冒烟测试：让 BELLHOP 真跑一次

先用一个最小环境（25 kHz、25 m 水深、1 km）确认 exe 能起来。
预期：打印出若干条到达路径。

如果这里就报 `Bellhop did not generate expected output file`，
说明 PATH 或运行库有问题，先别往下做。
"""
    ),
    code(
        """
env_smoke = pm.create_env2d(name="smoke", frequency=25000, depth=25,
                            tx_depth=5, rx_depth=10, rx_range=1000)
arr_smoke = pm.compute_arrivals(env_smoke)

print("到达路径条数:", len(arr_smoke))
assert len(arr_smoke) > 0, "BELLHOP 没有输出，检查 PATH / DLL"
print("✓ 第 0 步完成：BELLHOP 可以正常工作")
"""
    ),
    md(
        """
## 第 1 步 · 定义浅海环境

BELLHOP 的输入是一个环境文件（`.env`），`arlpy` 用 `create_env2d()`
帮我们生成。关键参数就是下面这几个；后面每一步都复用 `make_env()`，
**每次只改接收深度和接收距离**——因为声线、到达、传播损失需要的接收
网格不一样。

单位提醒：`bottom_density` 是 **kg/m³**（1.8 g/cm³ = 1800），
`bottom_absorption` 是 **dB/λ**。
"""
    ),
    code(
        """
# ---------- 环境参数 ----------
FREQ       = 300.0     # 频率 Hz
DEPTH      = 100.0     # 水深 m
TX_DEPTH   = 50.0      # 声源深度 m
RX_DEPTH   = 50.0      # 接收深度 m
C_WATER    = 1500.0    # 海水声速 m/s（等声速）
C_BOTTOM   = 1700.0    # 海底声速 m/s
RHO_BOTTOM = 1800.0    # 海底密度 kg/m^3
ALPHA_BOT  = 0.5       # 海底吸收 dB/lambda
MAX_ANGLE  = 80.0      # 最大发射角 deg


def make_env(rx_depth, rx_range, soundspeed=C_WATER, name="pekeris"):
    # 按给定接收深度/距离构造 2D 环境
    return pm.create_env2d(
        name=name,
        frequency=FREQ,
        depth=DEPTH,
        soundspeed=soundspeed,
        bottom_soundspeed=C_BOTTOM,
        bottom_density=RHO_BOTTOM,
        bottom_absorption=ALPHA_BOT,
        bottom_roughness=0.0,
        tx_depth=TX_DEPTH,
        rx_depth=rx_depth,
        rx_range=rx_range,
        max_angle=MAX_ANGLE,
    )


env = make_env(RX_DEPTH, 5000.0)
pm.print_env(env)
print("✓ 第 1 步完成")
"""
    ),
    md(
        """
## 第 2 步 · 本征声线（run type `R`）

BELLHOP 从声源按不同发射角打出一束声线，追到各个接收距离。
这里接收深度固定 50 m、距离 0.2–5 km 每隔 200 m 放一个接收点。

预期：约 50 条声线；浅海里声线在海底/海面之间反复反弹。
"""
    ),
    code(
        """
ray_ranges = np.arange(200.0, 5000.0 + 1, 200.0)
env_ray = make_env(RX_DEPTH, ray_ranges, name="rays")
rays = pm.compute_rays(env_ray)          # pandas DataFrame

print("声线条数:", len(rays))
print("列:", list(rays.columns))
rays.head(3)
"""
    ),
    code(
        """
fig, ax = plt.subplots(figsize=(10, 4.2))
for _, row in rays.iterrows():
    path = np.asarray(row["ray"], dtype=float)   # 每行是 [range(m), depth(m)] 轨迹
    ax.plot(path[:, 0] / 1000.0, path[:, 1], lw=0.6, alpha=0.6)

ax.axhline(0.0, color="deepskyblue", lw=1.5)     # 海面
ax.axhline(DEPTH, color="peru", lw=2)            # 海底
ax.plot(0.0, TX_DEPTH, "r*", ms=15)              # 声源
ax.plot(ray_ranges / 1000.0, np.full_like(ray_ranges, RX_DEPTH), "kv", ms=4)
ax.set_xlabel("距离 (km)"); ax.set_ylabel("深度 (m)")
ax.set_ylim(DEPTH + 15, -3); ax.set_xlim(0, 5)
ax.set_title(f"浅海 Pekeris 波导本征声线（{len(rays)} 条）")
ax.grid(alpha=0.3)
fig.savefig(OUT_DIR / "step2_rays.png", dpi=140, bbox_inches="tight")
plt.show()
print("✓ 第 2 步完成")
"""
    ),
    md(
        """
## 第 3 步 · 到达结构（run type `A`）

把接收点放到 **5 km、50 m 深**，让 BELLHOP 输出所有到达路径的
**幅度 / 时延 / 到达角 / 反射次数**。

预期：几十到上百条路径，时延展宽几百毫秒——浅海多途非常严重，
这也是后面相干 TL 剧烈起伏的原因。
"""
    ),
    code(
        """
env_arr = make_env(RX_DEPTH, 5000.0, name="arrivals")
arr = pm.compute_arrivals(env_arr)               # pandas DataFrame

t = arr["time_of_arrival"].to_numpy(dtype=float)
a_db = 20 * np.log10(np.maximum(np.abs(arr["arrival_amplitude"].to_numpy()), 1e-12))

print("到达路径:", len(arr))
print(f"最早 / 最晚到达: {t.min():.4f} / {t.max():.4f} s")
print(f"时延展宽      : {(t.max() - t.min()) * 1e3:.1f} ms")
print(f"最强路径幅度  : {a_db.max():.1f} dB（相对 1 m）")
arr.head(8)
"""
    ),
    code(
        """
order = np.argsort(t)
rel_db = a_db[order] - a_db.max()          # 相对最强路径

fig, ax = plt.subplots(figsize=(10, 4.2))
ax.stem((t[order] - t[order].min()) * 1e3, rel_db,
        linefmt="C0-", markerfmt="C0o", basefmt=" ", bottom=-140.0)
ax.set_ylim(-140, 5)
ax.set_xlabel("相对时延 (ms)"); ax.set_ylabel("相对幅度 (dB)")
ax.set_title(f"5 km / 50 m 处到达结构（{len(arr)} 条路径）")
ax.grid(alpha=0.3)
fig.savefig(OUT_DIR / "step3_arrivals.png", dpi=140, bbox_inches="tight")
plt.show()
print("✓ 第 3 步完成")
"""
    ),
    md(
        """
## 第 4 步 · 传播损失曲线（run type `C` / `I`）

这是 BELLHOP 最常用的输出，也是**最容易踩坑的地方**：

* `compute_transmission_loss()` 返回的是**复声压**（pandas DataFrame，
  index = 接收深度，columns = 接收距离），不是 dB；
* 要自己换算：`TL = -20*log10|p|`（BELLHOP 中 |p|=1 对应声源 1 m 处）；
* `mode="coherent"` 相干叠加（有干涉条纹），`mode="incoherent"`
  非相干叠加（平滑）。

预期：相干曲线上下起伏；非相干曲线单调上升，落在球面扩展
（20log r，10 km 处 80 dB）与柱面扩展（约 70 dB）之间。
"""
    ),
    code(
        """
ranges = np.arange(200.0, 10000.0 + 50, 50.0)
env_tl = make_env(RX_DEPTH, ranges, name="tl")

field_coh = pm.compute_transmission_loss(env_tl, mode="coherent")
field_inc = pm.compute_transmission_loss(env_tl, mode="incoherent")

print("返回类型:", type(field_coh).__name__, "形状:", field_coh.shape)
print("index(接收深度) =", list(field_coh.index))
print("columns 前 3 个 =", list(field_coh.columns[:3]))

# 复声压 -> 传播损失 (dB)
TL_coh = -20 * np.log10(np.maximum(np.abs(field_coh.to_numpy()[0]), 1e-12))
TL_inc = -20 * np.log10(np.maximum(np.abs(field_inc.to_numpy()[0]), 1e-12))

for r in (1000, 5000, 10000):
    i = int(np.argmin(np.abs(ranges - r)))
    print(f"{r/1000:5.0f} km: 相干 {TL_coh[i]:6.1f} dB | 非相干 {TL_inc[i]:6.1f} dB")
"""
    ),
    code(
        """
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.plot(ranges / 1000, TL_coh, lw=1.0, color="crimson", label="相干 TL")
ax.plot(ranges / 1000, TL_inc, lw=1.8, color="navy", label="非相干 TL")
ax.plot(ranges / 1000, 20 * np.log10(ranges), "k--", lw=1.0, label="球面扩展 20log r")
ax.set_xlabel("距离 (km)"); ax.set_ylabel("传播损失 (dB)")
ax.set_xlim(0, 10); ax.grid(alpha=0.3); ax.legend()
ax.set_title("300 Hz 浅海 Pekeris 波导传播损失（接收 50 m）")
fig.savefig(OUT_DIR / "step4_tl_curve.png", dpi=140, bbox_inches="tight")
plt.show()
print("✓ 第 4 步完成")
"""
    ),
    md(
        """
## 第 5 步 · TL(r, z) 场

把接收深度铺满整个水层（2–98 m，步长 2 m），得到一张"距离 × 深度"的
传播损失图。

注意：这里用**非相干**模式。相干结果在 50 m 的距离步长下会出现
假条纹（距离采样不足导致的混叠）；要看清真实的干涉条纹需要把步长
降到几米——那是下一格（可选）做的事。
"""
    ),
    code(
        """
depths = np.arange(2.0, 100.0, 2.0)
env_map = make_env(depths, ranges, name="tlmap")
field_map = pm.compute_transmission_loss(env_map, mode="incoherent").sort_index()

dep_ax = np.asarray(field_map.index, dtype=float)
rng_ax = np.asarray(field_map.columns, dtype=float)
TL_map = -20 * np.log10(np.maximum(np.abs(field_map.to_numpy()), 1e-12))
print("TL 场形状 (深度, 距离) =", TL_map.shape)

vmin, vmax = np.percentile(TL_map, [2, 98])
fig, ax = plt.subplots(figsize=(9.5, 4.6))
mesh = ax.pcolormesh(rng_ax / 1000, dep_ax, TL_map, cmap="turbo",
                     vmin=vmin, vmax=vmax, shading="auto")
ax.plot(0.0, TX_DEPTH, "w*", ms=16, mec="k")
ax.set_xlabel("距离 (km)"); ax.set_ylabel("深度 (m)")
ax.set_title("非相干传播损失 TL(r,z)")
ax.invert_yaxis()
fig.colorbar(mesh, ax=ax, label="传播损失 (dB)")
fig.savefig(OUT_DIR / "step5_tl_map.png", dpi=140, bbox_inches="tight")
plt.show()
print("✓ 第 5 步完成")
"""
    ),
    md(
        """
### 第 5 步（可选）· 相干干涉条纹

只取 0.3–2 km、距离步长 5 m。可以看到几十米尺度的明暗条纹——
多阶简正波之间的干涉，这正是相干 TL 的"真面目"。
"""
    ),
    code(
        """
zoom_ranges = np.arange(300.0, 2000.0 + 1, 5.0)
env_zoom = make_env(depths, zoom_ranges, name="tlzoom")
field_zoom = pm.compute_transmission_loss(env_zoom, mode="coherent").sort_index()

dep_z = np.asarray(field_zoom.index, dtype=float)
rng_z = np.asarray(field_zoom.columns, dtype=float)
TL_zoom = -20 * np.log10(np.maximum(np.abs(field_zoom.to_numpy()), 1e-12))

fig, ax = plt.subplots(figsize=(9.5, 4.6))
mesh = ax.pcolormesh(rng_z / 1000, dep_z, TL_zoom, cmap="turbo",
                     vmin=35, vmax=95, shading="auto")
ax.plot(0.0, TX_DEPTH, "w*", ms=16, mec="k")
ax.set_xlabel("距离 (km)"); ax.set_ylabel("深度 (m)")
ax.set_title("相干 TL(r,z) 局部（0.3–2 km，步长 5 m）")
ax.invert_yaxis()
fig.colorbar(mesh, ax=ax, label="传播损失 (dB)")
fig.savefig(OUT_DIR / "step5b_tl_zoom.png", dpi=140, bbox_inches="tight")
plt.show()
print("✓ 第 5 步（可选）完成")
"""
    ),
    md(
        """
## 第 6 步 · 温跃层（负声速梯度）对比

把声速剖面换成"表层暖、深层冷"的负梯度（1502 → 1478 m/s）。
声线会向下折射，改变各深度的能量分布。

对比 10 m（温跃层上方）和 90 m（下方）的非相干 TL。
预期：浅层损失增大（多出几 dB），深层差异较小。

> 在 300 Hz、沙底这种强海底作用条件下，剖面差异的量级就是几 dB；
> 想看到更明显的效果，可以提高频率、减小海底吸收，或者换成
> 正梯度（表面声道）。
"""
    ),
    code(
        """
SSP_THERMO = np.array([[0.0, 1502.0],
                       [20.0, 1500.0],
                       [40.0, 1490.0],
                       [60.0, 1480.0],
                       [100.0, 1478.0]])


def tl_curve(soundspeed, rx_depth, mode="incoherent"):
    env = make_env(rx_depth, ranges, soundspeed=soundspeed, name="cmp")
    fld = pm.compute_transmission_loss(env, mode=mode).sort_index()
    return -20 * np.log10(np.maximum(np.abs(fld.to_numpy()[0]), 1e-12))


TL_iso_10, TL_iso_90 = tl_curve(C_WATER, 10.0), tl_curve(C_WATER, 90.0)
TL_tc_10, TL_tc_90 = tl_curve(SSP_THERMO, 10.0), tl_curve(SSP_THERMO, 90.0)

for r in (2000, 5000, 10000):
    i = int(np.argmin(np.abs(ranges - r)))
    print(f"{r/1000:5.0f} km  10 m 处: 等声速 {TL_iso_10[i]:6.1f} dB, "
          f"温跃层 {TL_tc_10[i]:6.1f} dB, 差 {TL_tc_10[i]-TL_iso_10[i]:+5.1f} dB")
    print(f"          90 m 处: 等声速 {TL_iso_90[i]:6.1f} dB, "
          f"温跃层 {TL_tc_90[i]:6.1f} dB, 差 {TL_tc_90[i]-TL_iso_90[i]:+5.1f} dB")
"""
    ),
    code(
        """
fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))

ax = axes[0]
ax.plot(ranges / 1000, TL_iso_10, "b-", lw=1.6, label="等声速")
ax.plot(ranges / 1000, TL_tc_10, "g-", lw=1.6, label="温跃层")
ax.set_title("接收深度 10 m（温跃层上方）")

ax = axes[1]
ax.plot(ranges / 1000, TL_iso_90, "b-", lw=1.6, label="等声速")
ax.plot(ranges / 1000, TL_tc_90, "g-", lw=1.6, label="温跃层")
ax.set_title("接收深度 90 m（温跃层下方）")

for ax in axes:
    ax.set_xlabel("距离 (km)"); ax.set_ylabel("非相干传播损失 (dB)")
    ax.set_xlim(0, 10); ax.grid(alpha=0.3); ax.legend()

fig.suptitle("负声速梯度（温跃层）对传播损失的影响", fontsize=13)
fig.tight_layout()
fig.savefig(OUT_DIR / "step6_thermocline.png", dpi=140, bbox_inches="tight")
plt.show()
print("✓ 第 6 步完成")
"""
    ),
    md(
        """
## 小结

到这里你完整复现了：

1. 环境定义（Pekeris 波导，`.env` 由 `arlpy` 生成）；
2. 本征声线（run type `R`）；
3. 到达结构（`A`）：5 km 处约 96 条路径、时延展宽约 490 ms；
4. 相干 / 非相干传播损失（`C` / `I`）：10 km 处约 67 / 64 dB；
5. TL(r,z) 场，以及相干干涉条纹；
6. 温跃层对比：浅层损失最多增大 2.7 dB。

命令行版本（同样结果，输出到项目目录）：`scripts\\shallow_water_bellhop.py`

---

### 排错

| 现象 | 原因 / 处理 |
|---|---|
| `No module named arlpy` | 内核选错了，换成安装过 aubellhop 的环境 |
| `Bellhop did not generate expected output file` | PATH 里没有 `bellhop.exe`，重跑第 0 步 |
| 崩溃 / 退出码 `3221225477`、`-1073740940` | Windows 运行库版本不对：确认 `...\\aubellhop\\bin\\` 下有 7 个 MSYS2 DLL（见项目 README） |
| 中文标题变方框 | 缺雅黑字体；本机有 `C:\\Windows\\Fonts\\msyh.ttc`，重启内核即可 |
| 想清空重来 | 菜单 Kernels → Restart Kernel，再从第 0 步运行 |
"""
    ),
]

nb = nbf.v4.new_notebook(cells=cells)
nb.metadata = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3.12.14"},
}

TARGET.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, str(TARGET))
print(f"written: {TARGET}")
print(f"cells  : {len(cells)} (code={sum(1 for c in cells if c['cell_type'] == 'code')})")
