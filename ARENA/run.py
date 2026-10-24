"""Python 3.11 entrypoint. Local educational demo; no debug mode by default."""

import argparse, sqlite3
from pathlib import Path
from app import create_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARENA - Quản lý giải đấu Liên Quân")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Nạp dữ liệu demo nếu database chưa có tài khoản",
    )
    parser.add_argument(
        "--init-demo", action="store_true", help="Chỉ khởi tạo demo rồi thoát"
    )
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--backup", metavar="FILE", help="Sao lưu SQLite an toàn ra file mới rồi thoát"
    )
    parser.add_argument(
        "--init-admin",
        action="store_true",
        help="Khởi tạo quản trị viên cho database trống (không nạp demo)",
    )
    args = parser.parse_args()
    app = create_app()
    if args.init_admin:
        if args.demo or args.init_demo or args.backup:
            parser.error(
                "--init-admin không kết hợp với --demo, --init-demo hoặc --backup."
            )
        from getpass import getpass
        from werkzeug.security import generate_password_hash
        from app.db import transaction
        from app.seed import PERMISSIONS

        with app.app_context(), transaction() as db:
            if db.execute("SELECT 1 FROM users").fetchone():
                parser.error("Database đã có tài khoản; không ghi đè.")
            name = input("Tên đăng nhập quản trị: ").strip().lower()
            if (
                not name
                or len(name) > 40
                or not name.isascii()
                or not all(c.isalnum() or c in "._-" for c in name)
            ):
                parser.error("Tên đăng nhập không hợp lệ.")
            pw = getpass("Mật khẩu (8–128 ký tự): ")
            if not 8 <= len(pw) <= 128 or pw != getpass("Nhập lại mật khẩu: "):
                parser.error("Mật khẩu không hợp lệ hoặc chưa khớp.")
            for role, permissions in PERMISSIONS.items():
                for permission in permissions:
                    db.execute(
                        "INSERT OR IGNORE INTO role_permissions VALUES(?,?)",
                        (role, permission),
                    )
            db.execute(
                "INSERT INTO users(username,password_hash,role) VALUES(?,?,'admin')",
                (name, generate_password_hash(pw)),
            )
        print(
            "Đã tạo quản trị. Chạy python run.py, đăng nhập và thêm khoa, lớp, tướng trong Quản trị."
        )
        raise SystemExit
    if args.backup:
        target = Path(args.backup)
        if target.exists():
            parser.error("File sao lưu đã tồn tại; dùng tên mới để không ghi đè.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with (
            sqlite3.connect(app.config["DATABASE"]) as source,
            sqlite3.connect(target) as destination,
        ):
            source.backup(destination)
        print("Đã sao lưu:", target)
        raise SystemExit
    if args.demo or args.init_demo:
        from app.seed import seed_demo

        with app.app_context():
            created = seed_demo()
        print(
            "Đã tạo dữ liệu DEMO."
            if created
            else "Database đã có dữ liệu; giữ nguyên, không nạp lại."
        )
    if not args.init_demo:
        print(f"ARENA: http://{args.host}:{args.port} | Dừng bằng Ctrl+C")
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
