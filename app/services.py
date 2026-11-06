"""服务层（Service）：全部业务规则与核心算法集中于此。

对应详细设计：
  4.4.1 预约时段冲突检测算法   -> ConflictDetector
  4.4.2 信用分结算算法         -> CreditService
  4.4.3 爽约扫描算法           -> ReservationService.sweep_no_show
  4.6   业务异常与错误码       -> errors.py
"""

import re
import secrets
from datetime import datetime, timedelta

from db import hash_password
from errors import (ValidationError, AuthError, ForbiddenError, NotFoundError,
                    ConflictError, BusinessRuleError)

DT_FMT = "%Y-%m-%d %H:%M"
CREDIT_MIN_TO_RESERVE = 60
CREDIT_COMPLETE_REWARD = 2
CREDIT_LATE_CANCEL = -5
CREDIT_NO_SHOW = -15
LATE_CANCEL_HOURS = 2
CHECKIN_GRACE_MINUTES = 30
ADVANCE_BOOKING_DAYS = 7
MIN_LEAD_MINUTES = 5
EFFECTIVE_STATUS = ("PENDING", "APPROVED", "CHECKED_IN")


# ------------------------------------------------------------------ 工具
class TimeUtil:
    """时间解析与格式化。对外只接受 'YYYY-MM-DD HH:MM' 或 ISO 形式。"""

    PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$")

    @staticmethod
    def parse(text):
        if not isinstance(text, str) or not TimeUtil.PATTERN.match(text.strip()):
            raise ValidationError("时间格式应为 YYYY-MM-DD HH:MM", {"value": text})
        try:
            return datetime.strptime(text.strip().replace("T", " ")[:16], DT_FMT)
        except ValueError:
            raise ValidationError("时间不是合法日期", {"value": text})

    @staticmethod
    def fmt(dt):
        return dt.strftime(DT_FMT)


class ConflictDetector:
    """时间区间重叠判定：半开区间 [start, end)，相邻不算冲突。"""

    @staticmethod
    def overlap(a_start, a_end, b_start, b_end):
        return a_start < b_end and b_start < a_end

    @classmethod
    def find_first(cls, slots, start, end):
        """在候选区间集合中找出第一个与目标区间冲突的项，未冲突返回 None。O(n)。"""
        for s in slots:
            if cls.overlap(start, end, TimeUtil.parse(s["start_at"]), TimeUtil.parse(s["end_at"])):
                return s
        return None


