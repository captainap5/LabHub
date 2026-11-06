"""生成全部工程图表（PNG，200dpi）到 docs/figures/。

图形全部使用 matplotlib 手绘坐标绘制，保证同一套视觉语言。
"""

import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Ellipse, Circle, FancyArrowPatch, Rectangle
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_data as PD

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "figures")
os.makedirs(OUT, exist_ok=True)

INK = "#0f172a"
INK2 = "#334155"
MUTED = "#64748b"
LINE = "#c9d4e6"
BRAND = "#2f5bea"
BRAND_SOFT = "#edf2ff"
BRAND_DARK = "#1e3fae"
OK = "#10875a"
OK_SOFT = "#e8f7f0"
WARN = "#b45309"
WARN_SOFT = "#fdf4e6"
DANGER = "#c02b2b"
DANGER_SOFT = "#fdeded"
NEUTRAL_SOFT = "#f4f6fb"


def canvas(w, h, figsize):
    fig = plt.figure(figsize=figsize, dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, label="", fc="#ffffff", ec=LINE, fs=8.5, bold=False, tc=INK,
        r=1.4, lw=1.0, z=3, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw, zorder=z, linestyle=ls))
    if label:
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fs,
                color=tc, zorder=z + 1, linespacing=1.65,
                fontweight="bold" if bold else "normal")


def arrow(ax, p1, p2, color=MUTED, lw=1.0, style="-|>", ls="-", rad=0.0, z=2, ms=10):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=ms, color=color,
                                 lw=lw, linestyle=ls, zorder=z, shrinkA=1, shrinkB=1,
                                 connectionstyle=f"arc3,rad={rad}"))


def diamond(ax, cx, cy, w, h, label, fs=7.6, fc=WARN_SOFT, ec=WARN):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)],
                         closed=True, fc=fc, ec=ec, lw=1.0, zorder=3))
    ax.text(cx, cy, label, ha="center", va="center", fontsize=fs, color=INK, zorder=4,
            linespacing=1.4)


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)
    print("生成", name)


# ------------------------------------------------------------------ 图1 雷达图
def fig_radar():
    labels = [f[0].replace("可行性", "") for f in PD.FEASIBILITY]
    values = [f[1] for f in PD.FEASIBILITY]
    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]
    vals = values + values[:1]
    base = [PD.FEASIBILITY_THRESHOLD] * n + [PD.FEASIBILITY_THRESHOLD]

    fig = plt.figure(figsize=(6.4, 5.4), dpi=200)
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=8, color=MUTED)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([f"{l}\n{v} 分" for l, v in zip(labels, values)], fontsize=10.5, color=INK2)
    ax.tick_params(pad=12)
    ax.grid(color=LINE, linewidth=.8)
    ax.spines["polar"].set_color(LINE)

    ax.plot(angles, base, color=DANGER, lw=1.1, ls="--", label="立项阈值 3.5")
    ax.fill(angles, vals, color=BRAND, alpha=.16)
    ax.plot(angles, vals, color=BRAND, lw=2.0, marker="o", ms=5, mfc="white", mew=1.6,
            label="本项目评分")
    for ang, v in zip(angles[:-1], values):
        ax.annotate(f"{v}", xy=(ang, v), xytext=(ang, v + .45), ha="center", fontsize=9,
                    color=BRAND_DARK, fontweight="bold")
    ax.set_title("五维可行性评估雷达图", fontsize=14, color=INK, pad=26, fontweight="bold")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False, fontsize=9)
    fig.subplots_adjust(top=.86, bottom=.14, left=.12, right=.88)
    save(fig, "fig1_feasibility_radar.png")


