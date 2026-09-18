#!/usr/bin/env python
"""用本机 Microsoft Word 把 DOCX 导出为 PDF（渲染质检的第一步）。

本机没有 LibreOffice，但装有 Microsoft Word，因此用 Word 的
ExportAsFixedFormat 生成 PDF，再用 pdf2image 转成逐页 PNG 做视觉检查。

运行（需要 pywin32 与本机安装的 Microsoft Word）：
    python scripts\\word_export_pdf.py in.docx out.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

import pythoncom
import win32com.client as win32

WD_EXPORT_FORMAT_PDF = 17


def export(docx: Path, pdf: Path) -> None:
    pythoncom.CoInitialize()
    word = win32.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    word.ScreenUpdating = False
    doc = None
    try:
        doc = word.Documents.Open(str(docx.resolve()), ReadOnly=True,
                                  AddToRecentFiles=False)
        doc.ExportAsFixedFormat(str(pdf.resolve()), WD_EXPORT_FORMAT_PDF)
        print(f"[word] exported: {pdf}")
    finally:
        # 导出后 Word 的自动化对象可能已经断开（Quit 会抛 AttributeError），
        # 这里尽力关闭，任何异常都忽略；Word 在最后一个文档关闭后会自行退出。
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            word.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: word_export_pdf.py <input.docx> <output.pdf>")
    export(Path(sys.argv[1]), Path(sys.argv[2]))
