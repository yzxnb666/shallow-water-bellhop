"""BELLHOP 运行环境自举。

Python 端通过两个途径使用 BELLHOP 可执行文件：

1. ``arlpy`` 只会从系统 PATH 里查找 ``bellhop.exe``，不会去 site-packages 里找；
2. ``aubellhop`` 会自己定位包内的 exe，但 exe 必须能找到匹配的 Fortran 运行库。

在 Windows 上有一个隐蔽的坑：aubellhop wheel 里的 ``bellhop.exe`` 是用
MSYS2 GCC 16.1.0 编译的。如果系统优先加载了 conda-forge 的 libgfortran
（16.2.0），声线（run type R）与到达结构（A）仍能正常计算，但任何需要写
``.shd`` 文件的任务（相干/非相干传播损失）会直接崩溃，退出码为 0xC0000374
或 0xC0000005。这种"部分功能正常"的现象很容易误导排查方向。

解决办法：把与编译器同源的 MSYS2 运行库放到 exe 同目录，Windows 会优先从
可执行文件所在目录加载动态库。需要的 7 个文件是：

    libgfortran-5.dll  libgcc_s_seh-1.dll  libwinpthread-1.dll
    libquadmath-0.dll  libgomp-1.dll       libatomic-1.dll
    libstdc++-6.dll

本模块负责：定位 exe 目录、检查运行库是否齐全、把该目录加入 PATH。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: 当前 Python 环境根目录（conda 环境中即为环境目录）
ENV_ROOT = Path(sys.prefix)

#: 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

_IS_WINDOWS = os.name == "nt"
_EXE_NAME = "bellhop.exe" if _IS_WINDOWS else "bellhop"

_REQUIRED_DLLS = (
    "libgfortran-5.dll",
    "libgcc_s_seh-1.dll",
    "libwinpthread-1.dll",
    "libquadmath-0.dll",
    "libgomp-1.dll",
    "libatomic-1.dll",
    "libstdc++-6.dll",
)


def _find_bellhop_bin() -> Path:
    """定位 aubellhop 自带的可执行文件目录。"""
    try:
        import aubellhop

        return Path(aubellhop.__file__).resolve().parent / "bin"
    except Exception:
        # 退回到 Windows conda 环境的常见布局
        return ENV_ROOT / "Lib" / "site-packages" / "aubellhop" / "bin"


BELLHOP_BIN = _find_bellhop_bin()


def check_runtime(verbose: bool = True) -> dict:
    """检查 exe 与运行库是否就位，返回体检结果。"""
    missing = []
    if _IS_WINDOWS:
        missing = [d for d in _REQUIRED_DLLS if not (BELLHOP_BIN / d).is_file()]

    report = {
        "env_root": str(ENV_ROOT),
        "bellhop_bin": str(BELLHOP_BIN),
        "exe": _EXE_NAME,
        "exe_found": (BELLHOP_BIN / _EXE_NAME).is_file(),
        "missing_dlls": missing,
    }
    report["ok"] = report["exe_found"] and not missing

    if verbose:
        print(f"[runtime] bellhop  : {'OK' if report['exe_found'] else 'MISSING'} ({BELLHOP_BIN})")
        if _IS_WINDOWS:
            state = "OK" if not missing else "MISSING " + ", ".join(missing)
            print(f"[runtime] 运行库    : {state}")
    return report


def prepare(verbose: bool = False) -> None:
    """把 exe 目录放到 PATH 最前面，供 arlpy 调用。"""
    report = check_runtime(verbose=verbose)
    if not report["ok"]:
        hint = ""
        if report["missing_dlls"] and _IS_WINDOWS:
            hint = (
                "\nWindows 上需要把与编译器同源的 MSYS2 运行库放到该目录：\n  "
                + "\n  ".join(_REQUIRED_DLLS)
                + "\n详见 README 的「Windows 运行库问题」一节。"
            )
        raise RuntimeError(
            f"BELLHOP 运行环境不完整：找不到 {_EXE_NAME} 或运行库。{hint}"
        )

    entries = os.environ.get("PATH", "").split(os.pathsep)
    if str(BELLHOP_BIN) not in entries:
        os.environ["PATH"] = os.pathsep.join([str(BELLHOP_BIN), *entries])


if __name__ == "__main__":
    check_runtime()