# ------------------------------------------------------------------ 图2 用例图
def fig_usecase():
    fig, ax = canvas(160, 100, (11, 6.9))

    ax.add_patch(FancyBboxPatch((36, 5), 88, 90, boxstyle="round,pad=0,rounding_size=2",
                                fc="#fbfcff", ec=BRAND, lw=1.3, zorder=1))
    ax.text(80, 91.6, "LabHub 实验室设备预约与管理系统", ha="center", fontsize=9.5,
            color=BRAND_DARK, fontweight="bold")

    def actor(x, y, name):
        ax.add_patch(Circle((x, y + 5.4), 1.5, fc="white", ec=INK2, lw=1.1, zorder=3))
        ax.plot([x, x], [y + 3.9, y + 0.4], color=INK2, lw=1.1, zorder=3)
        ax.plot([x - 3, x + 3], [y + 3.0, y + 3.0], color=INK2, lw=1.1, zorder=3)
        ax.plot([x, x - 2.4], [y + 0.4, y - 2.6], color=INK2, lw=1.1, zorder=3)
        ax.plot([x, x + 2.4], [y + 0.4, y - 2.6], color=INK2, lw=1.1, zorder=3)
        ax.text(x, y - 4.6, name, ha="center", fontsize=9, color=INK, fontweight="bold")

    actor(16, 62, "学生")
    actor(16, 28, "教师")
    actor(146, 55, "管理员")

    left = [("UC-01", "登录系统"), ("UC-02", "浏览设备目录"), ("UC-03", "提交设备预约"),
            ("UC-04", "取消预约"), ("UC-05", "签到 / 签退"), ("UC-06", "查看我的预约"),
            ("UC-07", "查看信用记录")]
    right = [("UC-08", "审批预约"), ("UC-09", "维护设备档案"), ("UC-10", "调整信用分"),
             ("UC-11", "查看统计报表"), ("UC-12", "查看审计日志")]

    pos = {}
    ys = [86, 76, 66, 56, 46, 36, 26]
    for (code, name), y in zip(left, ys):
        pos[code] = (60, y)
    for (code, name), y in zip(right, [86, 76, 66, 56, 46]):
        pos[code] = (100, y)
    pos["IN-01"] = (58, 12)
    pos["IN-02"] = (104, 12)

    # 关联线先画，椭圆覆盖后视觉更干净
    for code in ["UC-01", "UC-02", "UC-03", "UC-04", "UC-05", "UC-06", "UC-07"]:
        arrow(ax, (19.5, 62), pos[code], color="#94a3b8", lw=.85, style="-", z=1)
    for code in ["UC-02", "UC-03", "UC-06", "UC-08", "UC-11"]:
        arrow(ax, (19.5, 28), pos[code], color="#94a3b8", lw=.85, style="-", z=1)
    for code in ["UC-08", "UC-09", "UC-10", "UC-11", "UC-12"]:
        arrow(ax, (142.5, 55), pos[code], color="#94a3b8", lw=.85, style="-", z=1)

    for code, name in left + right:
        cx, cy = pos[code]
        ax.add_patch(Ellipse((cx, cy), 34, 8.4, fc="white", ec=BRAND, lw=1.0, zorder=3))
        ax.text(cx, cy + 1.3, name, ha="center", va="center", fontsize=8, color=INK, zorder=4)
        ax.text(cx, cy - 2.1, code, ha="center", va="center", fontsize=6.4, color=MUTED, zorder=4)

    for code, label in [("IN-01", "冲突检测"), ("IN-02", "信用分结算")]:
        cx, cy = pos[code]
        ax.add_patch(Ellipse((cx, cy), 32, 8.0, fc=OK_SOFT, ec=OK, lw=1.0, ls="--", zorder=3))
        ax.text(cx, cy + 1.2, label, ha="center", va="center", fontsize=7.6, color=OK, zorder=4)
        ax.text(cx, cy - 2.0, "«include»", ha="center", va="center", fontsize=6.2, color=OK, zorder=4)

    arrow(ax, (60, 61.8), (58, 16), color=OK, lw=1.0, ls="--", z=2)
    ax.text(53.4, 38, "«include»", fontsize=6.4, color=OK, rotation=88, ha="center")
    arrow(ax, (106, 41.8), (104, 16), color=OK, lw=1.0, ls="--", z=2)
    ax.text(110, 28, "«include»", fontsize=6.4, color=OK, rotation=-84, ha="center")

    save(fig, "fig2_usecase.png")


