import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "drink_machine.db")

# Flow rate measured with water: 25 ml in 15 s. Each pump can be re-calibrated
# in place with its actual liquid, which captures both pump variance and viscosity.
DEFAULT_ML_PER_S = round(25 / 15, 4)  # ~1.6667 ml/s


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS pump_assignments (
                pump_id    INTEGER PRIMARY KEY,
                ingredient TEXT NOT NULL DEFAULT '',
                ml_per_s   REAL NOT NULL DEFAULT {DEFAULT_ML_PER_S}
            )
            """
        )
        # Migrate databases created before the ml_per_s column existed.
        cols = [row[1] for row in conn.execute("PRAGMA table_info(pump_assignments)")]
        if "ml_per_s" not in cols:
            conn.execute(
                f"ALTER TABLE pump_assignments ADD COLUMN ml_per_s REAL NOT NULL DEFAULT {DEFAULT_ML_PER_S}"
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


def get_flow_rates() -> dict[int, float]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT pump_id, ml_per_s FROM pump_assignments ORDER BY pump_id"
        ).fetchall()
    return {row["pump_id"]: row["ml_per_s"] for row in rows}


def get_flow_rate(pump_id: int) -> float:
    with _conn() as conn:
        row = conn.execute(
            "SELECT ml_per_s FROM pump_assignments WHERE pump_id = ?", (pump_id,)
        ).fetchone()
    return row["ml_per_s"] if row else DEFAULT_ML_PER_S


def set_flow_rate(pump_id: int, ml_per_s: float) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE pump_assignments SET ml_per_s = ? WHERE pump_id = ?",
            (ml_per_s, pump_id),
        )
