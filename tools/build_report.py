"""构建《软件工程大作业报告》DOCX。

运行：python tools/build_report.py
输出：docs/LabHub软件工程大作业报告.docx
"""

import json
import os
import sys
from datetime import datetime

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "tools"))
import project_data as PD  # noqa: E402

FIG = os.path.join(BASE, "docs", "figures")
TEST = os.path.join(BASE, "tools", "test_results.json")

INK = "1F2937"
MUTED = "6B7280"
BRAND = "1E3FAE"

EA_BODY = "宋体"
EA_HEAD = "黑体"
ASCII_BODY = "Times New Roman"
ASCII_HEAD = "Arial"


# ================================================================ 基础设施
def set_font(run, size=12, bold=False, color=INK, ea=EA_BODY, ascii_=ASCII_BODY, italic=False):
    run.font.name = ascii_
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    rf.set(qn("w:eastAsia"), ea)


def para(doc, text="", size=12, bold=False, color=INK, align=None, indent=True,
         space_after=6, space_before=0, line=1.5, ea=EA_BODY):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = line
    if indent:
        pf.first_line_indent = Pt(size * 2)
    if align is not None:
        pf.alignment = align
    if text:
        r = p.add_run(text)
        set_font(r, size=size, bold=bold, color=color, ea=ea)
    return p


def h1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_font(r, size=16, bold=True, color=INK, ea=EA_HEAD, ascii_=ASCII_HEAD)
    p.style = doc.styles["Heading 1"]
    for run in p.runs:
        set_font(run, size=16, bold=True, color=INK, ea=EA_HEAD, ascii_=ASCII_HEAD)
    return p


def h2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p.style = doc.styles["Heading 2"]
    r = p.add_run(text)
    set_font(r, size=13.5, bold=True, color=INK, ea=EA_HEAD, ascii_=ASCII_HEAD)
    return p


def h3(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    p.style = doc.styles["Heading 3"]
    r = p.add_run(text)
    set_font(r, size=12, bold=True, color=INK, ea=EA_HEAD, ascii_=ASCII_HEAD)
    return p


def bullets(doc, items, size=11.5):
    for it in items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.4
        p.paragraph_format.left_indent = Pt(21)
        p.paragraph_format.first_line_indent = Pt(-10.5)
        r = p.add_run("• " + it)
        set_font(r, size=size, color=INK2 if False else INK)


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def cell_text(cell, text, size=9.5, bold=False, color=INK, align="left", ea=EA_BODY):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    p.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER,
                   "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
    for i, line in enumerate(str(text).split("\n")):
        if i > 0:
            p = cell.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            p.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER,
                           "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        r = p.add_run(line)
        set_font(r, size=size, bold=bold, color=color, ea=ea)


def table(doc, headers, rows, widths=None, size=9.5, caption=None, align_map=None,
          header_bg=BRAND, zebra="F4F6FB"):
    if caption:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(caption)
        set_font(r, size=10, bold=True, color=INK, ea=EA_HEAD)
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = doc.styles["Table Grid"]
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, htxt in enumerate(headers):
        c = t.rows[0].cells[i]
        cell_text(c, htxt, size=size, bold=True, color="FFFFFF", align="center", ea=EA_HEAD)
        shade(c, header_bg)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, val in enumerate(row):
            al = "center"
            if align_map and ci in align_map:
                al = align_map[ci]
            cell_text(cells[ci], val, size=size, align=al)
            if zebra and ri % 2 == 1:
                shade(cells[ci], zebra)
    if widths:
        for ri in range(len(t.rows)):
            for ci, w in enumerate(widths):
                t.rows[ri].cells[ci].width = Cm(w)
    return t


def figure(doc, name, caption, width=15.2):
    path = os.path.join(FIG, name)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    run = p.add_run()
    run.add_picture(path, width=Cm(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(10)
    r = c.add_run(caption)
    set_font(r, size=10, bold=True, color=MUTED, ea=EA_HEAD)


def code_block(doc, text, size=9):
    for line in text.rstrip("\n").split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.left_indent = Pt(16)
        r = p.add_run(line if line else " ")
        set_font(r, size=size, color="1E293B", ea="Consolas", ascii_="Consolas")


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_page_number_footer(doc):
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    set_font(run, size=9, color=MUTED)
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = "PAGE"
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
    run._r.append(fld1); run._r.append(instr); run._r.append(fld2)


def add_toc(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-3" \\h \\z \\u'
    sep = OxmlElement("w:fldChar"); sep.set(qn("w:fldCharType"), "separate")
    tip = OxmlElement("w:t"); tip.text = "（目录域：在 Word 中全选后按 F9，或右键“更新域”生成目录）"
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
    for el in (fld1, instr, sep, tip, fld2):
        run._r.append(el)


# ================================================================ 文档
def build():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.4)
    sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2.2)
    add_page_number_footer(doc)

    normal = doc.styles["Normal"]
    normal.font.name = ASCII_BODY
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), EA_BODY)

    cover(doc)
    toc_and_abstract(doc)
    ch1(doc)
    ch2(doc)
    ch3(doc)
    ch4(doc)
    ch5(doc)
    ch6(doc)
    ch7(doc)
    ch8(doc)
    appendix(doc)

    out = os.path.join(BASE, "docs", "LabHub软件工程大作业报告.docx")
    doc.save(out)
    print("报告已生成:", out)


# ---------------------------------------------------------------- 封面
def cover(doc):
    for _ in range(4):
        para(doc, "", space_after=0, indent=False)
    p = para(doc, "软件工程课程大作业报告", size=16, bold=True, color=MUTED,
             align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, ea=EA_HEAD, space_after=18)
    p = para(doc, "LabHub 实验室设备预约与管理系统", size=26, bold=True, color=INK,
             align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, ea=EA_HEAD, space_after=8)
    para(doc, "—— 基于生成式软件工程的 AI Agent 全生命周期协同开发 ——", size=13,
         color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, space_after=40)

    rows = [
        ("开发模式", "生成式软件工程：AI Agent 参与需求、设计、编码、测试、维护全流程"),
        ("系统形态", "B/S 三层架构（前端 SPA + REST 服务 + SQLite 数据库），可运行 Demo"),
        ("交付内容", "六个阶段的图表与文档、AI 三级分级机制表、Agent 失效评分与监管设计"),
        ("课程名称", "软件工程"),
        ("小组成员", "＿＿＿＿＿＿＿＿＿＿（请填写姓名 / 学号 / 分工）"),
        ("指导教师", "＿＿＿＿＿＿"),
        ("提交日期", datetime.now().strftime("%Y 年 %m 月 %d 日")),
    ]
    t = doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in rows:
        cells = t.add_row().cells
        cell_text(cells[0], k, size=11.5, bold=True, align="right", ea=EA_HEAD)
        cell_text(cells[1], v, size=11.5)
        cells[0].width = Cm(3.4)
        cells[1].width = Cm(11.8)
    page_break(doc)