# ------------------------------------------------------------------ 图3 架构图
def fig_arch():
    fig, ax = canvas(160, 108, (11, 7.4))

    def band(y, h, title, color=NEUTRAL_SOFT):
        ax.add_patch(FancyBboxPatch((3, y), 154, h, boxstyle="round,pad=0,rounding_size=1.6",
                                    fc=color, ec="none", zorder=1))
        ax.text(5.2, y + h - 2.4, title, fontsize=7.8, color=MUTED, fontweight="bold", zorder=2)

    # 用户层
    band(94, 11, "用户层 / 访问端")
    for i, (name, sub) in enumerate([("学生", "预约 · 签到"), ("教师", "审批 · 台账"),
                                     ("管理员", "档案 · 治理")]):
        box(ax, 22 + i * 40, 95.5, 34, 6.4, f"{name}浏览器  {sub}", fc="white", fs=7.8)
    ax.text(150, 98.7, "Chrome / Edge / 移动端\n同源访问，无需安装", fontsize=6.8, color=MUTED,
            va="center", ha="right")

    # 表现层
    band(78, 13, "表现层 / 单页应用 SPA", BRAND_SOFT)
    box(ax, 22, 79.4, 66, 9.4, "视图渲染  ·  状态管理  ·  REST 调用  ·  表单校验", fs=8, tc=BRAND_DARK)
    box(ax, 92, 79.4, 66, 9.4, "角色化导航  ·  预约弹窗  ·  统计看板  ·  审计时间线", fs=7.6)

    # 接入层
    band(62, 13, "接入层 / HTTP 服务", "#f1f5ff")
    box(ax, 22, 63.4, 124, 9.4,
        "路由分发    ·    会话鉴权（HttpOnly Cookie）    ·    参数校验    ·    统一异常映射    ·    静态资源托管",
        fs=7.8)

    # 应用层
    band(40, 19, "应用层 / 业务服务", "#eefbf5")
    services = ["AuthService\n登录 · 会话", "DeviceService\n设备档案", "ReservationService\n预约 · 审批 · 扫描",
                "CreditService\n信用结算", "StatsService\n统计 · 审计"]
    for i, s in enumerate(services):
        box(ax, 8 + i * 30.6, 42.6, 28, 11, s, fc="white", ec=OK, fs=7.3, tc=INK)
    ax.text(80, 41.6, "所有业务规则集中于此层，禁止接入层直接访问仓储", fontsize=6.6,
            color=MUTED, ha="center")

    # 数据层
    band(20, 17, "数据层 / 仓储与持久化")
    box(ax, 22, 21.6, 58, 10, "UnitOfWork\n事务边界（一次请求一事务）", fs=7.4)
    box(ax, 84, 21.6, 62, 10, "Repository\nUser / Device / Reservation / Credit / Audit / Session", fs=7.2)
    box(ax, 22, 12.2, 124, 7.6, "SQLite 3  ·  labhub.db  ·  WAL 未启用 / 单文件部署  ·  外键约束开启",
        fc="#f8fafc", fs=7.4)

    # 支撑
    band(2, 8.6, "支撑能力")
    for i, t in enumerate(["定时爽约扫描", "审计日志", "种子数据", "配置与常量"]):
        box(ax, 22 + i * 31, 3.2, 28, 5.2, t, fc="white", fs=7.2, ec=LINE)

    # 纵向箭头
    for x in (55, 105):
        arrow(ax, (x, 94), (x, 88.9), color=BRAND, lw=1.2)
        arrow(ax, (x, 79.2), (x, 72.9), color=BRAND, lw=1.2)
        arrow(ax, (x, 63.2), (x, 53.7), color=BRAND, lw=1.2)
        arrow(ax, (x, 42.4), (x, 31.7), color=BRAND, lw=1.2)
    ax.text(56.5, 91.4, "HTTP 请求", fontsize=6.4, color=BRAND)
    ax.text(56.5, 76, "fetch/JSON", fontsize=6.4, color=BRAND)
    ax.text(56.5, 58, "Service 调用", fontsize=6.4, color=BRAND)
    ax.text(56.5, 37, "仓储 / SQL", fontsize=6.4, color=BRAND)

    save(fig, "fig3_architecture.png")


