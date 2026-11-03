"""Хранилище на SQLite: пользователи, тренировки и шаги по дням."""
import sqlite3
from datetime import date, timedelta
from pathlib import Path


class Database:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                chat_id   INTEGER PRIMARY KEY,
                paused    INTEGER NOT NULL DEFAULT 0,
                skip_date TEXT
            );
            CREATE TABLE IF NOT EXISTS workouts (
                chat_id INTEGER NOT NULL,
                day     TEXT NOT NULL,
                PRIMARY KEY (chat_id, day)
            );
            CREATE TABLE IF NOT EXISTS steps (
                chat_id INTEGER NOT NULL,
                day     TEXT NOT NULL,
                steps   INTEGER NOT NULL,
                PRIMARY KEY (chat_id, day)
            );
            """
        )
        self.conn.commit()

    # ---- пользователи ----
    def add_user(self, chat_id: int) -> None:
        self.conn.execute(
            "INSERT INTO users (chat_id) VALUES (?) "
            "ON CONFLICT(chat_id) DO UPDATE SET paused = 0",
            (chat_id,),
        )
        self.conn.commit()

    def active_users(self) -> list[int]:
        rows = self.conn.execute("SELECT chat_id FROM users WHERE paused = 0")
        return [r["chat_id"] for r in rows]

    def set_paused(self, chat_id: int, paused: bool) -> None:
        self.conn.execute(
            "UPDATE users SET paused = ? WHERE chat_id = ?", (int(paused), chat_id)
        )
        self.conn.commit()

    # ---- тренировки ----
    def log_workout(self, chat_id: int, day: date) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO workouts (chat_id, day) VALUES (?, ?)",
            (chat_id, day.isoformat()),
        )
        self.conn.commit()

    def last_workout(self, chat_id: int) -> date | None:
        row = self.conn.execute(
            "SELECT MAX(day) AS d FROM workouts WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return date.fromisoformat(row["d"]) if row and row["d"] else None

    def count_workouts(self, chat_id: int, since: date) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS c FROM workouts WHERE chat_id = ? AND day >= ?",
            (chat_id, since.isoformat()),
        ).fetchone()
        return row["c"]

    def set_skip(self, chat_id: int, day: date) -> None:
        self.conn.execute(
            "UPDATE users SET skip_date = ? WHERE chat_id = ?",
            (day.isoformat(), chat_id),
        )
        self.conn.commit()

    def skipped_on(self, chat_id: int, day: date) -> bool:
        row = self.conn.execute(
            "SELECT skip_date FROM users WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return bool(row and row["skip_date"] == day.isoformat())

    # ---- шаги ----
    def set_steps(self, chat_id: int, day: date, steps: int) -> None:
        self.conn.execute(
            "INSERT INTO steps (chat_id, day, steps) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id, day) DO UPDATE SET steps = excluded.steps",
            (chat_id, day.isoformat(), steps),
        )
        self.conn.commit()

    def get_steps(self, chat_id: int, day: date) -> int | None:
        row = self.conn.execute(
            "SELECT steps FROM steps WHERE chat_id = ? AND day = ?",
            (chat_id, day.isoformat()),
        ).fetchone()
        return row["steps"] if row else None

    def steps_history(self, chat_id: int, today: date, days: int = 7) -> list[tuple[date, int | None]]:
        """Шаги за последние `days` дней (от старых к новым); None — нет данных."""
        result = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            result.append((d, self.get_steps(chat_id, d)))
        return result
