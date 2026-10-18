"""Trân: đội tuyển, lời mời, đội hình đăng ký và duyệt hồ sơ."""

from flask import (
    Blueprint,
    render_template,
    request,
    g,
    redirect,
    url_for,
    flash,
    abort,
)
from .db import query, transaction, audit, notify, now
from .common import student, permission, require, integer, clean, captain

bp = Blueprint("team", __name__)


def team_locked(db, team_id):
    return db.execute(
        "SELECT 1 FROM entries e JOIN events v ON v.id=e.event_id WHERE e.team_id=? AND e.status IN('pending','approved') AND v.status<>'finished'",
        (team_id,),
    ).fetchone()


@bp.route("/my-team")
def mine():
    sid = student()
    team = query(
        "SELECT t.* FROM teams t JOIN memberships m ON m.team_id=t.id WHERE m.student_id=? AND m.status='accepted'",
        (sid,),
        one=True,
    )
    members = (
        query(
            "SELECT s.*,m.status,m.position,m.id membership_id FROM memberships m JOIN students s ON s.id=m.student_id WHERE m.team_id=? AND m.status IN('accepted','invited') ORDER BY m.status,s.id",
            (team["id"],),
        )
        if team
        else []
    )
    invites = query(
        "SELECT m.id,t.name FROM memberships m JOIN teams t ON t.id=m.team_id WHERE m.student_id=? AND m.status='invited'",
        (sid,),
    )
    entries = (
        query(
            "SELECT e.*,v.name event_name FROM entries e JOIN events v ON v.id=e.event_id WHERE e.team_id=? ORDER BY e.id DESC",
            (team["id"],),
        )
        if team
        else []
    )
    return render_template(
        "team.html", team=team, members=members, invites=invites, entries=entries
    )


@bp.post("/teams")
def create():
    sid = student()
    name = clean(request.form.get("name"), "tên đội", 80)
    tag = clean(request.form.get("tag"), "tên viết tắt", 6).upper()
    with transaction() as db:
        require(
            not db.execute(
                "SELECT 1 FROM memberships WHERE student_id=? AND status='accepted'",
                (sid,),
            ).fetchone(),
            "Bạn đã thuộc một đội.",
        )
        require(
            not db.execute("SELECT 1 FROM teams WHERE name=?", (name,)).fetchone(),
            "Tên đội đã tồn tại.",
        )
        tid = db.execute(
            "INSERT INTO teams(name,tag,captain_id) VALUES(?,?,?)", (name, tag, sid)
        ).lastrowid
        db.execute(
            "INSERT INTO memberships(team_id,student_id,status) VALUES(?,?,'accepted')",
            (tid, sid),
        )
        audit(db, g.user, "team.create", tid)
    flash("Đã tạo đội. Hãy mời đủ 5 thành viên để đăng ký giải.", "success")
    return redirect(url_for("team.mine"))


@bp.post("/teams/<int:tid>/invite")
def invite(tid):
    student()
    with transaction() as db:
        captain(db, tid, g.user)
        require(
            not team_locked(db, tid),
            "Đội hình đang có hồ sơ giải chưa kết thúc. Chưa thể đổi thành viên.",
        )
        member = db.execute(
            "SELECT * FROM students WHERE code=?",
            (request.form.get("code", "").strip(),),
        ).fetchone()
        require(member, "Không tìm thấy MSSV. Người chơi cần đăng ký tài khoản trước.")
        require(
            not db.execute(
                "SELECT 1 FROM memberships WHERE student_id=? AND status='accepted'",
                (member["id"],),
            ).fetchone(),
            "Sinh viên đã thuộc một đội.",
        )
        db.execute(
            "INSERT INTO memberships(team_id,student_id,status) VALUES(?,?,'invited') ON CONFLICT(team_id,student_id) DO UPDATE SET status='invited'",
            (tid, member["id"]),
        )
        u = db.execute(
            "SELECT id FROM users WHERE student_id=?", (member["id"],)
        ).fetchone()
        if u:
            notify(
                db,
                u["id"],
                "Bạn được mời tham gia đội. Mở mục Đội của tôi để phản hồi.",
            )
        audit(db, g.user, "team.invite", tid, str(member["id"]))
    flash("Đã gửi lời mời.", "success")
    return redirect(url_for("team.mine"))