# ------------------------------------------------------------------ 图4 类图
def fig_class():
    fig, ax = canvas(160, 100, (11, 6.9))

    def uml(x, y, w, h, name, attrs, methods, fc="white", ec=BRAND):
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.1, zorder=3))
        head = 5.4
        ax.plot([x, x + w], [y + h - head, y + h - head], color=ec, lw=1.0, zorder=4)
        ax.text(x + w / 2, y + h - head / 2, name, ha="center", va="center", fontsize=8.2,
                color=INK, fontweight="bold", zorder=4)
        n_attr = len(attrs)
        split = y + h - head - n_attr * 3.0 - 1.2
        ax.plot([x, x + w], [split, split], color=ec, lw=0.8, zorder=4)
        for i, a in enumerate(attrs):
            ax.text(x + 1.4, y + h - head - 2.9 - i * 3.0, a, fontsize=6.3, color=INK2, zorder=4)
        for i, m in enumerate(methods):
            ax.text(x + 1.4, split - 3.0 - i * 3.0, m, fontsize=6.3, color=BRAND_DARK, zorder=4)

    w, h = 38, 22
    c1, c2, c3, c4 = 3, 43.5, 84, 124.5

    uml(c1, 74, w, h, "User", ["- id: int", "- username: str", "- role: Role", "- credit: int"],
        ["+ login(pwd): bool", "+ canReserve(): bool"])
    uml(c1, 44, w, h, "Reservation", ["- id: int", "- startAt / endAt", "- status: Status"],
        ["+ overlap(o): bool", "+ transit(to): void"])
    uml(c1, 14, w, h, "Device", ["- code: str", "- openHour / closeHour", "- requiresApproval: bool"],
        ["+ isAvailable(): bool", "+ maxHours(): int"])

    uml(c2, 74, w, h, "UserRepository", ["- conn: Connection"],
        ["+ findByUsername(u)", "+ updateCredit(id, v)"])
    uml(c2, 44, w, h, "ReservationRepository", ["- conn: Connection"],
        ["+ overlapping(d, s, e)", "+ create(data): int"])
    uml(c2, 14, w, h, "DeviceRepository", ["- conn: Connection"],
        ["+ findById(id)", "+ updateStatus(id, s)"])

    uml(c3, 74, w, h, "AuthService", ["- uow: UnitOfWork"],
        ["+ login(u, p): Session", "+ current(token): User"])
    uml(c3, 44, w, h, "ReservationService", ["- uow: UnitOfWork", "- credit: CreditService"],
        ["+ create(u, dto): int", "+ review(actor, id)", "+ sweepNoShow(): int"])
    uml(c3, 14, w, h, "DeviceService", ["- uow: UnitOfWork"],
        ["+ list(q): Page", "+ save(actor, dto)"])

    uml(c4, 74, w, h, "Session", ["- token: str", "- expiresAt: datetime"],
        ["+ isExpired(): bool"], ec=MUTED)
    uml(c4, 44, w, h, "ConflictDetector", ["«utility»"],
        ["+ overlap(a, b): bool", "+ findFirst(slots)"], ec=OK, fc="#fbfffd")
    uml(c4, 14, w, h, "CreditService", ["«rule» 0..100"],
        ["+ apply(u, rid, d): int", "+ history(u): list"], ec=OK, fc="#fbfffd")

    # 关联
    arrow(ax, (22, 74), (22, 66), color=INK2, lw=1.0, style="-", z=1)
    ax.text(23.2, 69.6, "1", fontsize=6.6, color=INK2)
    ax.text(23.2, 66.4, "0..*  发起", fontsize=6.4, color=INK2)
    arrow(ax, (22, 44), (22, 36), color=INK2, lw=1.0, style="-", z=1)
    ax.text(23.2, 40, "0..*", fontsize=6.4, color=INK2)
    ax.text(23.2, 37.2, "1  占用", fontsize=6.4, color=INK2)

    # 服务->仓储 依赖
    for y in (85, 55, 25):
        arrow(ax, (84, y), (81.6, y), color=BRAND, lw=1.1, style="-|>", z=2)
    arrow(ax, (124.5, 85), (121.6, 85), color=BRAND, lw=1.1, style="-|>", z=2)
    arrow(ax, (124.5, 55), (121.6, 55), color=OK, lw=1.1, style="-|>", z=2)
    arrow(ax, (124.5, 25), (121.6, 25), color=OK, lw=1.1, style="-|>", z=2)

    ax.text(80, 4.2,
            "注：实体关联为 1..0..*；服务层通过 UnitOfWork 聚合各仓储；ConflictDetector 与 CreditService 为无状态规则类。",
            ha="center", fontsize=6.8, color=MUTED)
    save(fig, "fig4_class.png")


