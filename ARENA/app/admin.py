"""Lộc: tài khoản/danh mục; Nghi: nhật ký và kiểm tra vận hành."""

from flask import (
    Blueprint,
    render_template,
    request,
    g,
    flash,
    redirect,
    url_for,
    abort,
)
from .common import permission, require, integer, clean
from .db import query, transaction, audit

bp = Blueprint("admin", __name__)


@bp.get("/admin")
def index():
    permission("admin")
    return render_template(
        "admin.html",
        users=query(
            "SELECT u.id,u.username,u.role,u.active,s.full_name FROM users u LEFT JOIN students s ON s.id=u.student_id ORDER BY u.id"
        ),
        heroes=query("SELECT * FROM heroes ORDER BY name"),
        classes=query(
            "SELECT c.*,k.name college FROM classes c JOIN colleges k ON k.id=c.college_id"
        ),
        colleges=query("SELECT * FROM colleges"),
    )


@bp.post("/admin/users/<int:uid>")
def user(uid):
    permission("admin")
    active = int(request.form.get("active") == "1")
    role = request.form.get("role")
    require(
        role in ("admin", "organizer", "referee", "student"), "Vai trò không hợp lệ."
    )
    with transaction() as db:
        u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        require(u, "Không có tài khoản.")
        require(
            uid != g.user["id"] or (active and role == "admin"),
            "Không thể tự khóa hoặc tự hạ quyền quản trị.",
        )
        if role == "student":
            require(u["student_id"] is not None, "Tài khoản không có hồ sơ sinh viên.")
        if u["role"] == "student" and role != "student":
            require(
                not db.execute(
                    "SELECT 1 FROM memberships WHERE student_id=? AND status='accepted'",
                    (u["student_id"],),
                ).fetchone(),
                "Tài khoản đang là thành viên đội, không chuyển sang nhân sự giải.",
            )
        if u["role"] == "admin" and (not active or role != "admin"):
            require(
                db.execute(
                    "SELECT COUNT(*) FROM users WHERE role='admin' AND active=1"
                ).fetchone()[0]
                > 1,
                "Phải còn ít nhất một quản trị viên hoạt động.",
            )
        if not active or role not in ("organizer", "referee"):
            require(not db.execute("SELECT 1 FROM matches m JOIN events e ON e.id=m.event_id WHERE m.referee_id=? AND e.status<>'finished' AND m.state IN ('scheduled','live')", (uid,)).fetchone(), "Tài khoản còn được phân công trận chưa kết thúc. Hãy đổi trọng tài trước.")
        db.execute("UPDATE users SET active=?,role=? WHERE id=?", (active, role, uid))
        audit(db, g.user, "user.update", uid, f"{role}:{active}")
    flash("Đã cập nhật tài khoản.", "success")
    return redirect(url_for("admin.index"))


@bp.post("/admin/catalog")
def catalog():
    permission("admin")
    kind = request.form.get("kind")
    name = clean(request.form.get("name"), "tên danh mục", 100)
    with transaction() as db:
        if kind == "hero":
            db.execute("INSERT INTO heroes(name) VALUES(?)", (name,))
        elif kind == "college":
            db.execute("INSERT INTO colleges(name) VALUES(?)", (name,))
        elif kind == "class":
            cid = integer(request.form.get("college_id"), "Khoa", 1)
            require(
                db.execute("SELECT 1 FROM colleges WHERE id=?", (cid,)).fetchone(),
                "Khoa không hợp lệ.",
            )
            db.execute("INSERT INTO classes(name,college_id) VALUES(?,?)", (name, cid))
        else:
            abort(400)
        audit(db, g.user, "catalog.create", kind, name)
    flash("Đã thêm danh mục.", "success")
    return redirect(url_for("admin.index"))


@bp.post("/admin/heroes/<int:hid>")
def hero(hid):
    permission("admin")
    with transaction() as db:
        db.execute("UPDATE heroes SET active=1-active WHERE id=?", (hid,))
        audit(db, g.user, "hero.toggle", hid)
    flash("Đã đổi trạng thái tướng.", "success")
    return redirect(url_for("admin.index"))


@bp.get("/audit")
def logs():
    permission("audit")
    page = integer(request.args.get("page", "1"), "Trang", 1, 100000)
    return render_template(
        "audit.html",
        logs=query(
            "SELECT a.*,u.username FROM audit a JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 50 OFFSET ?",
            ((page - 1) * 50,),
        ),
        page=page,
    )


@bp.route("/notifications", methods=["GET", "POST"])
def notifications():
    if not g.user:
        abort(401)
    if request.method == "POST":
        with transaction() as db:
            db.execute(
                "UPDATE notifications SET read=1 WHERE user_id=?", (g.user["id"],)
            )
        return redirect(url_for("admin.notifications"))
    return render_template(
        "notifications.html",
        items=query(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100",
            (g.user["id"],),
        ),
    )
