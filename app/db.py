"""数据访问基础设施：SQLite 连接、建表 DDL、初始化与种子数据。"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "labhub.db")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('STUDENT','TEACHER','ADMIN')),
    dept          TEXT DEFAULT '',
    credit        INTEGER NOT NULL DEFAULT 100,
    status        TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','BANNED')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    code              TEXT NOT NULL UNIQUE,
    name              TEXT NOT NULL,
    category          TEXT NOT NULL,
    location          TEXT NOT NULL,
    hourly_price      REAL NOT NULL DEFAULT 0,
    requires_approval INTEGER NOT NULL DEFAULT 0,
    max_hours         INTEGER NOT NULL DEFAULT 4,
    open_hour         INTEGER NOT NULL DEFAULT 8,
    close_hour        INTEGER NOT NULL DEFAULT 22,
    status            TEXT NOT NULL DEFAULT 'AVAILABLE'
                      CHECK (status IN ('AVAILABLE','MAINTENANCE','RETIRED')),
    description       TEXT DEFAULT '',
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reservations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    device_id     INTEGER NOT NULL REFERENCES devices(id),
    start_at      TEXT NOT NULL,
    end_at        TEXT NOT NULL,
    purpose       TEXT NOT NULL DEFAULT '',
    headcount     INTEGER NOT NULL DEFAULT 1,
    status        TEXT NOT NULL DEFAULT 'PENDING'
                  CHECK (status IN ('PENDING','APPROVED','REJECTED','CHECKED_IN',
                                    'COMPLETED','CANCELLED','NO_SHOW')),
    approver_id   INTEGER REFERENCES users(id),
    approve_remark TEXT DEFAULT '',
    credit_delta  INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    checked_in_at TEXT,
    checked_out_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_res_device_time ON reservations(device_id, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_res_user ON reservations(user_id, start_at);

CREATE TABLE IF NOT EXISTS credit_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    reservation_id INTEGER,
    delta          INTEGER NOT NULL,
    reason         TEXT NOT NULL,
    balance_after  INTEGER NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id    INTEGER,
    actor_name  TEXT,
    action      TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id   TEXT,
    detail      TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL
);
"""