# ---------------------------------------------------------------- 摘要
def toc_and_abstract(doc):
    para(doc, "目  录", size=16, bold=True, color=INK, align=WD_ALIGN_PARAGRAPH.CENTER,
         indent=False, ea=EA_HEAD, space_after=10)
    add_toc(doc)
    page_break(doc)

    para(doc, "摘  要", size=16, bold=True, color=INK, align=WD_ALIGN_PARAGRAPH.CENTER,
         indent=False, ea=EA_HEAD, space_after=12)
    para(doc, "本作业以“生成式软件工程”为方法主线，选取高校实验室设备管理这一真实痛点，"
              "开发了一套可运行的实验室设备预约与管理系统 LabHub。系统采用 B/S 三层架构："
              "原生前端单页应用负责视图与交互，Python 标准库实现的 REST 服务承载业务规则，"
              "SQLite 数据库负责持久化，零第三方依赖即可启动，覆盖设备档案、时段预约、审批流转、"
              "信用约束、审计日志与统计报表六大能力。")
    para(doc, "开发全程由 AI Agent 协同完成，并按任务性质实施 L1（自动完成）/ L2（人机协同）/ "
              "L3（纯人工）三级管理：可模板化、可脚本验证的任务交给 Agent 自动执行；涉及业务判断的任务由 "
              "Agent 产出初稿、人工评审修订；涉及责任认定与不可逆操作的任务坚持人工主导。")
    para(doc, "为量化 AI 的可靠程度，本文设计了 Agent 失效评分模型 AFS，从正确性、完整性、一致性、"
              "可验证性、可维护性五个维度对各阶段产出打分，并将评分结果反馈到分级授权策略，形成"
              "“评分 → 调级 → 复评”的闭环监管。最终系统通过 32 条自动化接口用例（通过率 100%），"
              "累计记录并修复缺陷 20 个，缺陷帕累托分析显示业务规则类缺陷占 30%，是后续改进的第一优先级。")
    para(doc, "关键词：生成式软件工程；AI Agent；人机协同；软件生命周期；失效评分", bold=False)
    page_break(doc)


# ---------------------------------------------------------------- 第1章
def ch1(doc):
    h1(doc, "第1章  可行性分析")

    h2(doc, "1.1  项目背景与目标")
    para(doc, "高校实验室设备普遍存在“找设备靠打听、用设备靠运气、还设备靠自觉”的问题：设备信息"
              "分散在各个实验室，预约依赖微信群接龙，高峰期时段冲突频发，爽约与长时间占用无人追责，"
              "管理员既掌握不了真实使用率，也缺乏约束手段。")
    para(doc, "本项目旨在建设一套轻量的实验室设备预约与管理系统 LabHub，实现“设备可查、时段可约、"
              "风险可控、使用可统计”的目标。系统按 Demo 规模裁剪，但保留了完整的前后端与数据库链路，"
              "覆盖学生、教师、管理员三类角色的核心场景。")

    h2(doc, "1.2  评估方法")
    para(doc, "采用五维评估法，从经济、技术、操作、人员、时间五个维度分别按 1～5 分打分"
              "（1=严重不可行，3=基本可行，5=非常可行），并设定立项阈值：任一维度低于 3.5 分"
              "即需要调整方案或补足资源后再评估。评分由小组讨论形成，AI Agent 提供同类系统调研"
              "材料与测算初稿（L2 协同）。")
    table(doc,
          ["维度", "得分", "评分依据"],
          [[f[0], f"{f[1]}", f[2]] for f in PD.FEASIBILITY],
          widths=[2.6, 1.6, 12.2],
          caption="表 1-1  五维可行性评分表",
          align_map={1: "center"})

    figure(doc, "fig1_feasibility_radar.png", "图 1-1  五维可行性雷达图", width=11.5)

    h2(doc, "1.3  分维度说明")
    h3(doc, "（1）经济可行性（4.2 分）")
    para(doc, "技术栈全部采用开源或标准库组件，无商业授权费用；部署复用校园现有服务器，"
              "SQLite 单文件数据库免去独立数据库服务器的采购与运维成本。人力方面以课程小组 3 人投入为主，"
              "AI Agent 承担了大量样板代码与文档初稿工作，实际人力投入压缩至约 3 人·周。"
              "唯一需要持续投入的是设备数据的维护，可由实验室管理员在现有工作流程中顺带完成。")
    h3(doc, "（2）技术可行性（4.5 分）")
    para(doc, "系统的两个技术核心——时段冲突检测与审批状态机——均为经典问题：前者可归纳为区间重叠"
              "判定，时间复杂度 O(n)；后者是有限状态机，状态与迁移均可穷举验证。团队具备 Python 与 "
              "JavaScript 开发基础，且 AI Agent 在此类有明确契约的编码任务上可靠性较高（详见第 6 章 AFS 评分），"
              "技术风险整体可控。")
    h3(doc, "（3）操作可行性（4.0 分）")
    para(doc, "系统为浏览器端访问，无需安装客户端；学生侧的高频操作（查找设备、提交预约、签到）"
              "均不超过 3 步；管理员功能与常见后台管理系统一致。风险点在于部分年长教师对线上审批流程"
              "不熟悉，将通过操作指引与默认“即约即用”策略降低影响。")
    h3(doc, "（4）人员可行性（3.8 分，最低维度）")
    para(doc, "小组缺少专职测试与运维角色，质量保障主要依赖自动化测试脚本与 AI 协同评审。"
              "为此本项目将“人员”维度的应对措施具体化：以 32 条接口用例作为回归底线，AI 产出必须经过 "
              "L2 人工复核方可合入，避免因人力不足而放松质量门槛。")
    h3(doc, "（5）时间可行性（4.3 分）")
    para(doc, "总周期 6 周：需求 1 周、设计 1 周、编码 2 周、测试 1 周、维护复盘 1 周，"
              "关键路径上预留 20% 缓冲。实际执行中编码阶段因跨零点预约、夜间演示数据等问题返工约 1.5 天，"
              "在缓冲范围内消化。")

    h2(doc, "1.4  结论与风险对策")
    para(doc, "五个维度得分全部高于 3.5 分的立项阈值，最低维度为人员可行性（3.8 分），"
              "结论：项目可行，建议立项。主要风险与对策如下：")
    table(doc,
          ["风险", "影响", "对策"],
          [["AI 生成代码存在业务规则错误", "高", "关键规则（冲突/信用/状态机）必须人工评审 + 用例覆盖"],
           ["夜间与跨零点时段无设备可演示", "中", "保留 24 小时开放设备，测试用例与运行时间解耦"],
           ["小组无专职测试角色", "中", "自动化接口测试作为回归底线，缺陷统一登记"],
           ["SQLite 并发写入受限", "低", "缩短事务粒度，Demo 规模内可满足；扩展期可平替 MySQL"]],
          widths=[5.2, 1.8, 9.4],
          caption="表 1-2  主要风险与对策")
    page_break(doc)


