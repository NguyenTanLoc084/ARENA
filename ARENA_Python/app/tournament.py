"""Khang: lịch/nhánh. Lộc: ranh giới giao dịch. Lịch luôn tạo nguyên tử."""

import random
from datetime import datetime, timedelta
from flask import (
    Blueprint,
    render_template,
    request,
    g,
    redirect,
    url_for,
    flash,
    abort,
    jsonify,
)
from .db import query, transaction, audit
from .common import require, permission, integer, clean, local_to_utc

bp = Blueprint("event", __name__)


def match_rows(eid):
    return query(
        """SELECT m.*,r.name round_name,r.number round_number,a.name a_name,a.tag a_tag,b.name b_name,b.tag b_tag,u.username referee,
    (SELECT COUNT(*) FROM games WHERE match_id=m.id AND winner_id=m.team_a) score_a,
    (SELECT COUNT(*) FROM games WHERE match_id=m.id AND winner_id=m.team_b) score_b
    FROM matches m JOIN rounds r ON r.id=m.round_id LEFT JOIN teams a ON a.id=m.team_a LEFT JOIN teams b ON b.id=m.team_b
    LEFT JOIN users u ON u.id=m.referee_id WHERE m.event_id=? ORDER BY r.number,m.slot""",
        (eid,),
    )


@bp.route("/events/new", methods=["GET", "POST"])
def create():
    permission("event")
    if request.method == "POST":
        f = request.form
        fmt = f.get("format")
        require(fmt in ("knockout", "roundrobin"), "Thể thức không hợp lệ.")
        opens = local_to_utc(f.get("opens"))
        closes = local_to_utc(f.get("closes"))
        require(opens < closes, "Ngày đóng phải sau ngày mở.")
        with transaction() as db:
            eid = db.execute(
                "INSERT INTO events(name,format,opens,closes,reserve_max,pool) VALUES(?,?,?,?,?,?)",
                (
                    clean(f.get("name"), "tên giải", 150),
                    fmt,
                    opens,
                    closes,
                    integer(f.get("reserve_max"), "Số dự bị", 0, 2),
                    integer(f.get("pool"), "Quỹ thưởng", 0, 10**12),
                ),
            ).lastrowid
            audit(db, g.user, "event.create", eid)
        flash("Đã tạo giải nháp. Mở đăng ký khi điều lệ đã sẵn sàng.", "success")
        return redirect(url_for("event.detail", eid=eid))
    return render_template("event_form.html")


@bp.get("/events/<int:eid>")
def detail(eid):
    e = query("SELECT * FROM events WHERE id=?", (eid,), one=True)
    if not e:
        abort(404)
    entries = query(
        "SELECT e.*,t.name,t.tag FROM entries e JOIN teams t ON t.id=e.team_id WHERE e.event_id=? ORDER BY e.created",
        (eid,),
    )
    from .common import can

    rosters = {}
    if can("event"):
        for en in entries:
            rosters[en["id"]] = query(
                "SELECT s.code,s.full_name,s.ign,r.starter FROM rosters r JOIN students s ON s.id=r.student_id WHERE r.entry_id=? ORDER BY r.starter DESC,s.id",
                (en["id"],),
            )
    from .reports import standings

    return render_template(
        "event.html",
        event=e,
        entries=entries,
        matches=match_rows(eid),
        rosters=rosters,
        standings=standings(eid),
        referees=query(
            "SELECT id,username FROM users WHERE role IN('organizer','referee') AND active=1"
        ),
        prizes=query("SELECT * FROM prizes WHERE event_id=? ORDER BY rank", (eid,)),
    )


@bp.post("/events/<int:eid>/state")
def state(eid):
    permission("event")
    target = request.form.get("state")
    with transaction() as db:
        e = db.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
        require(e, "Không có giải.")
        allowed = {"draft": "open", "open": "locked", "locked": "live"}
        require(
            allowed.get(e["status"]) == target,
            "Không thể chuyển trạng thái theo thứ tự này.",
        )
        if target == "live":
            require(
                db.execute("SELECT 1 FROM matches WHERE event_id=?", (eid,)).fetchone(),
                "Cần xếp lịch trước khi bắt đầu giải.",
            )
        db.execute("UPDATE events SET status=? WHERE id=?", (target, eid))
        audit(db, g.user, "event.state", eid, target)
    flash("Đã cập nhật trạng thái giải.", "success")
    return redirect(url_for("event.detail", eid=eid))