def now_str(dt=None):
    return (dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return digest.hex(), salt


def connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = connect()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- 种子数据
USERS = [
    ("admin",    "admin123", "王敏",   "ADMIN",   "设备与实验室管理处", 100),
    ("teacher1", "123456",   "李国强", "TEACHER", "机械工程学院",       100),
    ("stu001",   "123456",   "陈晓",   "STUDENT", "机械工程学院",       100),
    ("stu002",   "123456",   "刘洋",   "STUDENT", "电子信息学院",        55),
    ("stu003",   "123456",   "赵一鸣", "STUDENT", "材料科学学院",        88),
]

DEVICES = [
    ("DEV-3DP-01", "高精度光固化3D打印机", "增材制造", "A栋302", 30.0, 0, 4, 8, 22,
     "AVAILABLE", "成型精度 25μm，支持树脂材料，需自备或现场购买耗材。"),
    ("DEV-GPU-02", "GPU 计算服务器（8×A100）", "高性能计算", "A栋405机房", 50.0, 1, 8, 0, 24,
     "AVAILABLE", "面向深度学习训练任务，需导师审批，单次不超过 8 小时。"),
    ("DEV-OSC-03", "四通道数字示波器", "电子测量", "B栋201", 10.0, 0, 4, 8, 22,
     "AVAILABLE", "带宽 500MHz，配套差分探头 4 套。"),
    ("DEV-SPC-04", "紫外可见光谱分析仪", "材料分析", "C栋103", 40.0, 1, 2, 9, 18,
     "AVAILABLE", "需持证操作，单次不超过 2 小时，须管理员审批。"),
    ("DEV-MIC-05", "倒置荧光显微镜", "生物成像", "C栋205", 20.0, 0, 4, 8, 22,
     "AVAILABLE", "含 4 组滤光片，可连接 CCD 相机采集图像。"),
    ("DEV-LSR-06", "CO2 激光切割机", "减材加工", "D栋101", 35.0, 1, 3, 9, 20,
     "MAINTENANCE", "激光管更换中，预计 3 个工作日后恢复。"),
    ("DEV-ROB-07", "六轴协作机械臂", "机器人", "A栋108", 45.0, 1, 4, 8, 22,
     "AVAILABLE", "负载 5kg，需完成安全培训后使用。"),
    ("DEV-VR-08", "VR 交互开发套件", "虚拟现实", "E栋402", 15.0, 0, 4, 0, 24,
     "AVAILABLE", "位于 24 小时开放创客空间，可自助取用，含头显 2 台与手柄 4 支。"),
]


def seed_if_empty():
    conn = connect()
    cur = conn.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] > 0:
        conn.close()
        return False

    now = datetime.now()
    user_ids = {}
    for username, pwd, name, role, dept, credit in USERS:
        h, salt = hash_password(pwd)
        cur = conn.execute(
            "INSERT INTO users(username,password_hash,salt,name,role,dept,credit,status,created_at)"
            " VALUES(?,?,?,?,?,?,?, 'ACTIVE', ?)",
            (username, h, salt, name, role, dept, credit, now_str(now)),
        )
        user_ids[username] = cur.lastrowid

    device_ids = {}
    for d in DEVICES:
        cur = conn.execute(
            "INSERT INTO devices(code,name,category,location,hourly_price,requires_approval,"
            "max_hours,open_hour,close_hour,status,description,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (*d, now_str(now)),
        )
        device_ids[d[0]] = cur.lastrowid

    def day(offset):
        return (now + timedelta(days=offset)).strftime("%Y-%m-%d")

    rows = [
        # user, device, 开始, 结束, 用途, 人数, 状态, 审批人, 备注, 信用变化
        ("stu001", "DEV-3DP-01", f"{day(0)} 14:00", f"{day(0)} 16:00", "毕业设计外壳样件打印", 1,
         "APPROVED", "teacher1", "已核对耗材余量", 0),
        ("stu003", "DEV-OSC-03", f"{day(0)} 09:00", f"{day(0)} 11:00", "电路实验调试", 2,
         "CHECKED_IN", None, "", 0),
        ("stu001", "DEV-MIC-05", f"{day(1)} 10:00", f"{day(1)} 12:00", "细胞切片观察", 1,
         "PENDING", None, "", 0),
        ("stu003", "DEV-GPU-02", f"{day(1)} 13:00", f"{day(1)} 19:00", "模型训练实验", 1,
         "PENDING", None, "", 0),
        ("stu002", "DEV-VR-08", f"{day(-2)} 15:00", f"{day(-2)} 17:00", "交互原型测试", 2,
         "NO_SHOW", None, "超时 30 分钟未签到", -15),
        ("stu002", "DEV-OSC-03", f"{day(-4)} 10:00", f"{day(-4)} 12:00", "课程实验", 1,
         "COMPLETED", None, "", 2),
        ("stu001", "DEV-ROB-07", f"{day(-5)} 09:00", f"{day(-5)} 12:00", "抓取算法联调", 3,
         "COMPLETED", "teacher1", "安全培训已确认", 2),
        ("stu003", "DEV-SPC-04", f"{day(2)} 09:00", f"{day(2)} 11:00", "薄膜透过率测试", 1,
         "PENDING", None, "", 0),
    ]
    for u, d, s, e, purpose, head, status, approver, remark, delta in rows:
        created = s.split(" ")[0] + " 08:30:00"
        cur = conn.execute(
            "INSERT INTO reservations(user_id,device_id,start_at,end_at,purpose,headcount,status,"
            "approver_id,approve_remark,credit_delta,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (user_ids[u], device_ids[d], s, e, purpose, head, status,
             user_ids.get(approver) if approver else None, remark, delta, created),
        )
        if delta:
            conn.execute(
                "INSERT INTO credit_logs(user_id,reservation_id,delta,reason,balance_after,created_at)"
                " VALUES(?,?,?,?,?,?)",
                (user_ids[u], cur.lastrowid, delta,
                 "爽约扣分" if delta < 0 else "按时完成加分", 100 + delta, created),
            )

    conn.execute(
        "INSERT INTO audit_logs(actor_id,actor_name,action,target_type,target_id,detail,created_at)"
        " VALUES(?,?,?,?,?,?,?)",
        (user_ids["admin"], "王敏", "SYSTEM_INIT", "system", "-", "系统初始化并导入设备基础数据", now_str(now)),
    )
    conn.commit()
    conn.close()
    return True


if __name__ == "__main__":
    init_db()
    created = seed_if_empty()
    print("数据库初始化完成:", DB_PATH, "| 种子数据写入:", created)