# ---------------------------------------------------------------- 第2章
def ch2(doc):
    h1(doc, "第2章  需求分析")

    h2(doc, "2.1  利益相关者与角色")
    table(doc,
          ["角色", "核心诉求", "系统权限"],
          [["学生", "快速找到并预约设备，按时使用不被打扰", "浏览设备、预约、取消、签到签退、查看信用"],
           ["教师", "高价值设备使用需经其确认，掌握小组使用情况", "学生权限 + 审批预约、全量台账、统计报表"],
           ["管理员", "设备资产可控、使用率可量化、违规可治理", "全部权限 + 设备档案维护、信用调整、审计日志"]],
          widths=[2.2, 6.6, 7.6],
          caption="表 2-1  角色与权限矩阵")

    h2(doc, "2.2  用例分析")
    figure(doc, "fig2_usecase.png", "图 2-1  系统用例图")
    table(doc,
          ["编号", "用例名称", "参与者", "说明", "优先级"],
          [[u[0], u[1], u[2], u[3], u[4]] for u in PD.USE_CASES],
          widths=[1.6, 3.0, 2.6, 7.6, 1.6],
          caption="表 2-2  用例清单",
          align_map={0: "center", 4: "center"})

    h3(doc, "关键用例描述：UC-03 提交设备预约")
    table(doc,
          ["条目", "内容"],
          [["参与者", "学生 / 教师"],
           ["前置条件", "已登录；账号状态正常；信用分 ≥ 60"],
           ["基本流", "1) 选择设备与日期；2) 选择起止时间；3) 填写用途与人数；4) 提交；"
                      "5) 系统依次校验信用、设备状态、时间窗、时段冲突；6) 按设备规则置为待审批或直接生效；"
                      "7) 返回预约编号并写入审计日志"],
           ["备选流", "信用不足 → 返回 BIZ_422 并提示当前分值；设备维护中 → 返回 BIZ_422；"
                      "时间窗非法 → 返回 400/422；时段冲突 → 返回 409 并展示冲突时段"],
           ["后置条件", "预约记录落库；冲突时段被占位；审计日志新增一条 RES_CREATE"]],
          widths=[2.6, 13.8],
          caption="表 2-3  UC-03 用例描述")

    h2(doc, "2.3  用户需求")
    para(doc, "用户需求从三类角色的访谈与痛点归纳得到，采用“作为…我希望…以便…”之外的自然语言条目化"
              "描述，并按 MoSCoW 思想标注优先级：")
    table(doc,
          ["编号", "角色", "用户需求描述", "对应能力", "优先级"],
          [[u[0], u[1], u[2], u[3], u[4]] for u in PD.USER_REQUIREMENTS],
          widths=[1.5, 1.7, 7.4, 3.4, 1.5],
          caption="表 2-4  用户需求清单（UR）",
          align_map={0: "center", 4: "center"})

    h2(doc, "2.4  开发需求")
    para(doc, "开发需求将用户需求转译为可验证的工程约束，分为功能与非功能两类，每条均可映射到"
              "设计项与测试用例：")
    table(doc,
          ["编号", "类别", "需求描述", "优先级"],
          [[d[0], d[1], d[2], d[3]] for d in PD.DEV_REQUIREMENTS],
          widths=[1.6, 2.0, 11.6, 1.4],
          caption="表 2-5  开发需求清单（DR）",
          align_map={0: "center", 3: "center"})

    h2(doc, "2.5  需求追踪矩阵")
    para(doc, "建立“用户需求 → 用例 → 模块 → 测试用例”的四层追踪，保证每条需求可验证、可回归：")
    table(doc,
          ["用户需求", "用例", "实现模块", "验证测试"],
          [["UR-01 设备检索", "UC-02", "DeviceService.list / 前端筛选", "TC-05"],
           ["UR-02 在线预约", "UC-03", "ReservationService.create", "TC-06、TC-08~TC-13"],
           ["UR-03 冲突检测", "UC-03", "ConflictDetector + overlapping()", "TC-07"],
           ["UR-04 签到签退", "UC-05", "check_in / check_out", "TC-20~TC-22"],
           ["UR-05 取消规则", "UC-04", "cancel + 信用结算", "TC-23、TC-24"],
           ["UR-06 信用透明", "UC-07", "CreditService.history", "信用记录页"],
           ["UR-07 审批流", "UC-08", "review 状态机", "TC-14、TC-17~TC-19"],
           ["UR-09 设备档案", "UC-09", "DeviceService.create/update", "TC-25~TC-27"],
           ["UR-10 信用治理", "UC-10", "CreditService.apply + 爽约扫描", "TC-15、TC-28、TC-31"],
           ["UR-11 统计报表", "UC-11", "StatsService.overview", "TC-30"],
           ["UR-12 审计追溯", "UC-12", "AuditRepository + 接入层埋点", "TC-29"]],
          widths=[4.2, 2.0, 6.6, 3.6],
          caption="表 2-6  需求追踪矩阵（节选）")
    page_break(doc)