# ------------------------------------------------------------------ 图5 流程图
def fig_flow():
    fig, ax = canvas(160, 100, (9.5, 6.0))

    box(ax, 47, 92, 30, 5.6, "开始", fc=BRAND_SOFT, ec=BRAND, fs=8, bold=True, r=2.6)
    box(ax, 47, 82, 30, 6.4, "接收预约请求\n解析并校验参数")
    diamond(ax, 62, 71, 34, 9.6, "信用分 ≥ 60 且\n账号正常？")
    diamond(ax, 62, 58, 34, 9.6, "设备状态\n为可预约？")
    diamond(ax, 62, 45, 34, 9.6, "时间窗合法？\n（开放/时长/提前量）")
    diamond(ax, 62, 32, 34, 9.6, "存在时段冲突？")
    diamond(ax, 62, 19, 34, 9.6, "设备需审批？")

    box(ax, 34, 5.6, 26, 6.2, "状态 = PENDING", fc=WARN_SOFT, ec=WARN, fs=7.6)
    box(ax, 88, 5.6, 26, 6.2, "状态 = APPROVED", fc=OK_SOFT, ec=OK, fs=7.6)

    err = [
        (71, "返回 BIZ_422\n信用分不足"),
        (58, "返回 BIZ_422\n设备不可用"),
        (45, "返回 400 / 422\n时间窗非法"),
        (32, "返回 409\n时段冲突"),
    ]
    for y, t in err:
        box(ax, 118, y - 3.6, 34, 7.2, t, fc=DANGER_SOFT, ec=DANGER, fs=7.2, tc=DANGER)

    # 主干
    arrow(ax, (62, 92), (62, 88.4), color=INK2)
    arrow(ax, (62, 82), (62, 75.8), color=INK2)
    for y0, y1 in [(66.2, 62.8), (53.2, 49.8), (40.2, 36.8), (27.2, 23.8)]:
        arrow(ax, (62, y0), (62, y1), color=INK2)
    ax.text(64.2, 64.5, "是", fontsize=6.8, color=OK)
    ax.text(64.2, 51.5, "是", fontsize=6.8, color=OK)
    ax.text(64.2, 38.5, "是", fontsize=6.8, color=OK)
    ax.text(64.2, 25.5, "否", fontsize=6.8, color=OK)

    for y in (71, 58, 45):
        arrow(ax, (79, y), (118, y), color=DANGER, lw=.95, style="-|>")
        ax.text(88, y + 1.4, "否", fontsize=6.8, color=DANGER)
    arrow(ax, (79, 32), (118, 32), color=DANGER, lw=.95, style="-|>")
    ax.text(88, 33.4, "是", fontsize=6.8, color=DANGER)

    # 审批分支
    arrow(ax, (62, 14.2), (47, 11.8), color=INK2, rad=.12)
    ax.text(50, 14.6, "是", fontsize=6.8, color=WARN)
    arrow(ax, (72, 14.2), (88, 11.8), color=INK2, rad=-.12)
    ax.text(78, 14.6, "否", fontsize=6.8, color=OK)

    box(ax, 34, 0.6, 80, 4.4, "写审计日志 · 提交事务 · 返回 201 {id, status}", fs=7.2, fc="#f8fafc")
    arrow(ax, (47, 5.6), (62, 5.0), color=INK2, lw=1.0)
    arrow(ax, (101, 5.6), (78, 5.0), color=INK2, lw=1.0)

    ax.text(4, 96, "创建预约主流程", fontsize=10, color=INK, fontweight="bold")
    save(fig, "fig5_flowchart.png")


