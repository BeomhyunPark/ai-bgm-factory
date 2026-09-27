import fcntl
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import FactoryError


@contextmanager
def run_lock(root):
    with (root / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise FactoryError("Run is already locked by another process") from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


class Store:
    def __init__(self, data_dir):
        self.path = data_dir / "app.db"
        self.db = sqlite3.connect(self.path, timeout=15)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        # BEGIN IMMEDIATE serializes migration discovery and application across processes.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
            )
            current = {r[0] for r in self.db.execute("SELECT version FROM schema_migrations")}
            for file in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
                version = int(file.name.split("_")[0])
                if version not in current:
                    for statement in file.read_text().split(";"):
                        if statement.strip():
                            self.db.execute(statement)
                    self.db.execute("INSERT INTO schema_migrations VALUES (?)", (version,))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            self.db.close()
            raise

    def save(self, manifest):
        m = manifest
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?)",
                (m["run_id"], m["status"], m["config_hash"], m["updated_at"], json.dumps(m)),
            )
            for s in m["stages"]:
                self.db.execute(
                    "INSERT OR REPLACE INTO stages VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        m["run_id"],
                        s["name"],
                        s["attempt"],
                        s["status"],
                        s["input_hash"],
                        s.get("duration_ms"),
                    ),
                )
            for a in m["artifacts"]:
                self.db.execute(
                    "INSERT OR REPLACE INTO artifacts VALUES (?, ?, ?, ?)",
                    (m["run_id"], a["path"], a["sha256"], a["bytes"]),
                )

    def close(self):
        self.db.close()