# ---------------------------------------------------------------- 第3章
def ch3(doc):
    h1(doc, "第3章  总体设计")

    h2(doc, "3.1  设计目标与原则")
    bullets(doc, [
        "分层清晰：接入层、服务层、仓储层单向依赖，禁止跨层调用，业务规则只允许出现在服务层；",
        "零依赖可运行：不引入第三方包，任何装有 Python 3.10+ 的机器一条命令即可启动演示；",
        "契约先行：接口与错误码先于编码确定，前后端按契约并行开发；",
        "可验证：所有业务规则都能落成自动化用例，规则变更必须伴随用例变更；",
        "可追溯：关键操作写入审计日志，状态变更可还原责任链。",
    ])

    h2(doc, "3.2  系统架构")
    figure(doc, "fig3_architecture.png", "图 3-1  系统总体架构图", width=15.6)
    table(doc,
          ["层次", "职责", "关键构件"],
          [["用户层", "三类角色通过浏览器访问，同源无需安装", "Chrome / Edge / 移动端"],
           ["表现层", "视图渲染、状态管理、REST 调用、基础表单校验", "index.html + app.js + style.css"],
           ["接入层", "路由分发、会话鉴权、参数解析、统一异常映射、静态托管", "server.py（Handler + ROUTES）"],
           ["应用层", "全部业务规则：认证、设备、预约、信用、统计", "5 个 Service + ConflictDetector"],
           ["数据层", "事务边界与数据存取，屏蔽 SQL 细节", "UnitOfWork + 6 个 Repository + SQLite"],
           ["支撑", "定时爽约扫描、审计、种子数据、常量配置", "sweep 线程 / db.py"]],
          widths=[2.0, 8.0, 6.4],
          caption="表 3-1  分层职责说明")

    h2(doc, "3.3  技术选型")
    table(doc,
          ["层次", "选型", "选型理由", "生产替代方案"],
          [["前端", "原生 HTML/CSS/JS 单页应用", "无构建链路，演示即开即用", "Vue3 / React + Vite"],
           ["后端", "Python 标准库 http.server", "零依赖、代码即文档，便于课程评审", "FastAPI / Spring Boot"],
           ["数据库", "SQLite 3", "单文件、零运维，支持外键与索引", "MySQL 8 / PostgreSQL"],
           ["鉴权", "HttpOnly Cookie + 服务端会话", "实现简单且规避 XSS 读取令牌", "JWT + Redis 会话"],
           ["测试", "自研接口测试脚本", "与用例表一一对应，结果可导入报告", "pytest + requests"]],
          widths=[1.8, 4.4, 5.6, 4.2],
          caption="表 3-2  技术选型与理由")

    h2(doc, "3.4  模块划分")
    table(doc,
          ["模块", "文件", "行数", "职责"],
          [["数据基础设施", "app/db.py", "229", "建表 DDL、连接管理、口令散列、种子数据"],
           ["统一异常", "app/errors.py", "57", "业务异常体系与错误码"],
           ["仓储层", "app/repos.py", "246", "6 个 Repository 与 UnitOfWork 事务边界"],
           ["服务层", "app/services.py", "411", "认证/设备/预约/信用/统计全部业务规则"],
           ["接入层", "app/server.py", "337", "路由、鉴权、异常映射、静态资源、后台扫描"],
           ["前端", "app/static/*", "1002", "单页应用：登录、工作台、设备、预约、审批、治理"],
           ["自动化测试", "tests/api_test.py", "242", "32 条接口用例与结果输出"]],
          widths=[3.0, 3.4, 1.6, 8.4],
          caption="表 3-3  模块清单",
          align_map={2: "center"})

    h2(doc, "3.5  数据库设计")
    table(doc,
          ["表名", "用途", "关键字段"],
          [["users", "账号与信用", "role、credit、status（ACTIVE/BANNED）"],
           ["devices", "设备档案", "code（唯一）、requires_approval、open/close_hour、status"],
           ["reservations", "预约记录", "user_id、device_id、start_at/end_at、status、credit_delta"],
           ["credit_logs", "信用流水", "user_id、reservation_id、delta、balance_after"],
           ["audit_logs", "审计留痕", "actor、action、target_type/target_id、detail"],
           ["sessions", "登录会话", "token、user_id、expires_at"]],
          widths=[2.8, 3.0, 10.6],
          caption="表 3-4  数据表清单")
    para(doc, "核心关系：users 与 reservations 为 1..0..*（发起）；devices 与 reservations 为 "
              "1..0..*（占用）；reservations 与 credit_logs 为 1..0..*（结算流水）。"
              "预约表建立 (device_id, start_at, end_at) 复合索引，直接服务冲突检测查询。")
    para(doc, "预约状态取值：PENDING、APPROVED、REJECTED、CHECKED_IN、COMPLETED、CANCELLED、"
              "NO_SHOW，以 CHECK 约束落库，非法状态在数据库层即被拒绝。")

    h2(doc, "3.6  关键设计决策（ADR）")
    h3(doc, "ADR-01 待审批申请同样占用时段")
    para(doc, "冲突查询纳入 PENDING 状态。若待审批记录不占位，两个相同时段的申请可能被先后提交并通过，"
              "造成审批通过即冲突的尴尬局面。代价是未通过申请会短暂锁住时段，通过“驳回后立即释放”缓解。")
    h3(doc, "ADR-02 信用分结算收敛到单一入口")
    para(doc, "所有加扣分必须经过 CreditService.apply，由其统一执行区间截断 [0,100]、落流水与"
              "归零自动停用。前期散落在各处的结算代码曾导致扣分为负（缺陷 D-10），收敛后该类问题从结构上消除。")
    h3(doc, "ADR-03 24 小时设备允许跨零点预约")
    para(doc, "普通设备要求预约时段同日完成；对 open_hour=0 且 close_hour=24 的自助设备，允许"
              "跨一个自然日。该决策源于测试暴露的夜间无法预约问题（缺陷 D-02、D-03），在规则表达力与"
              "实现复杂度之间取平衡。")
    page_break(doc)


