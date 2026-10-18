"""Trân: một nguồn tính điểm, KDA và thưởng. Không sửa tổng bằng tay."""

import csv, io
from flask import (
    Blueprint,
    render_template,
    request,
    g,
    redirect,
    url_for,
    flash,
    abort,
    Response,
)
from .db import query, transaction, audit, now
from .common import require, permission, integer, clean

bp = Blueprint("report", __name__)


def standings(eid):
    event = query("SELECT * FROM events WHERE id=?", (eid,), one=True)
    teams = query(
        "SELECT t.* FROM teams t JOIN entries e ON e.team_id=t.id WHERE e.event_id=? AND e.status='approved'",
        (eid,),
    )
    rows = {
        t["id"]: dict(
            id=t["id"],
            name=t["name"],
            tag=t["tag"],
            wins=0,
            losses=0,
            game_wins=0,
            game_losses=0,
            points=0,
            rank=None,
            amount=0,
        )
        for t in teams
    }
    matches = query(
        "SELECT m.*,r.number round_number FROM matches m JOIN rounds r ON r.id=m.round_id WHERE m.event_id=?",
        (eid,),
    )
    last_round = max((m["round_number"] for m in matches), default=0)
    for m in matches:
        if m["state"] == "finished":
            a, b = m["team_a"], m["team_b"]
            winner = m["winner_id"]
            loser = b if winner == a else a
            rows[winner]["wins"] += 1
            rows[loser]["losses"] += 1
            if event["format"] == "knockout":
                rows[loser]["rank"] = 2 ** (last_round - m["round_number"]) + 1
            if event["format"] == "knockout" and m["round_number"] == last_round:
                rows[winner]["rank"] = 1
    for game in query(
        "SELECT v.winner_id,m.team_a,m.team_b FROM games v JOIN matches m ON m.id=v.match_id WHERE m.event_id=? AND m.state='finished'",
        (eid,),
    ):
        winner = game["winner_id"]
        loser = game["team_b"] if winner == game["team_a"] else game["team_a"]
        rows[winner]["game_wins"] += 1
        rows[loser]["game_losses"] += 1
    for r in rows.values():
        r["points"] = (
            r["wins"] * event["win_points"] + r["losses"] * event["loss_points"]
        )
        r["diff"] = r["game_wins"] - r["game_losses"]
    result = list(rows.values())
    if event["format"] == "roundrobin":
        result.sort(
            key=lambda r: (-r["points"], -r["diff"], -r["game_wins"], r["name"])
        )
        previous = None
        rank = 0
        for i, r in enumerate(result, 1):
            score = (r["points"], r["diff"], r["game_wins"])
            if score != previous:
                rank = i
            r["rank"] = rank
            previous = score
    else:
        result.sort(key=lambda r: (r["rank"] or 999, -r["wins"], r["name"]))
    final = {
        r["team_id"]: r
        for r in query("SELECT * FROM final_results WHERE event_id=?", (eid,))
    }
    for r in result:
        if r["id"] in final:
            r["rank"] = final[r["id"]]["rank"]
            r["amount"] = final[r["id"]]["amount"]
    return result


def kda(eid):
    return query(
        """SELECT s.ign,t.name team_name,SUM(c.kills) kills,SUM(c.deaths) deaths,SUM(c.assists) assists,COUNT(*) games,
    ROUND(1.0*(SUM(c.kills)+SUM(c.assists))/MAX(1,SUM(c.deaths)),2) kda
    FROM stats c JOIN students s ON s.id=c.student_id JOIN teams t ON t.id=c.team_id JOIN games v ON v.id=c.game_id
    JOIN matches m ON m.id=v.match_id WHERE m.event_id=? GROUP BY c.student_id,c.team_id ORDER BY kda DESC,kills DESC,s.ign""",
        (eid,),
    )


@bp.get("/events/<int:eid>/report")
def view(eid):
    e = query("SELECT * FROM events WHERE id=?", (eid,), one=True)
    if not e:
        abort(404)
    return render_template(
        "report.html",
        event=e,
        standings=standings(eid),
        players=kda(eid),
        total=query(
            "SELECT COALESCE(SUM(amount),0) total FROM final_results WHERE event_id=?",
            (eid,),
            one=True,
        )["total"],
    )


