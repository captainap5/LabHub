"""HTTP 接入层：路由分发、会话鉴权、统一异常处理、静态资源托管。

启动：python server.py [端口]
"""

import json
import mimetypes
import os
import re
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

import db
from errors import AppError, ValidationError, ForbiddenError
from repos import UnitOfWork
from services import (AuthService, DeviceService, ReservationService, StatsService, CreditService)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
COOKIE_NAME = "labhub_token"

ROUTES = []


def route(method, pattern, roles=None, auth=True):
    """注册路由。roles=None 表示不限制角色。"""
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn, roles, auth))
        return fn
    return deco


# ------------------------------------------------------------------ 路由定义
@route("POST", r"/api/auth/login", auth=False)
def login(ctx):
    body = ctx["body"]
    return AuthService(ctx["uow"]).login(body.get("username", ""), body.get("password", ""))


@route("POST", r"/api/auth/logout", auth=False)
def logout(ctx):
    token = ctx["token"]
    if token:
        AuthService(ctx["uow"]).logout(token)
    return {"ok": True}, 200, {"Set-Cookie": f"{COOKIE_NAME}=; Path=/; Max-Age=0"}


@route("GET", r"/api/auth/me", auth=False)
def me(ctx):
    token = ctx["token"]
    if not token:
        return {"user": None}
    return {"user": AuthService(ctx["uow"]).current(token)}


@route("GET", r"/api/meta", auth=False)
def meta(ctx):
    svc = DeviceService(ctx["uow"])
    return {
        "roles": ["STUDENT", "TEACHER", "ADMIN"],
        "statuses": ["PENDING", "APPROVED", "REJECTED", "CHECKED_IN", "COMPLETED",
                     "CANCELLED", "NO_SHOW"],
        "categories": svc.uow.devices.categories(),
        "rules": {"credit_min_to_reserve": 60, "late_cancel_hours": 2,
                  "checkin_grace_minutes": 30, "advance_booking_days": 7},
    }


@route("GET", r"/api/devices")
def device_list(ctx):
    q = ctx["query"]
    return DeviceService(ctx["uow"]).list(q.get("keyword", [""])[0], q.get("category", [""])[0],
                                          q.get("status", [""])[0])


@route("GET", r"/api/devices/(\d+)")
def device_detail(ctx, did):
    return DeviceService(ctx["uow"]).detail(int(did))


@route("POST", r"/api/devices", roles=("ADMIN",))
def device_create(ctx):
    return DeviceService(ctx["uow"]).create(ctx["user"], ctx["body"]), 201


@route("PUT", r"/api/devices/(\d+)", roles=("ADMIN",))
def device_update(ctx, did):
    return DeviceService(ctx["uow"]).update(ctx["user"], int(did), ctx["body"])


@route("GET", r"/api/reservations")
def res_list(ctx):
    q = ctx["query"]
    return ReservationService(ctx["uow"]).list(ctx["user"], q.get("status", [""])[0],
                                               q.get("keyword", [""])[0])


@route("POST", r"/api/reservations", roles=("STUDENT", "TEACHER"))
def res_create(ctx):
    return ReservationService(ctx["uow"]).create(ctx["user"], ctx["body"]), 201


@route("POST", r"/api/reservations/(\d+)/cancel")
def res_cancel(ctx, rid):
    return ReservationService(ctx["uow"]).cancel(ctx["user"], int(rid), ctx["body"].get("reason", ""))


@route("POST", r"/api/reservations/(\d+)/approve", roles=("ADMIN", "TEACHER"))
def res_approve(ctx, rid):
    return ReservationService(ctx["uow"]).review(ctx["user"], int(rid), True,
                                                 ctx["body"].get("remark", ""))


@route("POST", r"/api/reservations/(\d+)/reject", roles=("ADMIN", "TEACHER"))
def res_reject(ctx, rid):
    return ReservationService(ctx["uow"]).review(ctx["user"], int(rid), False,
                                                 ctx["body"].get("remark", ""))


@route("POST", r"/api/reservations/(\d+)/checkin")
def res_checkin(ctx, rid):
    return ReservationService(ctx["uow"]).check_in(ctx["user"], int(rid))


@route("POST", r"/api/reservations/(\d+)/checkout")
def res_checkout(ctx, rid):
    return ReservationService(ctx["uow"]).check_out(ctx["user"], int(rid))


@route("GET", r"/api/stats/overview", roles=("ADMIN", "TEACHER"))
def stats_overview(ctx):
    return StatsService(ctx["uow"]).overview(ctx["user"])


@route("GET", r"/api/audit-logs", roles=("ADMIN",))
def audit_logs(ctx):
    return StatsService(ctx["uow"]).audit(ctx["user"])


