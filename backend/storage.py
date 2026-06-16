import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "drink_machine.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pump_assignments (
                pump_id    INTEGER PRIMARY KEY,
                ingredient TEXT NOT NULL DEFAULT ''
            )
            """
        )
        for pump_id in range(1, 9):
            conn.execute(
                "INSERT OR IGNORE INTO pump_assignments (pump_id, ingredient) VALUES (?, '')",
                (pump_id,),
            )


def get_assignments() -> dict[int, str]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT pump_id, ingredient FROM pump_assignments ORDER BY pump_id"
        ).fetchall()
    return {row["pump_id"]: row["ingredient"] for row in rows}


def set_assignment(pump_id: int, ingredient: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE pump_assignments SET ingredient = ? WHERE pump_id = ?",
            (ingredient.strip(), pump_id),
        )
