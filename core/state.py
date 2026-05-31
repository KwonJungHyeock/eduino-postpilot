"""
Eduino_PostPilot - 발행 상태 관리 (SQLite)
------------------------------------------------------------
어떤 제품을 이미 처리/발행했는지 추적합니다.
상태: none(미작업) / draft(초안생성됨) / published(발행됨)
"""
from __future__ import annotations

import sqlite3
from contextlib import closing

import config


def _conn() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.STATE_DB)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS product_state (
            code TEXT PRIMARY KEY,
            name TEXT,
            status TEXT DEFAULT 'none',
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )"""
    )
    return conn


def get_status(code: str) -> str:
    with closing(_conn()) as c:
        row = c.execute("SELECT status FROM product_state WHERE code=?", (code,)).fetchone()
        return row[0] if row else "none"


def set_status(code: str, name: str, status: str) -> None:
    with closing(_conn()) as c:
        c.execute(
            """INSERT INTO product_state (code, name, status, updated_at)
               VALUES (?,?,?, datetime('now','localtime'))
               ON CONFLICT(code) DO UPDATE SET
                 status=excluded.status,
                 name=excluded.name,
                 updated_at=excluded.updated_at""",
            (code, name, status),
        )
        c.commit()


STATUS_LABEL = {
    "none": "⚪ 미작업",
    "draft": "🟡 초안 생성됨",
    "published": "🟢 발행 완료",
}