@route("GET", r"/api/users", roles=("ADMIN", "TEACHER"))
def user_list(ctx):
    return {"items": ctx["uow"].users.list_all()}


@route("POST", r"/api/users/(\d+)/credit", roles=("ADMIN",))
def user_credit(ctx, uid):
    body = ctx.get("body") or {}
    try:
        delta = int(body.get("delta", 0))
    except (TypeError, ValueError):
        raise ValidationError("分值必须为整数")
    if delta == 0 or abs(delta) > 50:
        raise ValidationError("单次调整幅度应在 1~50 之间")
    svc = CreditService(ctx["uow"])
    balance = svc.apply(int(uid), None, delta, body.get("reason") or "管理员手动调整")
    ctx["uow"].audits.write(ctx["user"]["id"], ctx["user"]["name"], "CREDIT_ADJUST", "user",
                            uid, f"{delta:+d} -> {balance}")
    ctx["uow"].commit()
    return {"user_id": int(uid), "credit": balance}


@route("GET", r"/api/credits")
def credit_history(ctx):
    q = ctx["query"]
    uid = q.get("user_id", [None])[0]
    return CreditService(ctx["uow"]).history(ctx["user"], int(uid) if uid else None)


@route("POST", r"/api/admin/sweep", roles=("ADMIN",))
def sweep(ctx):
    return ReservationService(ctx["uow"]).sweep_no_show(ctx["user"])


# ------------------------------------------------------------------ 处理器
class Handler(BaseHTTPRequestHandler):
    server_version = "LabHub/1.0"
    protocol_version = "HTTP/1.1"

    # 静默访问日志，只打印异常
    def log_message(self, fmt, *args):
        pass

    # ---- 工具
    def _cookies(self):
        raw = self.headers.get("Cookie", "")
        out = {}
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
        return out

    def _send_json(self, payload, status=200, extra_headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        if not os.path.isfile(path):
            self._send_json({"error": {"code": "RES_404", "message": "页面不存在"}}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if len(raw) > 256 * 1024:
            raise ValidationError("请求体过大")
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValidationError("请求体必须是合法 JSON")

    # ---- 分发
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if not path.startswith("/api/"):
            if path == "/":
                path = "/index.html"
            return self._send_file(os.path.join(STATIC_DIR, path.lstrip("/").replace("../", "")))

        for m, pattern, fn, roles, auth_required in ROUTES:
            if m != method:
                continue
            match = pattern.match(path)
            if not match:
                continue
            return self._handle(fn, match.groups(), roles, auth_required, parse_qs(parsed.query))

        self._send_json({"error": {"code": "RES_404", "message": f"接口不存在: {method} {path}"}}, 404)

    def _handle(self, fn, groups, roles, auth_required, query):
        uow = UnitOfWork()
        try:
            token = self._cookies().get(COOKIE_NAME, "") or \
                (self.headers.get("Authorization", "").replace("Bearer ", "").strip())
            user = None
            if auth_required or roles:
                user = AuthService(uow).current(token)
                if roles and user["role"] not in roles:
                    raise ForbiddenError("当前角色无权访问该接口")

            body = self._read_body() if self.command in ("POST", "PUT") else {}
            ctx = {"uow": uow, "user": user, "token": token, "body": body,
                   "query": query, "headers": self.headers}
            result = fn(ctx, *groups)

            headers = {}
            if isinstance(result, tuple):
                payload, status = result[0], result[1]
                headers = result[2] if len(result) > 2 else {}
            else:
                payload, status = result, 200

            if isinstance(payload, dict) and "user" in payload and "token" in payload:
                headers.setdefault("Set-Cookie",
                                   f"{COOKIE_NAME}={payload['token']}; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800")
                payload = {k: v for k, v in payload.items() if k != "token"}

            self._send_json(payload, status, headers)
        except AppError as e:
            uow.rollback()
            self._send_json({"error": e.to_dict()}, e.http_status)
        except Exception as e:  # 兜底：未知异常不泄露堆栈给前端
            uow.rollback()
            traceback.print_exc()
            self._send_json({"error": {"code": "SYS_500", "message": "服务器内部错误",
                                       "detail": {"type": type(e).__name__}}}, 500)
        finally:
            uow.close()


def sweep_loop():
    """后台爽约扫描：每 60 秒执行一次。"""
    while True:
        time.sleep(60)
        uow = UnitOfWork()
        try:
            ReservationService(uow).sweep_no_show()
        except Exception:
            traceback.print_exc()
        finally:
            uow.close()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    db.init_db()
    db.seed_if_empty()
    threading.Thread(target=sweep_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"LabHub 已启动: http://127.0.0.1:{port}")
    print("演示账号: admin/admin123 · teacher1/123456 · stu001/123456 · stu002/123456")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