# ------------------------------------------------------------------ 认证
class AuthService:
    def __init__(self, uow):
        self.uow = uow

    def login(self, username, password):
        if not username or not password:
            raise ValidationError("用户名和密码不能为空")
        user = self.uow.users.by_username(username)
        if not user:
            raise AuthError("用户名或密码错误")
        digest, _ = hash_password(password, user["salt"])
        if digest != user["password_hash"]:
            raise AuthError("用户名或密码错误")
        if user["status"] == "BANNED":
            raise ForbiddenError("账号已停用，请联系管理员")
        token = secrets.token_hex(24)
        expires = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        self.uow.sessions.create(token, user["id"], expires)
        self.uow.audits.write(user["id"], user["name"], "LOGIN", "user", user["id"], "登录成功")
        self.uow.commit()
        return {"token": token, "user": self.public_user(user)}

    def logout(self, token):
        self.uow.sessions.delete(token)
        self.uow.commit()

    def current(self, token):
        if not token:
            raise AuthError()
        row = self.uow.sessions.find(token)
        if not row:
            raise AuthError("登录状态已失效，请重新登录")
        if row["expires_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
            self.uow.sessions.delete(token)
            self.uow.commit()
            raise AuthError("登录已过期")
        return {"id": row["uid"], "username": row["username"], "name": row["name"],
                "role": row["role"], "credit": row["credit"], "token": token}

    @staticmethod
    def public_user(user):
        return {k: user[k] for k in ("id", "username", "name", "role", "dept", "credit", "status")}


# ------------------------------------------------------------------ 设备
class DeviceService:
    def __init__(self, uow):
        self.uow = uow

    def list(self, keyword="", category="", status=""):
        items = self.uow.devices.list(keyword, category, status)
        return {"items": items, "categories": self.uow.devices.categories(), "total": len(items)}

    def detail(self, did):
        d = self.uow.devices.by_id(did)
        if not d:
            raise NotFoundError("设备不存在")
        return d

    def create(self, actor, payload):
        self._require_admin(actor)
        code = (payload.get("code") or "").strip().upper()
        if not code or not payload.get("name"):
            raise ValidationError("设备编号与名称必填")
        if self.uow.devices.by_code(code):
            raise ConflictError(f"设备编号 {code} 已存在")
        data = self._normalize(payload)
        data["code"] = code
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        did = self.uow.devices.create(data)
        self.uow.audits.write(actor["id"], actor["name"], "DEVICE_CREATE", "device", did, code)
        self.uow.commit()
        return {"id": did}

    def update(self, actor, did, payload):
        self._require_admin(actor)
        self.detail(did)
        data = self._normalize(payload)
        self.uow.devices.update(did, data)
        self.uow.audits.write(actor["id"], actor["name"], "DEVICE_UPDATE", "device", did,
                              f"状态={data['status']}")
        self.uow.commit()
        return {"id": did}

    def _normalize(self, p):
        try:
            open_hour = int(p.get("open_hour", 8))
            close_hour = int(p.get("close_hour", 22))
            max_hours = int(p.get("max_hours", 4))
            price = float(p.get("hourly_price", 0))
        except (TypeError, ValueError):
            raise ValidationError("开放时间、最长时长、单价必须为数字")
        if not 0 <= open_hour < close_hour <= 24:
            raise ValidationError("开放时间区间不合法")
        if not 1 <= max_hours <= 12:
            raise ValidationError("单次最长时长应在 1~12 小时之间")
        return {
            "name": (p.get("name") or "").strip(),
            "category": (p.get("category") or "其他").strip(),
            "location": (p.get("location") or "").strip(),
            "hourly_price": price,
            "requires_approval": 1 if str(p.get("requires_approval")) in ("1", "true", "True") else 0,
            "max_hours": max_hours,
            "open_hour": open_hour,
            "close_hour": close_hour,
            "status": p.get("status") if p.get("status") in ("AVAILABLE", "MAINTENANCE", "RETIRED") else "AVAILABLE",
            "description": (p.get("description") or "").strip(),
        }

    @staticmethod
    def _require_admin(actor):
        if actor["role"] != "ADMIN":
            raise ForbiddenError("仅管理员可维护设备档案")


# ------------------------------------------------------------------ 信用
class CreditService:
    def __init__(self, uow):
        self.uow = uow

    def apply(self, user_id, reservation_id, delta, reason):
        """结算信用分并落流水，返回结算后分值。区间 [0, 100]。"""
        user = self.uow.users.by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")
        balance = max(0, min(100, user["credit"] + delta))
        real_delta = balance - user["credit"]
        self.uow.users.update_credit(user_id, balance)
        if real_delta != 0:
            self.uow.credits.add(user_id, reservation_id, real_delta, reason, balance)
        if balance <= 0 and user["status"] == "ACTIVE":
            self.uow.users.update_status(user_id, "BANNED")
            self.uow.audits.write(None, "system", "USER_AUTO_BAN", "user", user_id, "信用分归零自动停用")
        return balance

    def history(self, actor, user_id=None):
        uid = user_id if (user_id and actor["role"] == "ADMIN") else actor["id"]
        return {"items": self.uow.credits.list_by_user(uid), "user_id": uid}


# ------------------------------------------------------------------ 预约
class ReservationService:
    def __init__(self, uow):
        self.uow = uow
        self.credit = CreditService(uow)

    # ---- 查询
    def list(self, actor, status="", keyword=""):
        scope_user = None if actor["role"] in ("ADMIN", "TEACHER") else actor["id"]
        items = self.uow.reservations.list_scoped(scope_user, status, keyword)
        return {"items": items, "total": len(items)}

    # ---- 创建
    def create(self, actor, payload):
        if actor["role"] == "ADMIN":
            raise ForbiddenError("管理员不参与设备预约，请使用审批与统计功能")
        user = self.uow.users.by_id(actor["id"])
        if user["status"] != "ACTIVE":
            raise ForbiddenError("账号状态异常，无法预约")
        if user["credit"] < CREDIT_MIN_TO_RESERVE:
            raise BusinessRuleError(
                f"信用分 {user['credit']} 低于 {CREDIT_MIN_TO_RESERVE}，暂无法预约设备",
                {"credit": user["credit"]})

        device_id = payload.get("device_id")
        if not device_id:
            raise ValidationError("请选择设备")
        device = self.uow.devices.by_id(int(device_id))
        if not device:
            raise NotFoundError("设备不存在")
        if device["status"] != "AVAILABLE":
            raise BusinessRuleError(f"设备当前状态为 {device['status']}，暂不可预约")

        start = TimeUtil.parse(payload.get("start_at"))
        end = TimeUtil.parse(payload.get("end_at"))
        self._validate_window(start, end, device)

        conflicts = self.uow.reservations.overlapping(device["id"], TimeUtil.fmt(start), TimeUtil.fmt(end))
        hit = ConflictDetector.find_first(conflicts, start, end)
        if hit:
            raise ConflictError(
                f"该时段与已有预约冲突（{hit['start_at']} ~ {hit['end_at']}）",
                {"conflict_id": hit["id"]})

        status = "PENDING" if device["requires_approval"] else "APPROVED"
        rid = self.uow.reservations.create({
            "user_id": actor["id"], "device_id": device["id"],
            "start_at": TimeUtil.fmt(start), "end_at": TimeUtil.fmt(end),
            "purpose": (payload.get("purpose") or "课程/科研使用").strip()[:120],
            "headcount": max(1, int(payload.get("headcount") or 1)),
            "status": status, "credit_delta": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.uow.audits.write(actor["id"], actor["name"], "RES_CREATE", "reservation", rid,
                              f"{device['name']} {TimeUtil.fmt(start)}~{TimeUtil.fmt(end)} -> {status}")
        self.uow.commit()
        return {"id": rid, "status": status, "requires_approval": device["requires_approval"]}

    def _validate_window(self, start, end, device):
        now = datetime.now()
        if end <= start:
            raise ValidationError("结束时间必须晚于开始时间")
        hours = (end - start).total_seconds() / 3600
        if hours > device["max_hours"]:
            raise BusinessRuleError(f"单次预约不得超过 {device['max_hours']} 小时")
        if start < now - timedelta(minutes=1):
            raise BusinessRuleError("不能预约已经过去的时段")
        if start < now + timedelta(minutes=MIN_LEAD_MINUTES):
            raise BusinessRuleError(f"请至少提前 {MIN_LEAD_MINUTES} 分钟预约")
        if start > now + timedelta(days=ADVANCE_BOOKING_DAYS):
            raise BusinessRuleError(f"最多只能预约未来 {ADVANCE_BOOKING_DAYS} 天内的时段")
        if start.date() != end.date():
            # 24 小时开放的自助设备允许跨零点使用，其余设备要求同日完成
            if not (device["open_hour"] == 0 and device["close_hour"] == 24):
                raise BusinessRuleError("暂不支持跨天预约，请将时段控制在同一天内")
            if (end.date() - start.date()).days != 1:
                raise BusinessRuleError("单次预约最多跨越一个自然日")
        else:
            open_min = device["open_hour"] * 60
            close_min = device["close_hour"] * 60
            start_min = start.hour * 60 + start.minute
            end_min = end.hour * 60 + end.minute
            if start_min < open_min or end_min > close_min:
                raise BusinessRuleError(
                    f"设备开放时间为 {device['open_hour']}:00 - {device['close_hour']}:00")

    # ---- 取消
    def cancel(self, actor, rid, reason=""):
        res = self._get(rid)
        if res["user_id"] != actor["id"] and actor["role"] != "ADMIN":
            raise ForbiddenError("只能取消自己的预约")
        if res["status"] not in ("PENDING", "APPROVED"):
            raise ConflictError(f"当前状态 {res['status']} 不允许取消")
        start = TimeUtil.parse(res["start_at"])
        hours_left = (start - datetime.now()).total_seconds() / 3600
        delta = CREDIT_LATE_CANCEL if 0 < hours_left < LATE_CANCEL_HOURS else 0
        self.uow.reservations.set_status(rid, "CANCELLED")
        if delta:
            self.credit.apply(res["user_id"], rid, delta, "临近开始取消预约")
        self.uow.audits.write(actor["id"], actor["name"], "RES_CANCEL", "reservation", rid,
                              reason or "用户取消")
        self.uow.commit()
        return {"id": rid, "credit_delta": delta}

    # ---- 审批
    def review(self, actor, rid, approve, remark=""):
        if actor["role"] not in ("ADMIN", "TEACHER"):
            raise ForbiddenError("仅管理员或教师可审批")
        res = self._get(rid)
        if res["status"] != "PENDING":
            raise ConflictError("仅待审批的预约可以审批")
        if res["user_id"] == actor["id"]:
            raise ForbiddenError("不能审批自己的预约")
        new_status = "APPROVED" if approve else "REJECTED"
        self.uow.reservations.set_status(rid, new_status, approver_id=actor["id"],
                                         approve_remark=(remark or "")[:200])
        self.uow.audits.write(actor["id"], actor["name"],
                              "RES_APPROVE" if approve else "RES_REJECT", "reservation", rid, remark)
        self.uow.commit()
        return {"id": rid, "status": new_status}

    # ---- 签到 / 签退
    def check_in(self, actor, rid):
        res = self._get(rid)
        if res["user_id"] != actor["id"]:
            raise ForbiddenError("只能为自己的预约签到")
        if res["status"] != "APPROVED":
            raise ConflictError("只有已通过的预约可以签到")
        now = datetime.now()
        start = TimeUtil.parse(res["start_at"])
        if now < start - timedelta(minutes=15):
            raise BusinessRuleError("尚未到签到时间（可提前 15 分钟签到）")
        if now > start + timedelta(minutes=CHECKIN_GRACE_MINUTES):
            raise BusinessRuleError("已超过签到宽限期，本次预约将被记为爽约")
        self.uow.reservations.set_status(rid, "CHECKED_IN", checked_in_at=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.uow.audits.write(actor["id"], actor["name"], "RES_CHECKIN", "reservation", rid, "")
        self.uow.commit()
        return {"id": rid, "status": "CHECKED_IN"}

    def check_out(self, actor, rid):
        res = self._get(rid)
        if res["user_id"] != actor["id"] and actor["role"] != "ADMIN":
            raise ForbiddenError("只能为自己的预约签退")
        if res["status"] != "CHECKED_IN":
            raise ConflictError("只有已签到的预约可以签退")
        self.uow.reservations.set_status(rid, "COMPLETED",
                                         checked_out_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                         credit_delta=CREDIT_COMPLETE_REWARD)
        balance = self.credit.apply(res["user_id"], rid, CREDIT_COMPLETE_REWARD, "按时完成使用")
        self.uow.audits.write(actor["id"], actor["name"], "RES_CHECKOUT", "reservation", rid,
                              f"信用分结算后 {balance}")
        self.uow.commit()
        return {"id": rid, "status": "COMPLETED", "credit": balance}

    # ---- 爽约扫描（定时任务，也可由管理员手动触发）
    def sweep_no_show(self, actor=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        rows = self.uow.reservations.due_for_no_show(now, CHECKIN_GRACE_MINUTES)
        for r in rows:
            self.uow.reservations.set_status(r["id"], "NO_SHOW",
                                             credit_delta=CREDIT_NO_SHOW,
                                             approve_remark="超时未签到，系统判定爽约")
            self.credit.apply(r["user_id"], r["id"], CREDIT_NO_SHOW, "超时未签到判定爽约")
            self.uow.audits.write(None, "system", "RES_NO_SHOW", "reservation", r["id"], r["user_name"])
        self.uow.commit()
        return {"affected": len(rows), "ids": [r["id"] for r in rows]}

    def _get(self, rid):
        res = self.uow.reservations.by_id(rid)
        if not res:
            raise NotFoundError("预约记录不存在")
        return res


# ------------------------------------------------------------------ 统计
class StatsService:
    def __init__(self, uow):
        self.uow = uow

    def overview(self, actor):
        if actor["role"] not in ("ADMIN", "TEACHER"):
            raise ForbiddenError("仅管理员或教师可查看统计")
        by_status = self.uow.reservations.stats_by_status()
        total = sum(by_status.values())
        done = by_status.get("COMPLETED", 0)
        no_show = by_status.get("NO_SHOW", 0)
        users = self.uow.users.list_all()
        devices = self.uow.devices.list()
        return {
            "reservation_total": total,
            "by_status": by_status,
            "device_total": len(devices),
            "device_available": len([d for d in devices if d["status"] == "AVAILABLE"]),
            "user_total": len(users),
            "no_show_rate": round(no_show / total * 100, 1) if total else 0.0,
            "completion_rate": round(done / total * 100, 1) if total else 0.0,
            "top_devices": self.uow.reservations.top_devices(),
            "trend": self.uow.reservations.daily_trend(),
            "low_credit_users": [u for u in users if u["credit"] < CREDIT_MIN_TO_RESERVE],
        }

    def audit(self, actor):
        if actor["role"] != "ADMIN":
            raise ForbiddenError("仅管理员可查看审计日志")
        return {"items": self.uow.audits.list_all()}
