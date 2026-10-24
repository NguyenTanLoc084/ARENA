"""Hợp đồng dùng chung: lỗi nghiệp vụ và kiểm tra quyền ở máy chủ."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import g, abort
from .db import query


class BusinessError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise BusinessError(message)


def integer(value, name, minimum=0, maximum=10**9):
    try:
        n = int(str(value))
    except (ValueError, TypeError):
        raise BusinessError(f"{name} phải là số nguyên.") from None
    require(minimum <= n <= maximum, f"{name} phải từ {minimum} đến {maximum}.")
    return n


def clean(value, name, maxlen=120):
    value = str(value or "").strip()
    require(bool(value), f"Vui lòng nhập {name}.")
    require(len(value) <= maxlen, f"{name} tối đa {maxlen} ký tự.")
    return value


def can(permission):
    return bool(
        g.user
        and query(
            "SELECT 1 FROM role_permissions WHERE role=? AND permission=?",
            (g.user["role"], permission),
            one=True,
        )
    )


def permission(name):
    if not g.user:
        abort(401)
    if not can(name):
        abort(403)


def student():
    permission("team")
    require(g.user["student_id"] is not None, "Tài khoản chưa có hồ sơ sinh viên.")
    return g.user["student_id"]


def captain(db, team_id, user):
    row = db.execute(
        "SELECT * FROM teams WHERE id=? AND active=1", (team_id,)
    ).fetchone()
    require(row is not None, "Không tìm thấy đội đang hoạt động.")
    if user["role"] != "student" or row["captain_id"] != user["student_id"]:
        abort(403)
    return row


def local_to_utc(value):
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(
            tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")
        )
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    except (ValueError, TypeError):
        raise BusinessError("Ngày giờ không hợp lệ.") from None


def display_time(value):
    if not value:
        return "Chưa xếp giờ"
    dt = datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y · %H:%M")


def local_input(value):
    if not value:
        return ""
    dt = datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%dT%H:%M")
