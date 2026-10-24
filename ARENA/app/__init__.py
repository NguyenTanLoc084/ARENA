import os, secrets, sqlite3
from pathlib import Path
from flask import Flask, render_template, g, Blueprint
from markupsafe import Markup
from .db import get_db, query, close_db
from .common import BusinessError, can, display_time, local_input

LABELS = {
    "draft": "Bản nháp",
    "open": "Mở đăng ký",
    "locked": "Đã khóa đăng ký",
    "live": "Đang thi đấu",
    "finished": "Đã hoàn tất",
    "scheduled": "Sắp diễn ra",
    "bye": "Miễn vòng",
    "pending": "Chờ duyệt",
    "approved": "Đã duyệt",
    "rejected": "Từ chối",
    "withdrawn": "Đã rút",
    "accepted": "Đã tham gia",
    "invited": "Chờ phản hồi",
    "knockout": "Loại trực tiếp",
    "roundrobin": "Vòng tròn",
    "admin": "Quản trị",
    "organizer": "Ban tổ chức",
    "referee": "Trọng tài",
    "student": "Sinh viên",
}


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_path = Path(app.instance_path) / "secret.key"
    if not secret_path.exists():
        try:
            with secret_path.open("x") as f:
                f.write(secrets.token_hex(32))
            secret_path.chmod(0o600)
        except FileExistsError:
            pass
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secret_path.read_text(),
        DATABASE=str(Path(app.instance_path) / "arena.sqlite3"),
        MAX_CONTENT_LENGTH=512 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
    )
    if config:
        app.config.update(config)
    from . import auth, team, tournament, matches, reports, admin

    for bp in (auth.bp, team.bp, tournament.bp, matches.bp, reports.bp, admin.bp):
        app.register_blueprint(bp)
    app.teardown_appcontext(close_db)
    app.before_request(auth.load_user)
    app.before_request(auth.csrf_guard)

    @app.context_processor
    def context():
        def csrf_field():
            return Markup(
                '<input type="hidden" name="csrf" value="' + auth.csrf_token() + '">'
            )

        return dict(
            can=can,
            labels=LABELS,
            csrf_field=csrf_field,
            csrf_token=auth.csrf_token,
            unread=query(
                "SELECT COUNT(*) n FROM notifications WHERE user_id=? AND read=0",
                (g.user["id"],),
                one=True,
            )["n"]
            if g.user
            else 0,
        )

    app.jinja_env.filters["timevn"] = display_time
    app.jinja_env.filters["localinput"] = local_input
    app.jinja_env.filters["money"] = lambda n: f"{int(n):,}".replace(",", ".") + " ₫"
    web = Blueprint("web", __name__)

    @web.get("/")
    def home():
        events = query(
            "SELECT e.*,(SELECT COUNT(*) FROM entries WHERE event_id=e.id AND status='approved') teams FROM events e ORDER BY e.id DESC"
        )
        live = query("""SELECT m.*,a.name a_name,b.name b_name,e.name event_name,
        (SELECT COUNT(*) FROM games WHERE match_id=m.id AND winner_id=m.team_a) score_a,
        (SELECT COUNT(*) FROM games WHERE match_id=m.id AND winner_id=m.team_b) score_b
        FROM matches m JOIN events e ON e.id=m.event_id LEFT JOIN teams a ON a.id=m.team_a LEFT JOIN teams b ON b.id=m.team_b
        WHERE m.state='live' ORDER BY m.id LIMIT 3""")
        totals = {
            t: query("SELECT COUNT(*) n FROM " + t, one=True)["n"]
            for t in ["teams", "events", "matches", "students"]
        }
        tasks = []
        if can("event"):
            for row in query("SELECT e.id,e.name,COUNT(*) n FROM entries x JOIN events e ON e.id=x.event_id WHERE x.status='pending' GROUP BY e.id ORDER BY e.id DESC LIMIT 3"):
                tasks.append(dict(title=row["name"], detail=f'{row["n"]} hồ sơ cần duyệt', href=f'/events/{row["id"]}#teams'))
        if g.user and g.user["role"] == "referee":
            for row in query("SELECT id,state FROM matches WHERE referee_id=? AND state IN ('live','scheduled') ORDER BY CASE state WHEN 'live' THEN 0 ELSE 1 END,starts LIMIT 3", (g.user["id"],)):
                tasks.append(dict(title=f'Trận #{row["id"]}',detail=LABELS[row["state"]],href=f'/matches/{row["id"]}'))
        if g.user and g.user["role"] == "student":
            tasks.append(dict(title="Đội hình của bạn",detail="Lời mời, thành viên và hồ sơ đăng ký",href="/my-team"))
        return render_template("home.html", events=events, live=live, totals=totals, tasks=tasks)

    app.register_blueprint(web)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(BusinessError)
    def business(error):
        return render_template("error.html", code=400, message=str(error)), 400

    @app.errorhandler(sqlite3.IntegrityError)
    def integrity(error):
        app.logger.info("Constraint violation: %s", error)
        return render_template(
            "error.html",
            code=409,
            message="Dữ liệu trùng hoặc liên kết không hợp lệ. Chưa có thay đổi nào được lưu. Hãy tải lại và kiểm tra.",
        ), 409

    for code, message in [
        (400, "Biểu mẫu không hợp lệ hoặc phiên đã hết hạn."),
        (401, "Bạn cần đăng nhập để sử dụng chức năng này."),
        (403, "Tài khoản không có quyền thực hiện thao tác này."),
        (404, "Không tìm thấy nội dung bạn yêu cầu."),
        (413, "Dữ liệu gửi lên quá lớn."),
        (
            500,
            "Có lỗi hệ thống. Thao tác chưa được xác nhận; hãy kiểm tra lại trước khi thử tiếp.",
        ),
    ]:

        def handler(error, code=code, message=message):
            return render_template("error.html", code=code, message=message), code

        app.register_error_handler(code, handler)
    with app.app_context():
        get_db().executescript((Path(__file__).parent / "schema.sql").read_text())
    return app