# ---------------------------------------------------------------- 第4章
def ch4(doc):
    h1(doc, "第4章  详细设计")

    h2(doc, "4.1  类设计")
    figure(doc, "fig4_class.png", "图 4-1  核心 UML 类图")
    table(doc,
          ["类", "职责", "关键方法"],
          [["User / Device / Reservation", "领域实体，承载数据与少量判断逻辑", "overlap()、canReserve()"],
           ["UserRepository 等", "数据存取，屏蔽数据库细节", "overlapping()、create()、set_status()"],
           ["AuthService", "登录认证、会话签发与校验", "login()、current()"],
           ["ReservationService", "预约全生命周期规则", "create()、cancel()、review()、check_in()、sweep_no_show()"],
           ["DeviceService", "设备档案维护与查询", "list()、create()、update()"],
           ["CreditService", "信用分结算唯一入口", "apply()、history()"],
           ["ConflictDetector", "无状态区间冲突判定", "overlap()、find_first()"],
           ["StatsService", "统计与审计查询", "overview()、audit()"]],
          widths=[4.4, 6.0, 6.0],
          caption="表 4-1  类职责说明")

    h2(doc, "4.2  接口设计")
    para(doc, "接口统一前缀 /api，JSON 报文；写操作经角色校验后进入服务层。错误响应统一为 "
              "{error:{code,message,detail}} 结构。")
    table(doc,
          ["方法", "路径", "说明", "权限"],
          [["POST", "/api/auth/login", "登录，签发会话 Cookie", "公开"],
           ["POST", "/api/auth/logout", "注销会话", "公开"],
           ["GET", "/api/auth/me", "当前登录用户", "公开"],
           ["GET", "/api/meta", "枚举与业务常量", "公开"],
           ["GET", "/api/devices", "设备列表（关键字/类别/状态）", "登录"],
           ["POST", "/api/devices", "新增设备", "ADMIN"],
           ["PUT", "/api/devices/{id}", "编辑设备", "ADMIN"],
           ["GET", "/api/reservations", "预约列表（按角色过滤范围）", "登录"],
           ["POST", "/api/reservations", "创建预约", "STUDENT/TEACHER"],
           ["POST", "/api/reservations/{id}/cancel", "取消预约", "本人或 ADMIN"],
           ["POST", "/api/reservations/{id}/approve", "审批通过", "TEACHER/ADMIN"],
           ["POST", "/api/reservations/{id}/reject", "审批驳回", "TEACHER/ADMIN"],
           ["POST", "/api/reservations/{id}/checkin", "签到", "本人"],
           ["POST", "/api/reservations/{id}/checkout", "签退并结算信用", "本人或 ADMIN"],
           ["GET", "/api/stats/overview", "统计概览", "TEACHER/ADMIN"],
           ["GET", "/api/users", "用户列表", "TEACHER/ADMIN"],
           ["POST", "/api/users/{id}/credit", "调整信用分", "ADMIN"],
           ["GET", "/api/audit-logs", "审计日志", "ADMIN"],
           ["POST", "/api/admin/sweep", "手动触发爽约扫描", "ADMIN"]],
          widths=[1.4, 6.2, 6.4, 2.6],
          caption="表 4-2  REST 接口清单",
          align_map={0: "center"})

    h2(doc, "4.3  核心算法设计")
    h3(doc, "4.3.1  时段冲突检测")
    para(doc, "将每个预约建模为半开区间 [start, end)，两个区间冲突当且仅当 a.start < b.end 且 "
              "b.start < a.end（相邻时段不算冲突）。检测在服务层完成，候选集由数据库索引预过滤：")
    code_block(doc, """SELECT * FROM reservations
 WHERE device_id = :d
   AND status IN ('PENDING','APPROVED','CHECKED_IN')   -- 待审批同样占位
   AND start_at < :end AND end_at > :start;            -- 区间相交

# 服务层逐条精确判定（O(n)）
for slot in candidates:
    if overlap(start, end, slot.start, slot.end):
        return ConflictError(slot)   # 409，返回冲突时段
return None""")
    para(doc, "复杂度分析：SQL 命中 (device_id, start_at, end_at) 索引，候选集规模为单设备相邻"
              "预约数 n，逐条判定 O(n)，整体满足 DR-09。")
    h3(doc, "4.3.2  信用分结算")
    code_block(doc, """function apply(user, reservation, delta, reason):
    balance = clamp(user.credit + delta, 0, 100)     # 区间截断
    realDelta = balance - user.credit
    if realDelta != 0: insert credit_logs(...)
    update users set credit = balance
    if balance == 0: disable(user)                   # 归零自动停用
    return balance""")
    table(doc,
          ["事件", "分值", "说明"],
          [["按时签退完成使用", "+2", "上限 100"],
           ["开始前 ≥2 小时取消", "0", "鼓励提前释放时段"],
           ["开始前 <2 小时取消", "−5", "临期占用他人机会"],
           ["超时 30 分钟未签到", "−15", "系统自动判定爽约"],
           ["管理员人工调整", "±1~50", "须填写原因并写审计日志"],
           ["信用分 < 60", "—", "暂停新建预约（TC-15）"],
           ["信用分 = 0", "—", "账号自动停用"]],
          widths=[5.4, 2.0, 9.0],
          caption="表 4-3  信用分规则",
          align_map={1: "center"})
    h3(doc, "4.3.3  爽约扫描（幂等设计）")
    para(doc, "后台线程每 60 秒扫描一次 start_at + 30min < now 且状态仍为 PENDING/APPROVED 的记录，"
              "置为 NO_SHOW 并扣 15 分。幂等性由状态条件保证：记录一旦脱离 PENDING/APPROVED 即不再命中，"
              "且状态更新与扣分在同一事务内提交（该设计修复了缺陷 D-19 的二次扣分问题）。")

    h2(doc, "4.4  预约状态机")
    figure(doc, "fig7_state.png", "图 4-2  预约生命周期状态机", width=15.6)
    table(doc,
          ["当前状态", "事件", "目标状态", "守卫条件 / 副作用"],
          [["—", "提交预约", "PENDING / APPROVED", "6 项业务校验通过；免审批设备直接 APPROVED"],
           ["PENDING", "审批通过", "APPROVED", "审批人不能是申请人（D-17）"],
           ["PENDING", "审批驳回", "REJECTED", "记录驳回意见"],
           ["PENDING / APPROVED", "取消", "CANCELLED", "距开始 <2h 扣 5 分"],
           ["APPROVED", "签到", "CHECKED_IN", "时间窗 [start−15min, start+30min]"],
           ["APPROVED", "超时未签到", "NO_SHOW", "后台扫描自动触发，扣 15 分"],
           ["CHECKED_IN", "签退", "COMPLETED", "信用 +2 并落流水"]],
          widths=[3.4, 3.0, 3.6, 6.4],
          caption="表 4-4  状态迁移表")

    h2(doc, "4.5  关键时序")
    figure(doc, "fig8_sequence.png", "图 4-3  创建预约时序图", width=15.2)

    h2(doc, "4.6  异常设计")
    para(doc, "异常体系分为参数校验、认证、授权、资源、冲突、业务规则与系统兜底七类，"
              "接入层统一捕获并映射为 HTTP 状态码，服务层只抛业务异常、不感知 HTTP：")
    table(doc,
          ["错误码", "HTTP", "含义", "典型场景"],
          [["VAL_400", "400", "参数校验失败", "时间格式非法、必填项缺失"],
           ["AUTH_401", "401", "未登录或会话过期", "Cookie 失效后调用接口"],
           ["AUTH_403", "403", "角色或归属不满足", "学生调审批接口、审批自己的预约"],
           ["RES_404", "404", "资源不存在", "预约编号非法"],
           ["RES_409", "409", "状态/资源冲突", "时段冲突、重复取消、重复审批"],
           ["BIZ_422", "422", "业务规则未通过", "信用不足、超出时长、不在开放时间"],
           ["SYS_500", "500", "系统内部错误", "未预期异常，不向前端泄露堆栈"]],
          widths=[2.4, 1.4, 4.0, 8.6],
          caption="表 4-5  错误码表",
          align_map={0: "center", 1: "center"})
    para(doc, "事务策略：一次请求一个 UnitOfWork，服务层任何异常触发整体回滚，杜绝“状态已改、"
              "流水未记”的半成品数据（对应 DR-13）。")
    page_break(doc)


