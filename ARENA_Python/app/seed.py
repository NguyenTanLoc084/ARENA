"""Dữ liệu DEMO giả lập; không sử dụng MSSV thật. Idempotent, không xóa dữ liệu."""

from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
from .db import transaction, now
from .tournament import create_schedule
from .matches import save_game

PERMISSIONS = {
    "admin": ["admin", "audit"],
    "organizer": ["event", "result", "audit"],
    "referee": ["result"],
    "student": ["team"],
}


def seed_demo():
    with transaction() as db:
        if db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return False
        for role, perms in PERMISSIONS.items():
            for p in perms:
                db.execute(
                    "INSERT OR IGNORE INTO role_permissions VALUES(?,?)", (role, p)
                )
        db.execute("INSERT INTO colleges VALUES(1,'Công nghệ thông tin')")
        db.execute("INSERT INTO classes VALUES(1,1,'CNTT K50')")
        for username, role in [
            ("admin", "admin"),
            ("btc", "organizer"),
            ("trongtai", "referee"),
        ]:
            db.execute(
                "INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                (username, generate_password_hash("Arena@2026"), role),
            )
        for hero in [
            "Valhein",
            "Krixi",
            "Butterfly",
            "Thane",
            "Maloch",
            "Violet",
            "Nakroth",
            "Alice",
            "Lauriel",
            "Yorn",
        ]:
            db.execute("INSERT INTO heroes(name) VALUES(?)", (hero,))
        names = [
            ("HCMUE Phoenix", "PHX"),
            ("Saigon Titans", "TTN"),
            ("Cyber Wolves", "WLF"),
            ("Lotus Gaming", "LTS"),
        ]
        for index, (name, tag) in enumerate(names):
            members = []
            for j in range(7):
                number = index * 7 + j + 1
                sid = db.execute(
                    "INSERT INTO students(code,full_name,game_id,ign,class_id) VALUES(?,?,?,?,1)",
                    (
                        f"DEMO{number:03}",
                        f"Sinh viên mẫu {number}",
                        f"GAME{number:03}",
                        f"{tag} · Player{j + 1}",
                    ),
                ).lastrowid
                members.append(sid)
                username = f"doitruong{index + 1}" if j == 0 else f"sv{number:02}"
                db.execute(
                    "INSERT INTO users(username,password_hash,student_id,role) VALUES(?,?,?,'student')",
                    (username, generate_password_hash("Arena@2026"), sid),
                )
            tid = db.execute(
                "INSERT INTO teams(name,tag,captain_id) VALUES(?,?,?)",
                (name, tag, members[0]),
            ).lastrowid
            for sid in members:
                db.execute(
                    "INSERT INTO memberships(team_id,student_id,status) VALUES(?,?,'accepted')",
                    (tid, sid),
                )
        n = datetime.now(timezone.utc)
        fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M")
        # First: locked registration, ready for schedule; second: live seeded; third: open demo.
        e1 = db.execute(
            "INSERT INTO events(name,format,status,opens,closes,pool) VALUES(?,'knockout','locked',?,?,5000000)",
            (
                "HCMUE Campus Cup",
                fmt(n - timedelta(days=10)),
                fmt(n - timedelta(days=1)),
            ),
        ).lastrowid
        e2 = db.execute(
            "INSERT INTO events(name,format,status,opens,closes,pool) VALUES(?,'roundrobin','locked',?,?,3000000)",
            (
                "Student League · Mùa thu",
                fmt(n - timedelta(days=10)),
                fmt(n - timedelta(days=1)),
            ),
        ).lastrowid
        db.execute(
            "INSERT INTO events(name,format,status,opens,closes,pool) VALUES(?,'knockout','open',?,?,2000000)",
            (
                "Freshman Open · Chào tân sinh viên",
                fmt(n - timedelta(days=1)),
                fmt(n + timedelta(days=30)),
            ),
        )
        for eid in [e1, e2]:
            for team in db.execute("SELECT * FROM teams").fetchall():
                entry = db.execute(
                    "INSERT INTO entries(event_id,team_id,status,reviewer_id,created) VALUES(?,?,'approved',2,?)",
                    (eid, team["id"], now()),
                ).lastrowid
                for i, member in enumerate(
                    db.execute(
                        "SELECT student_id FROM memberships WHERE team_id=? ORDER BY student_id",
                        (team["id"],),
                    ).fetchall()
                ):
                    db.execute(
                        "INSERT INTO rosters(entry_id,event_id,student_id,starter,holding) VALUES(?,?,?,?,1)",
                        (entry, eid, member[0], int(i < 5)),
                    )
            for rank, amount in [
                (1, 2000000 if eid == e2 else 3000000),
                (2, 1000000 if eid == e2 else 2000000),
            ]:
                db.execute("INSERT INTO prizes VALUES(?,?,?)", (eid, rank, amount))
        organizer = db.execute("SELECT * FROM users WHERE username='btc'").fetchone()
        create_schedule(db, organizer, e2, 3, fmt(n + timedelta(days=1)), 3)
        db.execute("UPDATE events SET status='live' WHERE id=?", (e2,))
        m = db.execute(
            "SELECT * FROM matches WHERE event_id=? ORDER BY id LIMIT 1", (e2,)
        ).fetchone()
        db.execute("UPDATE matches SET state='live' WHERE id=?", (m["id"],))
        rows = []
        for tid in [m["team_a"], m["team_b"]]:
            for sid in db.execute(
                "SELECT r.student_id FROM rosters r JOIN entries e ON e.id=r.entry_id WHERE e.event_id=? AND e.team_id=? AND r.starter=1",
                (e2, tid),
            ).fetchall():
                rows.append(
                    dict(
                        student_id=sid[0],
                        team_id=tid,
                        hero_id=1,
                        kills=2 if tid == m["team_a"] else 1,
                        deaths=1 if tid == m["team_a"] else 2,
                        assists=3,
                        gold=8000,
                    )
                )
        save_game(db, organizer, m["id"], 1, 1, m["team_a"], 1100, rows)
    return True
