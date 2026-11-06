"""仓储层（Repository）：屏蔽 SQL 细节，只做数据存取，不含业务规则。"""

from db import connect, now_str


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


class UserRepository:
    def __init__(self, conn):
        self.conn = conn

    def by_username(self, username):
        cur = self.conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return dict(row) if row else None

    def by_id(self, uid):
        cur = self.conn.execute("SELECT * FROM users WHERE id = ?", (uid,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_all(self):
        cur = self.conn.execute(
            "SELECT id,username,name,role,dept,credit,status,created_at FROM users ORDER BY id")
        return _rows(cur)

    def update_credit(self, uid, credit):
        self.conn.execute("UPDATE users SET credit = ? WHERE id = ?", (credit, uid))

    def update_status(self, uid, status):
        self.conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, uid))


class DeviceRepository:
    def __init__(self, conn):
        self.conn = conn

    def list(self, keyword="", category="", status=""):
        sql = "SELECT * FROM devices WHERE 1=1"
        args = []
        if keyword:
            sql += " AND (name LIKE ? OR code LIKE ? OR location LIKE ?)"
            args += [f"%{keyword}%"] * 3
        if category:
            sql += " AND category = ?"
            args.append(category)
        if status:
            sql += " AND status = ?"
            args.append(status)
        sql += " ORDER BY id"
        return _rows(self.conn.execute(sql, args))

    def by_id(self, did):
        cur = self.conn.execute("SELECT * FROM devices WHERE id = ?", (did,))
        row = cur.fetchone()
        return dict(row) if row else None

    def by_code(self, code):
        cur = self.conn.execute("SELECT * FROM devices WHERE code = ?", (code,))
        row = cur.fetchone()
        return dict(row) if row else None

    def create(self, data):
        cur = self.conn.execute(
            "INSERT INTO devices(code,name,category,location,hourly_price,requires_approval,"
            "max_hours,open_hour,close_hour,status,description,created_at)"
            " VALUES(:code,:name,:category,:location,:hourly_price,:requires_approval,"
            ":max_hours,:open_hour,:close_hour,:status,:description,:created_at)", data)
        return cur.lastrowid

    def update(self, did, data):
        data = dict(data)
        data["id"] = did
        self.conn.execute(
            "UPDATE devices SET name=:name, category=:category, location=:location,"
            " hourly_price=:hourly_price, requires_approval=:requires_approval,"
            " max_hours=:max_hours, open_hour=:open_hour, close_hour=:close_hour,"
            " status=:status, description=:description WHERE id=:id", data)

    def categories(self):
        cur = self.conn.execute("SELECT DISTINCT category FROM devices ORDER BY category")
        return [r["category"] for r in cur.fetchall()]


