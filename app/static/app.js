/* LabHub 前端主逻辑：状态管理 + 视图渲染 + REST 调用（无框架、无构建） */

const STATE = { user: null, route: "dashboard", meta: null, devices: [], reservations: [], cache: {} };

const STATUS_TEXT = {
  PENDING: "待审批", APPROVED: "已通过", REJECTED: "已驳回", CHECKED_IN: "使用中",
  COMPLETED: "已完成", CANCELLED: "已取消", NO_SHOW: "爽约"
};
const STATUS_CLASS = {
  PENDING: "b-pending", APPROVED: "b-approved", REJECTED: "b-rejected", CHECKED_IN: "b-checked",
  COMPLETED: "b-completed", CANCELLED: "b-cancelled", NO_SHOW: "b-noshow"
};
const DEVICE_TEXT = { AVAILABLE: "可预约", MAINTENANCE: "维护中", RETIRED: "已退役" };
const DEVICE_CLASS = { AVAILABLE: "b-ok", MAINTENANCE: "b-maint", RETIRED: "b-retired" };
const ROLE_TEXT = { STUDENT: "学生", TEACHER: "教师", ADMIN: "管理员" };

/* ------------------------------------------------------------ 基础设施 */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(path, { method = "GET", body = null } = {}) {
  const opt = { method, headers: {} };
  if (body) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const res = await fetch(path, opt);
  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }
  if (!res.ok) {
    const msg = (data && data.error && data.error.message) || `请求失败（${res.status}）`;
    const err = new Error(msg);
    err.code = data && data.error ? data.error.code : "SYS";
    throw err;
  }
  return data;
}

function toast(msg, type = "") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.getElementById("toast-root").appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function fmtTime(s) { return s ? s.slice(0, 16) : "-"; }
function badge(status) { return `<span class="badge ${STATUS_CLASS[status] || ""}">${STATUS_TEXT[status] || status}</span>`; }
function deviceBadge(s) { return `<span class="badge ${DEVICE_CLASS[s] || ""}">${DEVICE_TEXT[s] || s}</span>`; }
function money(v) { return Number(v) % 1 === 0 ? Number(v).toFixed(0) : Number(v).toFixed(1); }

/* ------------------------------------------------------------ 登录 */
function renderLogin() {
  document.getElementById("app-root").classList.add("hidden");
  const root = document.getElementById("login-root");
  root.classList.remove("hidden");
  root.className = "login-wrap";
  root.innerHTML = `
    <div class="login-brand">
      <div class="brand-mark"><div class="brand-logo">LH</div><span>LabHub 实验室设备共享平台</span></div>
      <div>
        <h1>让每一台设备<br/>都被看见、被高效使用</h1>
        <p class="lead">面向高校实验室的设备预约与管理系统，覆盖设备档案、时段预约、审批流转、信用约束与使用统计的全流程。</p>
        <ul class="brand-points">
          <li><span class="dot">01</span><span>时段级冲突检测，杜绝“撞车预约”与资源空转</span></li>
          <li><span class="dot">02</span><span>按设备风险等级自动分流：即约即用 / 人工审批</span></li>
          <li><span class="dot">03</span><span>信用分与爽约惩戒联动，约束占用不使用行为</span></li>
          <li><span class="dot">04</span><span>全量操作审计，管理员可追溯每一次状态变更</span></li>
        </ul>
      </div>
      <div class="login-foot">Software Engineering Project · LabHub v1.0</div>
    </div>
    <div class="login-panel">
      <div class="login-card">
        <h2>登录</h2>
        <p class="sub">请使用校园统一账号登录，演示环境已内置测试账号</p>
        <form id="login-form">
          <div class="field"><label>用户名</label><input id="username" autocomplete="username" placeholder="请输入用户名" /></div>
          <div class="field"><label>密码</label><input id="password" type="password" autocomplete="current-password" placeholder="请输入密码" /></div>
          <button class="btn btn-primary btn-block" type="submit">登录系统</button>
          <p class="login-error" id="login-error"></p>
        </form>
        <div class="demo-accounts">
          <div class="t">快速填入演示账号</div>
          <div class="chip-row">
            <button class="chip" data-u="stu001" data-p="123456">学生 · 陈晓</button>
            <button class="chip" data-u="teacher1" data-p="123456">教师 · 李国强</button>
            <button class="chip" data-u="admin" data-p="admin123">管理员 · 王敏</button>
            <button class="chip" data-u="stu002" data-p="123456">低信用学生 · 刘洋</button>
          </div>
        </div>
      </div>
    </div>`;

  root.querySelectorAll(".chip").forEach(btn => btn.addEventListener("click", () => {
    root.querySelector("#username").value = btn.dataset.u;
    root.querySelector("#password").value = btn.dataset.p;
  }));

  root.querySelector("#login-form").addEventListener("submit", async e => {
    e.preventDefault();
    const errBox = root.querySelector("#login-error");
    errBox.textContent = "";
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: { username: root.querySelector("#username").value.trim(), password: root.querySelector("#password").value }
      });
      STATE.user = data.user;
      await bootApp();
    } catch (err) { errBox.textContent = err.message; }
  });
}