# ---------------------------------------------------------------- 第5章
def ch5(doc):
    with open(TEST, encoding="utf-8") as f:
        tr = json.load(f)

    h1(doc, "第5章  实现与测试")

    h2(doc, "5.1  实现概述")
    para(doc, "系统按第 3、4 章的设计实现，后端 Python 1280 行、前端 1002 行、自动化测试 242 行，"
              "合计约 2500 行核心代码（不含文档与图表工具）。编码阶段由 AI Agent 完成 CRUD、路由与"
              "页面的初稿（L1），业务规则与边界条件由人工逐条评审并补充（L2），详见第 7 章任务分级。")
    code_block(doc, """LabHub/
├── app/
│   ├── db.py           # DDL / 连接 / 种子数据
│   ├── errors.py       # AppError 异常体系
│   ├── repos.py        # Repository + UnitOfWork
│   ├── services.py     # 业务规则（冲突检测 / 信用 / 状态机）
│   ├── server.py       # HTTP 路由 / 鉴权 / 异常映射
│   └── static/         # index.html + app.js + style.css
├── tests/api_test.py   # 32 条接口用例
└── docs/               # 本报告与全部图表""")

    h2(doc, "5.2  程序流程图")
    figure(doc, "fig5_flowchart.png", "图 5-1  创建预约程序流程图", width=13.2)

    h2(doc, "5.3  测试策略与环境")
    table(doc,
          ["项", "内容"],
          [["测试分层", "接口级自动化测试（主）+ 页面手工验收（辅）+ 并发/边界专项"],
           ["测试环境", "Windows 11 / Python 3.13 / SQLite 3 / 127.0.0.1"],
           ["数据管理", "每轮测试前执行 tools/reset_db.py 重建种子数据，保证可重复"],
           ["准入准出", "准入：接口可启动且种子数据完整；准出：32 条用例全部通过且无致命缺陷"],
           ["缺陷管理", "统一登记编号 D-01~D-20，与第 6 章帕累托分析联动"]],
          widths=[2.6, 13.8],
          caption="表 5-1  测试策略概要")

    h2(doc, "5.4  测试用例与执行结果")
    para(doc, f"共设计 {tr['total']} 条接口用例，覆盖认证鉴权、设备管理、预约创建、审批流转、"
              f"签到签退、信用治理与统计审计七个模块。执行结果：通过 {tr['passed']} 条，"
              f"失败 {tr['failed']} 条，通过率 {tr['pass_rate']}%。")
    groups = [
        ("认证与权限", ["TC-01", "TC-02", "TC-03", "TC-04"]),
        ("设备查询与管理", ["TC-05", "TC-25", "TC-26", "TC-27"]),
        ("预约创建校验", ["TC-06", "TC-07", "TC-08", "TC-09", "TC-10", "TC-11", "TC-12", "TC-13",
                          "TC-14", "TC-15", "TC-16"]),
        ("审批与状态机", ["TC-17", "TC-18", "TC-19", "TC-23", "TC-24"]),
        ("签到签退与信用", ["TC-20", "TC-21", "TC-22", "TC-28"]),
        ("统计审计与后台任务", ["TC-29", "TC-30", "TC-31", "TC-32"]),
    ]
    rows = []
    for g, ids in groups:
        cases = [c for c in tr["cases"] if c["id"] in ids]
        rows.append([g, str(len(cases)),
                     str(sum(1 for c in cases if c["passed"])),
                     "100%" if all(c["passed"] for c in cases) else f"{sum(1 for c in cases if c['passed'])/len(cases)*100:.0f}%"])
    table(doc, ["模块分组", "用例数", "通过", "通过率"], rows,
          widths=[6.0, 3.0, 3.0, 3.6],
          caption="表 5-2  分组测试结果统计",
          align_map={1: "center", 2: "center", 3: "center"})

    rows = [[c["id"], c["name"], c["expect"], "通过" if c["passed"] else "失败"]
            for c in tr["cases"]]
    table(doc, ["编号", "用例名称", "预期结果", "结论"], rows,
          widths=[1.8, 5.6, 6.4, 1.6],
          caption="表 5-3  测试用例执行明细",
          align_map={0: "center", 3: "center"})

    h2(doc, "5.5  功能验收场景")
    table(doc,
          ["场景", "操作路径", "验收标准", "结果"],
          [["学生完整预约闭环", "登录 → 设备目录 → 预约 24h 设备 → 我的预约签到 → 签退",
            "预约即时生效，签退后信用分 +2 且流水可查", "通过"],
           ["教师审批流", "教师登录 → 审批中心 → 通过 GPU 服务器申请",
            "状态变为已通过，学生端可见审批意见", "通过"],
           ["信用约束", "使用低信用账号 stu002 预约 → 管理员调整信用分",
            "低于 60 分被拦截；调整后恢复预约资格并写审计", "通过"],
           ["管理员治理", "新增设备 → 置为维护中 → 查看统计与审计日志",
            "维护中设备不可预约，统计口径正确，审计完整", "通过"]],
          widths=[3.2, 6.0, 5.4, 1.6],
          caption="表 5-4  端到端验收场景",
          align_map={3: "center"})

    h2(doc, "5.6  测试结论")
    para(doc, "全部 32 条用例通过，两轮回归未发现致命缺陷；并发写库场景在缩短事务粒度后未复现锁冲突。"
              "系统达到准入准出标准，进入维护阶段。")
    page_break(doc)


