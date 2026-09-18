#!/usr/bin/env python
"""生成《浅海声传播 BELLHOP 仿真实验报告》DOCX。

用打包的 Python（含 python-docx）运行：
    <deps>\\python\\python.exe scripts\\build_report_docx.py

输出：output/report/浅海声传播BELLHOP仿真实验报告.docx
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

PROJECT = Path(__file__).resolve().parent.parent
ASSETS = PROJECT / "output" / "report" / "assets"
OUT_DOCX = PROJECT / "output" / "report" / "浅海声传播BELLHOP仿真实验报告.docx"

BODY_EA = "宋体"
BODY_ASCII = "Times New Roman"
HEAD_EA = "黑体"
HEAD_ASCII = "Arial"
BODY_SIZE = 10.5
LINE_SPACING = 1.32
TEXT_WIDTH_CM = 15.8

doc = Document()


# ======================================================================
# 排版工具
# ======================================================================
def set_font(run, size=BODY_SIZE, bold=False, ascii_font=BODY_ASCII,
             ea_font=BODY_EA, color="000000", italic=False):
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)
    run.font.name = ascii_font
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)
    rFonts.set(qn("w:eastAsia"), ea_font)


def set_outline(paragraph, level):
    pPr = paragraph._p.get_or_add_pPr()
    el = OxmlElement("w:outlineLvl")
    el.set(qn("w:val"), str(level))
    pPr.append(el)


def para(text="", size=BODY_SIZE, bold=False, align="left", indent=True,
         space_before=0, space_after=6, line=LINE_SPACING, color="000000",
         ascii_font=BODY_ASCII, ea_font=BODY_EA, keep_with_next=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT,
                    "center": WD_ALIGN_PARAGRAPH.CENTER,
                    "right": WD_ALIGN_PARAGRAPH.RIGHT,
                    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY}[align]
    if indent:
        pf.first_line_indent = Pt(size * 2)
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    pf.keep_with_next = keep_with_next
    if text:
        run = p.add_run(text)
        set_font(run, size=size, bold=bold, color=color,
                 ascii_font=ascii_font, ea_font=ea_font)
    return p


def h1(text):
    p = para(text, size=15, bold=True, indent=False, space_before=16,
             space_after=8, line=1.15, ascii_font=HEAD_ASCII, ea_font=HEAD_EA,
             keep_with_next=True)
    set_outline(p, 0)


def h2(text):
    p = para(text, size=12.5, bold=True, indent=False, space_before=11,
             space_after=6, line=1.15, ascii_font=HEAD_ASCII, ea_font=HEAD_EA,
             keep_with_next=True)
    set_outline(p, 1)


def caption(text, keep_with_next=False):
    return para(text, size=9, indent=False, align="center", space_before=3,
                space_after=10, line=1.1, keep_with_next=keep_with_next)


def figure(path: Path, width_cm: float, cap: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    caption(cap)


def equation(name: str, number: int, target_pt: float = 11.0, nominal_pt: float = 20.0):
    """居中公式 + 右侧编号（用制表位对齐）。"""
    path = ASSETS / f"{name}.png"
    px_w, _ = Image.open(path).size
    width_cm = (px_w / 300.0) * 2.54 * (target_pt / nominal_pt)
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    pf.keep_with_next = True
    pf.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM / 2), WD_TAB_ALIGNMENT.CENTER)
    pf.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run("\t")
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    r = p.add_run(f"\t({number})")
    set_font(r, size=BODY_SIZE)


def cell_text(cell, text, size=9.5, bold=False, color="000000", align="left", fill=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT,
                   "center": WD_ALIGN_PARAGRAPH.CENTER,
                   "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
    pf = p.paragraph_format
    pf.space_before = Pt(2)
    pf.space_after = Pt(2)
    pf.line_spacing = 1.12
    run = p.add_run(str(text))
    set_font(run, size=size, bold=bold, color=color)
    if fill:
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), fill)
        tcPr.append(shd)
    tcPr = cell._tc.get_or_add_tcPr()
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), "center")
    tcPr.append(vAlign)


def table(headers, rows, widths_cm, aligns=None, size=9.5, header_fill="1F4E79",
          zebra="F2F6FA", cap=None):
    if cap:
        caption(cap, keep_with_next=True)
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    for j, txt in enumerate(headers):
        cell_text(t.rows[0].cells[j], txt, size=size, bold=True,
                  color="FFFFFF", align="center", fill=header_fill)
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j, txt in enumerate(row):
            al = (aligns or ["left"] * len(headers))[j]
            cell_text(cells[j], txt, size=size, align=al,
                      fill=(zebra if i % 2 == 1 else None))

    for row in t.rows:
        for j, w in enumerate(widths_cm):
            row.cells[j].width = Cm(w)

    tbl = t._tbl
    tblPr = parse_xml(
        f'<w:tblPr {nsdecls("w")}>'
        '<w:tblW w:w="0" w:type="auto"/>'
        '<w:jc w:val="center"/>'
        '<w:tblBorders>'
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="D9D9D9"/>'
        '<w:left w:val="single" w:sz="6" w:space="0" w:color="D9D9D9"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="D9D9D9"/>'
        '<w:right w:val="single" w:sz="6" w:space="0" w:color="D9D9D9"/>'
        '<w:insideH w:val="single" w:sz="6" w:space="0" w:color="D9D9D9"/>'
        '<w:insideV w:val="single" w:sz="6" w:space="0" w:color="D9D9D9"/>'
        '</w:tblBorders>'
        '<w:tblLayout w:type="fixed"/>'
        '<w:tblCellMar>'
        '<w:top w:w="80" w:type="dxa"/>'
        '<w:left w:w="110" w:type="dxa"/>'
        '<w:bottom w:w="80" w:type="dxa"/>'
        '<w:right w:w="110" w:type="dxa"/>'
        '</w:tblCellMar>'
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1"'
        ' w:lastColumn="0" w:noHBand="1" w:noVBand="1"/>'
        '</w:tblPr>'
    )
    tbl.replace(tbl.tblPr, tblPr)

    trPr = t.rows[0]._tr.get_or_add_trPr()
    hdr = OxmlElement("w:tblHeader")
    hdr.set(qn("w:val"), "true")
    trPr.append(hdr)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))

    # 让整张表尽量待在同一页：除最后一行外，所有单元格段落都"与下段同页"，
    # 避免出现表头加一行就断页的情况。
    for row in t.rows[:-1]:
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.keep_with_next = True

    para("", indent=False, space_after=2, size=1)
    return t


def add_page_number_footer():
    p = doc.sections[0].footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    f1 = OxmlElement("w:fldChar")
    f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = "PAGE"
    f2 = OxmlElement("w:fldChar")
    f2.set(qn("w:fldCharType"), "end")
    run._r.append(f1)
    run._r.append(it)
    run._r.append(f2)
    set_font(run, size=9, color="404040")


# ======================================================================
# 页面设置
# ======================================================================
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(2.5)
sec.bottom_margin = Cm(2.5)
sec.left_margin = Cm(2.6)
sec.right_margin = Cm(2.6)

normal = doc.styles["Normal"]
normal.font.name = BODY_ASCII
normal.font.size = Pt(BODY_SIZE)
normal._element.rPr.rFonts.set(qn("w:eastAsia"), BODY_EA)

add_page_number_footer()


# ======================================================================
# 标题与引言
# ======================================================================
para("浅海声传播 BELLHOP 仿真实验报告", size=19, bold=True, align="center",
     indent=False, space_before=6, space_after=4, line=1.1,
     ascii_font=HEAD_ASCII, ea_font=HEAD_EA)
para("水声基础原理 操作步骤 结果分析", size=11, align="center", indent=False,
     space_after=14, color="404040", ascii_font=HEAD_ASCII, ea_font=HEAD_EA)

para("本报告记录一次完整的浅海声传播仿真实验。实验用开源水声计算包 aubellhop"
     "（内含 BELLHOP 可执行程序）和 arlpy，在一个 100 m 水深的等声速浅海波导中"
     "计算声线、到达结构与传播损失，再把声速剖面换成温跃层，观察剖面变化对传播"
     "的影响。报告面向第一次接触水声计算的读者：第二节解释必要的物理概念，"
     "第三节到第五节给出可以照着做的环境准备与操作步骤，第六节分析计算结果，"
     "第七节汇总复现过程中容易出错的细节。")

para("实验的主要结果如下。在 300 Hz、100 m 水深的沙底浅海波导中，5 km 处共收到"
     "96 条到达路径，最早与最晚到达相差 487 ms；非相干传播损失在 1 km 与 10 km 处"
     "分别为 50.6 dB 与 64.1 dB，增长速率为 13.4 dB 每十倍距离，介于理想波导的"
     "柱面扩展与自由空间球面扩展之间；相干叠加使传播损失出现明显起伏，标准差 5.8 dB；"
     "把声速剖面换成负梯度后，浅层传播损失最多增加 2.7 dB，深层变化在 2.4 dB 以内。",
     space_after=10)


# ======================================================================
# 一、实验目的与总体思路
# ======================================================================
h1("一、实验目的与总体思路")
h2("1.1 实验目的")
para("这次实验要解决三个问题。第一是学会用 BELLHOP 计算浅海声场的基本输出，"
     "包括声线、到达结构和传播损失；第二是理解这些输出背后的物理含义，知道曲线上的"
     "起伏从哪里来；第三是把整套流程整理成别人可以照着做的步骤，包括环境准备、"
     "参数设置和结果检查。")
para("实验在一台普通 Windows 计算机上完成，全部计算在几秒内结束，不需要高性能集群，"
     "适合作为水声计算的入门练习。")

h2("1.2 计算场景")
para("计算对象是一个 100 m 水深的浅海波导。海水等声速 1500 m/s，海底取沙质参数"
     "（声速 1700 m/s、密度 1.8 g/cm³、吸收 0.5 dB/λ），声源与接收器都放在 50 m 深，"
     "工作频率 300 Hz，作用距离 0.2 到 10 km。作为对照，第二个场景把海水换成负声速"
     "梯度的温跃层剖面，其余条件不变。")

h2("1.3 主要结论")
para("（1）5 km 处一共收到 96 条到达路径，最早与最晚到达相差 487 ms，说明浅海多途"
     "非常严重。")
para("（2）非相干传播损失在 1 km 和 10 km 处分别是 50.6 dB 和 64.1 dB，增长速率约"
     "13.4 dB 每十倍距离，介于理想波导的柱面扩展（10 log r）和自由空间球面扩展"
     "（20 log r）之间。")
para("（3）相干传播损失在非相干曲线上下来回摆动，标准差约 5.8 dB，极值区间 40.9 到"
     "84.6 dB，这是多阶简正波干涉的结果。")
para("（4）把声速剖面换成负梯度后，浅层（10 m）传播损失最多增加 2.7 dB，深层（90 m）"
     "变化在 2.4 dB 以内。在这个频率和海底条件下，剖面变化带来的是几 dB 量级的差异。")


# ======================================================================
# 二、水声基础知识
# ======================================================================
h1("二、水声基础知识")

h2("2.1 海水中的声速")
para("声波在海水中传播的速度由温度 T、盐度 S 和深度（压力）D 共同决定。在盐度接近"
     "35‰ 的开放海域，可以用式(1)做快速估算。")
equation("eq_speed", 1)
para("三个因素中温度的影响最大：水温每升高 1 °C，声速大约增加 4.6 m/s；深度每增加"
     "1 m，声速约增加 0.016 m/s；盐度每变化 1‰，声速变化约 1.3 m/s。因此海洋中的"
     "声速主要由温度决定，而温度又随季节和深度变化，这就形成了各种不同的声速剖面。"
     "本实验使用的 1500 m/s 是浅海常见值，10 °C、35‰ 的水中声速大约就是这个数值。")

h2("2.2 声速剖面与声线折射")
para("当声速随深度变化时，声线不再走直线。在水平分层的海洋中，声线满足式(2)的折射"
     "关系，其中 θ 是声线与水平方向的夹角。")
equation("eq_snell", 2)
para("这条关系与光学中的折射定律等价，结论可以概括成一句话：声线总是向声速更小的"
     "方向弯曲。图1(a)给出三种典型剖面，图1(b)是相应的声线轨迹。")
para("等声速条件下声线是直线。温度随深度下降形成负梯度时，声线不断向下弯曲，能量"
     "被压向海底，浅层出现能量稀疏的区域，本实验的第二个场景就是这种情况。反过来，"
     "如果表层被风浪搅拌、形成温度略高且声速随深度增加的混合层，声线向上弯曲，在表层"
     "形成一个声道，声波可以被限制在几十米深度内远距离传播。")
figure(ASSETS / "fig_principles.png", 15.6,
       "图1 声速剖面、声线折射与传播损失随距离增长的规律")

h2("2.3 传播损失与扩展规律")
para("传播损失描述声波从声源传播到某点后衰减了多少，定义见式(3)，其中 p(r,z) 是接收点"
     "的声压，参考值是距声源 1 m 处的声压。")
equation("eq_tl", 3)
para("损失由两部分组成：几何扩展使能量在空间上摊薄；介质与边界吸收把声能转化为热。"
     "在 300 Hz 这个频率上，海水的吸收大约只有每公里 0.02 dB 量级，10 km 累计不到 1 dB，"
     "可以忽略；真正起作用的是海底吸收。")
para("几何扩展的规律取决于声能被限制的程度。在自由空间中声波向四面八方扩散，属于"
     "球面扩展，损失按 20 log r 增长，距离增加十倍损失增加 20 dB；在理想的浅海波导中，"
     "声能被上下边界限制住，只在水平方向扩散，属于柱面扩展，损失按 10 log r 增长；"
     "真实的浅海介于两者之间，工程上常用 15 log r 作为经验估计。式(4)给出两种理想情形，"
     "图1(c)把它们与本实验的实测曲线画在一起。")
equation("eq_spread", 4)
para("本实验测得的非相干传播损失在 1 km 到 10 km 之间增长 13.4 dB，斜率约为 13.4 log r，"
     "落在 10 log r 与 20 log r 之间，比经验值 15 log r 略缓，说明声能被边界限制得比较充分。")

h2("2.4 多途传播、相干与非相干")
para("浅海中同一个接收点往往同时收到多条经过不同路径的声波，这就是多途传播。每条路径"
     "的传播时间不同，最早和最晚到达的时间差称为时延展宽，见式(5)。")
equation("eq_delay", 5)
para("把各条路径按声压叠加还是按功率叠加，会得到两种不同的结果。相干叠加保留相位，"
     "见式(6)，各路径同相时相互增强、反相时相互抵消，结果随距离剧烈起伏；非相干叠加"
     "只累加功率，得到平滑的平均趋势。")
equation("eq_coherent", 6)
para("两种结果各有用途：相干结果对应实际接收波形与通信中的码间干扰，非相干结果对应"
     "平均能量分布和声呐作用距离估计。本实验两种都会计算并对比。")

h2("2.5 干涉条纹与简正波")
para("相干传播损失曲线上的周期性起伏来自多阶简正波的干涉。可以把声场理解成若干个"
     "竖直方向的驻波模式，每个模式沿水平方向以各自的波数传播；两个模式之间的相位差"
     "随距离线性变化，于是它们的叠加忽而增强、忽而抵消，形成明暗相间的条纹。")
para("条纹间距由两个模式的水平波数差决定。相邻高阶模式之间的间距只有几十米，最低阶"
     "模式之间的间距可以达到上千米，因此相干声场是粗条纹叠加细条纹的结构。这也解释了"
     "实验中的一个现象：用 50 m 的距离步长计算相干声场时会出现假的条纹，即采样混叠，"
     "必须把步长降到 5 m 才能看清真实的干涉结构。")

h2("2.6 海面与海底边界")
para("海面可以近似看成压力释放的软边界，声波反射后相位翻转约 180°，反射系数接近 −1。"
     "海底则是决定浅海传播损失的关键边界，需要用三个参数描述：海底声速、海底密度和"
     "海底吸收。")
para("海底吸收用 dB/λ 表示，意思是声波在海底介质中每传播一个波长衰减多少分贝。本实验"
     "取沙底参数 0.5 dB/λ，对应 300 Hz 时波长 5 m，也就是在海底中每米衰减约 0.1 dB，"
     "多次触底的声线会被迅速削弱。泥质海底的吸收更大、声速更低，传播条件通常更差。")

h2("2.7 BELLHOP 模型与运行类型")
para("BELLHOP 是 Acoustics Toolbox 中的水声传播计算程序，采用射线理论（高斯射线束）"
     "求解声场。它的输入是一个文本格式的环境文件（.env），内容包括频率、声速剖面、"
     "海底参数、声源与接收器位置以及发射角范围。")
para("按任务类型不同，它输出不同的结果文件，常用的几种是：R 声线轨迹、E 本征声线、"
     "A 到达结构、C 相干传播损失、I 非相干传播损失。本实验用 Python 包 aubellhop 调用"
     "它，并用 arlpy 生成环境文件、读取计算结果。")
para("射线方法擅长给出多途结构和宽带结果，适合本实验这种数百赫兹、100 m 水深的浅海"
     "场景；当频率很低、必须考虑绕射与强模态效应时，简正波模型或抛物方程模型更合适。")


# ======================================================================
# 三、实验环境与复现准备
# ======================================================================
h1("三、实验环境与复现准备")

h2("3.1 软件与版本")
table(
    ["组件", "版本或位置", "作用"],
    [
        ["Python", "3.12.14", "运行计算与绘图脚本"],
        ["aubellhop", "0.2.1", "BELLHOP 的 Python 封装，内含 bellhop.exe"],
        ["arlpy", "1.9.3", "生成环境文件、读取结果、绘图"],
        ["NumPy", "1.26.4", "数组与数值运算"],
        ["SciPy", "1.13.1", "插值等辅助计算"],
        ["Matplotlib", "随环境安装", "绘制声线、到达结构与传播损失图"],
        ["conda 环境", "underwater", "本实验使用的独立环境"],
    ],
    widths_cm=[3.2, 5.6, 6.8],
    cap="表1 实验环境与软件版本",
)

h2("3.2 两个必须注意的环境问题")
para("第一个问题是可执行文件的查找路径。arlpy 只通过系统的 PATH 变量查找 bellhop.exe，"
     "不会去 Python 包目录里找。如果从没有激活 conda 环境的地方启动，例如某些编辑器的"
     "内置终端或 Jupyter 内核，程序会找不到可执行文件，此时 BELLHOP 不会给出明确的错误"
     "信息，只在日志中留下一句 Bellhop did not generate expected output file，很容易被"
     "误判成参数问题。解决办法是把 aubellhop 的 bin 目录加入 PATH，或在脚本里显式追加。")
para("第二个问题是运行库版本。aubellhop 自带的 bellhop.exe 由 MSYS2 GCC 16.1.0 编译，"
     "运行时需要同一来源的运行库。如果机器上优先加载了 conda-forge 的 libgfortran"
     "（16.2.0），到达结构（run type A）和声线（R）依然可以正常计算，但任何要生成 .shd"
     "文件的任务，也就是相干与非相干传播损失，会直接崩溃，退出码为 0xC0000374 或"
     "0xC0000005。这种部分功能正常的情况最容易误导排查方向：只验证到达路径时，一切"
     "看起来都是对的。解决办法是把与编译器匹配的 7 个 MSYS2 运行库放到 exe 同目录，"
     "Windows 会优先从可执行文件所在目录加载动态库。")

h2("3.3 两种运行方式")
para("方式一，命令行运行完整实验。命令如下，全部计算与绘图约 5 秒完成，结果写入"
     "output 目录。")
para("conda activate underwater", indent=False, size=10, ascii_font="Consolas",
     ea_font="Consolas", space_after=0)
para("cd /d <项目目录>", indent=False, size=10,
     ascii_font="Consolas", ea_font="Consolas", space_after=0)
para("python scripts\\shallow_water_bellhop.py", indent=False, size=10,
     ascii_font="Consolas", ea_font="Consolas", space_after=8)
para("激活环境后也可以直接运行项目目录下的 run.bat，它等价于上面的命令。")
para("方式二，分步运行。执行 python scripts\\build_notebook.py 会生成 notebook 文件"
     "notebooks\\01_shallow_water_bellhop.ipynb，其中把整个实验拆成环境自检、声线、到达结构、"
     "传播损失、传播损失场、温跃层对比六步，每一步都有检查点和预期数值，适合第一次"
     "上手时对照学习。")


# ======================================================================
# 四、实验设置
# ======================================================================
h1("四、实验设置")

h2("4.1 场景一：Pekeris 波导")
para("第一个场景是最简单的浅海模型：均匀水层覆盖在均匀半空间海底之上，海水等声速，"
     "海底参数处处相同。这种模型在文献中称为 Pekeris 波导，是理解浅海传播的起点。")
table(
    ["参数", "取值", "说明"],
    [
        ["工作频率", "300 Hz", "水声常用低频段"],
        ["水深", "100 m", "典型浅海大陆架水深"],
        ["海水声速", "1500 m/s", "等声速剖面"],
        ["海底声速", "1700 m/s", "沙质海底"],
        ["海底密度", "1.8 g/cm³", "即 1800 kg/m³"],
        ["海底吸收", "0.5 dB/λ", "沙底典型值"],
        ["声源深度", "50 m", "位于水层中部"],
        ["接收深度", "50 m（损失场 2 至 98 m）", "单点与场两种接收方式"],
        ["水平距离", "0.2 至 10 km", "传播损失曲线步长 50 m"],
        ["发射角范围", "±80°", "声线覆盖范围"],
    ],
    widths_cm=[3.4, 6.0, 6.2],
    cap="表2 场景一的环境参数",
)

h2("4.2 场景二：温跃层")
para("第二个场景把等声速剖面换成负声速梯度剖面，模拟夏季常见的温跃层：表层水温高、"
     "声速大，20 至 40 m 之间温度快速下降，深层水温低、声速小。除声速剖面外，其余参数"
     "与表2完全相同，接收深度取 10 m（温跃层上方）和 90 m（温跃层下方）。")
table(
    ["深度 / m", "声速 / (m·s⁻¹)", "对应水层特征"],
    [
        ["0", "1502", "表层混合层"],
        ["20", "1500", "混合层底部"],
        ["40", "1490", "温跃层中部"],
        ["60", "1480", "温跃层底部"],
        ["100", "1478", "近海底冷水"],
    ],
    widths_cm=[3.4, 4.4, 7.8],
    aligns=["center", "center", "left"],
    cap="表3 场景二的声速剖面采样点",
)

h2("4.3 接收网格的选取")
para("声线、到达结构和传播损失对接收点的要求并不相同。计算声线时，接收点是若干离散"
     "位置，本实验每 200 m 放一个，范围 0.2 至 5 km；计算到达结构时只取一个点，即"
     "5 km、50 m；计算传播损失曲线时需要密集的距离网格，步长 50 m，范围 0.2 至 10 km；"
     "绘制传播损失场时还要把接收深度铺满水层，即 2 至 98 m、步长 2 m。观察相干干涉"
     "条纹时，距离步长必须从 50 m 降到 5 m。这一点在复现时最容易忽略，步长选错会得到"
     "看似合理、实际错误的条纹。")


# ======================================================================
# 五、实验步骤与检查点
# ======================================================================
h1("五、实验步骤与检查点")
para("按表4的顺序执行，每一步结束后对照预期结果。如果某一步得到空结果或者数字相差"
     "很远，先回到上一步检查输入，再继续往下做。")
table(
    ["步骤", "操作", "预期结果"],
    [
        ["0", "环境自检：导入 aubellhop 与 arlpy，打印版本和模型列表",
         "版本号正确，模型列表为 ['bellhop']"],
        ["0", "冒烟测试：计算一个 25 kHz、25 m 水深的算例",
         "输出若干条到达路径，程序无报错"],
        ["1", "定义环境：按表2生成 .env 文件并打印参数",
         "参数表与设置一致"],
        ["2", "声线：run type R，接收点 0.2 至 5 km，每 200 m 一个",
         "约 50 条声线"],
        ["3", "到达结构：run type A，接收点 5 km、50 m",
         "96 条路径，时延展宽约 487 ms"],
        ["4", "传播损失：run type C 与 I，距离 0.2 至 10 km，步长 50 m",
         "1 km 处 55.3 / 50.6 dB，10 km 处 67.4 / 64.1 dB"],
        ["5", "传播损失场：接收深度 2 至 98 m，非相干模式",
         "得到 49 行 197 列的结果矩阵"],
        ["6", "温跃层对比：改用表3的剖面，接收深度 10 m 与 90 m",
         "浅层 10 km 处相差约 +2.7 dB"],
    ],
    widths_cm=[1.2, 8.0, 6.4],
    aligns=["center", "left", "left"],
    cap="表4 实验步骤与检查点",
)
para("需要说明的是，第 4 步得到的传播损失不是直接输出的分贝值。接口返回的是复声压，"
     "必须按式(3)换算。如果直接把返回值当作分贝使用，会得到复数结果，这是初学者最常"
     "遇到的接口问题。")


# ======================================================================
# 六、结果与分析
# ======================================================================
h1("六、结果与分析")

h2("6.1 声速剖面与本征声线")
figure(ASSETS / "fig_ssp_rays.png", 15.4,
       "图2 场景一的声速剖面与本征声线")
para("图2(b)是 5 km 范围内的声线轨迹。50 条声线在 100 m 厚的水层里反复反射，发射角"
     "越大，与海底和海面的作用次数越多。图中靠近海面的少数声线在 5 km 内几乎没有与"
     "海底作用，它们的能量衰减最小，也是最先到达的路径。")

h2("6.2 到达结构")
figure(ASSETS / "fig_arrivals.png", 15.6,
       "图3 5 km 处到达结构、发射角分布与反射次数统计")
para("图3(a)给出 5 km 处的到达结构。96 条路径的到达时间从 3.3333 s 延伸到 3.8204 s，"
     "展宽 487 ms。最早的到达时间正好等于 5000 除以 1500，即 3.333 s，对应沿水平方向"
     "直线传播的路径，这个数值可以用来检查计算是否正确。")
para("从发射角看，能够到达 5 km 的声线集中在正负 29° 以内。更大角度的声线虽然也发射"
     "出去了，但它们在传播过程中反复触底，能量被海底吸收掉，到达时已经低于计算门限；"
     "图3(b)中点的颜色和大小也反映了这一点，时延越晚的路径通常触底次数越多、幅度越低。"
     "图3(c)显示反射次数的分布：多数路径在 5 km 内与海面和海底各反射 5 到 13 次。")
para("96 条路径中有 76 条位于最强路径的 20 dB 以内，90 条位于 40 dB 以内。也就是说，"
     "时延上路径分布很宽，但能量集中在少数早期到达的路径上，这一点对通信系统设计很"
     "重要，因为均衡器只需要处理有限数量的强路径。")

h2("6.3 传播损失曲线")
figure(ASSETS / "fig_tl_curve.png", 13.0,
       "图4 接收深度 50 m 处的相干与非相干传播损失，以及两种理想扩展规律")
table(
    ["距离", "非相干（实测）", "相干（实测）", "球面扩展 20 log r", "柱面扩展 10 log r"],
    [
        ["0.2 km", "41.8 dB", "42.9 dB", "46.0 dB", "23.0 dB"],
        ["1 km", "50.6 dB", "55.3 dB", "60.0 dB", "30.0 dB"],
        ["5 km", "59.6 dB", "53.5 dB", "74.0 dB", "37.0 dB"],
        ["10 km", "64.1 dB", "67.4 dB", "80.0 dB", "40.0 dB"],
    ],
    widths_cm=[2.4, 3.4, 3.0, 3.6, 3.6],
    aligns=["center", "center", "center", "center", "center"],
    cap="表5 传播损失实测值与两种理想扩展规律的比较（接收深度 50 m）",
)
para("0.2 km 处非相干传播损失为 41.8 dB，与球面扩展的 46 dB 接近，说明近场声波还没有被"
     "边界限制住，能量按球面向外扩散。随着距离增加，声能被限制在 100 m 厚的水层内，"
     "损失增长明显变缓：1 km 到 10 km 只增加 13.4 dB，远小于球面扩展的 20 dB，也比"
     "经验值 15 dB 略缓。")
para("图4中的相干曲线围绕非相干曲线上下摆动，标准差 5.8 dB，极值区间为 40.9 到 84.6 dB。"
     "摆动是相位的直接体现：某些距离上多途信号同相叠加，损失比平均趋势低 10 dB 以上；"
     "另一些距离上反相抵消，损失比平均趋势高出十几分贝。如果只关心平均能量，用非相干"
     "结果；如果关心接收波形、通信误码或阵列处理，就必须使用相干结果。")

h2("6.4 传播损失场与干涉条纹")
figure(ASSETS / "fig_tl_map.png", 15.6,
       "图5 非相干传播损失场（左）与相干传播损失场局部放大（右）")
para("图5(a)把接收深度铺满整个水层，横轴为距离，纵轴为深度，颜色表示非相干传播损失。"
     "在等声速、沙底的条件下，损失场几乎不随深度变化，只随距离缓慢增加。这说明声能被"
     "上下边界充分混合，靠近海面与靠近海底的接收条件差别不大。")
para("图5(b)把距离范围缩小到 0.3 至 2 km，并把步长降到 5 m，用相干模式重新计算。这时"
     "可以看到清晰的明暗条纹：亮条纹是干涉增强的位置，暗条纹是干涉抵消的位置，条纹"
     "间距从几十米到上百米不等，与简正波干涉的尺度相符。")

h2("6.5 温跃层对比")
figure(ASSETS / "fig_thermocline.png", 15.4,
       "图6 温跃层剖面对浅层与深层传播损失的影响")
table(
    ["距离", "10 m 处差值", "90 m 处差值"],
    [
        ["2 km", "+0.8 dB", "−1.0 dB"],
        ["5 km", "+0.9 dB", "+2.4 dB"],
        ["10 km", "+2.7 dB", "+1.8 dB"],
    ],
    widths_cm=[3.0, 4.6, 4.6],
    aligns=["center", "center", "center"],
    cap="表6 温跃层相对等声速剖面的传播损失差值（正号表示温跃层损失更大）",
)
para("图6(b)中绿色曲线为温跃层结果，蓝色曲线为等声速结果。把海水换成负声速梯度后，"
     "声线向下弯曲，更多能量被折向海底。由于沙底吸收为"
     "0.5 dB/λ，触底次数增加意味着额外损失，因此总体传播损失上升：10 m 深处在 2 km、"
     "5 km、10 km 处分别增加 0.8、0.9 和 2.7 dB。")
para("90 m 深处的情况稍有不同。2 km 处温跃层的损失反而比等声速低 1.0 dB，因为折射"
     "把能量送进了这个深度；随着距离增加，多次触底的代价逐渐占上风，5 km 和 10 km 处"
     "分别变成增加 2.4 dB 和 1.8 dB。")
para("这里并没有出现教科书中那种强烈的表面影区。原因有两方面：一是本实验频率只有"
     "300 Hz、水深只有 100 m，声波波长远大于温跃层尺度，绕射和模态混合填补了影区；"
     "二是沙底反射仍然很强，能量可以通过海底与海面之间的多次反射到达浅层。如果提高"
     "频率、加深水深或者换用吸收更强的泥质海底，影区效应会明显得多。")

h2("6.6 结果的可信度与局限")
para("本实验的结果可以通过几个独立方式互相验证：最早到达时间与 5000 除以 1500 的解析"
     "值一致；非相干传播损失的增长率落在柱面扩展与球面扩展之间；相干损失的平均值与"
     "边界损失的量级相符。")
para("同时也应当看到局限。第一，模型假设海底是均匀半空间，真实海底存在分层和起伏，"
     "会带来额外损失；第二，声速剖面被简化成理想剖面，没有考虑季节变化与实测不确定性；"
     "第三，计算是二维的，忽略了水平方向的折射和侧向传播；第四，射线理论在高频更可靠，"
     "本实验的 300 Hz 在浅海中已经属于需要谨慎使用的频段，不过本实验的对比结论，也就是"
     "剖面变化带来几 dB 差异，对方法误差并不敏感。")


# ======================================================================
# 七、常见问题与注意事项
# ======================================================================
h1("七、常见问题与注意事项")
table(
    ["现象", "原因", "处理办法"],
    [
        ["Bellhop did not generate expected output file",
         "PATH 中没有 bellhop.exe",
         "把 aubellhop 的 bin 目录加入 PATH，或运行 run.bat"],
        ["进程崩溃，退出码 3221225477 或 −1073740940",
         "运行库与编译器不匹配",
         "确认 exe 同目录下有 7 个 MSYS2 运行库"],
        ["传播损失结果是复数",
         "接口返回复声压而非分贝值",
         "用 −20 log10|p| 换算为传播损失"],
        ["传播损失场出现规则细条纹",
         "距离步长过大导致混叠",
         "步长减小到 5 m，或改用非相干模式"],
        ["图中中文显示为方框",
         "缺少中文字体",
         "指定 Microsoft YaHei 或 SimHei"],
        ["结果为 None 或空",
         "接收网格或任务类型设置有误",
         "检查 rx_range、rx_depth 与 mode 参数"],
    ],
    widths_cm=[5.4, 4.4, 5.8],
    cap="表7 复现过程中的常见问题",
)


# ======================================================================
# 八、结论
# ======================================================================
h1("八、结论")
para("这次实验用 BELLHOP 完成了浅海声传播的完整计算流程，得到了声线、到达结构和传播"
     "损失三类结果，并用温跃层算例验证了声速剖面对传播的影响。")
para("从物理上看，浅海传播的核心特征是多途与边界作用。5 km 处的 96 条路径、487 ms 的"
     "时延展宽、13.4 log r 的扩展速率，都反映了声能在海面与海底之间反复反射、被部分"
     "吸收后向前传播的过程。相干与非相干结果的差别，标准差 5.8 dB，说明相位信息在实际"
     "系统中不可忽略。")
para("从方法上看，复现一个水声计算任务需要注意若干细节：环境变量的查找路径、运行库"
     "与编译器的匹配、接收网格与采样步长的选择。这些细节本身不涉及物理，却足以让结果"
     "从正确变成看起来正确其实错误。")


# ======================================================================
# 附录
# ======================================================================
h1("附录 A 实验文件与目录")
table(
    ["文件或目录", "说明"],
    [
        ["scripts\\shallow_water_bellhop.py", "命令行完整实验脚本"],
        ["scripts\\_bellhop_runtime.py", "运行库自检与 PATH 自举"],
        ["scripts\\build_notebook.py", "生成分步复现用的 notebook"],
        ["scripts\\report_figures.py", "生成报告插图与公式图片"],
        ["scripts\\build_report_docx.py", "生成本报告的 DOCX 文件"],
        ["scripts\\render_report_qa.py", "调用 Word 导出 PDF 并转成逐页图片，用于排版检查"],
        ["output\\figures\\", "实验图：声线、传播损失、传播损失场、温跃层对比"],
        ["output\\data\\", "结果数据：传播损失曲线、到达结构、损失场矩阵"],
        ["output\\report\\", "本报告及其插图素材"],
        ["tools\\bellhop_runtime_msys2_gcc16.1.0\\", "与编译器匹配的 MSYS2 运行库备份"],
    ],
    widths_cm=[7.2, 8.4],
    cap="表8 实验文件与目录说明",
)

h1("附录 B 主要数据文件")
para("tl_vs_range_pekeris.csv 保存场景一的传播损失曲线，包含距离、相干传播损失与非相干"
     "传播损失三列；arrivals_5km.csv 保存 5 km 处每条到达路径的时延、幅度、到达角、"
     "发射角与反射次数；tl_map_pekeris.csv 与 tl_map_pekeris_zoom_coherent.csv 分别保存"
     "非相干与相干传播损失场矩阵；tl_thermocline_vs_iso.csv 保存温跃层与等声速剖面的"
     "对比结果；summary.json 汇总主要数值。")

h1("附录 C 参考资料")
para("[1] M. B. Porter. The BELLHOP Manual and User's Guide: Preliminary Draft. "
     "Heat, Light, and Sound Research, Inc., 2011.", indent=False, space_after=3)
para("[2] M. B. Porter. Acoustics Toolbox. http://oalib.hlsresearch.com/AcousticsToolbox/",
     indent=False, space_after=3)
para("[3] F. B. Jensen, W. A. Kuperman, M. B. Porter, H. Schmidt. Computational Ocean "
     "Acoustics, 2nd ed. Springer, 2011.", indent=False, space_after=3)
para("[4] R. J. Urick. Principles of Underwater Sound, 3rd ed. McGraw-Hill, 1983.",
     indent=False, space_after=3)
para("[5] aubellhop 0.2.1. https://github.com/avc-adelaide/aubellhop",
     indent=False, space_after=3)
para("[6] arlpy 1.9.3. https://github.com/org-arl/arlpy", indent=False, space_after=3)

OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
doc.save(str(OUT_DOCX))
print("written:", OUT_DOCX)