/* ------------------------------------------------------------ 应用骨架 */
function navItems() {
  const role = STATE.user.role;
  const items = [
    { key: "dashboard", label: "工作台", ico: "▦" },
    { key: "devices", label: "设备目录", ico: "◫" },
  ];
  if (role !== "ADMIN") items.push({ key: "reservations", label: "我的预约", ico: "≡" });
  if (role === "ADMIN" || role === "TEACHER") {
    items.push({ key: "approvals", label: "审批中心", ico: "✓" });
    items.push({ key: "allRes", label: "预约台账", ico: "≣" });
  }
  if (role === "ADMIN") {
    items.push({ key: "users", label: "用户与信用", ico: "☰" });
    items.push({ key: "audit", label: "审计日志", ico: "◷" });
  }
  items.push({ key: "credits", label: "信用记录", ico: "★" });
  return items;
}

function renderShell() {
  const root = document.getElementById("app-root");
  document.getElementById("login-root").classList.add("hidden");
  root.classList.remove("hidden");
  root.className = "app";
  const items = navItems();
  root.innerHTML = `
    <aside class="sidebar">
      <div class="side-brand"><div class="brand-logo">LH</div><span>LabHub</span></div>
      <div class="nav-group-label">工作区</div>
      <nav id="nav">${items.map(i => `
        <button class="nav-item ${STATE.route === i.key ? "active" : ""}" data-route="${i.key}">
          <span class="ico">${i.ico}</span><span>${i.label}</span>
        </button>`).join("")}
      </nav>
      <div class="side-user">
        <div class="who">
          <div class="avatar">${esc(STATE.user.name.slice(-2))}</div>
          <div><div class="nm">${esc(STATE.user.name)}</div>
            <div class="rl">${ROLE_TEXT[STATE.user.role]} · ${esc(STATE.user.dept || "")}</div></div>
        </div>
        <button class="logout-link" id="logout">退出登录</button>
      </div>
    </aside>
    <main class="main" id="view"></main>`;

  root.querySelectorAll("[data-route]").forEach(btn => btn.addEventListener("click", () => go(btn.dataset.route)));
  root.querySelector("#logout").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" }).catch(() => {});
    STATE.user = null;
    renderLogin();
  });
}

function go(route) {
  STATE.route = route;
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.route === route));
  renderView();
}

const TITLES = {
  dashboard: ["工作台", "关键指标、待办事项与近期安排一览"],
  devices: ["设备目录", "浏览实验室开放设备，按类别与状态筛选后发起预约"],
  reservations: ["我的预约", "查看预约进度，支持取消、签到与签退"],
  approvals: ["审批中心", "处理待审批的设备预约申请"],
  allRes: ["预约台账", "全量预约记录查询与状态跟踪"],
  users: ["用户与信用", "账号状态维护与信用分调整"],
  audit: ["审计日志", "系统关键操作的完整留痕"],
  credits: ["信用记录", "信用分变动明细与当前评级"]
};

async function renderView() {
  const view = document.getElementById("view");
  const [title, desc] = TITLES[STATE.route] || ["", ""];
  view.innerHTML = `
    <div class="topbar">
      <div><h2>${title}</h2><div class="desc">${desc}</div></div>
      <div class="credit-pill">信用分 <b>${STATE.user.credit}</b> / 100</div>
    </div>
    <div id="page-body"><div class="empty">加载中…</div></div>`;
  try {
    await (VIEWS[STATE.route] || VIEWS.dashboard)();
  } catch (err) {
    document.getElementById("page-body").innerHTML = `<div class="card empty"><div class="big">加载失败</div>${esc(err.message)}</div>`;
  }
}

/* ------------------------------------------------------------ 视图：工作台 */
const VIEWS = {};

