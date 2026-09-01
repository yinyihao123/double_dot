import sqlite3
import time
import json


class SQLiteTaskStore:
    def __init__(self, path="workspace/tasks.db"):
        self.path = path
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _initialize(self):
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, status TEXT NOT NULL, goal TEXT NOT NULL,
                result TEXT, error TEXT, step INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL, updated_at REAL NOT NULL
            )""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(tasks)")}
            for name in ("phase", "plan", "latest_tool", "next_action", "trace"):
                if name not in columns:
                    db.execute(f"ALTER TABLE tasks ADD COLUMN {name} TEXT")

    def save(self, snapshot):
        with self._connect() as db:
            db.execute("""INSERT OR REPLACE INTO tasks
                (task_id,status,goal,result,error,step,created_at,updated_at,phase,plan,latest_tool,next_action,trace)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", tuple(
                json.dumps(snapshot.get("trace", [])[-100:], ensure_ascii=False) if k == "trace" else snapshot.get(k)
                for k in (
                    "task_id", "status", "goal", "result", "error", "step", "created_at", "updated_at",
                    "phase", "plan", "latest_tool", "next_action", "trace")))

    def get(self, task_id):
        with self._connect() as db:
            row = db.execute("SELECT task_id,status,goal,result,error,step,created_at,updated_at,phase,plan,latest_tool,next_action,trace FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            return None
        data = dict(zip(("task_id", "status", "goal", "result", "error", "step", "created_at", "updated_at", "phase", "plan", "latest_tool", "next_action", "trace"), row))
        try:
            data["trace"] = json.loads(data["trace"] or "[]")
        except (TypeError, ValueError):
            data["trace"] = []
        return data

    def list(self):
        with self._connect() as db:
            rows = db.execute("SELECT task_id,status,goal,result,error,step,created_at,updated_at,phase,plan,latest_tool,next_action,trace FROM tasks ORDER BY created_at DESC").fetchall()
        keys = ("task_id", "status", "goal", "result", "error", "step", "created_at", "updated_at", "phase", "plan", "latest_tool", "next_action", "trace")
        result = []
        for row in rows:
            item = dict(zip(keys, row))
            try: item["trace"] = json.loads(item["trace"] or "[]")
            except (TypeError, ValueError): item["trace"] = []
            result.append(item)
        return result

    def mark_interrupted(self):
        now = time.time()
        with self._connect() as db:
            db.execute("""UPDATE tasks SET status='FAILED', error=?, updated_at=?
                         WHERE status IN ('RUNNING', 'WAITING')""",
                       ("任务因进程重启而中断。", now))
