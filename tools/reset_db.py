"""重置演示数据库（删除后重新建表并写入种子数据）。

用途：保证自动化测试与演示的可重复性。服务运行中也可执行——每次请求独立建连，
文件被替换后下一次请求即生效。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))

import db  # noqa: E402


def main():
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
        print("已删除旧数据库:", db.DB_PATH)
    db.init_db()
    db.seed_if_empty()
    print("已重建数据库并写入种子数据")


if __name__ == "__main__":
    main()