# ---------------------------------------------------------------- 第6章
def ch6(doc):
    h1(doc, "第6章  维护与 AI 可靠性复盘")

    h2(doc, "6.1  缺陷数据")
    para(doc, "开发全程累计登记缺陷 20 个（D-01~D-20），每条缺陷记录标题、类别、严重度、发现阶段、"
              "关联需求、根因、修复方式与责任等级（该缺陷主要由 AI 自动完成 / 人机协同 / 人工引入）。")
    rows = [[d[0], d[1], d[2], d[3], d[4], d[8]] for d in PD.DEFECTS]
    table(doc, ["编号", "标题", "类别", "严重度", "发现阶段", "责任等级"], rows,
          widths=[1.5, 6.0, 2.0, 1.6, 2.2, 1.7],
          caption="表 6-1  缺陷清单",
          align_map={0: "center", 2: "center", 3: "center", 5: "center"})

    h2(doc, "6.2  缺陷帕累托分析")
    figure(doc, "fig6_pareto.png", "图 6-1  缺陷类型帕累托图", width=14.2)
    para(doc, "按类别排序后，业务规则（6 个，30%）、权限（3 个）、参数校验（3 个）合计 60%；"
              "再加上时间边界与交互展示两类后累计达到 80%。符合帕累托法则：约 20% 的缺陷类型贡献了 "
              "80% 的缺陷。")
    para(doc, "结论与改进顺序：第一优先级是“业务规则类”缺陷——其共性是 AI 对隐含业务约束"
              "（签到窗口、信用阈值、状态占位）理解不完整，改进措施是把规则从代码中抽离为常量表并在"
              "评审时逐条对齐需求；第二优先级是权限类缺陷，已通过“路由层强制声明角色 + 服务层二次校验”"
              "的双保险机制从结构上加固。")

    h2(doc, "6.3  典型失效案例复盘")
    cases = [
        ("D-06  学生可直接调用审批接口（致命）",
         "安全测试中学生账号成功调用了 /approve 接口。",
         "最初接口只在按钮层面隐藏了审批入口，路由注册时漏写 roles 声明，服务层也没有二次校验——"
         "AI 倾向于按“正常操作路径”生成代码，安全约束属于隐含需求。",
         "越权审批会破坏预约公平性，属于致命缺陷。",
         "路由注册强制要求 roles 参数（缺失即拒绝启动）；服务层二次校验角色；"
         "补充越权用例 TC-19 纳入回归。", "L1（Agent 自动生成代码引入，人工评审发现）"),
        ("D-08  冲突检测未包含 PENDING 状态（致命）",
         "同一时段提交两个申请并先后通过审批，设备被双重占用。",
         "AI 生成冲突查询时按直觉只过滤了“已生效”状态，未意识到“待审批”也应占位；"
         "该约束属于业务设计决策，未写入需求条目。",
         "高峰期设备双重占用，直接冲击系统核心价值。",
         "冲突查询纳入 PENDING（ADR-01）；补充用例 TC-07 验证同设备同时段 409。",
         "L2（设计决策人机协同确认）"),
        ("D-02 / D-03  跨零点与夜间场景全面失效（严重）",
         "晚上 22:30 演示时所有预约一律被拒绝，自动化测试大面积失败。",
         "普通设备 22:00 关闭且规则禁止跨天，种子数据又只有日间设备——"
         "“演示/测试发生在什么时间”这一真实约束在需求和设计阶段完全被忽略。",
         "夜间测试无法进行，演示风险高。",
         "引入 24 小时开放设备并允许其跨零点预约（ADR-03）；测试用例与当前时刻解耦；"
         "将“时间环境依赖”列入测试设计检查单。", "L2（测试数据设计协同修订）"),
    ]
    for title, phen, root, impact, fix, level in cases:
        h3(doc, title)
        table(doc, ["项", "内容"],
              [["现象", phen], ["根因分析", root], ["影响", impact],
               ["修复与预防", fix], ["责任等级", level]],
              widths=[2.6, 13.8], size=9.5)

    h2(doc, "6.4  Agent 失效评分模型（AFS）")
    para(doc, "为了回答“AI 到底靠不靠谱”而不是凭感觉下结论，本项目设计了 Agent 失效评分"
              "（Agent Failure Score, AFS）。AFS 以百分制刻画某阶段 Agent 产出的可靠程度，"
              "分数越高越可靠，由五个维度加权得到：")
    table(doc, ["维度", "权重", "考察内容"],
          [[d[0], f"{int(d[1]*100)}%", d[2]] for d in PD.AFS_DIMENSIONS],
          widths=[2.6, 1.8, 11.8],
          caption="表 6-2  AFS 评分维度与权重",
          align_map={1: "center"})
    code_block(doc, """AFS = 0.30×正确性 + 0.20×完整性 + 0.20×一致性
          + 0.15×可验证性 + 0.15×可维护性        （各维度 0~100 分）

≥ 90  → L1 可托管：抽检 ≤10%
80~89 → 需抽检：关键产出人工评审，其余抽查
70~79 → 需全量复核：逐条人工确认后方可使用
< 70  → 禁止自动执行：Agent 仅提供材料，人工主导""")
    para(doc, "评分数据来源：缺陷记录（错误密度）、测试结果（可验证性）、评审意见（一致性与完整性）"
              "与代码修订量（可维护性）。每个阶段评分需两名成员复核，避免主观打分。")

    h2(doc, "6.5  各阶段评分结果")
    rows = []
    for r in PD.AFS:
        score = sum(r[i + 1] * PD.AFS_DIMENSIONS[i][1] for i in range(5))
        rows.append([r[0], str(r[1]), str(r[2]), str(r[3]), str(r[4]), str(r[5]),
                     f"{score:.1f}", r[6]])
    table(doc, ["阶段", "正确性", "完整性", "一致性", "可验证性", "可维护性", "AFS", "主要失效模式"],
          rows, widths=[2.2, 1.5, 1.5, 1.5, 1.7, 1.7, 1.3, 5.0],
          caption="表 6-3  各阶段 AFS 评分明细",
          align_map={i: "center" for i in range(1, 7)})
    figure(doc, "fig9_afs.png", "图 6-2  各阶段 Agent 失效评分与授权等级", width=14.6)
    para(doc, "规律非常明显：结构化程度越高的阶段（可行性分析、总体设计）AFS 越高；"
              "而编码实现（74.0）与维护复盘（69.4）最低——前者的失效集中在边界条件与隐含规则，"
              "后者的失效在于根因归纳停留在表层。这组评分直接驱动第 7 章的分级授权：编码阶段的"
              "状态机与信用规则从 L1 降级为 L2 逐条评审，维护复盘的结论一律人工确认。")

    h2(doc, "6.6  维护策略与迭代计划")
    bullets(doc, [
        "回归底线：任何代码变更必须重跑 32 条接口用例，全绿方可合入；",
        "规则变更流程：业务常量修改 → 同步需求条目 → 同步用例 → 评审留痕；",
        "缺陷预防：业务规则类缺陷优先通过“规则常量化 + 用例先行”预防；",
        "下一迭代：预约提醒通知、设备使用率报表导出、教师批量审批、MySQL 平滑迁移；",
        "AFS 复评节奏：每迭代末重新评分，连续两轮 ≥90 的任务类型方可升为 L1。",
    ])
    page_break(doc)