# ------------------------------------------------------------------ 图6 帕累托
def fig_pareto():
    counts = {}
    for d in PD.DEFECTS:
        counts[d[2]] = counts.get(d[2], 0) + 1
    items = sorted(counts.items(), key=lambda x: -x[1])
    labels = [i[0] for i in items]
    vals = [i[1] for i in items]
    total = sum(vals)
    cum = np.cumsum(vals) / total * 100

    fig, ax1 = plt.subplots(figsize=(8.6, 4.8), dpi=200)
    x = np.arange(len(labels))
    bars = ax1.bar(x, vals, width=.62, color=BRAND, zorder=3, label="缺陷数")
    for b, v in zip(bars, vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + .12, str(v), ha="center", fontsize=9,
                 color=INK2, fontweight="bold")

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9.5)
    ax1.set_ylabel("缺陷数量（个）", fontsize=10, color=INK2)
    ax1.set_ylim(0, max(vals) * 1.35)
    ax1.tick_params(axis="y", labelsize=9, colors=MUTED)
    ax1.grid(axis="y", color="#e8eef7", lw=.8, zorder=0)
    ax1.set_axisbelow(True)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)
    ax1.spines["left"].set_color(LINE)
    ax1.spines["bottom"].set_color(LINE)

    ax2 = ax1.twinx()
    ax2.plot(x, cum, color=DANGER, marker="o", ms=4.5, lw=1.8, zorder=5, label="累计占比")
    ax2.set_ylim(0, 108)
    ax2.set_ylabel("累计占比（%）", fontsize=10, color=DANGER)
    ax2.tick_params(axis="y", labelsize=9, colors=DANGER)
    for s in ("top", "left"):
        ax2.spines[s].set_visible(False)
    for xi, c in zip(x, cum):
        ax2.text(xi + (0.16 if xi == 0 else 0), c + (1.2 if xi == 0 else 3.4),
                 f"{c:.0f}%", ha="left" if xi == 0 else "center", fontsize=8, color=DANGER)

    ax2.axhline(80, color=WARN, ls="--", lw=1.1)
    ax2.text(len(labels) - .35, 82.4, "80% 累计线", fontsize=8, color=WARN, ha="right")

    ax1.set_title("缺陷类型帕累托图（n = %d）" % total, fontsize=12.5, color=INK,
                  fontweight="bold", pad=14)
    fig.tight_layout()
    save(fig, "fig6_pareto.png")


# ------------------------------------------------------------------ 图7 状态机
def fig_state():
    fig, ax = canvas(160, 80, (11, 5.5))

    ax.add_patch(Circle((8, 52), 2.4, fc=INK, ec=INK, zorder=3))
    ax.text(8, 47.4, "提交", fontsize=6.8, color=MUTED, ha="center")

    box(ax, 22, 46, 26, 12, "PENDING\n待审批", fc=WARN_SOFT, ec=WARN, fs=8.4, bold=True)
    box(ax, 66, 46, 26, 12, "APPROVED\n已通过", fc=BRAND_SOFT, ec=BRAND, fs=8.4, bold=True)
    box(ax, 110, 46, 26, 12, "CHECKED_IN\n使用中", fc=OK_SOFT, ec=OK, fs=8.4, bold=True)
    box(ax, 110, 22, 26, 12, "COMPLETED\n已完成", fc="#eef1f7", ec=INK2, fs=8.4, bold=True)
    box(ax, 66, 22, 26, 12, "CANCELLED\n已取消", fc="#f4f6fb", ec=MUTED, fs=8.4, bold=True)
    box(ax, 22, 22, 26, 12, "REJECTED\n已驳回", fc=DANGER_SOFT, ec=DANGER, fs=8.4, bold=True)
    box(ax, 110, 2, 26, 12, "NO_SHOW\n爽约", fc=DANGER_SOFT, ec=DANGER, fs=8.4, bold=True)

    arrow(ax, (10.4, 52), (22, 52), color=INK2)
    arrow(ax, (48, 52), (66, 52), color=OK)
    ax.text(57, 53.6, "审批通过", fontsize=6.6, color=OK, ha="center")
    arrow(ax, (22, 44), (22, 34), color=DANGER)
    ax.text(16.4, 39, "驳回", fontsize=6.6, color=DANGER, ha="center", rotation=90)
    ax.text(23.4, 36, "−0 分", fontsize=6.2, color=MUTED)
    arrow(ax, (92, 52), (110, 52), color=OK)
    ax.text(101, 53.6, "签到", fontsize=6.6, color=OK, ha="center")
    arrow(ax, (123, 46), (123, 34), color=OK)
    ax.text(124.6, 40, "签退  信用 +2", fontsize=6.6, color=OK, va="center")

    # 取消：PENDING / APPROVED -> CANCELLED
    arrow(ax, (42, 46), (70, 33), color=MUTED, rad=.14)
    ax.text(46, 41.4, "取消（不扣分）", fontsize=6.4, color=MUTED)
    arrow(ax, (86, 46), (88, 34), color=MUTED, rad=-.1)
    ax.text(87.6, 41.4, "取消（<2h −5）", fontsize=6.4, color=MUTED)

    # 爽约：APPROVED -> NO_SHOW（绕行右侧，避免穿过其他状态框）
    ax.plot([89, 146], [58.6, 58.6], color=DANGER, lw=1.0, zorder=2)
    ax.plot([146, 146], [58.6, 8], color=DANGER, lw=1.0, zorder=2)
    arrow(ax, (146, 8), (136.6, 8), color=DANGER)
    ax.text(148.6, 33, "超时 30min 未签到 −15", fontsize=6.4, color=DANGER, va="center", rotation=90)

    ax.text(4, 76, "预约状态机（7 状态 / 9 条合法迁移）", fontsize=10, color=INK, fontweight="bold")
    save(fig, "fig7_state.png")


