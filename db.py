import sqlite3
from contextlib import contextmanager
from datetime import datetime

from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                done_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS ai_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                goal TEXT,
                plan_text TEXT,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS monthly_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                year INTEGER,
                month INTEGER,
                day INTEGER,
                text TEXT,
                done INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TEXT
            )
        """)


def upsert_user(user_id: int, username: str, first_name: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
        if c.fetchone() is None:
            c.execute(
                "INSERT INTO users (user_id, username, first_name, created_at) VALUES (?,?,?,?)",
                (user_id, username, first_name, datetime.utcnow().isoformat()),
            )


def get_all_user_ids():
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [r["user_id"] for r in rows]


# ---------- Tasks ("Rejalarim") ----------

def add_task(user_id: int, title: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO tasks (user_id, title, status, created_at) VALUES (?,?, 'pending', ?)",
            (user_id, title, datetime.utcnow().isoformat()),
        )


def get_tasks(user_id: int, status: str = None):
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id=? AND status=? ORDER BY id DESC",
                (user_id, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id=? ORDER BY id DESC", (user_id,)
            ).fetchall()
        return rows


def set_task_status(task_id: int, user_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status=?, done_at=? WHERE id=? AND user_id=?",
            (status, datetime.utcnow().isoformat() if status == "done" else None, task_id, user_id),
        )


def delete_task(task_id: int, user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))


# ---------- AI plans ----------

def save_ai_plan(user_id: int, goal: str, plan_text: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ai_plans (user_id, goal, plan_text, created_at) VALUES (?,?,?,?)",
            (user_id, goal, plan_text, datetime.utcnow().isoformat()),
        )


def get_ai_plans(user_id: int, limit: int = 10):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM ai_plans WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


# ---------- Monthly entries ----------

def add_monthly_entry(user_id: int, year: int, month: int, day: int, text: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO monthly_entries (user_id, year, month, day, text, done, created_at) "
            "VALUES (?,?,?,?,?,0,?)",
            (user_id, year, month, day, text, datetime.utcnow().isoformat()),
        )


def get_month_entries(user_id: int, year: int, month: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM monthly_entries WHERE user_id=? AND year=? AND month=? ORDER BY day ASC, id ASC",
            (user_id, year, month),
        ).fetchall()


def get_day_entries(user_id: int, year: int, month: int, day: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM monthly_entries WHERE user_id=? AND year=? AND month=? AND day=? ORDER BY id ASC",
            (user_id, year, month, day),
        ).fetchall()


def toggle_monthly_entry(entry_id: int, user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT done FROM monthly_entries WHERE id=? AND user_id=?", (entry_id, user_id)
        ).fetchone()
        if row is not None:
            new_val = 0 if row["done"] else 1
            conn.execute(
                "UPDATE monthly_entries SET done=? WHERE id=? AND user_id=?",
                (new_val, entry_id, user_id),
            )


def delete_monthly_entry(entry_id: int, user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM monthly_entries WHERE id=? AND user_id=?", (entry_id, user_id))


# ---------- Chat history (AI bilan suhbat) ----------

def add_chat_message(user_id: int, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_history (user_id, role, content, created_at) VALUES (?,?,?,?)",
            (user_id, role, content, datetime.utcnow().isoformat()),
        )
        # eski xabarlarni tozalash: faqat oxirgi 30 tasini saqlaymiz
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM chat_history WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()]
        if len(ids) > 30:
            old_ids = ids[30:]
            conn.executemany("DELETE FROM chat_history WHERE id=?", [(i,) for i in old_ids])


def get_chat_history(user_id: int, limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return list(reversed(rows))


def clear_chat_history(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM chat_history WHERE user_id=?", (user_id,))


# ---------- Natijalarim (statistika) ----------

def get_stats(user_id: int):
    with get_conn() as conn:
        total_tasks = conn.execute(
            "SELECT COUNT(*) c FROM tasks WHERE user_id=?", (user_id,)
        ).fetchone()["c"]
        done_tasks = conn.execute(
            "SELECT COUNT(*) c FROM tasks WHERE user_id=? AND status='done'", (user_id,)
        ).fetchone()["c"]
        ai_plans_count = conn.execute(
            "SELECT COUNT(*) c FROM ai_plans WHERE user_id=?", (user_id,)
        ).fetchone()["c"]
        now = datetime.utcnow()
        month_total = conn.execute(
            "SELECT COUNT(*) c FROM monthly_entries WHERE user_id=? AND year=? AND month=?",
            (user_id, now.year, now.month),
        ).fetchone()["c"]
        month_done = conn.execute(
            "SELECT COUNT(*) c FROM monthly_entries WHERE user_id=? AND year=? AND month=? AND done=1",
            (user_id, now.year, now.month),
        ).fetchone()["c"]
        return {
            "total_tasks": total_tasks,
            "done_tasks": done_tasks,
            "ai_plans_count": ai_plans_count,
            "month_total": month_total,
            "month_done": month_done,
        }
