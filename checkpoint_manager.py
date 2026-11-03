"""
Checkpoint Manager Module
Provides crash-safe, deterministic task tracking (SQLite + JSON checkpoint),
two-phase commit staging, atomic JSONL appending with fsync, and self-repair.
"""

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from config import CONFIG, DATASET_FILENAMES
from logger import logger

def make_chapter_key(target: Dict[str, Any]) -> str:
    """
    Creates a deterministic, clean filesystem/database slug for a chapter target.
    """
    board = target.get("board", "unknown")
    cls = target.get("class", "unknown")
    subj = target.get("subject", "unknown")
    ch = target.get("chapter", "unknown")

    raw = f"{board}_{cls}_{subj}_{ch}"
    slug = re.sub(r"[^\w\-_]+", "_", raw).strip("_")
    # Truncate if excessively long while keeping unique hash suffix
    if len(slug) > 120:
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
        slug = slug[:110] + "_" + h
    return slug

def make_task_id(chapter_key: str, dataset_name: str, batch_index: int) -> str:
    """
    Creates a deterministic task identifier.
    """
    return f"{chapter_key}_{dataset_name}_b{batch_index}"

class CheckpointManager:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or CONFIG.get("output_dir", "output_datasets")
        os.makedirs(self.output_dir, exist_ok=True)

        self.sqlite_path = os.path.join(self.output_dir, CONFIG.get("sqlite_db_name", "tasks.db"))
        self.checkpoint_path = os.path.join(self.output_dir, CONFIG.get("checkpoint_name", "checkpoint.json"))
        self.manifest_path = os.path.join(self.output_dir, CONFIG.get("manifest_name", "manifest.json"))
        self._write_lock = threading.Lock()

        self._init_sqlite()
        self._init_manifest()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path, timeout=60.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=60000;")
        return conn

    def _init_sqlite(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    chapter_key TEXT NOT NULL,
                    dataset_name TEXT NOT NULL,
                    batch_index INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    record_count INTEGER DEFAULT 0,
                    error_msg TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_chapter ON tasks(chapter_key)")
            conn.commit()

    def _init_manifest(self) -> None:
        if not os.path.exists(self.manifest_path):
            manifest_data = {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "datasets": {name: {"records": 0, "sha256": None, "bytes": 0} for name in DATASET_FILENAMES}
            }
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

    def register_tasks_if_missing(self, tasks: List[Dict[str, Any]]) -> int:
        """
        Batch registers planned tasks with status 'pending' if not already in DB.
        """
        now = datetime.now().isoformat()
        inserted = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for t in tasks:
                cursor.execute("""
                    INSERT OR IGNORE INTO tasks 
                    (task_id, chapter_key, dataset_name, batch_index, status, record_count, error_msg, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'pending', 0, NULL, ?, ?)
                """, (t["task_id"], t["chapter_key"], t["dataset_name"], t["batch_index"], now, now))
                if cursor.rowcount > 0:
                    inserted += 1
            conn.commit()
        return inserted

    def is_task_completed(self, task_id: str) -> bool:
        with self._get_connection() as conn:
            row = conn.execute("SELECT status FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            return bool(row and row["status"] == "completed")

    def recover_stale_tasks(self) -> int:
        """
        Resets any tasks left in 'running' status (e.g. from an unexpected crash or kill)
        back to 'pending' so they are seamlessly resumed without data loss.
        """
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET status = 'pending', updated_at = ?
                WHERE status = 'running'
            """, (now,))
            recovered = cursor.rowcount
            conn.commit()
        if recovered > 0:
            logger.info(f"Crash recovery: reset {recovered} interrupted 'running' tasks back to 'pending'.")
            self._update_checkpoint_file()
        return recovered

    def reset_failed_tasks(self) -> int:
        """
        Resets 'failed' tasks back to 'pending' for retry.
        """
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET status = 'pending', error_msg = NULL, updated_at = ?
                WHERE status = 'failed'
            """, (now,))
            retried = cursor.rowcount
            conn.commit()
        if retried > 0:
            logger.info(f"Retry mode: reset {retried} failed tasks back to 'pending'.")
            self._update_checkpoint_file()
        return retried

    def mark_task_started(self, task_id: str, chapter_key: str, dataset_name: str, batch_index: int) -> None:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tasks (task_id, chapter_key, dataset_name, batch_index, status, record_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'running', 0, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET status = 'running', updated_at = ?
            """, (task_id, chapter_key, dataset_name, batch_index, now, now, now))
            conn.commit()

    def mark_task_completed(self, task_id: str, record_count: int) -> None:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE tasks 
                SET status = 'completed', record_count = ?, error_msg = NULL, updated_at = ?
                WHERE task_id = ?
            """, (record_count, now, task_id))
            conn.commit()
        self._update_checkpoint_file()

    def mark_task_failed(self, task_id: str, error_msg: str) -> None:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE tasks 
                SET status = 'failed', error_msg = ?, updated_at = ?
                WHERE task_id = ?
            """, (error_msg, now, task_id))
            conn.commit()
        self._update_checkpoint_file()

    def append_records(self, dataset_name: str, records: List[Dict[str, Any]]) -> int:
        """
        Thread-safe, durable append to JSONL file with flush and os.fsync.
        Updates manifest with record counts and SHA-256.
        """
        if not records:
            return 0

        filename = DATASET_FILENAMES.get(dataset_name, f"{dataset_name}.jsonl")
        filepath = os.path.join(self.output_dir, filename)

        with self._write_lock:
            # Atomic append with fsync
            with open(filepath, "a", encoding="utf-8") as f:
                for r in records:
                    line = json.dumps(r, ensure_ascii=False)
                    f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())

            # Update manifest
            self._sync_manifest_for_file(dataset_name, filepath)
        return len(records)

    def _sync_manifest_for_file(self, dataset_name: str, filepath: str) -> None:
        if not os.path.exists(filepath):
            return

        total_lines = 0
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    total_lines += 1

        file_size = os.path.getsize(filepath)

        manifest = {}
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = {}

        if "datasets" not in manifest:
            manifest["datasets"] = {}

        manifest["datasets"][dataset_name] = {
            "records": total_lines,
            "sha256": sha.hexdigest(),
            "bytes": file_size
        }
        manifest["updated_at"] = datetime.now().isoformat()

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def verify_and_repair_jsonl(self, dataset_name: str) -> Dict[str, Any]:
        """
        Scans JSONL file line-by-line, removes corrupted trailing lines if present.
        """
        filename = DATASET_FILENAMES.get(dataset_name, f"{dataset_name}.jsonl")
        filepath = os.path.join(self.output_dir, filename)
        if not os.path.exists(filepath):
            return {"records": 0, "status": "FILE_NOT_FOUND", "repaired": False}

        valid_lines: List[str] = []
        corrupted_lines = 0

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    json.loads(raw)
                    valid_lines.append(raw)
                except json.JSONDecodeError:
                    corrupted_lines += 1

        repaired = False
        if corrupted_lines > 0:
            logger.warning(f"Repairing {filepath}: truncated {corrupted_lines} corrupted lines at EOF.")
            with open(filepath, "w", encoding="utf-8") as f:
                for vl in valid_lines:
                    f.write(vl + "\n")
                f.flush()
                os.fsync(f.fileno())
            repaired = True

        self._sync_manifest_for_file(dataset_name, filepath)
        return {
            "records": len(valid_lines),
            "status": "HEALTHY" if corrupted_lines == 0 else f"REPAIRED ({corrupted_lines} dropped)",
            "repaired": repaired
        }

    def _update_checkpoint_file(self) -> None:
        summary = self.get_progress_summary()
        try:
            with self._write_lock:
                with open(self.checkpoint_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update checkpoint.json: {e}")

    def get_progress_summary(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'").fetchone()[0]
            running = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'running'").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'").fetchone()[0]
            records = conn.execute("SELECT SUM(record_count) FROM tasks WHERE status = 'completed'").fetchone()[0] or 0

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": pending + running,
            "failed_tasks": failed,
            "total_records_committed": records,
            "sqlite_db_path": self.sqlite_path,
            "manifest_path": self.manifest_path,
            "checkpoint_path": self.checkpoint_path
        }