@bp.post("/invites/<int:mid>")
def respond(mid):
    sid = student()
    accept = request.form.get("action") == "accept"
    with transaction() as db:
        m = db.execute(
            "SELECT * FROM memberships WHERE id=? AND student_id=? AND status='invited'",
            (mid, sid),
        ).fetchone()
        require(m, "Lời mời không tồn tại hoặc đã được xử lý.")
        require(
            not team_locked(db, m["team_id"]),
            "Đội đang khóa đội hình theo giải. Hãy liên hệ đội trưởng.",
        )
        if accept:
            require(
                not db.execute(
                    "SELECT 1 FROM memberships WHERE student_id=? AND status='accepted'",
                    (sid,),
                ).fetchone(),
                "Bạn đã thuộc một đội khác.",
            )
        db.execute(
            "UPDATE memberships SET status=? WHERE id=?",
            ("accepted" if accept else "declined", mid),
        )
        audit(db, g.user, "invite.respond", mid)
    flash("Đã phản hồi lời mời.", "success")
    return redirect(url_for("team.mine"))


@bp.post("/teams/<int:tid>/member")
def change_member(tid):
    sid = student()
    target = integer(request.form.get("student_id"), "Thành viên", 1)
    action = request.form.get("action")
    with transaction() as db:
        t = db.execute("SELECT * FROM teams WHERE id=?", (tid,)).fetchone()
        require(t, "Không tìm thấy đội.")
        if target != sid or action == "captain":
            captain(db, tid, g.user)
        require(
            not team_locked(db, tid),
            "Đội có hồ sơ giải đang hoạt động; không được thay nhân sự.",
        )
        require(
            db.execute(
                "SELECT 1 FROM memberships WHERE team_id=? AND student_id=? AND status='accepted'",
                (tid, target),
            ).fetchone(),
            "Thành viên không hợp lệ.",
        )
        if action == "captain":
            db.execute("UPDATE teams SET captain_id=? WHERE id=?", (target, tid))
        else:
            require(
                target != t["captain_id"],
                "Đội trưởng cần chuyển quyền trước khi rời đội.",
            )
            db.execute(
                "UPDATE memberships SET status='left' WHERE team_id=? AND student_id=?",
                (tid, target),
            )
        audit(db, g.user, "team.member", tid, f"{action}:{target}")
    flash("Đã cập nhật thành viên.", "success")
    return redirect(url_for("team.mine"))


def submit_entry(db, user, eid, tid, starters, reserves):
    captain(db, tid, user)
    e = db.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    require(e, "Không tìm thấy giải.")
    require(
        e["status"] == "open" and e["opens"] <= now() <= e["closes"],
        "Giải không trong thời gian nhận đăng ký.",
    )
    require(
        len(starters) == 5 and len(reserves) <= e["reserve_max"],
        "Cần đúng 5 người đánh chính và không quá số dự bị cho phép.",
    )
    ids = starters + reserves
    require(len(set(ids)) == len(ids), "Mỗi thành viên chỉ xuất hiện một lần.")
    for sid in ids:
        require(
            db.execute(
                "SELECT 1 FROM memberships WHERE team_id=? AND student_id=? AND status='accepted'",
                (tid, sid),
            ).fetchone(),
            "Đội hình có thành viên chưa chấp nhận hoặc không thuộc đội.",
        )
    old = db.execute(
        "SELECT * FROM entries WHERE event_id=? AND team_id=?", (eid, tid)
    ).fetchone()
    require(
        not old or old["status"] in ("withdrawn", "rejected"),
        "Đội đã nộp hồ sơ cho giải này.",
    )
    require(
        not db.execute("SELECT 1 FROM matches WHERE event_id=?", (eid,)).fetchone(),
        "Giải đã xếp lịch, không thể nộp lại.",
    )
    for sid in ids:
        require(
            not db.execute(
                "SELECT 1 FROM rosters WHERE event_id=? AND student_id=? AND holding=1",
                (eid, sid),
            ).fetchone(),
            "Một thành viên đã đăng ký cho đội khác trong giải.",
        )
    if old:
        entry = old["id"]
        db.execute("DELETE FROM rosters WHERE entry_id=?", (entry,))
        db.execute(
            "UPDATE entries SET status='pending',reason='',reviewer_id=NULL,created=? WHERE id=?",
            (now(), entry),
        )
    else:
        entry = db.execute(
            "INSERT INTO entries(event_id,team_id,status,created) VALUES(?,?,'pending',?)",
            (eid, tid, now()),
        ).lastrowid
    for sid in ids:
        db.execute(
            "INSERT INTO rosters(entry_id,event_id,student_id,starter,holding) VALUES(?,?,?,?,1)",
            (entry, eid, sid, int(sid in starters)),
        )
    audit(db, user, "entry.submit", entry, ",".join(map(str, ids)))
    return entry


