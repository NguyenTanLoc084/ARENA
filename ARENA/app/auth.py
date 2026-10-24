"""Trân: xác thực và hồ sơ. Không nhận role từ form đăng ký."""

import secrets, time
from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    g,
    flash,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
from .db import query, transaction, audit
from .common import require, clean, student, integer

bp = Blueprint("auth", __name__)


def load_user():
    g.user = query(
        "SELECT u.*,s.ign,s.full_name FROM users u LEFT JOIN students s ON s.id=u.student_id WHERE u.id=? AND u.active=1",
        (session.get("uid"),),
        one=True,
    )
    if not g.user:
        session.pop("uid", None)


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    return session["csrf"]


def csrf_guard():
    if request.method == "POST":
        sent = request.form.get("csrf") or request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(sent, session.get("csrf", "")) or not sent:
            abort(400, description="Phiên biểu mẫu đã hết hạn. Hãy tải lại trang.")


def password(value):
    require(8 <= len(value) <= 128, "Mật khẩu cần 8–128 ký tự.")
    return value


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("username", "").strip().lower()
        bucket = (request.remote_addr or "") + ":" + name
        with transaction() as db:
            limit = db.execute(
                "SELECT * FROM login_limits WHERE bucket=?", (bucket,)
            ).fetchone()
            if limit and limit["until"] > time.time() and limit["attempts"] >= 8:
                flash("Đã thử quá nhiều lần. Hãy thử lại sau 5 phút.", "error")
                return render_template("login.html"), 429
            user = db.execute(
                "SELECT * FROM users WHERE username=?", (name,)
            ).fetchone()
            valid = bool(
                user
                and user["active"]
                and check_password_hash(
                    user["password_hash"], request.form.get("password", "")
                )
            )
            if valid:
                db.execute("DELETE FROM login_limits WHERE bucket=?", (bucket,))
            else:
                attempts = (
                    limit["attempts"] if limit and limit["until"] > time.time() else 0
                ) + 1
                db.execute(
                    "INSERT OR REPLACE INTO login_limits VALUES(?,?,?)",
                    (bucket, attempts, time.time() + 300),
                )
        if valid:
            session.clear()
            session["uid"] = user["id"]
            csrf_token()
            flash("Đăng nhập thành công.", "success")
            return redirect(url_for("web.home"))
        flash(
            "Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản đã bị khóa.",
            "error",
        )
    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.home"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        name = clean(f.get("username"), "tên đăng nhập", 40).lower()
        require(
            name.isascii() and all(c.isalnum() or c in "._-" for c in name),
            "Tên đăng nhập chỉ gồm chữ Latin, số, dấu . _ -.",
        )
        pw = password(f.get("password", ""))
        require(pw == f.get("confirm"), "Hai mật khẩu chưa khớp.")
        with transaction() as db:
            code = clean(f.get("code"), "MSSV", 30)
            game = clean(f.get("game_id"), "Ingame ID", 64)
            require(
                not db.execute(
                    "SELECT 1 FROM students WHERE code=? OR game_id=?", (code, game)
                ).fetchone(),
                "MSSV hoặc Ingame ID đã có. Hãy dùng tài khoản đã được cấp hoặc liên hệ BTC.",
            )
            require(
                not db.execute(
                    "SELECT 1 FROM users WHERE username=?", (name,)
                ).fetchone(),
                "Tên đăng nhập đã được dùng.",
            )
            cid = integer(f.get("class_id"), "Lớp", 1)
            require(
                db.execute("SELECT 1 FROM classes WHERE id=?", (cid,)).fetchone(),
                "Lớp không hợp lệ.",
            )
            sid = db.execute(
                "INSERT INTO students(code,full_name,game_id,ign,class_id) VALUES(?,?,?,?,?)",
                (
                    code,
                    clean(f.get("full_name"), "họ tên"),
                    game,
                    clean(f.get("ign"), "tên trong game", 80),
                    cid,
                ),
            ).lastrowid
            uid = db.execute(
                "INSERT INTO users(username,password_hash,student_id,role) VALUES(?,?,?,'student')",
                (name, generate_password_hash(pw), sid),
            ).lastrowid
        session.clear()
        session["uid"] = uid
        flash("Tài khoản đã tạo. Bạn có thể thành lập đội.", "success")
        return redirect(url_for("team.mine"))
    return render_template("register.html", classes=query("SELECT * FROM classes"))


@bp.route("/profile", methods=["GET", "POST"])
def profile():
    sid = student()
    if request.method == "POST":
        with transaction() as db:
            old = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
            f = request.form
            game = clean(f.get("game_id"), "Ingame ID", 64)
            require(
                game == old["game_id"]
                or not db.execute(
                    "SELECT 1 FROM rosters WHERE student_id=? AND holding=1", (sid,)
                ).fetchone(),
                "Đã có hồ sơ giải giữ chỗ; chưa thể đổi Ingame ID.",
            )
            require(
                not db.execute(
                    "SELECT 1 FROM students WHERE game_id=? AND id<>?", (game, sid)
                ).fetchone(),
                "Ingame ID đã được dùng.",
            )
            db.execute(
                "UPDATE students SET full_name=?,ign=?,game_id=? WHERE id=?",
                (
                    clean(f.get("full_name"), "họ tên"),
                    clean(f.get("ign"), "tên trong game", 80),
                    game,
                    sid,
                ),
            )
            audit(db, g.user, "profile.update", sid)
        flash("Đã lưu hồ sơ.", "success")
        return redirect(url_for("auth.profile"))
    return render_template(
        "profile.html",
        profile=query(
            "SELECT s.*,c.name class_name FROM students s JOIN classes c ON c.id=s.class_id WHERE s.id=?",
            (sid,),
            one=True,
        ),
    )


@bp.post("/password")
def change_password():
    if not g.user:
        abort(401)
    require(
        check_password_hash(g.user["password_hash"], request.form.get("old", "")),
        "Mật khẩu hiện tại không đúng.",
    )
    pw = password(request.form.get("new", ""))
    require(pw == request.form.get("confirm"), "Hai mật khẩu mới chưa khớp.")
    with transaction() as db:
        db.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (generate_password_hash(pw), g.user["id"]),
        )
        audit(db, g.user, "password.change", g.user["id"])
    session.clear()
    flash("Đã đổi mật khẩu. Vui lòng đăng nhập lại.", "success")
    return redirect(url_for("auth.login"))


@bp.get("/password")
def password_form():
    if not g.user:
        abort(401)
    return render_template("password.html")
