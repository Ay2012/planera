"""Small SQLite compatibility migrations for local development databases."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_UPLOADS_TABLE = "uploads"
_LEGACY_UPLOADS_TABLE = "uploads__legacy_schema_compat"
_EXPECTED_UPLOAD_COLUMNS = {
    "source_id",
    "user_id",
    "original_filename",
    "storage_path",
    "content_type",
    "size_bytes",
    "content_hash",
    "status",
    "rows",
    "columns",
    "relation_count",
    "primary_relation_name",
    "created_at",
    "updated_at",
}


def ensure_sqlite_schema_compatibility(engine: Engine) -> None:
    """Upgrade legacy local SQLite tables that predate the current ORM shape."""

    _migrate_uploads_table_if_needed(engine)


def _migrate_uploads_table_if_needed(engine: Engine) -> None:
    inspector = inspect(engine)
    if _UPLOADS_TABLE not in inspector.get_table_names():
        return

    columns = inspector.get_columns(_UPLOADS_TABLE)
    column_names = {column["name"] for column in columns}
    pk_columns = [column["name"] for column in columns if column.get("primary_key")]
    if column_names == _EXPECTED_UPLOAD_COLUMNS and pk_columns == ["source_id"]:
        return

    if _LEGACY_UPLOADS_TABLE in inspector.get_table_names():
        raise RuntimeError(
            "Cannot migrate the uploads table because a previous temporary migration table still exists: "
            f"{_LEGACY_UPLOADS_TABLE}."
        )

    select_sql = _build_upload_copy_select(column_names)
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {_UPLOADS_TABLE} RENAME TO {_LEGACY_UPLOADS_TABLE}"))
        connection.execute(
            text(
                f"""
                CREATE TABLE {_UPLOADS_TABLE} (
                    source_id VARCHAR(64) NOT NULL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    original_filename VARCHAR(512) NOT NULL,
                    storage_path VARCHAR(1024) NOT NULL,
                    content_type VARCHAR(255) NOT NULL DEFAULT 'application/octet-stream',
                    size_bytes INTEGER NOT NULL,
                    content_hash VARCHAR(128) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'verified',
                    rows INTEGER,
                    columns INTEGER,
                    relation_count INTEGER,
                    primary_relation_name VARCHAR(255),
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                INSERT INTO {_UPLOADS_TABLE} (
                    source_id,
                    user_id,
                    original_filename,
                    storage_path,
                    content_type,
                    size_bytes,
                    content_hash,
                    status,
                    rows,
                    columns,
                    relation_count,
                    primary_relation_name,
                    created_at,
                    updated_at
                )
                {select_sql}
                """
            )
        )
        connection.execute(text(f"DROP TABLE {_LEGACY_UPLOADS_TABLE}"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_uploads_user_id ON uploads (user_id)"))


def _build_upload_copy_select(column_names: set[str]) -> str:
    def has_column(name: str) -> bool:
        return name in column_names

    def quoted(name: str) -> str:
        return f'"{name}"'

    def first_present(*names: str, default: str) -> str:
        for name in names:
            if has_column(name):
                return quoted(name)
        return default

    source_id_expr = first_present(
        "source_id",
        "upload_id",
        default="('source_' || lower(hex(randomblob(4))))",
    )
    content_type_expr = first_present("content_type", default="'application/octet-stream'")
    status_expr = first_present("status", default="'verified'")
    created_at_expr = first_present("created_at", default="CURRENT_TIMESTAMP")
    updated_at_expr = first_present("updated_at", "created_at", default="CURRENT_TIMESTAMP")

    return f"""
        SELECT
            COALESCE(NULLIF({source_id_expr}, ''), 'source_' || lower(hex(randomblob(4)))) AS source_id,
            {first_present("user_id", default='0')} AS user_id,
            {first_present("original_filename", default="'upload.csv'")} AS original_filename,
            {first_present("storage_path", default="''")} AS storage_path,
            COALESCE({content_type_expr}, 'application/octet-stream') AS content_type,
            {first_present("size_bytes", default='0')} AS size_bytes,
            {first_present("content_hash", default="''")} AS content_hash,
            COALESCE({status_expr}, 'verified') AS status,
            {first_present("rows", default='NULL')} AS rows,
            {first_present("columns", default='NULL')} AS columns,
            {first_present("relation_count", default='NULL')} AS relation_count,
            {first_present("primary_relation_name", default='NULL')} AS primary_relation_name,
            COALESCE({created_at_expr}, CURRENT_TIMESTAMP) AS created_at,
            COALESCE({updated_at_expr}, COALESCE({created_at_expr}, CURRENT_TIMESTAMP)) AS updated_at
        FROM {_LEGACY_UPLOADS_TABLE}
    """
