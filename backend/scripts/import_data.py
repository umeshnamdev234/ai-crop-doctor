"""Imports experts, products or centres from JSON / CSV into PostgreSQL.

Run migrations first:  alembic upgrade head

    python scripts/import_data.py all data/sample_directory.json          # all three kinds from one JSON
    python scripts/import_data.py experts my_experts.csv --replace          # one kind; deactivate rows not in file
    python scripts/import_data.py all data/sample_directory.json --if-empty # seed only empty tables

Rows are upserted by id, so re-running is safe. Uses DATABASE_URL from the environment / .env.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import DirectoryRepository  # noqa: E402
from app.directory import KIND_MODELS, load_file  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["all", *KIND_MODELS], help="what to import ('all' needs a JSON file with all three keys)")
    ap.add_argument("file", help="JSON or CSV file")
    ap.add_argument("--replace", action="store_true", help="deactivate rows whose id is not in the file")
    ap.add_argument("--if-empty", action="store_true", help="only import into tables that have no rows (seeding)")
    args = ap.parse_args()
    kinds = list(KIND_MODELS) if args.kind == "all" else [args.kind]

    try:
        data = {k: load_file(k, args.file) for k in kinds}
    except (ValidationError, KeyError) as e:
        print(f"Invalid data in {args.file}: {e}", file=sys.stderr)
        return 1

    repo = DirectoryRepository(get_settings().database_url)
    if not await repo.connect():
        print("Cannot connect to PostgreSQL", file=sys.stderr)
        return 1
    try:
        if await repo.migration_revision() is None:
            print("Database schema missing. Run first: alembic upgrade head", file=sys.stderr)
            return 1
        for kind, items in data.items():
            ids = [i.id for i in items]
            if len(ids) != len(set(ids)):
                print(f"Duplicate ids in {kind}", file=sys.stderr)
                return 1
            if args.if_empty and await repo.row_count(kind) > 0:
                print(f"{kind}: already has data, skipping seed")
                continue
            print(f"{kind}: imported {await repo.upsert_many(kind, items)}")
            if args.replace:
                print(f"{kind}: deactivated {await repo.deactivate_except(kind, ids)} not in the file")
        print("Directory:", (await repo.meta())["counts"])
    finally:
        await repo.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