class ReservationRepository:
    def __init__(self, conn):
        self.conn = conn

    def by_id(self, rid):
        cur = self.conn.execute("SELECT * FROM reservations WHERE id = ?", (rid,))
        row = cur.fetchone()
        return dict(row) if row else None

    def overlapping(self, device_id, start_at, end_at, exclude_id=None):
        """查询同设备上时间区间相交且仍然占用资源的预约。"""
        sql = ("SELECT r.*, u.name AS user_name FROM reservations r JOIN users u ON u.id = r.user_id"
               " WHERE r.device_id = ? AND r.status IN ('PENDING','APPROVED','CHECKED_IN')"
               " AND r.start_at < ? AND r.end_at > ?")
        args = [device_id, end_at, start_at]
        if exclude_id:
            sql += " AND r.id <> ?"
            args.append(exclude_id)
        return _rows(self.conn.execute(sql, args))

    def list_scoped(self, user_id=None, status="", keyword=""):
        sql = ("SELECT r.*, d.name AS device_name, d.code AS device_code, d.location,"
               " u.name AS user_name FROM reservations r"
               " JOIN devices d ON d.id = r.device_id JOIN users u ON u.id = r.user_id WHERE 1=1")
        args = []
        if user_id:
            sql += " AND r.user_id = ?"
            args.append(user_id)
        if status:
            sql += " AND r.status = ?"
            args.append(status)
        if keyword:
            sql += " AND (d.name LIKE ? OR r.purpose LIKE ? OR u.name LIKE ?)"
            args += [f"%{keyword}%"] * 3
        sql += " ORDER BY r.start_at DESC LIMIT 200"
        return _rows(self.conn.execute(sql, args))

    def create(self, data):
        cur = self.conn.execute(
            "INSERT INTO reservations(user_id,device_id,start_at,end_at,purpose,headcount,status,"
            "credit_delta,created_at) VALUES(:user_id,:device_id,:start_at,:end_at,:purpose,"
            ":headcount,:status,:credit_delta,:created_at)", data)
        return cur.lastrowid

    def set_status(self, rid, status, **extra):
        fields = ["status = ?"]
        args = [status]
        for k, v in extra.items():
            fields.append(f"{k} = ?")
            args.append(v)
        args.append(rid)
        self.conn.execute(f"UPDATE reservations SET {', '.join(fields)} WHERE id = ?", args)

    def due_for_no_show(self, now, grace_minutes):
        sql = ("SELECT r.*, u.name AS user_name FROM reservations r JOIN users u ON u.id = r.user_id"
               " WHERE r.status IN ('PENDING','APPROVED')"
               " AND datetime(r.start_at, ?) < datetime(?)")
        return _rows(self.conn.execute(sql, (f"+{grace_minutes} minutes", now)))

    def stats_by_status(self):
        rows = self.conn.execute(
            "SELECT status, COUNT(*) AS c FROM reservations GROUP BY status").fetchall()
        return {r["status"]: r["c"] for r in rows}

    def top_devices(self, limit=5):
        cur = self.conn.execute(
            "SELECT d.name, COUNT(*) AS c FROM reservations r JOIN devices d ON d.id = r.device_id"
            " WHERE r.status IN ('APPROVED','CHECKED_IN','COMPLETED')"
            " GROUP BY d.id ORDER BY c DESC LIMIT ?", (limit,))
        return _rows(cur)

    def daily_trend(self, days=7):
        cur = self.conn.execute(
            "SELECT substr(start_at,1,10) AS day, COUNT(*) AS c FROM reservations"
            " WHERE substr(start_at,1,10) >= date('now', ?) GROUP BY day ORDER BY day",
            (f"-{days} days",))
        return _rows(cur)


class CreditRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, user_id, reservation_id, delta, reason, balance_after):
        self.conn.execute(
            "INSERT INTO credit_logs(user_id,reservation_id,delta,reason,balance_after,created_at)"
            " VALUES(?,?,?,?,?,?)",
            (user_id, reservation_id, delta, reason, balance_after, now_str()))

    def list_by_user(self, user_id, limit=50):
        cur = self.conn.execute(
            "SELECT * FROM credit_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        return _rows(cur)

    def list_all(self, limit=100):
        cur = self.conn.execute(
            "SELECT c.*, u.name AS user_name FROM credit_logs c JOIN users u ON u.id = c.user_id"
            " ORDER BY c.id DESC LIMIT ?", (limit,))
        return _rows(cur)


class AuditRepository:
    def __init__(self, conn):
        self.conn = conn

    def write(self, actor_id, actor_name, action, target_type, target_id, detail=""):
        self.conn.execute(
            "INSERT INTO audit_logs(actor_id,actor_name,action,target_type,target_id,detail,created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (actor_id, actor_name, action, target_type, str(target_id), detail, now_str()))

    def list_all(self, limit=100):
        cur = self.conn.execute(
            "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        return _rows(cur)


class SessionRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, token, user_id, expires_at):
        self.conn.execute(
            "INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",
            (token, user_id, expires_at))

    def find(self, token):
        cur = self.conn.execute(
            "SELECT s.*, u.id AS uid, u.name, u.role, u.credit, u.username, u.status"
            " FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?", (token,))
        row = cur.fetchone()
        return dict(row) if row else None

    def delete(self, token):
        self.conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def purge_expired(self, now):
        self.conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))


class UnitOfWork:
    """事务边界：一次请求一个连接，成功提交、异常回滚。"""

    def __init__(self):
        self.conn = connect()
        self.users = UserRepository(self.conn)
        self.devices = DeviceRepository(self.conn)
        self.reservations = ReservationRepository(self.conn)
        self.credits = CreditRepository(self.conn)
        self.audits = AuditRepository(self.conn)
        self.sessions = SessionRepository(self.conn)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
