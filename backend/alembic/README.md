# Alembic Migrations

This directory contains Alembic configuration and migration scripts for database version control.

## Quick Start

```bash
# From the backend directory:

# Generate a new migration after modifying models
alembic revision --autogenerate -m "describe your changes"

# Apply migrations
alembic upgrade head

# Check current database version
alembic current

# View revision history
alembic history

# Rollback last migration
alembic downgrade -1
```

## Migration Script Structure

Each migration script follows this pattern:

```python
"""Description of migration

Revision ID: abc123
Revises: previous_id
Create Date: 2024-01-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'abc123'
down_revision = 'previous_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add migration operations here
    pass


def downgrade() -> None:
    # Reverse upgrade operations
    pass
```

## Cross-Database Compatibility

Migrations use SQLAlchemy-compatible operations that work with both SQLite and PostgreSQL:

| Operation | SQLite | PostgreSQL |
|-----------|--------|------------|
| `add_column` | ✓ | ✓ |
| `drop_column` | ✓ | ✓ |
| `create_table` | ✓ | ✓ |
| `drop_table` | ✓ | ✓ |
| `create_index` | ✓ | ✓ |

## Common Operations

### Adding a Column

```python
def upgrade():
    op.add_column('table_name', sa.Column('new_column', sa.String(255), nullable=True))
```

### Creating a Table

```python
def upgrade():
    op.create_table(
        'new_table',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
```

### Creating an Index

```python
def upgrade():
    op.create_index('idx_table_column', 'table_name', ['column_name'])
```

### Modifying a Column (SQLite)

SQLite requires special handling for column modifications:

```python
def upgrade():
    # For SQLite, use render_as_batch=True in env.py
    op.alter_column('table_name', 'column_name', 
                    type_=sa.String(500), 
                    existing_type=sa.String(255))
```

## Environment Variables

The migration environment reads `DATABASE_URL` from the environment:

```bash
# For SQLite development
DATABASE_URL=sqlite:///./firewall_mgmt.db

# For PostgreSQL production
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
```

## Troubleshooting

### "Target metadata is empty"

Ensure all models are imported in `alembic/env.py`:
```python
import app.models  # noqa: F401
```

### SQLite alter table errors

The `render_as_batch=True` setting in `env.py` enables Alembic to generate batch-mode 
migrations compatible with SQLite's limited ALTER TABLE support.

### PostgreSQL connection refused

Verify PostgreSQL is running and the connection string is correct:
```bash
# Test connection
psql "postgresql://user:pass@host:5432/dbname"