import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

DB_FILE = "organizer_index.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    original_name TEXT,
    source_path TEXT,
    final_path TEXT,
    category TEXT,
    method TEXT,
    confidence REAL,
    reason TEXT,
    sha256 TEXT,
    size_bytes INTEGER,
    moved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename);
CREATE INDEX IF NOT EXISTS idx_files_sha256 ON files(sha256);
CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);
"""


class FileIndex:
    """SQLite index of every organized file. Powers --find, --report and duplicate detection."""

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def add(self, filename: str, original_name: str, source_path: str, final_path: str,
            category: str, method: str, confidence: float, reason: str,
            sha256: str = "", size_bytes: int = 0, moved_at: Optional[str] = None):
        self.conn.execute(
            "INSERT INTO files (filename, original_name, source_path, final_path, category, "
            "method, confidence, reason, sha256, size_bytes, moved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (filename, original_name, source_path, final_path, category, method,
             confidence, reason, sha256, size_bytes, moved_at or datetime.now().isoformat())
        )
        self.conn.commit()

    def remove_by_final_path(self, final_path: str):
        """Remove a record after an undo restores the file."""
        self.conn.execute("DELETE FROM files WHERE final_path = ?", (final_path,))
        self.conn.commit()

    def get_by_final_path(self, final_path: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM files WHERE final_path = ? LIMIT 1", (final_path,)
        ).fetchone()

    def update_final_path(self, old_path: str, new_path: str):
        """Keep the index in sync when a file is relocated (e.g. by --dedupe)."""
        self.conn.execute(
            "UPDATE files SET final_path = ? WHERE final_path = ?", (new_path, old_path)
        )
        self.conn.commit()

    def find_by_hash(self, sha256: str) -> Optional[sqlite3.Row]:
        """Return the first indexed file with this hash whose copy still exists on disk."""
        if not sha256:
            return None
        rows = self.conn.execute(
            "SELECT * FROM files WHERE sha256 = ? ORDER BY moved_at DESC", (sha256,)
        ).fetchall()
        for row in rows:
            if row["final_path"] and os.path.exists(row["final_path"]):
                return row
        return None

    def search(self, query: str, limit: int = 30) -> List[sqlite3.Row]:
        """Search filename, original name, category and reason. Terms are ANDed."""
        terms = [t for t in query.lower().split() if t]
        if not terms:
            return []
        where = []
        params: list = []
        for t in terms:
            like = f"%{t}%"
            where.append(
                "(LOWER(filename) LIKE ? OR LOWER(original_name) LIKE ? "
                "OR LOWER(category) LIKE ? OR LOWER(reason) LIKE ?)"
            )
            params.extend([like, like, like, like])
        sql = (
            "SELECT * FROM files WHERE " + " AND ".join(where) +
            " ORDER BY moved_at DESC LIMIT ?"
        )
        params.append(limit)
        return self.conn.execute(sql, params).fetchall()

    def report(self, days: int = 7) -> dict:
        """Aggregate stats for --report."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        total = self.conn.execute("SELECT COUNT(*) c, COALESCE(SUM(size_bytes),0) s FROM files").fetchone()
        recent = self.conn.execute(
            "SELECT COUNT(*) c FROM files WHERE moved_at >= ?", (since,)
        ).fetchone()
        by_category = self.conn.execute(
            "SELECT category, COUNT(*) c, COALESCE(SUM(size_bytes),0) s FROM files "
            "GROUP BY category ORDER BY c DESC"
        ).fetchall()
        recent_by_category = self.conn.execute(
            "SELECT category, COUNT(*) c FROM files WHERE moved_at >= ? "
            "GROUP BY category ORDER BY c DESC", (since,)
        ).fetchall()
        otros = self.conn.execute(
            "SELECT COUNT(*) c FROM files WHERE category = 'Otros' OR category LIKE 'Otros/%'"
        ).fetchone()
        low_confidence = self.conn.execute(
            "SELECT filename, category, confidence FROM files WHERE confidence < 0.5 "
            "ORDER BY moved_at DESC LIMIT 10"
        ).fetchall()
        duplicates = self.conn.execute(
            "SELECT sha256, COUNT(*) c FROM files WHERE sha256 != '' "
            "GROUP BY sha256 HAVING c > 1"
        ).fetchall()
        return {
            "total_files": total["c"],
            "total_bytes": total["s"],
            "recent_files": recent["c"],
            "days": days,
            "by_category": by_category,
            "recent_by_category": recent_by_category,
            "otros_count": otros["c"],
            "low_confidence": low_confidence,
            "duplicate_groups": len(duplicates),
        }

    def import_history(self, history_path: str = "organizer_history.json") -> int:
        """One-time import of the legacy JSON history into the index."""
        if not os.path.exists(history_path):
            return 0
        existing = self.conn.execute("SELECT COUNT(*) c FROM files").fetchone()["c"]
        if existing > 0:
            return 0
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return 0
        imported = 0
        for item in data:
            if item.get("category") == "IGNORED":
                continue
            filename = item.get("filename", "")
            target = item.get("target_folder", "")
            final_path = item.get("final_path") or (os.path.join(target, filename) if target else "")
            self.conn.execute(
                "INSERT INTO files (filename, original_name, source_path, final_path, category, "
                "method, confidence, reason, sha256, size_bytes, moved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', 0, ?)",
                (filename, filename, item.get("source_path", ""), final_path,
                 item.get("category", ""), item.get("method", ""),
                 item.get("confidence", 0), item.get("reason", ""),
                 item.get("timestamp", ""))
            )
            imported += 1
        self.conn.commit()
        return imported
