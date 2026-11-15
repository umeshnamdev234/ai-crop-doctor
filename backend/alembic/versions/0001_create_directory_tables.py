"""create experts, products and centres tables

Revision ID: 0001
Revises:
Create Date: 2026-11-15 10:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMPTY = sa.text("'{}'::text[]")
BLANK = sa.text("''")
TABLES = ("experts", "products", "centres")


def _arr(name: str) -> sa.Column:
    return sa.Column(name, postgresql.ARRAY(sa.Text()), nullable=False, server_default=EMPTY)


def _txt(name: str) -> sa.Column:
    return sa.Column(name, sa.Text(), nullable=False, server_default=BLANK)


def _common() -> list[sa.Column]:
    return [
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "experts",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("expert_type", sa.Text(), nullable=False),
        _arr("crops"), _arr("expertise"), _txt("organisation"), _txt("qualifications"),
        sa.Column("experience_years", sa.Integer(), nullable=False, server_default=sa.text("0")),
        _arr("languages"), _txt("state"), _txt("district"),
        sa.Column("rating", sa.Numeric(2, 1), nullable=False, server_default=sa.text("0")),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("fee", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("phone_consult", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("field_visit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        _arr("available_days"),
        *_common(),
        sa.CheckConstraint("experience_years BETWEEN 0 AND 80", name=op.f("ck_experts_experience_years")),
        sa.CheckConstraint("rating BETWEEN 0 AND 5", name=op.f("ck_experts_rating")),
        sa.CheckConstraint("fee >= 0", name=op.f("ck_experts_fee")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_experts")),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        _txt("active_ingredient"), _arr("targets"), _arr("crops"),
        sa.Column("organic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        _txt("dose"), _txt("safety_notes"),
        sa.Column("waiting_period_days", sa.Integer(), nullable=True),
        sa.Column("price_inr", sa.Integer(), nullable=True),
        _txt("unit"),
        *_common(),
        sa.CheckConstraint("waiting_period_days IS NULL OR waiting_period_days >= 0", name=op.f("ck_products_waiting_period_days")),
        sa.CheckConstraint("price_inr IS NULL OR price_inr >= 0", name=op.f("ck_products_price_inr")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_table(
        "centres",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("centre_type", sa.Text(), nullable=False),
        _arr("services"), _txt("state"), _txt("district"), _txt("address"), _arr("languages"), _arr("open_days"),
        sa.Column("free_service", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_common(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_centres")),
    )

    op.create_index("ix_experts_type_lower", "experts", [sa.text("lower(expert_type)")], postgresql_where=sa.text("active"))
    op.create_index("ix_experts_location", "experts", [sa.text("lower(state)"), sa.text("lower(district)")], postgresql_where=sa.text("active"))
    op.create_index("ix_products_category_lower", "products", [sa.text("lower(category)")], postgresql_where=sa.text("active"))
    op.create_index("ix_products_targets", "products", ["targets"], postgresql_using="gin")
    op.create_index("ix_centres_location", "centres", [sa.text("lower(state)"), sa.text("lower(district)")], postgresql_where=sa.text("active"))

    op.execute(
        """
        CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for t in TABLES:
        op.execute(f"CREATE TRIGGER {t}_updated_at BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION touch_updated_at()")


def downgrade() -> None:
    for t in TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {t}_updated_at ON {t}")
    op.execute("DROP FUNCTION IF EXISTS touch_updated_at()")
    op.drop_index("ix_centres_location", table_name="centres")
    op.drop_index("ix_products_targets", table_name="products")
    op.drop_index("ix_products_category_lower", table_name="products")
    op.drop_index("ix_experts_location", table_name="experts")
    op.drop_index("ix_experts_type_lower", table_name="experts")
    for t in reversed(TABLES):
        op.drop_table(t)