VIEWS.dashboard = async () => {
  const body = document.getElementById("page-body");
  const role = STATE.user.role;
  if (role === "ADMIN" || role === "TEACHER") {
    const s = await api("/api/stats/overview");
    const order = ["PENDING", "APPROVED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW", "REJECTED"];
    const rows = order.filter(k => (s.by_status[k] || 0) > 0).map(k => [k, s.by_status[k]]);
    const max = Math.max(1, ...rows.map(r => r[1]));
    const topMax = Math.max(1, ...s.top_devices.map(d => d.c));
    body.innerHTML = `
      <div class="grid grid-4">
        <div class="card stat"><div class="k">预约总量</div><div class="v">${s.reservation_total}<small>单</small></div>
          <div class="foot">近 7 日持续累积</div></div>
        <div class="card stat"><div class="k">设备可用率</div><div class="v">${Math.round(s.device_available / Math.max(1, s.device_total) * 100)}<small>%</small></div>
          <div class="foot">${s.device_available} / ${s.device_total} 台可预约</div></div>
        <div class="card stat"><div class="k">爽约率</div><div class="v">${s.no_show_rate}<small>%</small></div>
          <div class="foot">信用约束生效中</div></div>
        <div class="card stat"><div class="k">注册用户</div><div class="v">${s.user_total}<small>人</small></div>
          <div class="foot">其中 ${s.low_credit_users.length} 人信用分低于 60</div></div>
      </div>
      <div class="grid grid-2" style="margin-top:16px">
        <div class="card">
          <div class="card-head"><h3>预约状态分布</h3><span class="hint">全量</span></div>
          <div class="bars">${rows.map(([k, v]) => `
            <div class="bar-col"><div class="bar-val">${v}</div>
              <div class="bar" style="height:${Math.round(v / max * 110)}px"></div>
              <div class="bar-label">${STATUS_TEXT[k]}</div></div>`).join("")}</div>
        </div>
        <div class="card">
          <div class="card-head"><h3>热门设备 Top 5</h3><span class="hint">按有效预约数</span></div>
          ${s.top_devices.length ? s.top_devices.map((d, i) => `
            <div class="rank-row"><span class="idx">${i + 1}</span><span class="nm">${esc(d.name)}</span>
              <span class="rank-bar" style="width:${Math.round(d.c / topMax * 110)}px"></span>
              <span class="mono">${d.c}</span></div>`).join("") : `<div class="empty">暂无数据</div>`}
          <div class="card-head" style="margin:18px 0 10px"><h3>近 7 日预约趋势</h3></div>
          ${trendSvg(s.trend)}
        </div>
      </div>
      ${role === "ADMIN" && s.low_credit_users.length ? `
      <div class="card" style="margin-top:16px">
        <div class="card-head"><h3>信用分预警</h3><span class="hint">低于 60 分将无法预约</span></div>
        <table><thead><tr><th>姓名</th><th>角色</th><th>院系</th><th>信用分</th><th>操作</th></tr></thead><tbody>
        ${s.low_credit_users.map(u => `<tr><td class="t-main">${esc(u.name)}</td>
          <td>${ROLE_TEXT[u.role]}</td><td class="t-sub">${esc(u.dept)}</td>
          <td><span class="badge b-rejected">${u.credit}</span></td>
          <td><button class="btn btn-sm" onclick="openCreditModal(${u.id},'${esc(u.name)}',${u.credit})">调整</button></td></tr>`).join("")}
        </tbody></table>
      </div>` : ""}`;
  } else {
    const data = await api("/api/reservations");
    const items = data.items;
    const count = k => items.filter(r => r.status === k).length;
    const upcoming = items.filter(r => ["PENDING", "APPROVED", "CHECKED_IN"].includes(r.status))
      .sort((a, b) => a.start_at.localeCompare(b.start_at)).slice(0, 5);
    body.innerHTML = `
      <div class="grid grid-4">
        <div class="card stat"><div class="k">全部预约</div><div class="v">${items.length}<small>单</small></div><div class="foot">累计提交</div></div>
        <div class="card stat"><div class="k">待审批</div><div class="v">${count("PENDING")}<small>单</small></div><div class="foot">等待教师或管理员处理</div></div>
        <div class="card stat"><div class="k">使用中</div><div class="v">${count("CHECKED_IN")}<small>单</small></div><div class="foot">请按时签退</div></div>
        <div class="card stat"><div class="k">已完成</div><div class="v">${count("COMPLETED")}<small>单</small></div><div class="foot">爽约 ${count("NO_SHOW")} 次</div></div>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-head"><h3>近期安排</h3><button class="btn btn-sm btn-primary" onclick="go('devices')">去预约设备</button></div>
        ${upcoming.length ? `<table><thead><tr><th>设备</th><th>时段</th><th>状态</th><th>操作</th></tr></thead><tbody>
          ${upcoming.map(r => `<tr><td><div class="t-main">${esc(r.device_name)}</div><div class="t-sub mono">${esc(r.location)}</div></td>
            <td>${fmtTime(r.start_at)} ~ ${r.end_at.slice(11, 16)}</td><td>${badge(r.status)}</td>
            <td>${actionButtons(r)}</td></tr>`).join("")}</tbody></table>`
          : `<div class="empty"><div class="big">还没有进行中的预约</div>从设备目录挑选一台设备开始吧</div>`}
      </div>`;
  }
};

