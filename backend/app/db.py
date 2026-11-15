"""PostgreSQL access for the directory: experts, products and centres (asyncpg)."""
import functools
import logging
from typing import Optional

import asyncpg
from pydantic import BaseModel

from .directory import KIND_MODELS, Centre, Expert, Product

log = logging.getLogger("smarter_crops.db")

# Columns per table, taken from the Pydantic models so the two never drift apart
COLUMNS = {kind: list(model.model_fields) for kind, model in KIND_MODELS.items()}
TABLES = {"experts": "experts", "products": "products", "centres": "centres"}
NUMERIC = {"rating"}


class DatabaseUnavailable(Exception):
    pass


UNAVAILABLE_MSG = "Directory database is unreachable. Is PostgreSQL running? (docker compose ps)"
_CONNECTION_ERRORS = (OSError, TimeoutError, asyncpg.InterfaceError, asyncpg.PostgresConnectionError,
                      asyncpg.CannotConnectNowError)


def db_call(fn):
    """Turns connection-level failures into DatabaseUnavailable -> HTTP 503."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except _CONNECTION_ERRORS as e:
            log.warning("database call %s failed: %s", fn.__name__, e)
            raise DatabaseUnavailable(UNAVAILABLE_MSG) from e
    return wrapper


def _row_to(kind: str, row: asyncpg.Record) -> BaseModel:
    d = dict(row)
    for k in NUMERIC & d.keys():
        d[k] = float(d[k])
    return KIND_MODELS[kind].model_validate(d)


class DirectoryRepository:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> bool:
        if self.pool:
            return True
        try:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5, timeout=5, command_timeout=10)
            return True
        except (asyncpg.PostgresError, *_CONNECTION_ERRORS) as e:
            log.warning("PostgreSQL unavailable: %s", e)
            return False

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def _pool(self) -> asyncpg.Pool:
        if not self.pool and not await self.connect():
            raise DatabaseUnavailable(UNAVAILABLE_MSG)
        assert self.pool
        return self.pool

    async def ping(self) -> bool:
        try:
            await (await self._pool()).fetchval("SELECT 1")
            return True
        except (DatabaseUnavailable, asyncpg.PostgresError, *_CONNECTION_ERRORS):
            return False

    @db_call
    async def migration_revision(self) -> Optional[str]:
        pool = await self._pool()
        if not await pool.fetchval("SELECT to_regclass('alembic_version') IS NOT NULL"):
            return None
        return await pool.fetchval("SELECT version_num FROM alembic_version")

    # ---------- reads ----------
    @db_call
    async def all_active(self, kind: str) -> list[BaseModel]:
        """The directory is small (hundreds of rows), so ranking loads active rows and scores them in Python."""
        pool = await self._pool()
        rows = await pool.fetch(f"SELECT {', '.join(COLUMNS[kind])} FROM {TABLES[kind]} WHERE active")
        return [_row_to(kind, r) for r in rows]

    async def experts(self) -> list[Expert]:
        return await self.all_active("experts")  # type: ignore[return-value]

    async def products(self) -> list[Product]:
        return await self.all_active("products")  # type: ignore[return-value]

    async def centres(self) -> list[Centre]:
        return await self.all_active("centres")  # type: ignore[return-value]

    @db_call
    async def meta(self) -> dict:
        pool = await self._pool()
        counts = {k: await pool.fetchval(f"SELECT count(*) FROM {t} WHERE active") for k, t in TABLES.items()}
        locations = await pool.fetch(
            """SELECT state, array_agg(DISTINCT district ORDER BY district) AS districts FROM (
                   SELECT state, district FROM experts WHERE active AND state <> ''
                   UNION SELECT state, district FROM centres WHERE active AND state <> ''
               ) s GROUP BY state ORDER BY state"""
        )
        languages = await pool.fetchval(
            """SELECT coalesce(array_agg(DISTINCT l ORDER BY l), '{}') FROM (
                   SELECT unnest(languages) l FROM experts WHERE active
                   UNION SELECT unnest(languages) FROM centres WHERE active) x"""
        )
        return {
            "counts": counts,
            "states": {r["state"]: [d for d in r["districts"] if d] for r in locations},
            "languages": list(languages),
        }

    @db_call
    async def get(self, kind: str, item_id: str) -> Optional[BaseModel]:
        pool = await self._pool()
        row = await pool.fetchrow(f"SELECT {', '.join(COLUMNS[kind])} FROM {TABLES[kind]} WHERE id = $1 AND active", item_id)
        return _row_to(kind, row) if row else None

    @db_call
    async def row_count(self, kind: str) -> int:
        return await (await self._pool()).fetchval(f"SELECT count(*) FROM {TABLES[kind]}")

    # ---------- writes ----------
    @db_call
    async def upsert_many(self, kind: str, items: list[BaseModel]) -> int:
        cols = COLUMNS[kind]
        params = ", ".join(f"${i + 1}" for i in range(len(cols)))
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "id")
        sql = (f"INSERT INTO {TABLES[kind]} ({', '.join(cols)}, active) VALUES ({params}, true) "
               f"ON CONFLICT (id) DO UPDATE SET {updates}, active = true")
        pool = await self._pool()
        async with pool.acquire() as conn, conn.transaction():
            await conn.executemany(sql, [[getattr(it, c) for c in cols] for it in items])
        return len(items)

    @db_call
    async def deactivate(self, kind: str, item_id: str) -> bool:
        status = await (await self._pool()).execute(f"UPDATE {TABLES[kind]} SET active = false WHERE id = $1 AND active", item_id)
        return status.endswith("1")

    @db_call
    async def deactivate_except(self, kind: str, keep_ids: list[str]) -> int:
        status = await (await self._pool()).execute(
            f"UPDATE {TABLES[kind]} SET active = false WHERE active AND NOT (id = ANY($1::text[]))", keep_ids)
        return int(status.split()[-1])
