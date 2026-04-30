# Backend - Azure Firewall Management API

Python FastAPI backend for managing Azure Firewall rules with approval workflows.

## Setup

### Prerequisites

- Python 3.11 or higher
- pip or poetry for dependency management

### Installation

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

Required environment variables:
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`
- `DATABASE_URL` (see Database Setup below)
- `SECRET_KEY` (must be at least 16 characters)

See `.env.example` for all available options.

## Database Setup

### SQLite (Development)

SQLite is the default database for development. No additional setup required:

```env
DATABASE_URL=sqlite:///./firewall_mgmt.db
```

### PostgreSQL (Production)

For production deployments, use PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/firewall_mgmt
```

The application is configured to work with both databases using SQLAlchemy ORM with cross-database compatible types.

## Database Migrations

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database migrations.

### Migration Commands

All commands must be run from the `backend` directory.

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create a new migration after modifying models
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Check current revision
alembic current

# View migration history
alembic history

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision-id>

# Upgrade to specific revision
alembic upgrade <revision-id>
```

### Migration Workflow

1. **Modify models** - Add/modify columns in `app/models/`
2. **Generate migration** - Run `alembic revision --autogenerate -m "Your message"`
3. **Review migration** - Check the generated migration script in `alembic/versions/`
4. **Test migration** - Apply to your development database
5. **Apply to production** - Run `alembic upgrade head` in production

### Generating Migrations

When you modify SQLAlchemy models, generate a corresponding migration:

```bash
# Autogenerate detects changes in models
alembic revision --autogenerate -m "Add firewall_rule_description_column"
```

Review the generated file in `alembic/versions/` to ensure the changes are correct.

### Manual Migrations

For complex migrations, write them manually in the `alembic/versions/` directory:

```python
def upgrade():
    op.add_column('firewall_rules', sa.Column('new_column', sa.String(255)))

def downgrade():
    op.drop_column('firewall_rules', 'new_column')
```

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific category
pytest tests/test_models.py -v
pytest tests/test_database.py -v
pytest tests/test_config.py -v
```

### Test Database

Tests use an in-memory SQLite database by default, ensuring isolation between test runs.

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # Database engine and session setup
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── firewall_rule.py # Firewall rules and workloads
│   │   ├── approval.py      # Approval workflows
│   │   └── audit.py         # Audit logging and users
│   ├── schemas/             # Pydantic schemas
│   ├── api/                 # API route handlers
│   ├── auth/                # Authentication utilities
│   └── services/            # Business logic
├── tests/
│   ├── test_models.py       # Model tests
│   ├── test_database.py     # Database tests
│   └── test_config.py       # Configuration tests
├── alembic/                 # Alembic migration scripts
│   ├── env.py
│   └── versions/
├── alembic.ini              # Alembic configuration
├── .env.example             # Example environment variables
├── requirements.txt         # Python dependencies
└── Dockerfile               # Container configuration
```

## API

Start the server to access API documentation:

```bash
uvicorn app.main:app --reload
```

Then visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Docker

```bash
# Build the image
docker build -t firewall-mgmt-backend .

# Run the container
docker run -p 8000:8000 --env-file .env firewall-mgmt-backend
```

## Database Type Compatibility

The models use SQLAlchemy types compatible with both SQLite and PostgreSQL:

| SQLAlchemy Type | SQLite | PostgreSQL |
|----------------|--------|------------|
| `String(36)` | ✓ | ✓ |
| `Text` | ✓ | ✓ |
| `Integer` | ✓ | ✓ |
| `Boolean` | ✓ | ✓ |
| `DateTime` | ✓ | ✓ |
| `Enum` | ✓ | ✓ |
| `JSON` | ✓ | ✓ |
| `UUID` (as String) | ✓ | ✓ |

For PostgreSQL-specific features (native JSONB, ARRAY, INET), use the PostgreSQL dialect.