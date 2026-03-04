import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = Path.home() / ".tenrix" / "sessions.db"


class SessionStore:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH))
        self._create_tables()

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                file_path TEXT,
                file_name TEXT,
                created_at TEXT,
                row_count INTEGER,
                col_count INTEGER,
                engine TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                result_id TEXT PRIMARY KEY,
                session_id TEXT,
                analysis_id TEXT,
                analysis_name TEXT,
                success INTEGER,
                summary_json TEXT,
                data_json TEXT,
                interpretation TEXT,
                created_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        self._conn.commit()

    def create_session(self, file_path: str, load_result) -> str:
        session_id = str(uuid.uuid4())
        try:
            self._conn.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, file_path, getattr(load_result, 'file_name', ''),
                 datetime.now().isoformat(),
                 getattr(load_result, 'row_count', 0),
                 getattr(load_result, 'col_count', 0),
                 getattr(load_result, 'engine', 'pandas')),
            )
            self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
        return session_id

    def save_result(self, session_id: str, result) -> str:
        result_id = str(uuid.uuid4())
        try:
            self._conn.execute(
                "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (result_id, session_id,
                 getattr(result, 'analysis_id', ''),
                 getattr(result, 'analysis_name', ''),
                 1 if getattr(result, 'success', False) else 0,
                 json.dumps(getattr(result, 'summary', {}), default=str),
                 json.dumps(getattr(result, 'data', {}), default=str),
                 getattr(result, 'interpretation', ''),
                 datetime.now().isoformat()),
            )
            self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
        return result_id

    def get_results(self, session_id: str) -> list:
        try:
            cursor = self._conn.execute(
                "SELECT * FROM results WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            )
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get results: {e}")
            return []

    def get_recent_sessions(self, limit: int = 10) -> list[dict]:
        try:
            cursor = self._conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get recent sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> None:
        try:
            self._conn.execute("DELETE FROM results WHERE session_id = ?", (session_id,))
            self._conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
