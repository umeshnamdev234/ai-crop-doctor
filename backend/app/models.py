"""SQLAlchemy table definitions: the schema source of truth for Alembic.

Runtime queries use asyncpg directly (app/db.py); these definitions exist so that
`alembic revision --autogenerate` and `alembic check` can compare code with the database.
"""
from sqlalchemy import (
    TIMESTAMP, Boolean, CheckConstraint, Column, Index, Integer, MetaData, Numeric, Table, Text, func, text,
)
from sqlalchemy.dialects.postgresql import ARRAY

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

EMPTY = text("'{}'::text[]")
BLANK = text("''")


def _timestamps() -> list[Column]:
    return [
        Column("active", Boolean, nullable=False, server_default=text("true")),  # soft delete
        Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
        Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    ]


experts = Table(
    "experts", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("expert_type", Text, nullable=False),
    Column("crops", ARRAY(Text), nullable=False, server_default=EMPTY),
    Column("expertise", ARRAY(Text), nullable=False, server_default=EMPTY),
    Column("organisation", Text, nullable=False, server_default=BLANK),
    Column("qualifications", Text, nullable=False, server_default=BLANK),
    Column("experience_years", Integer, nullable=False, server_default=text("0")),
    Column("languages", ARRAY(Text), nullable=False, server_default=EMPTY),
    Column("state", Text, nullable=False, server_default=BLANK),
    Column("district", Text, nullable=False, server_default=BLANK),
    Column("rating", Numeric(2, 1), nullable=False, server_default=text("0")),
    Column("review_count", Integer, nullable=False, server_default=text("0")),
    Column("fee", Integer, nullable=False, server_default=text("0")),
    Column("phone_consult", Boolean, nullable=False, server_default=text("false")),
    Column("field_visit", Boolean, nullable=False, server_default=text("false")),
    Column("available_days", ARRAY(Text), nullable=False, server_default=EMPTY),
    *_timestamps(),
    CheckConstraint("experience_years BETWEEN 0 AND 80", name="experience_years"),
    CheckConstraint("rating BETWEEN 0 AND 5", name="rating"),
    CheckConstraint("fee >= 0", name="fee"),
)

products = Table(
    "products", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("active_ingredient", Text, nullable=False, server_default=BLANK),
    Column("targets", ARRAY(Text), nullable=False, server_default=EMPTY),
    Column("crops", ARRAY(Text), nullable=False, server_default=EMPTY),
    Column("organic", Boolean, nullable=False, server_default=text("false")),
    Column("dose", Text, nullable=False, server_default=BLANK),
    Column("safety_notes", Text, nullable=False, server_default=BLANK),
    Column("waiting_period_days", Integer),
    Column("price_inr", Integer),
    Column("unit", Text, nullable=False, server_default=BLANK),
    *_timestamps(),
    CheckConstraint("waiting_period_days IS NULL OR waiting_period_days >= 0", name="waiting_period_days"),
    CheckConstraint("price_inr IS NULL OR price_inr >= 0", name="price_inr"),
)

centres = Table(
    "centres", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("centre_type", Text, nullable=False),
    Column("services", ARRAY(Text), nullable=False, server_default=EMPTY),
    Column("state", Text, nullable=False, server_default=BLANK),
    Column("district", Text, nullable=False, server_default=BLANK),
    Column("address", Text, nullable=False, server_default=BLANK),
    Column("languages", ARRAY(Text), nullable=False, server_default=EMPTY),
    Column("open_days", ARRAY(Text), nullable=False, server_default=EMPTY),
    Column("free_service", Boolean, nullable=False, server_default=text("false")),
    *_timestamps(),
)

Index("ix_experts_type_lower", func.lower(experts.c.expert_type), postgresql_where=experts.c.active)
Index("ix_experts_location", func.lower(experts.c.state), func.lower(experts.c.district), postgresql_where=experts.c.active)
Index("ix_products_category_lower", func.lower(products.c.category), postgresql_where=products.c.active)
Index("ix_products_targets", products.c.targets, postgresql_using="gin")
Index("ix_centres_location", func.lower(centres.c.state), func.lower(centres.c.district), postgresql_where=centres.c.active)