@bp.post("/events/<int:eid>/prizes")
def prizes(eid):
    permission("event")
    rank = integer(request.form.get("rank"), "Hạng", 1, 32)
    amount = integer(request.form.get("amount"), "Tiền thưởng", 0, 10**12)
    with transaction() as db:
        e = db.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
        require(
            e and e["status"] in ("draft", "open", "locked"),
            "Mức thưởng phải được công bố trước khi giải bắt đầu.",
        )
        require(amount <= e["pool"], "Tiền thưởng một hạng không được vượt quỹ.")
        db.execute(
            "INSERT INTO prizes VALUES(?,?,?) ON CONFLICT(event_id,rank) DO UPDATE SET amount=excluded.amount",
            (eid, rank, amount),
        )
        audit(db, g.user, "prize.update", eid, f"{rank}:{amount}")
    flash("Đã lưu mức thưởng. Hạng không có mức thưởng được tính là 0 đồng.", "success")
    return redirect(url_for("event.detail", eid=eid))


def finalize(db, user, eid, reason):
    e = db.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    require(e and e["status"] == "live", "Giải không ở trạng thái đang diễn ra.")
    matches = db.execute("SELECT * FROM matches WHERE event_id=?", (eid,)).fetchall()
    require(
        matches and all(m["state"] in ("finished", "bye") for m in matches),
        "Còn trận chưa hoàn tất.",
    )
    rows = standings(eid)
    require(all(r["rank"] is not None for r in rows), "Chưa xác định được thứ hạng.")
    tied = len(set(r["rank"] for r in rows)) < len(rows)
    require(
        not tied or len(reason.strip()) >= 5,
        "Có đồng hạng. BTC cần ghi căn cứ áp dụng điều lệ đồng hạng ít nhất 5 ký tự.",
    )
    amounts = {
        p["rank"]: p["amount"]
        for p in db.execute("SELECT * FROM prizes WHERE event_id=?", (eid,))
    }
    total = sum(amounts.get(r["rank"], 0) for r in rows)
    require(
        total <= e["pool"],
        "Tổng thưởng cho tất cả đội (kể cả đồng hạng) vượt quỹ. Chưa thể chốt.",
    )
    for r in rows:
        db.execute(
            "INSERT INTO final_results VALUES(?,?,?,?,?,?,?)",
            (
                eid,
                r["id"],
                r["rank"],
                amounts.get(r["rank"], 0),
                reason,
                user["id"],
                now(),
            ),
        )
    db.execute("UPDATE events SET status='finished' WHERE id=?", (eid,))
    db.execute("UPDATE rosters SET holding=0 WHERE event_id=?", (eid,))
    audit(db, user, "event.finalize", eid, f"Tổng thưởng {total}. {reason}")


@bp.post("/events/<int:eid>/finalize")
def finish(eid):
    permission("event")
    with transaction() as db:
        finalize(db, g.user, eid, request.form.get("reason", "")[:500])
    flash("Đã chốt giải. Kết quả và tiền thưởng đã khóa.", "success")
    return redirect(url_for("report.view", eid=eid))


def safe_cell(value):
    text = str(value)
    return (
        "'" + text
        if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
        else text
    )


@bp.get("/events/<int:eid>/report.csv")
def export(eid):
    e = query("SELECT * FROM events WHERE id=?", (eid,), one=True)
    if not e:
        abort(404)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(
        [
            "Hạng",
            "Đội",
            "Thắng trận",
            "Thua trận",
            "Điểm",
            "Hiệu số ván",
            "Tiền thưởng VND",
            "Trạng thái",
        ]
    )
    for r in standings(eid):
        w.writerow(
            [
                r["rank"] or "",
                safe_cell(r["name"]),
                r["wins"],
                r["losses"],
                r["points"],
                r["diff"],
                r["amount"],
                "Đã chốt" if e["status"] == "finished" else "Tạm thời",
            ]
        )
    return Response(
        "\ufeff" + out.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="giai-{eid}-ket-qua.csv"'
        },
    )


@bp.post("/events/<int:eid>/budget")
def budget(eid):
    permission("event")
    amount = integer(request.form.get("pool"), "Quỹ thưởng", 0, 10**12)
    reason = clean(request.form.get("reason"), "lý do tăng quỹ", 300)
    with transaction() as db:
        e = db.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
        require(e and e["status"] != "finished", "Giải đã chốt hoặc không tồn tại.")
        require(amount > e["pool"], "Quỹ mới phải lớn hơn quỹ đã công bố.")
        db.execute("UPDATE events SET pool=? WHERE id=?", (amount, eid))
        audit(db, g.user, "budget.increase", eid, f"{e['pool']} -> {amount}: {reason}")
    flash("Đã bổ sung quỹ thưởng; mức thưởng theo hạng được giữ nguyên.", "success")
    return redirect(url_for("event.detail", eid=eid))
