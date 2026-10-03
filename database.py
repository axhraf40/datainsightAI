"""Base de données SQLite : utilisateurs, fichiers, conversations."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

DB_PATH = os.path.join("data", "app.db")
SESSION_TTL_HOURS = 24

_USER_FILE_META = (
    "id, user_id, filename, stored_path, row_count, col_count, "
    "columns_json, rag_profile_json, cleaning_json, uploaded_at"
)
_MESSAGE_META = (
    "id, conversation_id, role, content, chart_path, display_df_json, "
    "code, pdf_path, created_at"
)


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _migrate_client_session_cache(conn: sqlite3.Connection) -> None:
    table = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='client_session_cache'"
    ).fetchone()
    if table:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(client_session_cache)")}
        if "browser_id" in cols:
            return
    conn.execute("DROP TABLE IF EXISTS client_session_cache")
    conn.execute(
        """
        CREATE TABLE client_session_cache (
            browser_id TEXT PRIMARY KEY,
            auth_token TEXT NOT NULL,
            auth_binding TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )


def _migrate_sessions_table(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(user_sessions)")}
    if "binding_hash" in cols:
        return
    conn.execute("DELETE FROM user_sessions")
    conn.execute("DROP TABLE user_sessions")
    conn.execute(
        """
        CREATE TABLE user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            binding_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_used_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )


def _migrate_blob_storage(conn: sqlite3.Connection) -> None:
    file_cols = {row[1] for row in conn.execute("PRAGMA table_info(user_files)")}
    if "file_data" not in file_cols:
        conn.execute("ALTER TABLE user_files ADD COLUMN file_data BLOB")

    msg_cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)")}
    if "chart_data" not in msg_cols:
        conn.execute("ALTER TABLE messages ADD COLUMN chart_data BLOB")
    if "pdf_data" not in msg_cols:
        conn.execute("ALTER TABLE messages ADD COLUMN pdf_data BLOB")

    # Migrer les anciens fichiers disque vers la BDD
    rows = conn.execute(
        "SELECT id, stored_path, file_data FROM user_files WHERE file_data IS NULL"
    ).fetchall()
    for row in rows:
        path = row["stored_path"]
        if path and os.path.isfile(path):
            with open(path, "rb") as handle:
                conn.execute(
                    "UPDATE user_files SET file_data = ?, stored_path = '' WHERE id = ?",
                    (handle.read(), row["id"]),
                )

    chart_rows = conn.execute(
        "SELECT id, chart_path, chart_data FROM messages WHERE chart_data IS NULL AND chart_path IS NOT NULL"
    ).fetchall()
    for row in chart_rows:
        path = row["chart_path"]
        if path and os.path.isfile(path):
            with open(path, "rb") as handle:
                conn.execute(
                    "UPDATE messages SET chart_data = ?, chart_path = NULL WHERE id = ?",
                    (handle.read(), row["id"]),
                )

    pdf_rows = conn.execute(
        "SELECT id, pdf_path, pdf_data FROM messages WHERE pdf_data IS NULL AND pdf_path IS NOT NULL"
    ).fetchall()
    for row in pdf_rows:
        path = row["pdf_path"]
        if path and os.path.isfile(path):
            with open(path, "rb") as handle:
                conn.execute(
                    "UPDATE messages SET pdf_data = ?, pdf_path = NULL WHERE id = ?",
                    (handle.read(), row["id"]),
                )


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                reset_token TEXT,
                reset_expires TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                row_count INTEGER DEFAULT 0,
                col_count INTEGER DEFAULT 0,
                columns_json TEXT,
                rag_profile_json TEXT,
                cleaning_json TEXT,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_id INTEGER,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (file_id) REFERENCES user_files(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                chart_path TEXT,
                display_df_json TEXT,
                code TEXT,
                pdf_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                binding_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )
        _migrate_sessions_table(conn)
        _migrate_client_session_cache(conn)
        # Migration pour ajouter la colonne code si elle n'existe pas
        try:
            conn.execute("SELECT code FROM messages LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE messages ADD COLUMN code TEXT")
        # Migration pour ajouter la colonne pdf_path si elle n'existe pas
        try:
            conn.execute("SELECT pdf_path FROM messages LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE messages ADD COLUMN pdf_path TEXT")
        _migrate_blob_storage(conn)


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now() -> str:
    return datetime.now().isoformat()


def create_user(email: str, username: str, password_hash: str) -> int | None:
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO users (email, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (email.lower().strip(), username.strip(), password_hash, _now()),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_user_profile_db(
    user_id: int, email: str, username: str, password_hash: str | None = None
) -> tuple[bool, str]:
    email = email.lower().strip()
    username = username.strip()
    if not email or not username:
        return False, "L'email et le nom d'utilisateur ne peuvent pas être vides."
    try:
        with get_connection() as conn:
            row = conn.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id)).fetchone()
            if row:
                return False, "Cet email est déjà utilisé par un autre compte."
            
            row = conn.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id)).fetchone()
            if row:
                return False, "Ce nom d'utilisateur est déjà pris par un autre compte."
            
            if password_hash:
                conn.execute(
                    "UPDATE users SET email = ?, username = ?, password_hash = ? WHERE id = ?",
                    (email, username, password_hash, user_id),
                )
                revoke_all_user_sessions(user_id)
            else:
                conn.execute(
                    "UPDATE users SET email = ?, username = ? WHERE id = ?",
                    (email, username, user_id),
                )
            return True, "Profil mis à jour avec succès."
    except Exception as e:
        return False, f"Erreur de base de données : {e}"


def set_reset_token(email: str, token: str, expires: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET reset_token = ?, reset_expires = ? WHERE email = ?",
            (token, expires, email.lower().strip()),
        )
        return cur.rowcount > 0


def reset_password(email: str, token: str, password_hash: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT reset_token, reset_expires FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
        if not row or row["reset_token"] != token:
            return False
        if row["reset_expires"] and row["reset_expires"] < _now():
            return False
        cur = conn.execute(
            "UPDATE users SET password_hash = ?, reset_token = NULL, reset_expires = NULL WHERE email = ?",
            (password_hash, email.lower().strip()),
        )
        if cur.rowcount > 0:
            user_row = conn.execute("SELECT id FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
            if user_row:
                conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_row["id"],))
        return cur.rowcount > 0


def save_user_file(
    user_id: int,
    filename: str,
    file_bytes: bytes,
    row_count: int,
    col_count: int,
    columns: list[str],
    rag_profile: dict,
    cleaning_report: dict,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO user_files
            (user_id, filename, stored_path, file_data, row_count, col_count, columns_json,
             rag_profile_json, cleaning_json, uploaded_at)
            VALUES (?, ?, '', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                filename,
                file_bytes,
                row_count,
                col_count,
                json.dumps(columns, ensure_ascii=False),
                json.dumps(rag_profile, ensure_ascii=False),
                json.dumps(cleaning_report, ensure_ascii=False),
                _now(),
            ),
        )
        return cur.lastrowid


def list_user_files(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {_USER_FILE_META} FROM user_files WHERE user_id = ? ORDER BY uploaded_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_user_file(file_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {_USER_FILE_META} FROM user_files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def get_user_file_bytes(file_id: int, user_id: int) -> bytes | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT file_data FROM user_files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
        if not row:
            return None
        data = row["file_data"]
        if data:
            return bytes(data)
        legacy = conn.execute(
            "SELECT stored_path FROM user_files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
        if legacy and legacy["stored_path"] and os.path.isfile(legacy["stored_path"]):
            with open(legacy["stored_path"], "rb") as handle:
                blob = handle.read()
            conn.execute(
                "UPDATE user_files SET file_data = ?, stored_path = '' WHERE id = ?",
                (blob, file_id),
            )
            return blob
        return None


def delete_user_file(file_id: int, user_id: int) -> bool:
    record = get_user_file(file_id, user_id)
    if not record:
        return False
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE file_id = ?)", (file_id,))
        conn.execute("DELETE FROM conversations WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM user_files WHERE id = ? AND user_id = ?", (file_id, user_id))
    return True


def create_conversation(user_id: int, file_id: int | None, title: str) -> int:
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO conversations (user_id, file_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, file_id, title, now, now),
        )
        return cur.lastrowid


def list_conversations(user_id: int, file_id: int | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if file_id:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE user_id = ? AND file_id = ? ORDER BY updated_at DESC",
                (user_id, file_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_conversation(conversation_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def touch_conversation(conversation_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_now(), conversation_id),
        )


def rename_conversation(conversation_id: int, user_id: int, new_title: str) -> None:
    """Renomme le titre d'une conversation (vérifie que l'user en est propriétaire)."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (new_title.strip(), _now(), conversation_id, user_id),
        )