# ------------------------------------------------------------------ 图8 时序图
def fig_sequence():
    fig, ax = canvas(160, 100, (11, 6.9))
    parts = ["学生浏览器", "前端 SPA", "HTTP 接入层", "Reservation\nService", "Repository", "SQLite"]
    xs = [14, 40, 66, 92, 118, 144]
    top = 90
    for x, p in zip(xs, parts):
        box(ax, x - 14, top, 28, 7.4, p, fc=BRAND_SOFT, ec=BRAND, fs=7.4, bold=True)
        ax.plot([x, x], [top, 8], color="#cbd5e1", lw=.9, ls=(0, (4, 3)), zorder=1)

    msgs = [
        (0, 1, "填写预约表单并提交", 82),
        (1, 2, "POST /api/reservations", 75),
        (2, 2.6, "鉴权 → 参数校验（角色/信用/时间窗）", 68),
        (2, 3, "create(user, dto)", 61),
        (3, 4, "overlapping(device, s, e)", 54),
        (4, 5, "SELECT ... WHERE 时间相交", 47),
        (5, 4, "冲突列表（空）", 40, True),
        (4, 3, "插入预约记录", 33, True),
        (3, 2, "{id, status} + 审计日志", 26, True),
        (2, 1, "201 Created（Set-Cookie 已存在）", 19, True),
        (1, 0, "渲染结果 / 提示可签到时间", 12, True),
    ]
    for m in msgs:
        a, b, label, y = m[0], m[1], m[2], m[3]
        ret = len(m) > 4
        if isinstance(a, float):  # 自调用
            x = xs[2]
            ax.add_patch(FancyArrowPatch((x, y + 2.6), (x + 6, y + 2.6), arrowstyle="-|>",
                                         mutation_scale=9, color=OK, lw=.95))
            ax.plot([x + 6, x + 6], [y + 2.6, y], color=OK, lw=.95)
            arrow(ax, (x + 6, y), (x, y), color=OK, lw=.95)
            ax.text(x + 8, y + 3.4, label, fontsize=6.6, color=OK)
            continue
        x1, x2 = xs[int(a)], xs[int(b)]
        if x2 > x1:
            arrow(ax, (x1 + .6, y), (x2 - .6, y), color=INK2, lw=.95,
                  style="-|>" if not ret else "-|>")
        else:
            arrow(ax, (x1 - .6, y), (x2 + .6, y), color=OK if ret else INK2, lw=.95, ls="--" if ret else "-")
        ax.text((x1 + x2) / 2, y + 1.6, label, fontsize=6.6, color=OK if ret else INK2,
                ha="center")
    ax.text(4, 96, "创建预约时序图", fontsize=10, color=INK, fontweight="bold")
    ax.text(4, 4, "实线：请求调用；虚线：返回值。全流程在一个数据库事务内完成，任何一步失败整体回滚。",
            fontsize=6.6, color=MUTED)
    save(fig, "fig8_sequence.png")


