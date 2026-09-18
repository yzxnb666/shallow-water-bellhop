#!/usr/bin/env python
"""渲染 DOCX 为逐页 PNG，用于视觉质检。

流程：本机 Word 导出 PDF -> pdf2image（打包的 poppler）转 PNG。

依赖：本机装有 Microsoft Word；Python 需要 pdf2image 与 Pillow；
另一个用于驱动 Word 的解释器需要 pywin32（默认用当前解释器）。

可用环境变量覆盖默认设置：
    WORD_PY       驱动 Word 的 python.exe（需要 pywin32）
    POPPLER_BIN   包含 pdftoppm 的目录（不设则用 PATH 中的版本）

运行：
    python scripts\\render_report_qa.py output\\report\\xxx.docx
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from pdf2image import convert_from_path

WORD_PY = Path(os.environ.get("WORD_PY", sys.executable))
WORD_EXPORTER = Path(__file__).resolve().parent / "word_export_pdf.py"
POPPLER = os.environ.get("POPPLER_BIN") or None
DPI = 140


def main(docx: Path) -> None:
    out_dir = docx.parent / "qa"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf = out_dir / (docx.stem + ".pdf")
    subprocess.run([str(WORD_PY), str(WORD_EXPORTER), str(docx), str(pdf)],
                   check=True)

    pages = convert_from_path(str(pdf), dpi=DPI, poppler_path=POPPLER)
    for i, img in enumerate(pages, start=1):
        p = out_dir / f"page-{i}.png"
        img.save(p)
        print(f"[png] {p}  {img.size[0]}x{img.size[1]}")
    print(f"pages={len(pages)}  ->  {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: render_report_qa.py <input.docx>")
    main(Path(sys.argv[1]))