function trendSvg(trend) {
  if (!trend.length) return `<div class="empty">暂无数据</div>`;
  const w = 420, h = 110, pad = 18;
  const max = Math.max(1, ...trend.map(t => t.c));
  const pts = trend.map((t, i) => {
    const x = pad + (i * (w - pad * 2)) / Math.max(1, trend.length - 1);
    const y = h - pad - (t.c / max) * (h - pad * 2);
    return [x, y, t];
  });
  return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;height:120px">
    <polyline fill="none" stroke="#2f5bea" stroke-width="2"
      points="${pts.map(p => `${p[0]},${p[1]}`).join(" ")}" />
    ${pts.map(p => `<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="#fff" stroke="#2f5bea" stroke-width="2"/>`).join("")}
    ${pts.map(p => `<text x="${p[0]}" y="${h - 4}" font-size="9" fill="#8a97ab" text-anchor="middle">${p[2].day.slice(5)}</text>`).join("")}
  </svg>`;
}

/* ------------------------------------------------------------ 视图：设备 */
VIEWS.devices = async () => {
  const body = document.getElementById("page-body");
  const meta = await api("/api/meta");
  STATE.meta = meta;
  const q = STATE.cache.deviceQuery || { keyword: "", category: "", status: "" };
  const params = new URLSearchParams(Object.entries(q).filter(([, v]) => v)).toString();
  const data = await api("/api/devices" + (params ? "?" + params : ""));
  STATE.devices = data.items;
  const isAdmin = STATE.user.role === "ADMIN";

  body.innerHTML = `
    <div class="toolbar">
      <input id="f-kw" placeholder="搜索设备名称 / 编号 / 位置" value="${esc(q.keyword)}" style="width:240px" />
      <select id="f-cat"><option value="">全部类别</option>
        ${data.categories.map(c => `<option ${q.category === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
      <select id="f-st"><option value="">全部状态</option>
        ${Object.entries(DEVICE_TEXT).map(([k, v]) => `<option value="${k}" ${q.status === k ? "selected" : ""}>${v}</option>`).join("")}</select>
      <button class="btn btn-sm" id="f-go">筛选</button>
      <div class="spacer"></div>
      ${isAdmin ? `<button class="btn btn-sm btn-primary" id="add-device">新增设备</button>` : ""}
    </div>
    <div class="device-grid">
      ${data.items.map(d => `
        <div class="device-card">
          <div class="top">
            <div><h4>${esc(d.name)}</h4><div class="code">${esc(d.code)}</div></div>
            ${deviceBadge(d.status)}
          </div>
          <div class="meta">
            <span>类别 · ${esc(d.category)}</span>
            <span>位置 · ${esc(d.location)}</span>
            <span>单次 ≤ ${d.max_hours}h</span>
            <span>${d.requires_approval ? "需审批" : "即约即用"}</span>
          </div>
          <div class="desc">${esc(d.description || "暂无描述")}</div>
          <div class="foot">
            <div class="price">¥${money(d.hourly_price)}<small> /小时</small></div>
            ${isAdmin
              ? `<button class="btn btn-sm" onclick="openDeviceModal(${d.id})">编辑</button>`
              : `<button class="btn btn-sm btn-primary" ${d.status !== "AVAILABLE" ? "disabled style=opacity:.45" : ""}
                   onclick="openBooking(${d.id})">预约</button>`}
          </div>
        </div>`).join("") || `<div class="empty"><div class="big">没有匹配的设备</div>试试调整筛选条件</div>`}
    </div>`;

  document.getElementById("f-go").addEventListener("click", () => {
    STATE.cache.deviceQuery = {
      keyword: document.getElementById("f-kw").value.trim(),
      category: document.getElementById("f-cat").value,
      status: document.getElementById("f-st").value
    };
    renderView();
  });
  if (isAdmin) document.getElementById("add-device").addEventListener("click", () => openDeviceModal(null));
};

/* ------------------------------------------------------------ 视图：预约 */
function actionButtons(r) {
  const me = STATE.user;
  const btns = [];
  if (r.user_id === me.id) {
    if (["PENDING", "APPROVED"].includes(r.status))
      btns.push(`<button class="btn btn-sm btn-danger-ghost" onclick="cancelRes(${r.id})">取消</button>`);
    if (r.status === "APPROVED")
      btns.push(`<button class="btn btn-sm btn-ok-ghost" onclick="checkIn(${r.id})">签到</button>`);
    if (r.status === "CHECKED_IN")
      btns.push(`<button class="btn btn-sm btn-ok-ghost" onclick="checkOut(${r.id})">签退</button>`);
  }
  if ((me.role === "ADMIN" || me.role === "TEACHER") && r.status === "PENDING" && r.user_id !== me.id) {
    btns.push(`<button class="btn btn-sm btn-ok-ghost" onclick="review(${r.id},true)">通过</button>`);
    btns.push(`<button class="btn btn-sm btn-danger-ghost" onclick="review(${r.id},false)">驳回</button>`);
  }
  return btns.join(" ") || `<span class="t-sub">-</span>`;
}

function resTable(items, showUser) {
  if (!items.length) return `<div class="empty"><div class="big">暂无记录</div>当前筛选条件下没有预约</div>`;
  return `<table><thead><tr>
      <th>编号</th>${showUser ? "<th>申请人</th>" : ""}<th>设备</th><th>使用时段</th><th>用途</th><th>状态</th><th>操作</th>
    </tr></thead><tbody>
    ${items.map(r => `<tr>
      <td class="mono">#${String(r.id).padStart(4, "0")}</td>
      ${showUser ? `<td class="t-main">${esc(r.user_name)}</td>` : ""}
      <td><div class="t-main">${esc(r.device_name)}</div><div class="t-sub">${esc(r.location)}</div></td>
      <td>${fmtTime(r.start_at)}<div class="t-sub">至 ${fmtTime(r.end_at)}</div></td>
      <td class="t-sub" style="max-width:200px">${esc(r.purpose)}</td>
      <td>${badge(r.status)}</td>
      <td>${actionButtons(r)}</td></tr>`).join("")}
    </tbody></table>`;
}

VIEWS.reservations = async () => {
  const data = await api("/api/reservations");
  document.getElementById("page-body").innerHTML = `
    <div class="card">${resTable(data.items, false)}</div>`;
};

VIEWS.allRes = async () => {
  const data = await api("/api/reservations");
  const body = document.getElementById("page-body");
  const counts = {};
  data.items.forEach(r => counts[r.status] = (counts[r.status] || 0) + 1);
  body.innerHTML = `
    <div class="toolbar">
      ${Object.keys(STATUS_TEXT).map(k => `<span class="badge ${STATUS_CLASS[k]}">${STATUS_TEXT[k]} ${counts[k] || 0}</span>`).join("")}
    </div>
    <div class="card">${resTable(data.items, true)}</div>`;
};

VIEWS.approvals = async () => {
  const data = await api("/api/reservations?status=PENDING");
  const body = document.getElementById("page-body");
  body.innerHTML = `
    <div class="card">
      <div class="card-head"><h3>待处理申请（${data.items.length}）</h3><span class="hint">审批结果将写入审计日志</span></div>
      ${data.items.length ? data.items.map(r => `
        <div class="review-item">
          <div>
            <div class="line1">${esc(r.device_name)} · ${esc(r.user_name)}</div>
            <div class="line2">${fmtTime(r.start_at)} ~ ${fmtTime(r.end_at)} ｜ 用途：${esc(r.purpose)} ｜ ${r.headcount} 人</div>
          </div>
          <div class="acts">
            <button class="btn btn-sm btn-ok-ghost" onclick="review(${r.id},true)">通过</button>
            <button class="btn btn-sm btn-danger-ghost" onclick="review(${r.id},false)">驳回</button>
          </div>
        </div>`).join("") : `<div class="empty"><div class="big">没有待审批的申请</div>所有申请都已处理完毕</div>`}
    </div>`;
};

VIEWS.users = async () => {
  const data = await api("/api/users");
  document.getElementById("page-body").innerHTML = `
    <div class="card">
      <table><thead><tr><th>ID</th><th>姓名</th><th>账号</th><th>角色</th><th>院系</th><th>信用分</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>${data.items.map(u => `<tr>
        <td class="mono">${u.id}</td><td class="t-main">${esc(u.name)}</td><td class="mono">${esc(u.username)}</td>
        <td>${ROLE_TEXT[u.role]}</td><td class="t-sub">${esc(u.dept)}</td>
        <td><span class="badge ${u.credit < 60 ? "b-rejected" : "b-ok"}">${u.credit}</span></td>
        <td>${u.status === "ACTIVE" ? "正常" : "已停用"}</td>
        <td><button class="btn btn-sm" onclick="openCreditModal(${u.id},'${esc(u.name)}',${u.credit})">调整信用分</button></td>
      </tr>`).join("")}</tbody></table>
    </div>`;
};

VIEWS.audit = async () => {
  const data = await api("/api/audit-logs");
  document.getElementById("page-body").innerHTML = `
    <div class="card">
      <div class="tl">${data.items.map(a => `
        <div class="tl-item">
          <div class="tl-time">${fmtTime(a.created_at)} · ${esc(a.actor_name || "系统")}</div>
          <div class="tl-body"><b>${esc(a.action)}</b> ｜ ${esc(a.target_type)} #${esc(a.target_id)} ${a.detail ? "｜ " + esc(a.detail) : ""}</div>
        </div>`).join("")}</div>
    </div>`;
};

VIEWS.credits = async () => {
  const data = await api("/api/credits");
  document.getElementById("page-body").innerHTML = `
    <div class="grid grid-2">
      <div class="card stat">
        <div class="k">当前信用分</div><div class="v">${STATE.user.credit}<small>/ 100</small></div>
        <div class="foot">${STATE.user.credit >= 60 ? "状态正常，可正常预约" : "低于 60 分，预约功能已受限"}</div>
      </div>
      <div class="card">
        <div class="card-head"><h3>计分规则</h3></div>
        <div class="t-sub" style="line-height:2">
          · 按时完成使用 <b>+2</b>；· 距开始不足 2 小时取消 <b>-5</b><br/>
          · 超时 30 分钟未签到判定爽约 <b>-15</b>；· 信用分低于 60 暂停预约，归零自动停用
        </div>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-head"><h3>变动明细</h3></div>
      ${data.items.length ? `<table><thead><tr><th>时间</th><th>原因</th><th>关联预约</th><th>变动</th><th>结算后</th></tr></thead><tbody>
        ${data.items.map(c => `<tr><td class="mono">${fmtTime(c.created_at)}</td><td>${esc(c.reason)}</td>
          <td class="mono">${c.reservation_id ? "#" + c.reservation_id : "-"}</td>
          <td><b style="color:${c.delta > 0 ? "var(--ok)" : "var(--danger)"}">${c.delta > 0 ? "+" : ""}${c.delta}</b></td>
          <td>${c.balance_after}</td></tr>`).join("")}
      </tbody></table>` : `<div class="empty">暂无信用变动记录</div>`}
    </div>`;
};

/* ------------------------------------------------------------ 弹窗与动作 */
function closeModal() { document.getElementById("modal-root").innerHTML = ""; }

function openModal(html) {
  const root = document.getElementById("modal-root");
  root.innerHTML = `<div class="modal-mask" id="mask"><div class="modal">${html}</div></div>`;
  root.querySelector("#mask").addEventListener("click", e => { if (e.target.id === "mask") closeModal(); });
}

function hourOptions(open, close) {
  const out = [];
  for (let h = open; h <= close; h++) {
    for (const m of [0, 30]) {
      if (h === close && m > 0) continue;
      out.push(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
    }
  }
  return out;
}

function openBooking(deviceId) {
  const d = STATE.devices.find(x => x.id === deviceId);
  if (!d) return;
  const today = new Date();
  const iso = x => x.toISOString().slice(0, 10);
  const opts = hourOptions(d.open_hour, d.close_hour);
  const defaultStart = opts.find(o => o >= `${String(Math.min(21, Math.max(d.open_hour, new Date().getHours() + 1))).padStart(2, "0")}:00`) || opts[0];

  openModal(`
    <h3>预约 ${esc(d.name)}</h3>
    <p class="modal-sub">${esc(d.code)} · ${esc(d.location)} · 开放 ${d.open_hour}:00-${d.close_hour}:00 · 单次最长 ${d.max_hours} 小时</p>
    <div class="alert alert-info">${d.requires_approval
      ? "该设备需要人工审批，提交后状态为「待审批」，请留意审批结果。"
      : "该设备支持即约即用，提交后立即生效。"} 当前信用分 ${STATE.user.credit}。</div>
    <div class="field"><label>使用日期</label><input type="date" id="b-date" value="${iso(today)}" min="${iso(today)}" /></div>
    <div class="row2">
      <div class="field"><label>开始时间</label><select id="b-start">${opts.map(o => `<option ${o === defaultStart ? "selected" : ""}>${o}</option>`).join("")}</select></div>
      <div class="field"><label>结束时间</label><select id="b-end">${opts.map(o => `<option ${o === opts[Math.min(opts.length - 1, opts.indexOf(defaultStart) + 4)] ? "selected" : ""}>${o}</option>`).join("")}</select></div>
    </div>
    <div class="field"><label>使用用途</label><input id="b-purpose" placeholder="如：毕业设计样件打印" maxlength="60" /></div>
    <div class="field"><label>使用人数</label><input id="b-head" type="number" min="1" max="20" value="1" /></div>
    <p class="login-error" id="b-err"></p>
    <div class="modal-foot">
      <button class="btn" onclick="closeModal()">取消</button>
      <button class="btn btn-primary" id="b-submit">提交预约</button>
    </div>`);

  document.getElementById("b-submit").addEventListener("click", async () => {
    const errBox = document.getElementById("b-err");
    errBox.textContent = "";
    const date = document.getElementById("b-date").value;
    const start = document.getElementById("b-start").value;
    const end = document.getElementById("b-end").value;
    if (end <= start) { errBox.textContent = "结束时间必须晚于开始时间"; return; }
    try {
      const res = await api("/api/reservations", {
        method: "POST",
        body: {
          device_id: d.id, start_at: `${date} ${start}`, end_at: `${date} ${end}`,
          purpose: document.getElementById("b-purpose").value.trim() || "课程/科研使用",
          headcount: Number(document.getElementById("b-head").value || 1)
        }
      });
      closeModal();
      toast(res.status === "PENDING" ? "预约已提交，等待审批" : "预约成功，请按时签到", "ok");
      go("reservations");
    } catch (err) { errBox.textContent = err.message; }
  });
}

function openDeviceModal(id) {
  const d = id ? STATE.devices.find(x => x.id === id) : {
    code: "", name: "", category: "增材制造", location: "", hourly_price: 0, requires_approval: 0,
    max_hours: 4, open_hour: 8, close_hour: 22, status: "AVAILABLE", description: ""
  };
  openModal(`
    <h3>${id ? "编辑设备" : "新增设备"}</h3>
    <p class="modal-sub">设备档案由管理员统一维护，变更将记入审计日志</p>
    <div class="row2">
      <div class="field"><label>设备编号</label><input id="d-code" value="${esc(d.code)}" ${id ? "disabled" : ""} placeholder="DEV-XXX-00" /></div>
      <div class="field"><label>设备名称</label><input id="d-name" value="${esc(d.name)}" /></div>
    </div>
    <div class="row2">
      <div class="field"><label>类别</label><input id="d-cat" value="${esc(d.category)}" /></div>
      <div class="field"><label>存放位置</label><input id="d-loc" value="${esc(d.location)}" /></div>
    </div>
    <div class="row2">
      <div class="field"><label>每小时单价（元）</label><input id="d-price" type="number" step="0.5" value="${d.hourly_price}" /></div>
      <div class="field"><label>单次最长（小时）</label><input id="d-max" type="number" min="1" max="12" value="${d.max_hours}" /></div>
    </div>
    <div class="row2">
      <div class="field"><label>开放开始（时）</label><input id="d-open" type="number" min="0" max="23" value="${d.open_hour}" /></div>
      <div class="field"><label>开放结束（时）</label><input id="d-close" type="number" min="1" max="24" value="${d.close_hour}" /></div>
    </div>
    <div class="row2">
      <div class="field"><label>预约方式</label><select id="d-appr">
        <option value="0" ${!d.requires_approval ? "selected" : ""}>即约即用</option>
        <option value="1" ${d.requires_approval ? "selected" : ""}>需人工审批</option></select></div>
      <div class="field"><label>设备状态</label><select id="d-st">
        ${Object.entries(DEVICE_TEXT).map(([k, v]) => `<option value="${k}" ${d.status === k ? "selected" : ""}>${v}</option>`).join("")}
      </select></div>
    </div>
    <div class="field"><label>设备说明</label><textarea id="d-desc" rows="2">${esc(d.description)}</textarea></div>
    <p class="login-error" id="d-err"></p>
    <div class="modal-foot">
      <button class="btn" onclick="closeModal()">取消</button>
      <button class="btn btn-primary" id="d-submit">保存</button>
    </div>`);

  document.getElementById("d-submit").addEventListener("click", async () => {
    const payload = {
      code: document.getElementById("d-code").value.trim(),
      name: document.getElementById("d-name").value.trim(),
      category: document.getElementById("d-cat").value.trim(),
      location: document.getElementById("d-loc").value.trim(),
      hourly_price: Number(document.getElementById("d-price").value || 0),
      max_hours: Number(document.getElementById("d-max").value || 4),
      open_hour: Number(document.getElementById("d-open").value || 8),
      close_hour: Number(document.getElementById("d-close").value || 22),
      requires_approval: Number(document.getElementById("d-appr").value),
      status: document.getElementById("d-st").value,
      description: document.getElementById("d-desc").value.trim()
    };
    try {
      await api(id ? `/api/devices/${id}` : "/api/devices", { method: id ? "PUT" : "POST", body: payload });
      closeModal(); toast("设备信息已保存", "ok"); renderView();
    } catch (err) { document.getElementById("d-err").textContent = err.message; }
  });
}

function openCreditModal(uid, name, credit) {
  openModal(`
    <h3>调整信用分 · ${esc(name)}</h3>
    <p class="modal-sub">当前信用分 ${credit}，单次调整幅度 1~50，调整原因将写入审计日志</p>
    <div class="field"><label>调整分值（负数为扣分）</label><input id="c-delta" type="number" value="10" /></div>
    <div class="field"><label>调整原因</label><input id="c-reason" placeholder="如：申诉复核，恢复扣分" /></div>
    <p class="login-error" id="c-err"></p>
    <div class="modal-foot"><button class="btn" onclick="closeModal()">取消</button>
      <button class="btn btn-primary" id="c-submit">确认调整</button></div>`);
  document.getElementById("c-submit").addEventListener("click", async () => {
    try {
      await api(`/api/users/${uid}/credit`, {
        method: "POST",
        body: { delta: Number(document.getElementById("c-delta").value), reason: document.getElementById("c-reason").value }
      });
      closeModal(); toast("信用分已更新", "ok");
      if (uid === STATE.user.id) { const me = await api("/api/auth/me"); STATE.user = { ...STATE.user, ...me.user }; }
      renderView();
    } catch (err) { document.getElementById("c-err").textContent = err.message; }
  });
}

async function cancelRes(id) {
  if (!confirm("确认取消该预约？距开始不足 2 小时将扣 5 分信用分。")) return;
  try { const r = await api(`/api/reservations/${id}/cancel`, { method: "POST", body: {} });
    toast(r.credit_delta ? `已取消，信用分 ${r.credit_delta}` : "预约已取消", "ok"); refreshAfterAction(); }
  catch (e) { toast(e.message, "err"); }
}

async function checkIn(id) {
  try { await api(`/api/reservations/${id}/checkin`, { method: "POST", body: {} }); toast("签到成功", "ok"); refreshAfterAction(); }
  catch (e) { toast(e.message, "err"); }
}

async function checkOut(id) {
  try { const r = await api(`/api/reservations/${id}/checkout`, { method: "POST", body: {} });
    toast(`签退成功，信用分 +2（当前 ${r.credit}）`, "ok"); refreshAfterAction(); }
  catch (e) { toast(e.message, "err"); }
}

async function review(id, approve) {
  const remark = prompt(approve ? "通过意见（可留空）" : "驳回理由（将反馈给申请人）", approve ? "同意使用" : "");
  if (remark === null) return;
  try {
    await api(`/api/reservations/${id}/${approve ? "approve" : "reject"}`, { method: "POST", body: { remark } });
    toast(approve ? "已通过" : "已驳回", "ok");
    renderView();
  } catch (e) { toast(e.message, "err"); }
}

async function refreshAfterAction() {
  const me = await api("/api/auth/me");
  if (me.user) STATE.user = { ...STATE.user, ...me.user };
  renderView();
}

/* ------------------------------------------------------------ 启动 */
async function bootApp() {
  renderShell();
  await renderView();
}

(async function init() {
  try {
    const me = await api("/api/auth/me");
    if (me.user) { STATE.user = me.user; await bootApp(); return; }
  } catch (e) { /* 未登录 */ }
  renderLogin();
})();
