# Database Migrations

This directory contains database migration files managed by Flask-Migrate (Alembic).

## Overview

Flask-Migrate is a wrapper around Alembic that integrates with Flask-SQLAlchemy. It tracks database schema changes and allows you to version control your database structure.

## Important Note

**Use `python -m flask` instead of just `flask`** to ensure the correct Python environment is used:

```bash
# ✓ Correct (uses the right Python environment)
python -m flask db upgrade

# ✗ Wrong (may use different Python version without Flask-Migrate)
flask db upgrade
```

## Common Commands

### Initialize migrations (first time only)
```bash
python -m flask db init
```
This creates the migrations directory structure. Only needed once per project.

### Create a new migration
```bash
# Auto-generate migration from model changes
python -m flask db migrate -m "Description of changes"

# Create empty migration file
python -m flask db revision -m "Description of changes"
```

### Apply migrations
```bash
# Upgrade to latest version
python -m flask db upgrade

# Upgrade to specific revision
python -m flask db upgrade <revision_id>

# Downgrade one revision
python -m flask db downgrade

# Downgrade to specific revision
python -m flask db downgrade <revision_id>
```

### View migration history
```bash
# Show current revision
python -m flask db current

# Show migration history
python -m flask db history

# Show all heads
python -m flask db heads
```

### Mark migration as applied (without running it)
```bash
python -m flask db stamp <revision_id>
```
Useful when you've manually applied changes or need to sync the migration state.

### Other useful commands
```bash
# Show SQL for a migration (without applying)
python -m flask db upgrade --sql

# Show help
python -m flask db --help
```

## Migration File Structure

Migration files are located in `migrations/versions/` and follow this naming pattern:
```
<revision_id>_<description>.py
```

Each migration file contains:
- `revision`: Unique identifier for this migration
- `down_revision`: Previous migration this builds upon
- `upgrade()`: Function to apply changes
- `downgrade()`: Function to revert changes

## Best Practices

1. **Always review auto-generated migrations** before applying them
2. **Test migrations** on a development database first
3. **Never edit applied migrations** - create a new one instead
4. **Commit migration files** to version control
5. **Keep migrations small and focused** on specific changes
6. **Write descriptive migration messages**

## Manual Migration Creation

If you need to create a migration manually (like when flask db is not available):

1. Create a new file in `migrations/versions/` with format: `<revision_id>_description.py`
2. Use the template:

```python
"""Description of changes

Revision ID: <unique_id>
Revises: <previous_revision_id>
Create Date: YYYY-MM-DD HH:MM:SS.SSSSSS

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '<unique_id>'
down_revision = '<previous_revision_id>'
branch_labels = None
depends_on = None


def upgrade():
    # Add your upgrade commands here
    pass


def downgrade():
    # Add your downgrade commands here
    pass
```

3. Apply with: `flask db upgrade`

## Common Migration Examples

### Add a column
```python
def upgrade():
    op.add_column('table_name', sa.Column('column_name', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('table_name', 'column_name')
```

### Create a table
```python
def upgrade():
    op.create_table('table_name',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

def downgrade():
    op.drop_table('table_name')
```

### Add an index
```python
def upgrade():
    op.create_index('ix_table_column', 'table_name', ['column_name'])

def downgrade():
    op.drop_index('ix_table_column', table_name='table_name')
```

### Add a foreign key
```python
def upgrade():
    op.create_foreign_key('fk_table_other', 'table_name', 'other_table',
                         ['other_id'], ['id'])

def downgrade():
    op.drop_constraint('fk_table_other', 'table_name', type_='foreignkey')
```

## Troubleshooting

### "Target database is not up to date"
Run `flask db upgrade` to apply pending migrations.

### "Can't locate revision identified by"
The migration history is out of sync. Use `flask db stamp <revision_id>` to mark a specific revision as current.

### Migration already exists in database
If you manually created tables, use `flask db stamp head` to mark all migrations as applied.

## Project-Specific Notes

- Database: MariaDB/MySQL
- ORM: SQLAlchemy via Flask-SQLAlchemy
- Always use `datetime.now(timezone.utc)` for timestamp defaults
- All tables should have `created_at` and `updated_at` columns