# ------------------------------------------------------------------ 图9 AFS
def fig_afs():
    phases, scores = [], []
    for row in PD.AFS:
        score = sum(row[i + 1] * PD.AFS_DIMENSIONS[i][1] for i in range(5))
        phases.append(row[0])
        scores.append(round(score, 1))

    fig, ax = plt.subplots(figsize=(8.8, 4.4), dpi=200)
    y = np.arange(len(phases))[::-1]
    colors = [OK if s >= 90 else (BRAND if s >= 80 else (WARN if s >= 70 else DANGER)) for s in scores]
    bars = ax.barh(y, scores, height=.56, color=colors, zorder=3)
    for yi, s in zip(y, scores):
        ax.text(s + 0.8, yi, f"{s:.1f}", va="center", fontsize=9.5, color=INK2, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(phases, fontsize=10)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Agent 失效评分 AFS（越高越可靠）", fontsize=10, color=INK2)
    ax.grid(axis="x", color="#e8eef7", lw=.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(LINE)
    ax.spines["bottom"].set_color(LINE)

    for v, label in [(90, "L1 可托管"), (80, "需抽检"), (70, "需全量复核")]:
        ax.axvline(v, color=MUTED, ls="--", lw=.9, zorder=2)
        ax.text(v - 0.6, len(phases) - 0.35, label, fontsize=7.6, color=MUTED, ha="right")

    ax.set_title("各阶段 Agent 失效评分（AFS）与授权等级", fontsize=12.5, color=INK,
                 fontweight="bold", pad=12)
    fig.tight_layout()
    save(fig, "fig9_afs.png")


# ------------------------------------------------------------------ 图10 分级分布
def fig_levels():
    phases = [r[0] for r in PD.AI_LEVELS]
    l1 = [r[1] for r in PD.AI_LEVELS]
    l2 = [r[2] for r in PD.AI_LEVELS]
    l3 = [r[3] for r in PD.AI_LEVELS]
    fig, ax = plt.subplots(figsize=(8.6, 4.4), dpi=200)
    y = np.arange(len(phases))[::-1]
    ax.barh(y, l1, color=OK, height=.56, label="L1 自动完成", zorder=3)
    ax.barh(y, l2, left=l1, color=BRAND, height=.56, label="L2 人机协同", zorder=3)
    ax.barh(y, l3, left=np.array(l1) + np.array(l2), color=WARN, height=.56,
            label="L3 纯人工", zorder=3)
    for yi, a, b, c in zip(y, l1, l2, l3):
        ax.text(a / 2, yi, str(a), va="center", ha="center", fontsize=8.5, color="white")
        ax.text(a + b / 2, yi, str(b), va="center", ha="center", fontsize=8.5, color="white")
        ax.text(a + b + c / 2, yi, str(c), va="center", ha="center", fontsize=8.5, color="white")
        ax.text(a + b + c + .35, yi, f"{a + b + c} 项", va="center", fontsize=8, color=MUTED)
    ax.set_yticks(y)
    ax.set_yticklabels(phases, fontsize=10)
    ax.set_xlabel("任务数量（项）", fontsize=10, color=INK2)
    ax.grid(axis="x", color="#e8eef7", lw=.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(LINE)
    ax.spines["bottom"].set_color(LINE)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False, fontsize=9)
    ax.set_title("各阶段任务的人工介入等级分布", fontsize=12.5, color=INK, fontweight="bold",
                 pad=30)
    fig.tight_layout()
    save(fig, "fig10_ai_levels.png")


if __name__ == "__main__":
    fig_radar()
    fig_usecase()
    fig_arch()
    fig_class()
    fig_flow()
    fig_pareto()
    fig_state()
    fig_sequence()
    fig_afs()
    fig_levels()
    print("全部图表生成完毕 ->", os.path.abspath(OUT))
