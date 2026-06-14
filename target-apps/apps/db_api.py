import sqlite3
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

MAX_PAGE_SIZE = 50
MAX_TOTAL_ROWS = 500
MAX_NAME_LENGTH = 128
MAX_CATEGORY_LENGTH = 64
MAX_STATUS_LENGTH = 32
DEFAULT_PAGE_SIZE = 20
DB_PATH = Path("/tmp/ploadtesting-db-api.sqlite3")

if DB_PATH.exists():
    DB_PATH.unlink()

app = FastAPI(
    title="pLoadtesting Target Suite - DB API",
    version="1.0.0",
    description="Bounded SQLite-backed CRUD and list-filter target for local and CI-safe DB-heavy validation.",
)

_init_lock = Lock()
_seed_rows = (
    ("alpha", "ops", 10, "new"),
    ("beta", "ops", 20, "ready"),
    ("gamma", "sales", 30, "ready"),
    ("delta", "finance", 40, "archived"),
    ("epsilon", "sales", 50, "new"),
)


class RecordCreate(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    category: str = Field(default="general", min_length=1, max_length=MAX_CATEGORY_LENGTH)
    value: int = Field(default=0, ge=0, le=1_000_000)
    status: str = Field(default="new", min_length=1, max_length=MAX_STATUS_LENGTH)


class RecordUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    category: str | None = Field(default=None, min_length=1, max_length=MAX_CATEGORY_LENGTH)
    value: int | None = Field(default=None, ge=0, le=1_000_000)
    status: str | None = Field(default=None, min_length=1, max_length=MAX_STATUS_LENGTH)


def _connection() -> sqlite3.Connection:
    ensure_initialized()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_initialized() -> None:
    with _init_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT INTO records (name, category, value, status) VALUES (?, ?, ?, ?)",
                    _seed_rows,
                )
            conn.commit()
        finally:
            conn.close()


def _serialize(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "value": row["value"],
        "status": row["status"],
    }


def _get_record_or_404(conn: sqlite3.Connection, record_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, name, category, value, status FROM records WHERE id = ?",
        (record_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found.")
    return row


@app.get("/health")
async def health() -> dict:
    with _connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    return {"status": "ok", "target_app_id": "db-api", "seeded_rows": total}


@app.post("/api/records", status_code=201)
async def create_record(body: RecordCreate) -> dict:
    with _connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        if total >= MAX_TOTAL_ROWS:
            raise HTTPException(status_code=422, detail=f"record count exceeds safe cap of {MAX_TOTAL_ROWS}.")
        cursor = conn.execute(
            "INSERT INTO records (name, category, value, status) VALUES (?, ?, ?, ?)",
            (body.name, body.category, body.value, body.status),
        )
        conn.commit()
        row = _get_record_or_404(conn, cursor.lastrowid)
    return _serialize(row)


@app.get("/api/records/{record_id}")
async def get_record(record_id: int) -> dict:
    with _connection() as conn:
        row = _get_record_or_404(conn, record_id)
    return _serialize(row)


@app.patch("/api/records/{record_id}")
async def update_record(record_id: int, body: RecordUpdate) -> dict:
    values = body.model_dump(exclude_none=True)
    if not values:
        raise HTTPException(status_code=422, detail="At least one field must be provided.")

    with _connection() as conn:
        row = _get_record_or_404(conn, record_id)
        current = _serialize(row)
        merged = {**current, **values}
        conn.execute(
            """
            UPDATE records
            SET name = ?, category = ?, value = ?, status = ?
            WHERE id = ?
            """,
            (merged["name"], merged["category"], merged["value"], merged["status"], record_id),
        )
        conn.commit()
        updated = _get_record_or_404(conn, record_id)
    return _serialize(updated)


@app.get("/api/records")
async def list_records(
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0, le=MAX_TOTAL_ROWS),
    category: str | None = Query(default=None, max_length=MAX_CATEGORY_LENGTH),
    status: str | None = Query(default=None, max_length=MAX_STATUS_LENGTH),
    q: str | None = Query(default=None, max_length=MAX_NAME_LENGTH),
    sort_by: str = Query(default="id", pattern="^(id|name|value|status)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
):
    where_clauses = []
    params: list[object] = []
    if category:
        where_clauses.append("category = ?")
        params.append(category)
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    if q:
        where_clauses.append("name LIKE ?")
        params.append(f"%{q}%")
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with _connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM records {where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT id, name, category, value, status
            FROM records
            {where_sql}
            ORDER BY {sort_by} {sort_order.upper()}, id ASC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    return {
        "items": [_serialize(row) for row in rows],
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
    }
