"""接口级自动化测试（黑盒）。运行：python tests/api_test.py [端口]

输出：控制台用例表 + tools/test_results.json（供报告引用）
"""

import json
import os
import sys
import urllib.request
import urllib.error
import http.cookiejar
from datetime import datetime, timedelta

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
BASE = f"http://127.0.0.1:{PORT}"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "test_results.json")

RESULTS = []


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def call(self, method, path, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(BASE + path, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, {"raw": raw}


def login(username, password):
    c = Client()
    status, body = c.call("POST", "/api/auth/login", {"username": username, "password": password})
    return c, status, body


def case(tid, name, expect, actual, passed, note=""):
    RESULTS.append({"id": tid, "name": name, "expect": expect, "actual": actual,
                    "passed": bool(passed), "note": note})
    flag = "PASS" if passed else "FAIL"
    print(f"[{flag}] {tid} {name} | 期望: {expect} | 实际: {actual}")


def slot(offset_minutes, duration_minutes):
    s = datetime.now() + timedelta(minutes=offset_minutes)
    e = s + timedelta(minutes=duration_minutes)
    return s.strftime("%Y-%m-%d %H:%M"), e.strftime("%Y-%m-%d %H:%M")


def main():
    # ---------- 认证与权限 ----------
    stu, st, body = login("stu001", "123456")
    case("TC-01", "学生使用正确口令登录", "200 且返回用户信息", st, st == 200 and "user" in body)

    _, st2, b2 = login("stu001", "wrong")
    case("TC-02", "错误口令登录被拒绝", "401 AUTH_401", st2, st2 == 401)

    anon = Client()
    st3, b3 = anon.call("GET", "/api/reservations")
    case("TC-03", "未登录访问受保护接口", "401", st3, st3 == 401)

    st4, b4 = stu.call("GET", "/api/audit-logs")
    case("TC-04", "学生访问管理员接口", "403 AUTH_403", st4, st4 == 403)

    # ---------- 设备 ----------
    st5, b5 = stu.call("GET", "/api/devices?category=%E5%A2%9E%E6%9D%90%E5%88%B6%E9%80%A0")
    ok5 = st5 == 200 and all(d["category"] == "增材制造" for d in b5["items"])
    case("TC-05", "按类别筛选设备", "仅返回增材制造设备", f"{len(b5.get('items', []))} 条，类别一致={ok5}", ok5)

    devices = stu.call("GET", "/api/devices")[1]["items"]
    # dev24：24 小时开放、免审批，用于与当前时刻相关的用例（不受运行时间影响）
    dev24 = next(d for d in devices if d["requires_approval"] == 0
                 and d["open_hour"] == 0 and d["close_hour"] == 24)
    dev_free = next(d for d in devices if d["open_hour"] == 8 and d["status"] == "AVAILABLE")
    dev_appr = next(d for d in devices if d["requires_approval"] == 1 and d["status"] == "AVAILABLE")

    # ---------- 预约创建 ----------
    s, e = slot(60, 60)
    st6, b6 = stu.call("POST", "/api/reservations",
                       {"device_id": dev24["id"], "start_at": s, "end_at": e, "purpose": "自动化测试-正常预约"})
    case("TC-06", "即约即用设备提交预约", "201 且状态 APPROVED",
         f"{st6} {b6.get('status')}", st6 == 201 and b6.get("status") == "APPROVED")
    ok_id = b6.get("id")

    st7, b7 = stu.call("POST", "/api/reservations",
                       {"device_id": dev24["id"], "start_at": s, "end_at": e, "purpose": "自动化测试-冲突"})
    case("TC-07", "同设备同时段重复预约", "409 RES_409 并给出冲突时段", st7, st7 == 409)

    s8, e8 = slot(120, 60)
    st8, b8 = stu.call("POST", "/api/reservations",
                       {"device_id": dev24["id"], "start_at": e8, "end_at": s8, "purpose": "测试"})
    case("TC-08", "结束时间早于开始时间", "400 参数校验失败", st8, st8 == 400)

    s9, e9 = slot(120, dev24["max_hours"] * 60 + 60)
    st9, b9 = stu.call("POST", "/api/reservations",
                       {"device_id": dev24["id"], "start_at": s9, "end_at": e9, "purpose": "测试"})
    case("TC-09", "超出设备单次最长时长", "422 业务规则拦截", st9, st9 == 422)

    day = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    st10, b10 = stu.call("POST", "/api/reservations",
                         {"device_id": dev_free["id"], "start_at": f"{day} 05:00", "end_at": f"{day} 06:00"})
    case("TC-10", "预约时间早于开放时间", "422 提示开放时间", st10, st10 == 422)

    s11, e11 = slot(-120, 60)
    st11, b11 = stu.call("POST", "/api/reservations",
                         {"device_id": dev24["id"], "start_at": s11, "end_at": e11})
    case("TC-11", "预约已过去的时段", "422 拦截", st11, st11 == 422)

    far = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    st12, b12 = stu.call("POST", "/api/reservations",
                         {"device_id": dev24["id"], "start_at": f"{far} 10:00", "end_at": f"{far} 11:00"})
    case("TC-12", "超过 7 天预约窗口", "422 拦截", st12, st12 == 422)

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    st13, b13 = stu.call("POST", "/api/reservations",
                         {"device_id": dev_free["id"], "start_at": f"{tomorrow} 20:00",
                          "end_at": f"{tomorrow} 23:00"})
    case("TC-13", "跨开放时间边界预约", "422 拦截", st13, st13 in (422, 400))

    s14, e14 = slot(180, 60)
    st14, b14 = stu.call("POST", "/api/reservations",
                         {"device_id": dev_appr["id"], "start_at": s14, "end_at": e14, "purpose": "自动化测试-待审批"})
    case("TC-14", "需审批设备提交后进入待审批", "201 且状态 PENDING",
         f"{st14} {b14.get('status')}", st14 == 201 and b14.get("status") == "PENDING")

    low, _, _ = login("stu002", "123456")
    s15, e15 = slot(240, 60)
    st15, b15 = low.call("POST", "/api/reservations",
                         {"device_id": dev24["id"], "start_at": s15, "end_at": e15})
    case("TC-15", "信用分低于 60 的用户预约", "422 提示信用分不足", st15, st15 == 422)

    adm, _, _ = login("admin", "admin123")
    s16, e16 = slot(300, 60)
    st16, b16 = adm.call("POST", "/api/reservations",
                         {"device_id": dev24["id"], "start_at": s16, "end_at": e16})
    case("TC-16", "管理员发起预约", "403 角色不允许", st16, st16 == 403)

    # ---------- 审批 ----------
    tea, _, _ = login("teacher1", "123456")
    rid = b14.get("id")
    st17, b17 = tea.call("POST", f"/api/reservations/{rid}/approve", {"remark": "同意使用"})
    case("TC-17", "教师审批通过预约", "200 且状态 APPROVED",
         f"{st17} {b17.get('status')}", st17 == 200 and b17.get("status") == "APPROVED")

    st18, b18 = tea.call("POST", f"/api/reservations/{rid}/approve", {"remark": "重复审批"})
    case("TC-18", "重复审批同一预约", "409 状态冲突", st18, st18 == 409)

    st19, _ = stu.call("POST", f"/api/reservations/{rid}/approve", {"remark": "越权"})
    case("TC-19", "学生调用审批接口", "403 无权操作", st19, st19 == 403)

    # ---------- 签到 / 签退 ----------
    # 释放 TC-06 占用的时段，避免与后续用例相互干扰
    stu.call("POST", f"/api/reservations/{ok_id}/cancel", {"reason": "测试前置清理"})

    s20, e20 = slot(10, 60)
    st20, b20 = stu.call("POST", "/api/reservations", {"device_id": dev24["id"], "start_at": s20, "end_at": e20})
    rid20 = b20.get("id")
    st21, b21 = stu.call("POST", f"/api/reservations/{rid20}/checkin")
    case("TC-20", "预约开始前 15 分钟内签到", "200 且状态 CHECKED_IN",
         f"{st21} {b21.get('status')}", st21 == 200)

    st22, b22 = stu.call("POST", f"/api/reservations/{rid20}/checkout")
    case("TC-21", "已签到预约执行签退", "200 COMPLETED 且信用分 +2",
         f"{st22} {b22.get('status')} credit={b22.get('credit')}",
         st22 == 200 and b22.get("status") == "COMPLETED")

    s23, e23 = slot(180, 60)
    st23, b23 = stu.call("POST", "/api/reservations", {"device_id": dev24["id"], "start_at": s23, "end_at": e23})
    rid23 = b23.get("id")
    st24, b24 = stu.call("POST", f"/api/reservations/{rid23}/checkin")
    case("TC-22", "提前 3 小时签到", "422 提示未到签到时间", st24, st24 == 422)

    s25, e25 = slot(300, 60)
    st25a, b25a = stu.call("POST", "/api/reservations",
                           {"device_id": dev24["id"], "start_at": s25, "end_at": e25})
    rid25 = b25a.get("id")
    st25, b25 = stu.call("POST", f"/api/reservations/{rid25}/cancel", {"reason": "行程变更"})
    case("TC-23", "提前 2 小时以上取消预约", "200 且不扣信用分",
         f"{st25} delta={b25.get('credit_delta')}", st25 == 200 and b25.get("credit_delta") == 0)

    st26, b26 = stu.call("POST", f"/api/reservations/{rid25}/cancel", {})
    case("TC-24", "重复取消已取消预约", "409 状态冲突", st26, st26 == 409)

    # ---------- 设备管理 ----------
    payload = {"code": "DEV-TEST-99", "name": "测试设备", "category": "测试", "location": "Z101",
               "hourly_price": 1, "max_hours": 2, "open_hour": 8, "close_hour": 20,
               "requires_approval": 0, "status": "AVAILABLE", "description": "自动化测试创建"}
    st27, b27 = adm.call("POST", "/api/devices", payload)
    case("TC-25", "管理员新增设备", "201 返回新设备 ID", f"{st27} {b27.get('id')}", st27 == 201)

    st28, b28 = adm.call("POST", "/api/devices", payload)
    case("TC-26", "新增重复编号设备", "409 编号冲突", st28, st28 == 409)

    st29, b29 = adm.call("PUT", f"/api/devices/{b27.get('id')}", {**payload, "status": "MAINTENANCE"})
    case("TC-27", "修改设备状态为维护中", "200 更新成功", st29, st29 == 200)

    # ---------- 信用与管理 ----------
    st30, b30 = adm.call("POST", "/api/users/4/credit", {"delta": 10, "reason": "申诉复核恢复"})
    case("TC-28", "管理员调整用户信用分", "200 返回新分值",
         f"{st30} credit={b30.get('credit')}", st30 == 200 and b30.get("credit") == 65)

    st31, b31 = adm.call("GET", "/api/audit-logs")
    case("TC-29", "查询审计日志", "200 且包含本次操作记录",
         f"{st31} {len(b31.get('items', []))} 条", st31 == 200 and len(b31.get("items", [])) > 5)

    st32, b32 = adm.call("GET", "/api/stats/overview")
    case("TC-30", "管理员查看统计概览", "200 含状态分布与热门设备",
         f"{st32} total={b32.get('reservation_total')}", st32 == 200 and "by_status" in b32)

    st33, b33 = adm.call("POST", "/api/admin/sweep", {})
    case("TC-31", "手动触发爽约扫描", "200 返回影响条数", f"{st33} affected={b33.get('affected')}", st33 == 200)

    st34, b34 = tea.call("GET", "/api/reservations")
    case("TC-32", "教师查看全量预约台账", "200 且条数不少于学生视角",
         f"{st34} {len(b34.get('items', []))} 条", st34 == 200 and len(b34.get("items", [])) >= 1)

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["passed"])
    print("\n" + "=" * 66)
    print(f"合计 {total} 条用例，通过 {passed} 条，失败 {total - passed} 条，通过率 {passed / total * 100:.1f}%")
    print("=" * 66)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"total": total, "passed": passed, "failed": total - passed,
                   "pass_rate": round(passed / total * 100, 1), "cases": RESULTS},
                  f, ensure_ascii=False, indent=2)
    print("结果已写入", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