def add_message(
    conversation_id: int,
    role: str,
    content: str,
    display_df_json: str | None = None,
    code: str | None = None,
    chart_bytes: bytes | None = None,
    pdf_bytes: bytes | None = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO messages
            (conversation_id, role, content, chart_path, display_df_json, code, pdf_path,
             chart_data, pdf_data, created_at)
            VALUES (?, ?, ?, NULL, ?, ?, NULL, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                content,
                display_df_json,
                code,
                chart_bytes,
                pdf_bytes,
                _now(),
            ),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_now(), conversation_id),
        )
        return cur.lastrowid


def create_session(user_id: int) -> tuple[str, str]:
    """Crée une session serveur. Retourne (token, binding) — jamais à mettre dans l'URL."""
    token = secrets.token_urlsafe(32)
    binding = secrets.token_urlsafe(24)
    now = _now()
    expires = (datetime.now() + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_sessions (token_hash, user_id, binding_hash, expires_at, created_at, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (_hash_value(token), user_id, _hash_value(binding), expires, now, now),
        )
    return token, binding


def verify_session(token: str, binding: str | None = None) -> dict[str, Any] | None:
    if not token or not binding:
        return None
    token_hash = _hash_value(token)
    binding_hash = _hash_value(binding)
    now = _now()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.email, u.username, s.id AS session_id
            FROM users u
            JOIN user_sessions s ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.binding_hash = ? AND s.expires_at > ?
            """,
            (token_hash, binding_hash, now),
        ).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE user_sessions SET last_used_at = ? WHERE id = ?",
            (now, row["session_id"]),
        )
        return {"id": row["id"], "email": row["email"], "username": row["username"]}


def revoke_session(token: str) -> None:
    if not token:
        return
    token_hash = _hash_value(token)
    with get_connection() as conn:
        conn.execute("DELETE FROM user_sessions WHERE token_hash = ?", (token_hash,))


def revoke_all_user_sessions(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM client_session_cache WHERE user_id = ?", (user_id,))


def save_client_session_cache(
    browser_id: str,
    auth_token: str,
    auth_binding: str,
    user_id: int,
) -> None:
    expires = (datetime.now() + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO client_session_cache
            (browser_id, auth_token, auth_binding, user_id, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (browser_id, auth_token, auth_binding, user_id, expires),
        )


def load_client_session_cache(browser_id: str | None) -> tuple[str, str] | None:
    if not browser_id:
        return None
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT auth_token, auth_binding
            FROM client_session_cache
            WHERE browser_id = ? AND expires_at > ?
            """,
            (browser_id, _now()),
        ).fetchone()
        if not row:
            return None
        return row["auth_token"], row["auth_binding"]