@bp.route("/events/<int:eid>/register", methods=["GET", "POST"])
def enter(eid):
    sid = student()
    t = query("SELECT * FROM teams WHERE captain_id=? AND active=1", (sid,), one=True)
    require(t, "Chỉ đội trưởng có thể đăng ký giải.")
    if request.method == "POST":
        starters = [
            integer(v, "Thành viên", 1) for v in request.form.getlist("starters")
        ]
        reserves = [integer(v, "Dự bị", 1) for v in request.form.getlist("reserves")]
        with transaction() as db:
            submit_entry(db, g.user, eid, t["id"], starters, reserves)
        flash("Hồ sơ đã gửi đến BTC.", "success")
        return redirect(url_for("team.mine"))
    e = query("SELECT * FROM events WHERE id=?", (eid,), one=True)
    if not e:
        abort(404)
    return render_template(
        "entry_form.html",
        event=e,
        team=t,
        members=query(
            "SELECT s.* FROM students s JOIN memberships m ON m.student_id=s.id WHERE m.team_id=? AND m.status='accepted'",
            (t["id"],),
        ),
    )


@bp.post("/entries/<int:entry_id>/withdraw")
def withdraw(entry_id):
    student()
    with transaction() as db:
        e = db.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
        require(e, "Không tìm thấy hồ sơ.")
        captain(db, e["team_id"], g.user)
        require(e["status"] in ("pending", "approved"), "Không thể rút trạng thái này.")
        require(
            not db.execute(
                "SELECT 1 FROM matches WHERE event_id=?", (e["event_id"],)
            ).fetchone(),
            "Đã xếp lịch; không thể rút hồ sơ.",
        )
        db.execute("UPDATE entries SET status='withdrawn' WHERE id=?", (entry_id,))
        db.execute("UPDATE rosters SET holding=0 WHERE entry_id=?", (entry_id,))
        audit(db, g.user, "entry.withdraw", entry_id)
    flash("Đã rút hồ sơ.", "success")
    return redirect(url_for("team.mine"))


@bp.post("/entries/<int:entry_id>/review")
def review(entry_id):
    permission("event")
    decision = request.form.get("decision")
    require(decision in ("approved", "rejected"), "Quyết định không hợp lệ.")
    with transaction() as db:
        e = db.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
        require(e and e["status"] == "pending", "Hồ sơ không còn chờ duyệt.")
        ev = db.execute("SELECT * FROM events WHERE id=?", (e["event_id"],)).fetchone()
        require(ev["status"] in ("open", "locked"), "Giải không còn cho phép duyệt.")
        require(
            not db.execute(
                "SELECT 1 FROM matches WHERE event_id=?", (e["event_id"],)
            ).fetchone(),
            "Đã tạo lịch.",
        )
        if decision == "approved":
            roster = db.execute(
                "SELECT * FROM rosters WHERE entry_id=?", (entry_id,)
            ).fetchall()
            require(
                sum(r["starter"] for r in roster) == 5
                and len(roster) - 5 <= ev["reserve_max"],
                "Đội hình không hợp lệ.",
            )
            for r in roster:
                require(
                    db.execute(
                        "SELECT 1 FROM memberships WHERE team_id=? AND student_id=? AND status='accepted'",
                        (e["team_id"], r["student_id"]),
                    ).fetchone(),
                    "Thành viên không còn thuộc đội.",
                )
        reason = (
            clean(request.form.get("reason"), "lý do từ chối", 300)
            if decision == "rejected"
            else ""
        )
        db.execute(
            "UPDATE entries SET status=?,reason=?,reviewer_id=? WHERE id=?",
            (decision, reason, g.user["id"], entry_id),
        )
        db.execute(
            "UPDATE rosters SET holding=? WHERE entry_id=?",
            (int(decision == "approved"), entry_id),
        )
        u = db.execute(
            "SELECT u.id FROM users u JOIN teams t ON t.captain_id=u.student_id WHERE t.id=?",
            (e["team_id"],),
        ).fetchone()
        if u:
            notify(
                db,
                u["id"],
                "Hồ sơ của đội "
                + (
                    "đã được duyệt."
                    if decision == "approved"
                    else "bị từ chối: " + reason
                ),
            )
        audit(db, g.user, "entry.review", entry_id, decision + ":" + reason)
    flash("Đã cập nhật trạng thái hồ sơ.", "success")
    return redirect(url_for("event.detail", eid=e["event_id"]))
