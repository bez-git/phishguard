from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "ff5d19d59050"
down_revision = "97e3fcb46021"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    tables = set(insp.get_table_names())

    # Create table if missing
    if "report" not in tables:
        op.create_table(
            "report",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("url", sa.String(length=2048), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False, server_default="popup"),
            sa.Column("note", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        )
        tables.add("report")

    # Create index if missing
    if "report" in tables:
        existing_indexes = {ix["name"] for ix in insp.get_indexes("report")}
        if "ix_report_user_id" not in existing_indexes:
            op.create_index("ix_report_user_id", "report", ["user_id"])


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    if "report" in insp.get_table_names():
        existing_indexes = {ix["name"] for ix in insp.get_indexes("report")}
        if "ix_report_user_id" in existing_indexes:
            op.drop_index("ix_report_user_id", table_name="report")
        op.drop_table("report")
