"""AI Enumerator public v1 schema.

Creates the current core schema on a clean database and is safe to run after the
0.9.x schema because SQLAlchemy create_all only creates missing objects.
"""
from alembic import op

revision="0004_public_v1"
down_revision="0003_deep_exposure"
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    from app.db import Base
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=bind)

def downgrade():
    pass
