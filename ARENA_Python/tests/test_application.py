import sqlite3
import pytest
from app.db import get_db, transaction
from app.common import BusinessError, local_to_utc, local_input
from app.tournament import round_robin, create_schedule
from app.matches import save_game
from app.reports import finalize, kda, safe_cell
from app.team import submit_entry


def user(db, name="btc"):
    return db.execute("SELECT * FROM users WHERE username=?", (name,)).fetchone()


def current(db):
    return db.execute(
        "SELECT * FROM matches WHERE state='live' ORDER BY id LIMIT 1"
    ).fetchone()


def players(db, m):
    rows = []
    for tid in [m["team_a"], m["team_b"]]:
        for r in db.execute(
            "SELECT r.student_id FROM rosters r JOIN entries e ON e.id=r.entry_id WHERE e.event_id=? AND e.team_id=? AND r.starter=1",
            (m["event_id"], tid),
        ):
            rows.append(
                dict(
                    student_id=r[0],
                    team_id=tid,
                    hero_id=1,
                    kills=0,
                    deaths=0,
                    assists=3,
                    gold=None,
                )
            )
    return rows


def win(db, m, bo=None):
    db.execute("UPDATE matches SET state='live' WHERE id=?", (m["id"],))
    for number in range(1, (bo or m["best_of"]) // 2 + 2):
        fresh = db.execute("SELECT * FROM matches WHERE id=?", (m["id"],)).fetchone()
        save_game(
            db,
            user(db),
            m["id"],
            fresh["version"],
            number,
            m["team_a"],
            1200,
            players(db, m),
        )


@pytest.mark.parametrize(
    "uid,paths",
    [
        (
            None,
            [
                "/",
                "/login",
                "/register",
                "/events/1",
                "/events/2",
                "/events/3",
                "/matches/1",
                "/events/2/report",
                "/events/2/report.csv",
                "/api/events/2/state",
            ],
        ),
        (1, ["/admin", "/audit", "/notifications"]),
        (
            2,
            [
                "/",
                "/events/new",
                "/events/1",
                "/events/2",
                "/matches/1",
                "/matches/1?game=1",
                "/audit",
            ],
        ),
        (3, ["/matches/1", "/notifications"]),
        (4, ["/my-team", "/profile", "/events/3/register", "/notifications"]),
    ],
)
def test_all_pages(client, login, uid, paths):
    if uid:
        login(uid)
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
        assert b"Traceback" not in response.data


@pytest.mark.parametrize(
    "path", ["/admin", "/audit", "/profile", "/my-team", "/events/new"]
)
def test_private_pages_require_login(client, path):
    assert client.get(path).status_code == 401


def test_csrf_and_role(client, login):
    assert client.post("/events/1/state", data={"state": "live"}).status_code == 400
    token = login(4)
    assert (
        client.post("/events/1/state", data={**token, "state": "live"}).status_code
        == 403
    )
    assert client.get("/admin").status_code == 403


def test_real_login_and_lockout(client):
    client.get("/login")
    with client.session_transaction() as s:
        csrf = s["csrf"]
    assert (
        client.post(
            "/login", data={"csrf": csrf, "username": "btc", "password": "Arena@2026"}
        ).status_code
        == 302
    )
    with client.session_transaction() as s:
        assert s["uid"] == 2
        csrf = s["csrf"]
    client.post("/logout", data={"csrf": csrf})
    client.get("/login")
    with client.session_transaction() as s:
        csrf = s["csrf"]
    for _ in range(8):
        assert (
            client.post(
                "/login",
                data={"csrf": csrf, "username": "missing", "password": "wrong"},
            ).status_code
            == 200
        )
    assert (
        client.post(
            "/login", data={"csrf": csrf, "username": "missing", "password": "wrong"}
        ).status_code
        == 429
    )


def test_public_privacy(client):
    for path in [
        "/events/2",
        "/matches/1",
        "/events/2/report",
        "/events/2/report.csv",
        "/api/events/2/state",
    ]:
        data = client.get(path).data
        assert (
            b"DEMO001" not in data
            and b"GAME001" not in data
            and b"password_hash" not in data
        )


def test_seed_idempotent(app):
    from app.seed import seed_demo

    with app.app_context():
        assert seed_demo() is False
        assert get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 31


@pytest.mark.parametrize("size", [2, 3, 4, 5, 16, 31, 32])
def test_round_robin_every_pair_once(size):
    rounds = round_robin(range(size))
    pairs = [tuple(sorted(p)) for rr in rounds for p in rr]
    assert len(set(pairs)) == len(pairs) == size * (size - 1) // 2
    for rr in rounds:
        assert len({x for p in rr for x in p}) == 2 * len(rr)


def test_schedule_conflict_atomic(app):
    with app.app_context():
        db = get_db()
        start = db.execute("SELECT MIN(starts) FROM matches").fetchone()[0]
        with pytest.raises(BusinessError), transaction():
            create_schedule(db, user(db), 1, 3, start, 3)
        assert (
            db.execute("SELECT COUNT(*) FROM rounds WHERE event_id=1").fetchone()[0]
            == 0
        )
        assert (
            db.execute("SELECT COUNT(*) FROM matches WHERE event_id=1").fetchone()[0]
            == 0
        )


@pytest.mark.parametrize("teams,bo", [(3, 3), (4, 5)])
def test_knockout_to_final_prizes_and_release(app, teams, bo):
    with app.app_context():
        db = get_db()
        with transaction():
            if teams == 3:
                db.execute("DELETE FROM rosters WHERE entry_id=4")
                db.execute("DELETE FROM entries WHERE id=4")
            create_schedule(db, user(db), 1, bo, "2030-01-01T00:00", 3)
            db.execute("UPDATE events SET status='live' WHERE id=1")
            for m in db.execute(
                "SELECT * FROM matches WHERE event_id=1 ORDER BY id"
            ).fetchall():
                m = db.execute(
                    "SELECT * FROM matches WHERE id=?", (m["id"],)
                ).fetchone()
                if m["state"] != "bye":
                    assert m["team_a"] and m["team_b"]
                    win(db, m)
            finalize(db, user(db), 1, "Đồng hạng theo điều lệ giải")
        assert (
            db.execute("SELECT status FROM events WHERE id=1").fetchone()[0]
            == "finished"
        )
        assert (
            db.execute(
                "SELECT SUM(amount) FROM final_results WHERE event_id=1"
            ).fetchone()[0]
            == 5000000
        )
        assert (
            db.execute(
                "SELECT COUNT(*) FROM rosters WHERE event_id=1 AND holding=1"
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                "SELECT COUNT(*) FROM final_results WHERE event_id=1"
            ).fetchone()[0]
            == teams
        )


@pytest.mark.parametrize(
    "bad",
    [
        "nine",
        "duplicate",
        "negative",
        "outsider",
        "hero",
        "mismatch",
        "order",
        "winner",
        "duration",
    ],
)
def test_invalid_result_rolls_back(app, bad):
    with app.app_context():
        db = get_db()
        m = current(db)
        rows = players(db, m)
        number = 2
        winner = m["team_a"]
        duration = 100
        if bad == "nine":
            rows.pop()
        if bad == "duplicate":
            rows[1] = rows[0].copy()
        if bad == "negative":
            rows[0]["kills"] = -1
        if bad == "outsider":
            rows[0]["student_id"] = 999
        if bad == "hero":
            rows[0]["hero_id"] = 999
        if bad == "mismatch":
            rows[0]["kills"] = 1
        if bad == "order":
            number = 3
        if bad == "winner":
            winner = 999
        if bad == "duration":
            duration = 0
        with pytest.raises(BusinessError), transaction():
            save_game(
                db, user(db), m["id"], m["version"], number, winner, duration, rows
            )
        assert (
            db.execute(
                "SELECT COUNT(*) FROM games WHERE match_id=?", (m["id"],)
            ).fetchone()[0]
            == 1
        )
        assert (
            db.execute("SELECT version FROM matches WHERE id=?", (m["id"],)).fetchone()[
                0
            ]
            == m["version"]
        )


def test_stale_update_and_zero_deaths(app):
    with app.app_context():
        db = get_db()
        m = current(db)
        with transaction():
            save_game(
                db, user(db), m["id"], m["version"], 2, m["team_a"], 100, players(db, m)
            )
        with pytest.raises(BusinessError), transaction():
            save_game(
                db, user(db), m["id"], m["version"], 2, m["team_b"], 100, players(db, m)
            )
        assert len(kda(2)) == 10
        assert all(r["kda"] is not None for r in kda(2))


def test_referee_assignment_and_exception(app):
    from werkzeug.exceptions import Forbidden

    with app.app_context():
        db = get_db()
        m = current(db)
        rows = players(db, m)
        rows[0]["kills"] = 1
        with pytest.raises(BusinessError), transaction():
            save_game(
                db,
                user(db, "trongtai"),
                m["id"],
                m["version"],
                2,
                m["team_a"],
                100,
                rows,
                "Có ngoại lệ",
            )
        with transaction():
            save_game(
                db,
                user(db),
                m["id"],
                m["version"],
                2,
                m["team_a"],
                100,
                rows,
                "Hạ gục bởi công trình",
            )
        db.execute("UPDATE matches SET referee_id=2 WHERE id=?", (m["id"],))
        m = db.execute("SELECT * FROM matches WHERE id=?", (m["id"],)).fetchone()
        with pytest.raises(Forbidden), transaction():
            save_game(
                db,
                user(db, "trongtai"),
                m["id"],
                m["version"],
                2,
                m["team_b"],
                100,
                rows,
            )


def test_source_locked_after_next_starts(app):
    with app.app_context():
        db = get_db()
        with transaction():
            create_schedule(db, user(db), 1, 3, "2030-01-01T00:00", 3)
            db.execute("UPDATE events SET status='live' WHERE id=1")
            sources = db.execute(
                "SELECT * FROM matches WHERE event_id=1 AND next_id IS NOT NULL ORDER BY id"
            ).fetchall()
            for m in sources:
                win(db, m)
            db.execute(
                "UPDATE matches SET state='live' WHERE id=?", (sources[0]["next_id"],)
            )
        m = db.execute(
            "SELECT * FROM matches WHERE id=?", (sources[0]["id"],)
        ).fetchone()
        with pytest.raises(BusinessError), transaction():
            save_game(
                db, user(db), m["id"], m["version"], 1, m["team_b"], 100, players(db, m)
            )


def test_registration_review_withdraw(client, login, app):
    token = login(4)
    assert (
        client.post(
            "/events/3/register",
            data={
                **token,
                "starters": ["1", "2", "3", "4", "5"],
                "reserves": ["6", "7"],
            },
        ).status_code
        == 302
    )
    assert (
        client.post(
            "/events/3/register", data={**token, "starters": ["1", "2", "3", "4", "5"]}
        ).status_code
        == 400
    )
    with app.app_context():
        eid = (
            get_db()
            .execute("SELECT id FROM entries WHERE event_id=3 AND team_id=1")
            .fetchone()[0]
        )
    token = login(2)
    assert (
        client.post(
            f"/entries/{eid}/review", data={**token, "decision": "approved"}
        ).status_code
        == 302
    )
    token = login(4)
    assert client.post(f"/entries/{eid}/withdraw", data=token).status_code == 302
    with app.app_context():
        assert (
            get_db()
            .execute("SELECT SUM(holding) FROM rosters WHERE entry_id=?", (eid,))
            .fetchone()[0]
            == 0
        )


@pytest.mark.parametrize(
    "starters,reserves",
    [
        ([1, 2, 3, 4], []),
        ([1, 2, 3, 4, 5], [5]),
        ([1, 2, 3, 4, 8], []),
        ([1, 2, 3, 4, 5], [6, 7, 8]),
    ],
)
def test_invalid_registration(app, starters, reserves):
    with app.app_context():
        db = get_db()
        with pytest.raises(BusinessError), transaction():
            submit_entry(db, user(db, "doitruong1"), 3, 1, starters, reserves)
        assert (
            db.execute("SELECT COUNT(*) FROM entries WHERE event_id=3").fetchone()[0]
            == 0
        )


def test_admin_self_lock_and_budget(client, login, app):
    token = login(1)
    assert (
        client.post(
            "/admin/users/1", data={**token, "role": "student", "active": "0"}
        ).status_code
        == 400
    )
    token = login(2)
    assert (
        client.post(
            "/events/2/budget",
            data={**token, "pool": "4000000", "reason": "Bổ sung tài trợ"},
        ).status_code
        == 302
    )
    assert (
        client.post(
            "/events/2/budget", data={**token, "pool": "100", "reason": "Giảm quỹ"}
        ).status_code
        == 400
    )
    with app.app_context():
        assert (
            get_db().execute("SELECT pool FROM events WHERE id=2").fetchone()[0]
            == 4000000
        )


def test_time_and_csv():
    assert local_to_utc("2026-10-18T19:00") == "2026-10-18T12:00"
    assert local_input("2026-10-18T12:00") == "2026-10-18T19:00"
    for s in ["=SUM(1,2)", "+cmd", "-1", "@SUM(1)", "  =X"]:
        assert safe_cell(s).startswith("'")


def test_signup_team_invitation_flow(app, client, login):
    def signup(name, number):
        client.get("/register")
        with client.session_transaction() as s:
            csrf = s["csrf"]
        response = client.post(
            "/register",
            data={
                "csrf": csrf,
                "username": name,
                "password": "Testing@2026",
                "confirm": "Testing@2026",
                "code": number,
                "full_name": "Người kiểm thử",
                "game_id": "GAME" + number,
                "ign": name,
                "class_id": "1",
                "role": "admin",
            },
        )
        assert response.status_code == 302
        with client.session_transaction() as s:
            uid = s["uid"]
        return uid

    first = signup("newcaptain", "TEST100")
    with client.session_transaction() as s:
        s["csrf"] = "test-token"
    assert (
        client.post(
            "/teams", data={"csrf": "test-token", "name": "New Team", "tag": "NEW"}
        ).status_code
        == 302
    )
    second = signup("newmember", "TEST101")
    with app.app_context():
        db = get_db()
        tid = db.execute("SELECT id FROM teams WHERE name='New Team'").fetchone()[0]
        assert (
            db.execute("SELECT role FROM users WHERE id=?", (second,)).fetchone()[0]
            == "student"
        )
    token = login(first)
    assert (
        client.post(
            f"/teams/{tid}/invite", data={**token, "code": "TEST101"}
        ).status_code
        == 302
    )
    with app.app_context():
        invite = (
            get_db()
            .execute(
                "SELECT id FROM memberships WHERE team_id=? AND status='invited'",
                (tid,),
            )
            .fetchone()[0]
        )
    token = login(second)
    assert (
        client.post(
            f"/invites/{invite}", data={**token, "action": "accept"}
        ).status_code
        == 302
    )
    assert (
        client.post(
            "/teams", data={**token, "name": "Second team", "tag": "BAD"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/teams/{tid}/invite", data={**token, "code": "DEMO001"}
        ).status_code
        == 403
    )


def test_edit_completed_source_recalculates_next(app):
    with app.app_context():
        db = get_db()
        with transaction():
            create_schedule(db, user(db), 1, 3, "2030-01-01T00:00", 3)
            db.execute("UPDATE events SET status='live' WHERE id=1")
            m = db.execute(
                "SELECT * FROM matches WHERE event_id=1 ORDER BY id LIMIT 1"
            ).fetchone()
            win(db, m)
            m = db.execute("SELECT * FROM matches WHERE id=?", (m["id"],)).fetchone()
            save_game(
                db, user(db), m["id"], m["version"], 2, m["team_b"], 100, players(db, m)
            )
            target = db.execute(
                "SELECT * FROM matches WHERE id=?", (m["next_id"],)
            ).fetchone()
            assert target["team_" + m["next_slot"]] is None
            m = db.execute("SELECT * FROM matches WHERE id=?", (m["id"],)).fetchone()
            save_game(
                db, user(db), m["id"], m["version"], 3, m["team_b"], 100, players(db, m)
            )
            target = db.execute(
                "SELECT * FROM matches WHERE id=?", (m["next_id"],)
            ).fetchone()
            assert target["team_" + m["next_slot"]] == m["team_b"]


def test_roundrobin_budget_atomic_finalization(app):
    with app.app_context():
        db = get_db()
        with transaction():
            for m in db.execute(
                "SELECT * FROM matches WHERE event_id=2 ORDER BY id"
            ).fetchall():
                win(db, m)
            db.execute("UPDATE events SET pool=1 WHERE id=2")
        with pytest.raises(BusinessError), transaction():
            finalize(db, user(db), 2, "Áp dụng đồng hạng theo điều lệ")
        assert (
            db.execute(
                "SELECT COUNT(*) FROM final_results WHERE event_id=2"
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute("SELECT SUM(holding) FROM rosters WHERE event_id=2").fetchone()[
                0
            ]
            == 28
        )
        with transaction():
            db.execute("UPDATE events SET pool=20000000 WHERE id=2")
            finalize(db, user(db), 2, "Áp dụng đồng hạng theo điều lệ")
        assert (
            db.execute(
                "SELECT COUNT(*) FROM final_results WHERE event_id=2"
            ).fetchone()[0]
            == 4
        )


def test_edit_schedule_conflict(client, login, app):
    token = login(2)
    with app.app_context():
        db = get_db()
        m = db.execute("SELECT * FROM matches WHERE id=1").fetchone()
        start = local_input(m["starts"])
        end = local_input(m["ends"])
    assert (
        client.post(
            "/matches/2/schedule",
            data={
                **token,
                "starts": start,
                "ends": end,
                "referee_id": "3",
                "best_of": "3",
            },
        ).status_code
        == 400
    )


def test_database_constraints(app):
    with app.app_context():
        db = get_db()
        with pytest.raises(sqlite3.IntegrityError), transaction():
            db.execute(
                "INSERT INTO memberships(team_id,student_id,status) VALUES(2,1,'accepted')"
            )
        with pytest.raises(sqlite3.IntegrityError), transaction():
            db.execute(
                "INSERT INTO rosters(entry_id,event_id,student_id,starter,holding) VALUES(2,1,1,1,1)"
            )
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_password_all_roles(client, login):
    token = login(1)
    assert client.get("/password").status_code == 200
    assert (
        client.post(
            "/password",
            data={
                **token,
                "old": "wrong",
                "new": "Changed@2026",
                "confirm": "Changed@2026",
            },
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/password",
            data={
                **token,
                "old": "Arena@2026",
                "new": "Changed@2026",
                "confirm": "Changed@2026",
            },
        ).status_code
        == 302
    )
    assert client.get("/admin").status_code == 401
    client.get("/login")
    with client.session_transaction() as s:
        csrf = s["csrf"]
    assert (
        client.post(
            "/login",
            data={"csrf": csrf, "username": "admin", "password": "Changed@2026"},
        ).status_code
        == 302
    )


def test_clean_admin_initialization(tmp_path, monkeypatch):
    import runpy
    import app as package
    from pathlib import Path
    from werkzeug.security import check_password_hash

    application = package.create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "clean.sqlite3"),
            "SECRET_KEY": "test",
        }
    )
    monkeypatch.setattr(package, "create_app", lambda: application)
    monkeypatch.setattr("sys.argv", ["run.py", "--init-admin"])
    monkeypatch.setattr("builtins.input", lambda _: "ownadmin")
    monkeypatch.setattr("getpass.getpass", lambda _: "Private@2026")
    with pytest.raises(SystemExit):
        runpy.run_path(str(Path(__file__).parents[1] / "run.py"), run_name="__main__")
    with application.app_context():
        db = get_db()
        u = user(db, "ownadmin")
        assert u["role"] == "admin" and check_password_hash(
            u["password_hash"], "Private@2026"
        )
        assert db.execute("SELECT COUNT(*) FROM role_permissions").fetchone()[0] == 7
        assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
