"""Khang: kết quả ván, KDA, phiên bản và chuyển nhánh nguyên tử."""

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
from .db import query, transaction, audit
from .common import require, permission, integer

bp = Blueprint("match", __name__)


def allowed(user, m):
    if not user or user["role"] not in ("organizer", "referee"):
        abort(403)
    if user["role"] == "referee" and m["referee_id"] != user["id"]:
        abort(403)


def roster(mid):
    return query(
        """SELECT s.id,s.ign,s.full_name,s.code,r.starter,e.team_id,t.name team_name FROM matches m
    JOIN entries e ON e.event_id=m.event_id AND e.team_id IN(m.team_a,m.team_b) JOIN rosters r ON r.entry_id=e.id
    JOIN students s ON s.id=r.student_id JOIN teams t ON t.id=e.team_id WHERE m.id=? AND e.status='approved' ORDER BY e.team_id,r.starter DESC,s.id""",
        (mid,),
    )


@bp.get("/matches/<int:mid>")
def detail(mid):
    m = query(
        """SELECT m.*,a.name a_name,b.name b_name,e.name event_name,e.status event_status,r.name round_name
    FROM matches m JOIN events e ON e.id=m.event_id JOIN rounds r ON r.id=m.round_id LEFT JOIN teams a ON a.id=m.team_a LEFT JOIN teams b ON b.id=m.team_b WHERE m.id=?""",
        (mid,),
        one=True,
    )
    if not m:
        abort(404)
    editable = bool(
        g.user
        and (
            g.user["role"] == "organizer"
            or (g.user["role"] == "referee" and m["referee_id"] == g.user["id"])
        )
    )
    games = query(
        "SELECT g.*,t.name winner_name FROM games g JOIN teams t ON t.id=g.winner_id WHERE g.match_id=? ORDER BY g.number",
        (mid,),
    )
    stats = query(
        "SELECT c.*,s.ign,h.name hero_name FROM stats c JOIN games v ON v.id=c.game_id JOIN students s ON s.id=c.student_id JOIN heroes h ON h.id=c.hero_id WHERE v.match_id=?",
        (mid,),
    )
    editing = None
    values = {}
    if editable and request.args.get("game"):
        number = integer(request.args["game"], "Số ván", 1, 5)
        editing = next((x for x in games if x["number"] == number), None)
        if editing:
            values = {
                r["student_id"]: r for r in stats if r["game_id"] == editing["id"]
            }
    return render_template(
        "match.html",
        match=m,
        games=games,
        stats=stats,
        editable=editable,
        players=roster(mid) if editable else [],
        heroes=query("SELECT * FROM heroes WHERE active=1"),
        editing=editing,
        values=values,
        referees=query(
            "SELECT id,username FROM users WHERE role IN('organizer','referee') AND active=1"
        ),
    )


@bp.post("/matches/<int:mid>/start")
def start(mid):
    permission("result")
    with transaction() as db:
        m = db.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
        require(m, "Không có trận.")
        allowed(g.user, m)
        e = db.execute(
            "SELECT status FROM events WHERE id=?", (m["event_id"],)
        ).fetchone()
        require(e["status"] == "live", "BTC cần bắt đầu giải trước.")
        require(
            m["state"] == "scheduled" and m["team_a"] and m["team_b"],
            "Trận chưa đủ hai đội hoặc đã bắt đầu.",
        )
        require(
            not db.execute(
                "SELECT 1 FROM matches WHERE next_id=? AND state NOT IN('finished','bye')",
                (mid,),
            ).fetchone(),
            "Các trận nguồn chưa hoàn tất.",
        )
        db.execute(
            "UPDATE matches SET state='live',version=version+1 WHERE id=?", (mid,)
        )
        audit(db, g.user, "match.start", mid)
    flash("Trận đã bắt đầu.", "success")
    return redirect(url_for("match.detail", mid=mid))