def round_robin(teams):
    players = list(teams)
    if len(players) % 2:
        players.append(None)
    rounds = []
    for _ in range(len(players) - 1):
        rounds.append(
            [
                (players[i], players[-i - 1])
                for i in range(len(players) // 2)
                if players[i] is not None and players[-i - 1] is not None
            ]
        )
        players = [players[0], players[-1]] + players[1:-1]
    return rounds


def create_schedule(db, user, eid, best_of, start, referee):
    e = db.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    require(e and e["status"] == "locked", "Khóa đăng ký trước khi tạo lịch.")
    require(
        not db.execute("SELECT 1 FROM matches WHERE event_id=?", (eid,)).fetchone(),
        "Giải đã có lịch. Không tạo lại để tránh mất kết quả.",
    )
    require(
        not db.execute(
            "SELECT 1 FROM entries WHERE event_id=? AND status='pending'", (eid,)
        ).fetchone(),
        "Cần xử lý hết hồ sơ chờ duyệt.",
    )
    teams = [
        r[0]
        for r in db.execute(
            "SELECT team_id FROM entries WHERE event_id=? AND status='approved' ORDER BY id",
            (eid,),
        )
    ]
    require(2 <= len(teams) <= 32, "Phiên bản này hỗ trợ từ 2 đến 32 đội đã duyệt.")
    require(best_of in (3, 5), "Chỉ hỗ trợ Bo3 hoặc Bo5.")
    require(
        db.execute(
            "SELECT 1 FROM users WHERE id=? AND active=1 AND role IN('referee','organizer')",
            (referee,),
        ).fetchone(),
        "Trọng tài không hợp lệ.",
    )
    require(start >= e["closes"], "Lịch phải sau thời điểm đóng đăng ký.")
    random.SystemRandom().shuffle(teams)
    if e["format"] == "roundrobin":
        round_pairs = round_robin(teams)
    else:
        size = 1
        while size < len(teams):
            size *= 2
        half = size // 2
        padded = teams + [None] * (size - len(teams))
        round_pairs = [[(padded[i], padded[i + half]) for i in range(half)]]
        while len(round_pairs[-1]) > 1:
            round_pairs.append([(None, None)] * (len(round_pairs[-1]) // 2))
    round_ids = []
    match_ids = []
    for ri, pairs in enumerate(round_pairs):
        remaining = len(round_pairs) - ri
        name = (
            (
                "Chung kết"
                if remaining == 1
                else "Bán kết"
                if remaining == 2
                else f"Vòng {ri + 1}"
            )
            if e["format"] == "knockout"
            else f"Lượt {ri + 1}"
        )
        round_ids.append(
            db.execute(
                "INSERT INTO rounds(event_id,number,name) VALUES(?,?,?)",
                (eid, ri + 1, name),
            ).lastrowid
        )
    dt = datetime.strptime(start, "%Y-%m-%dT%H:%M")
    for ri, pairs in enumerate(round_pairs):
        row = []
        for slot, (a, b) in enumerate(pairs):
            starts = dt.strftime("%Y-%m-%dT%H:%M")
            dt += timedelta(hours=2)
            ends = dt.strftime("%Y-%m-%dT%H:%M")
            if a is not None and b is not None or ri > 0:
                others = db.execute(
                    "SELECT * FROM matches WHERE event_id<>? AND state<>'bye' AND starts<? AND ends>?",
                    (eid, ends, starts),
                ).fetchall()
                own = {a, b} - {None}
                for other in others:
                    require(
                        other["referee_id"] != referee
                        and not own.intersection(
                            {other["team_a"], other["team_b"]} - {None}
                        ),
                        "Lịch tạo mới trùng đội hoặc trọng tài ở giải khác. Chọn thời điểm hoặc trọng tài khác.",
                    )
            row.append(
                db.execute(
                    "INSERT INTO matches(event_id,round_id,slot,team_a,team_b,best_of,starts,ends,referee_id) VALUES(?,?,?,?,?,?,?,?,?)",
                    (eid, round_ids[ri], slot, a, b, best_of, starts, ends, referee),
                ).lastrowid
            )
        match_ids.append(row)
    if e["format"] == "knockout":
        for ri, row in enumerate(match_ids[:-1]):
            for slot, mid in enumerate(row):
                db.execute(
                    "UPDATE matches SET next_id=?,next_slot=? WHERE id=?",
                    (match_ids[ri + 1][slot // 2], "a" if slot % 2 == 0 else "b", mid),
                )
        for mid in match_ids[0]:
            m = db.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
            if m["team_a"] is None or m["team_b"] is None:
                winner = m["team_a"] or m["team_b"]
                db.execute(
                    "UPDATE matches SET state='bye',winner_id=? WHERE id=?",
                    (winner, mid),
                )
                if m["next_id"]:
                    db.execute(
                        "UPDATE matches SET team_" + m["next_slot"] + "=? WHERE id=?",
                        (winner, m["next_id"]),
                    )
    audit(db, user, "schedule.create", eid, ",".join(map(str, teams)))


@bp.post("/events/<int:eid>/schedule")
def schedule(eid):
    permission("event")
    with transaction() as db:
        create_schedule(
            db,
            g.user,
            eid,
            integer(request.form.get("best_of"), "Bo", 3, 5),
            local_to_utc(request.form.get("start")),
            integer(request.form.get("referee_id"), "Trọng tài", 1),
        )
    flash(
        "Đã tạo lịch. Các trận được xếp tuần tự, mỗi trận dự kiến 2 giờ; có thể sửa giờ từng trận trước khi bắt đầu.",
        "success",
    )
    return redirect(url_for("event.detail", eid=eid))


@bp.post("/matches/<int:mid>/schedule")
def edit_schedule(mid):
    permission("event")
    start = local_to_utc(request.form.get("starts"))
    end = local_to_utc(request.form.get("ends"))
    require(start < end, "Giờ kết thúc phải sau bắt đầu.")
    ref = integer(request.form.get("referee_id"), "Trọng tài", 1)
    bo = integer(request.form.get("best_of"), "Bo", 3, 5)
    require(bo in (3, 5), "Chỉ có Bo3 hoặc Bo5.")
    with transaction() as db:
        m = db.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
        require(m and m["state"] == "scheduled", "Chỉ sửa lịch trận chưa diễn ra.")
        ev = db.execute("SELECT * FROM events WHERE id=?", (m["event_id"],)).fetchone()
        require(start >= ev["closes"], "Lịch phải sau khi đóng đăng ký.")
        require(
            db.execute(
                "SELECT 1 FROM users WHERE id=? AND active=1 AND role IN('referee','organizer')",
                (ref,),
            ).fetchone(),
            "Trọng tài không hợp lệ.",
        )
        others = db.execute(
            "SELECT * FROM matches WHERE id<>? AND state<>'bye' AND starts<? AND ends>?",
            (mid, end, start),
        ).fetchall()
        own = {m["team_a"], m["team_b"]} - {None}
        for other in others:
            require(
                other["referee_id"] != ref
                and not own.intersection({other["team_a"], other["team_b"]} - {None}),
                "Lịch trùng đội hoặc trọng tài (kể cả giải khác).",
            )
        sources = db.execute("SELECT * FROM matches WHERE next_id=?", (mid,)).fetchall()
        for source in sources:
            require(
                not source["ends"] or source["ends"] <= start,
                "Trận phải bắt đầu sau khi trận nguồn kết thúc dự kiến.",
            )
        if m["next_id"]:
            target = db.execute(
                "SELECT * FROM matches WHERE id=?", (m["next_id"],)
            ).fetchone()
            require(
                not target["starts"] or end <= target["starts"],
                "Trận phải kết thúc trước khi trận kế tiếp bắt đầu.",
            )
        db.execute(
            "UPDATE matches SET starts=?,ends=?,referee_id=?,best_of=?,version=version+1 WHERE id=?",
            (start, end, ref, bo, mid),
        )
        audit(db, g.user, "schedule.update", mid)
    flash("Đã cập nhật lịch.", "success")
    return redirect(url_for("match.detail", mid=mid))


@bp.get("/api/events/<int:eid>/state")
def live(eid):
    e = query("SELECT status FROM events WHERE id=?", (eid,), one=True)
    if not e:
        abort(404)
    rows = query(
        "SELECT id,version,state FROM matches WHERE event_id=? ORDER BY id", (eid,)
    )
    return jsonify(
        status=e["status"],
        signature="|".join(f"{r['id']}:{r['version']}:{r['state']}" for r in rows),
    )
