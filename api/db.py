"""Persistencia SQLite — historial de análisis clínicos."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS analisis (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    nota TEXT NOT NULL,
    resultado_json TEXT NOT NULL,
    ejemplo_id TEXT NOT NULL DEFAULT 'propia',
    idioma TEXT NOT NULL DEFAULT 'spanish',
    mock_llm INTEGER NOT NULL DEFAULT 1,
    alerta INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_analisis_created_at ON analisis(created_at DESC);
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HistorialDB:
    """Acceso SQLite al historial de análisis."""

    def __init__(self, db_path: Path, max_items: int = 50) -> None:
        self.db_path = Path(db_path)
        self.max_items = max(1, int(max_items))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            self._ensure_column(conn, "pdf_origen", "TEXT")
            self._ensure_column(conn, "pdf_muestra_id", "TEXT")

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, name: str, col_type: str) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(analisis)").fetchall()}
        if name not in cols:
            conn.execute(f"ALTER TABLE analisis ADD COLUMN {name} {col_type}")

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        resultado = json.loads(row["resultado_json"])
        keys = row.keys()
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "nota": row["nota"],
            "resultado": resultado,
            "ejemplo_id": row["ejemplo_id"],
            "idioma": row["idioma"],
            "mock_llm": bool(row["mock_llm"]),
            "alerta": bool(row["alerta"]),
            "pdf_origen": row["pdf_origen"] if "pdf_origen" in keys else None,
            "pdf_muestra_id": row["pdf_muestra_id"] if "pdf_muestra_id" in keys else None,
        }

    def save_analisis(
        self,
        *,
        nota: str,
        resultado: dict[str, Any],
        ejemplo_id: str = "propia",
        idioma: str = "spanish",
        mock_llm: bool = True,
        alerta: bool = False,
        pdf_origen: str | None = None,
        pdf_muestra_id: str | None = None,
    ) -> dict[str, Any]:
        entry_id = str(uuid.uuid4())
        created_at = _utc_now_iso()
        payload = json.dumps(resultado, ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO analisis (
                    id, created_at, nota, resultado_json,
                    ejemplo_id, idioma, mock_llm, alerta,
                    pdf_origen, pdf_muestra_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    created_at,
                    nota,
                    payload,
                    ejemplo_id,
                    idioma,
                    int(mock_llm),
                    int(alerta),
                    pdf_origen,
                    pdf_muestra_id,
                ),
            )
            self._trim_old_rows(conn)

        return {
            "id": entry_id,
            "created_at": created_at,
            "nota": nota,
            "resultado": resultado,
            "ejemplo_id": ejemplo_id,
            "idioma": idioma,
            "mock_llm": mock_llm,
            "alerta": alerta,
            "pdf_origen": pdf_origen,
            "pdf_muestra_id": pdf_muestra_id,
        }

    def _trim_old_rows(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            DELETE FROM analisis
            WHERE id NOT IN (
                SELECT id FROM analisis
                ORDER BY created_at DESC
                LIMIT ?
            )
            """,
            (self.max_items,),
        )

    def list_analisis(self, limit: int = 10) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), self.max_items))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, nota, resultado_json,
                       ejemplo_id, idioma, mock_llm, alerta,
                       pdf_origen, pdf_muestra_id
                FROM analisis
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_analisis(self, entry_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, created_at, nota, resultado_json,
                       ejemplo_id, idioma, mock_llm, alerta,
                       pdf_origen, pdf_muestra_id
                FROM analisis WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def delete_analisis(self, entry_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM analisis WHERE id = ?", (entry_id,))
            deleted = cur.rowcount > 0
        return deleted

    def clear_analisis(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM analisis")
            n = cur.rowcount
        return n

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM analisis").fetchone()
        return int(row["n"]) if row else 0