def save_game(db, user, mid, version, number, winner, duration, rows, exception=""):
    m = db.execute("SELECT * FROM matches WHERE id=?", (mid,)).fetchone()
    require(m, "Không tìm thấy trận.")
    allowed(user, m)
    require(
        m["version"] == version,
        "Dữ liệu đã thay đổi. Tải lại trang trước khi lưu để tránh ghi đè.",
    )
    require(
        db.execute("SELECT status FROM events WHERE id=?", (m["event_id"],)).fetchone()[
            0
        ]
        == "live",
        "Giải chưa bắt đầu hoặc đã khóa kết quả.",
    )
    require(
        winner in (m["team_a"], m["team_b"]),
        "Đội thắng phải là một trong hai đội của trận.",
    )
    old = db.execute(
        "SELECT * FROM games WHERE match_id=? AND number=?", (mid, number)
    ).fetchone()
    existing = db.execute(
        "SELECT * FROM games WHERE match_id=? ORDER BY number", (mid,)
    ).fetchall()
    require(
        m["state"] == "live" or (old and m["state"] == "finished"),
        "Trận không cho phép nhập thêm ván.",
    )
    require(
        old or number == len(existing) + 1, "Số ván phải liên tiếp, không bỏ qua ván."
    )
    require(
        1 <= number <= m["best_of"] and 0 < duration <= 86400,
        "Số ván hoặc thời lượng không hợp lệ.",
    )
    target = (
        db.execute("SELECT * FROM matches WHERE id=?", (m["next_id"],)).fetchone()
        if m["next_id"]
        else None
    )
    require(
        not target or target["state"] == "scheduled",
        "Trận kế tiếp đã bắt đầu; không được sửa kết quả nguồn.",
    )
    require(
        len(rows) == 10 and len({r["student_id"] for r in rows}) == 10,
        "Cần chọn đúng 10 người chơi khác nhau.",
    )
    counts = {m["team_a"]: 0, m["team_b"]: 0}
    sums = {t: [0, 0] for t in counts}
    for row in rows:
        team = row["team_id"]
        require(team in counts, "Người chơi thuộc đội không tham gia trận này.")
        member = db.execute(
            "SELECT 1 FROM rosters r JOIN entries e ON e.id=r.entry_id WHERE e.event_id=? AND e.team_id=? AND r.student_id=? AND e.status='approved'",
            (m["event_id"], team, row["student_id"]),
        ).fetchone()
        require(member, "Người chơi không thuộc đội hình đã duyệt.")
        require(
            db.execute(
                "SELECT 1 FROM heroes WHERE id=? AND active=1", (row["hero_id"],)
            ).fetchone(),
            "Tướng không hợp lệ.",
        )
        for name in ("kills", "deaths", "assists"):
            require(
                isinstance(row[name], int) and 0 <= row[name] <= 1000,
                "K/D/A phải là số nguyên từ 0 đến 1000.",
            )
        require(
            row.get("gold") is None or 0 <= row["gold"] <= 1000000, "Vàng không hợp lệ."
        )
        counts[team] += 1
        sums[team][0] += row["kills"]
        sums[team][1] += row["deaths"]
    require(
        all(c == 5 for c in counts.values()), "Mỗi đội phải có đúng 5 người ra sân."
    )
    a, b = m["team_a"], m["team_b"]
    mismatch = sums[a][0] != sums[b][1] or sums[b][0] != sums[a][1]
    require(
        not mismatch or (user["role"] == "organizer" and len(exception.strip()) >= 5),
        "K/D hai đội chênh lệch. BTC phải xác nhận và ghi lý do ít nhất 5 ký tự.",
    )
    sequence = {v["number"]: v["winner_id"] for v in existing}
    sequence[number] = winner
    score = {a: 0, b: 0}
    threshold = m["best_of"] // 2 + 1
    for index in sorted(sequence):
        require(
            max(score.values()) < threshold,
            "Thay đổi này tạo ván dư sau thời điểm trận đã kết thúc. Hãy giữ kết quả nhất quán.",
        )
        score[sequence[index]] += 1
    won = next((tid for tid, count in score.items() if count >= threshold), None)
    if target and won:
        conflict = db.execute(
            "SELECT * FROM matches WHERE id<>? AND state<>'bye' AND starts<? AND ends>? AND (team_a=? OR team_b=?)",
            (target["id"], target["ends"], target["starts"], won, won),
        ).fetchone()
        require(
            not conflict,
            "Lịch vòng tiếp theo trùng với trận khác của đội thắng. BTC cần điều chỉnh lịch trước.",
        )
    if old:
        gid = old["id"]
        db.execute("DELETE FROM stats WHERE game_id=?", (gid,))
        db.execute(
            "UPDATE games SET winner_id=?,duration=?,exception_reason=?,author_id=? WHERE id=?",
            (winner, duration, exception.strip() if mismatch else "", user["id"], gid),
        )
    else:
        gid = db.execute(
            "INSERT INTO games(match_id,number,winner_id,duration,exception_reason,author_id) VALUES(?,?,?,?,?,?)",
            (
                mid,
                number,
                winner,
                duration,
                exception.strip() if mismatch else "",
                user["id"],
            ),
        ).lastrowid
    for row in rows:
        db.execute(
            "INSERT INTO stats VALUES(?,?,?,?,?,?,?,?)",
            (
                gid,
                row["student_id"],
                row["team_id"],
                row["hero_id"],
                row["kills"],
                row["deaths"],
                row["assists"],
                row.get("gold"),
            ),
        )
    db.execute(
        "UPDATE matches SET winner_id=?,state=?,version=version+1 WHERE id=?",
        (won, "finished" if won else "live", mid),
    )
    if target:
        db.execute(
            "UPDATE matches SET team_"
            + m["next_slot"]
            + "=?,version=version+1 WHERE id=?",
            (won, target["id"]),
        )
    audit(
        db,
        user,
        "game.update" if old else "game.create",
        gid,
        f"Ván {number}; thắng {winner}; tỷ số {score[a]}–{score[b]}; ngoại lệ: {exception if mismatch else 'không'}",
    )
    return gid


@bp.post("/matches/<int:mid>/games")
def save(mid):
    permission("result")
    f = request.form
    rows = []
    for sid_string in f.getlist("selected"):
        sid = integer(sid_string, "Người chơi", 1)
        rows.append(
            dict(
                student_id=sid,
                team_id=integer(f.get(f"team_{sid}"), "Đội", 1),
                hero_id=integer(f.get(f"hero_{sid}"), "Tướng", 1),
                kills=integer(f.get(f"k_{sid}"), "Kills", 0, 1000),
                deaths=integer(f.get(f"d_{sid}"), "Deaths", 0, 1000),
                assists=integer(f.get(f"a_{sid}"), "Assists", 0, 1000),
                gold=integer(f.get(f"g_{sid}"), "Vàng", 0, 1000000)
                if f.get(f"g_{sid}")
                else None,
            )
        )
    with transaction() as db:
        save_game(
            db,
            g.user,
            mid,
            integer(f.get("version"), "Phiên bản", 1),
            integer(f.get("number"), "Ván", 1, 5),
            integer(f.get("winner"), "Đội thắng", 1),
            integer(f.get("duration"), "Thời lượng", 1, 86400),
            rows,
            f.get("exception", "")[:500],
        )
    flash("Đã lưu ván, tính lại tỷ số và cập nhật nhánh đấu.", "success")
    return redirect(url_for("match.detail", mid=mid))