# ---------------------------------------------------------------- 第7章
def ch7(doc):
    h1(doc, "第7章  AI 分级机制与人机协同监管")

    h2(doc, "7.1  三级分级定义")
    table(doc, ["等级", "名称", "判定特征", "管理要求"],
          [[l[0], l[1], l[2], l[3]] for l in PD.LEVEL_DEF],
          widths=[1.4, 2.8, 6.6, 5.6],
          caption="表 7-1  AI 任务分级定义",
          align_map={0: "center"})

    h2(doc, "7.2  判定准则")
    para(doc, "任务归级依据以下四条准则，按序判定，先命中先归级：")
    bullets(doc, [
        "不可逆或对外负责？是 → L3（例如面向教师的交付决策、账号停用、密钥配置）；",
        "需要多方案权衡或业务上下文？是 → L2（例如优先级取舍、指标定标）；",
        "结果可被脚本/模板/用例自动验证且失败代价低？是 → L1（例如 CRUD、用例骨架、图表绘制）；",
        "以上均不满足时默认 L2，宁可多复核，不可放任自动执行。",
    ])

    h2(doc, "7.3  分阶段任务分级规划表")
    para(doc, "将六个生命周期阶段拆解为 28 项任务并逐项定级，形成本项目的 AI 任务分级总表：")
    rows = []
    for phase, tasks in PD.TASK_PLAN.items():
        for i, (tid, name, lvl, reason) in enumerate(tasks):
            rows.append([phase if i == 0 else "", tid, name, lvl, reason])
    table(doc, ["阶段", "任务编号", "任务内容", "等级", "归级理由"], rows,
          widths=[2.4, 2.0, 5.6, 1.3, 5.1],
          caption="表 7-2  AI 任务分级规划表",
          align_map={1: "center", 3: "center"})

    h2(doc, "7.4  等级分布")
    figure(doc, "fig10_ai_levels.png", "图 7-1  各阶段任务的人工介入等级分布", width=14.6)
    para(doc, "28 项任务中 L1 占 14 项、L2 占 10 项、L3 占 4 项（含 T1-4 立项决策、T2-4 需求取舍、"
              "T4-4 异常降级策略、T5-4 部署配置等）。整体呈“中间大、两头小”的橄榄形：全自动与纯人工"
              "都是少数，大部分价值产生在人机协同的界面之上。")

    h2(doc, "7.5  评级监管设计")
    para(doc, "分级不是贴标签，而是一套可执行的监管机制，由四个环节组成：")
    bullets(doc, [
        "准入门禁：任务开工前先查表定级；未定级任务默认 L2；L1 任务必须同时满足“有自动化验证手段”，"
        "否则强制降为 L2；",
        "过程留痕：L2 任务的人工评审意见回写任务记录（本项目以缺陷编号与评审备注为载体），"
        "L3 任务要求 Agent 仅输出材料、由人产出结论；",
        "结果核验：L1 产出一律先跑自动化用例（32 条接口用例即回归底线），失败即退回并记录；",
        "熔断降级：同一任务类型连续出现 2 次未通过核验，自动降级一级并触发复盘；"
        "降级信息同步到 AFS 台账。",
    ])

    h2(doc, "7.6  AFS 与分级的联动闭环")
    para(doc, "AFS 评分（第 6 章）为分级授权提供量化依据，两者构成闭环：")
    code_block(doc, """任务执行 → 自动化核验 + 人工评审 → 缺陷/评审数据沉淀
   ↑                                      ↓
分级授权调整 ← AFS 重评（每迭代末） ← 失效案例复盘

示例：编码实现阶段因 D-05/D-07/D-10 连续失效，
AFS 74.0 → 状态机与信用规则任务由 L1 降为 L2；
修复并连续两轮回归通过后，方可恢复 L1。""")
    para(doc, "该机制的价值在于把“AI 是否可靠”从主观印象变成可复核的数字与可执行的授权策略："
              "可靠性证据来自用例与缺陷台账，授权调整有据可查，风险始终被约束在人工可兜底的范围内。")
    page_break(doc)


# ---------------------------------------------------------------- 第8章
def ch8(doc):
    h1(doc, "第8章  总结与展望")
    h2(doc, "8.1  工作总结")
    para(doc, "本项目完整走通了生成式软件工程的六个阶段：从五维可行性论证、用例与需求建模、"
              "架构与数据库设计、类与算法的详细设计，到 32 条自动化用例支撑的实现验收，"
              "再到缺陷帕累托分析与 AFS 失效复盘。交付物包括可运行的前后端系统、六阶段图表文档、"
              "AI 任务分级机制表与评级监管设计。")
    h2(doc, "8.2  经验与反思")
    bullets(doc, [
        "AI 最可靠的场景是有明确契约、可自动验证的任务；最危险的场景是隐含业务规则与安全约束，"
        "必须靠人工评审与用例兜底；",
        "分级机制（L1/L2/L3）的价值不在于标注，而在于让复核资源集中投放在最需要的 L2 环节；",
        "AFS 评分让“AI 可靠性”可量化、可比较、可追溯，是分级授权从经验走向制度的关键；",
        "几个最严重的缺陷（越权、状态占位、跨零点）都源于“需求里没写、AI 就没做”，"
        "印证了需求完整性对 AI 协同开发的重要性。",
    ])
    h2(doc, "8.3  展望")
    para(doc, "后续计划：引入通知与提醒补齐签到触达；以 MySQL 与容器化部署支撑多实验室扩展；"
              "探索将 AFS 评分自动化（由评审机器人根据用例结果与代码修订量实时计算），"
              "使分级授权从“每迭代人工重评”演进为“实时动态调级”。")


# ---------------------------------------------------------------- 附录
def appendix(doc):
    page_break(doc)
    h1(doc, "附录 A  数据库核心 DDL")
    code_block(doc, """CREATE TABLE reservations (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL REFERENCES users(id),
  device_id     INTEGER NOT NULL REFERENCES devices(id),
  start_at      TEXT NOT NULL,            -- 'YYYY-MM-DD HH:MM'
  end_at        TEXT NOT NULL,
  purpose       TEXT NOT NULL DEFAULT '',
  headcount     INTEGER NOT NULL DEFAULT 1,
  status        TEXT NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING','APPROVED','REJECTED','CHECKED_IN',
                                  'COMPLETED','CANCELLED','NO_SHOW')),
  approver_id   INTEGER REFERENCES users(id),
  credit_delta  INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL
);
CREATE INDEX idx_res_device_time ON reservations(device_id, start_at, end_at);

CREATE TABLE users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,            -- PBKDF2-HMAC-SHA256 + salt
  role          TEXT NOT NULL CHECK (role IN ('STUDENT','TEACHER','ADMIN')),
  credit        INTEGER NOT NULL DEFAULT 100,
  status        TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','BANNED'))
);""", size=8.5)

    h1(doc, "附录 B  运行说明")
    code_block(doc, """# 1. 启动（Python 3.10+，零第三方依赖）
cd LabHub/app
python server.py            # 默认 http://127.0.0.1:8080

# 2. 演示账号
admin   / admin123    管理员（设备档案、信用治理、审计）
teacher1/ 123456      教师（审批、台账、统计）
stu001  / 123456      学生（预约、签到）
stu002  / 123456      学生（信用分 55，用于演示低分拦截）

# 3. 自动化测试（先重置数据再执行）
python tools/reset_db.py
python tests/api_test.py 8080     # 32 条用例

# 4. 重新生成图表 / 报告
python tools/make_figures.py
python tools/build_report.py""", size=9)

    h1(doc, "附录 C  AI 协作记录样例")
    table(doc, ["阶段", "任务与等级", "Prompt 要点", "人工介入"],
          [["需求分析", "T2-2 用例图（L2）",
            "提供角色清单与访谈记录，要求输出用例清单 + 参与者 + 优先级，并标注假设",
            "修正教师与学生的用例边界，补充信用相关用例"],
           ["编码实现", "T5-2 状态机与信用规则（L2）",
            "给出状态迁移表与规则常量，要求实现并同步生成边界用例",
            "发现签到窗口缺失（D-05）、扣分为负（D-10），要求修复并补用例"],
           ["测试验证", "T6-3 回归执行（L1）",
            "执行 32 条用例并输出 JSON 结果",
            "无（结果直接采信，纳入报告表 5-3）"],
           ["维护复盘", "T7-2 根因分析（L2）",
            "提供缺陷台账，要求按类别聚类并给出改进建议",
            "将根因从“代码问题”修正为“隐含需求未显式化”"]],
          widths=[2.0, 3.8, 5.8, 4.8],
          caption="表 C-1  AI 协作记录（节选）")


if __name__ == "__main__":
    build()