def clear_client_session_cache(browser_id: str | None) -> None:
    if not browser_id:
        return
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM client_session_cache WHERE browser_id = ?",
            (browser_id,),
        )


def get_messages(conversation_id: int, include_blobs: bool = False) -> list[dict[str, Any]]:
    blob_flags = (
        ", CASE WHEN chart_data IS NOT NULL OR (chart_path IS NOT NULL AND chart_path != '') "
        "THEN 1 ELSE 0 END AS has_chart"
        ", CASE WHEN pdf_data IS NOT NULL OR (pdf_path IS NOT NULL AND pdf_path != '') "
        "THEN 1 ELSE 0 END AS has_pdf"
    )
    with get_connection() as conn:
        if include_blobs:
            rows = conn.execute(
                f"""
                SELECT {_MESSAGE_META}, chart_data, pdf_data{blob_flags}
                FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
                """,
                (conversation_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT {_MESSAGE_META}{blob_flags}
                FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
                """,
                (conversation_id,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["has_chart"] = bool(item.pop("has_chart", 0))
            item["has_pdf"] = bool(item.pop("has_pdf", 0))
            result.append(item)
        return result


def get_message_attachment(
    message_id: int,
    user_id: int,
    kind: str,
) -> bytes | None:
    column = "chart_data" if kind == "chart" else "pdf_data"
    if column not in ("chart_data", "pdf_data"):
        return None
    with get_connection() as conn:
        row = conn.execute(
            f"""
            SELECT m.{column} AS data, m.chart_path, m.pdf_path
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.id = ? AND c.user_id = ?
            """,
            (message_id, user_id),
        ).fetchone()
        if not row:
            return None
        if row["data"]:
            return bytes(row["data"])
        legacy_path = row["chart_path"] if kind == "chart" else row["pdf_path"]
        if legacy_path and os.path.isfile(legacy_path):
            with open(legacy_path, "rb") as handle:
                blob = handle.read()
            conn.execute(
                f"UPDATE messages SET {column} = ?, "
                f"{'chart_path' if kind == 'chart' else 'pdf_path'} = NULL WHERE id = ?",
                (blob, message_id),
            )
            return blob
        return None
