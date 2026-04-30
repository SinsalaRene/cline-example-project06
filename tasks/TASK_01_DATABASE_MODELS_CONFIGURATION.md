# Task 1.1: Fix Database Models & Configuration

## Description
Fix database model inconsistencies, circular imports, and configuration setup to support both SQLite (development) and PostgreSQL (production).

## Context
The current codebase has several database-related issues:
- `PostgreSQL`-specific types (`PG_UUID`, `ARRAY`, `JSONB`, `INET`) used with SQLite
- Circular imports between `audit.py` and `firewall_rule.py` models
- No Alembic migration setup
- Missing `.env.example` configuration file
- No configuration validation

## Files to Modify
- `backend/app/models/firewall_rule.py` - Fix compatibility
- `backend/app/models/approval.py` - Fix circular imports
- `backend/app/models/audit.py` - Fix circular imports
- `backend/app/database.py` - Fix engine setup
- `backend/app/config.py` - Add validation
- `backend/.env.example` - Create new file
- Add `backend/alembic/` directory structure

## Deliverables

### Code Changes
1. Refactor models to use SQLAlchemy types compatible with both SQLite and PostgreSQL
2. Remove circular imports by using string type annotations where needed
3. Add proper `__tablename__` and column definitions
4. Add Alembic configuration
5. Create `.env.example` with all required variables

### Tests
1. `backend/tests/test_models.py` - Test all model creation and relationships
2. `backend/tests/test_database.py` - Test database connection and initialization
3. `backend/tests/test_config.py` - Test configuration loading

### Documentation Updates
1. Update `README.md` with database setup instructions
2. Update `backend/README.md` (create if needed) with database migration instructions
3. Document the migration workflow

## Acceptance Criteria
- [ ] All models work with both SQLite and PostgreSQL
- [ ] No circular imports in any model file
- [ ] Alembic migrations can be initialized and applied
- [ ] `.env.example` contains all required variables with examples
- [ ] Configuration validates required fields
- [ ] All tests pass
- [ ] Documentation is complete and accurate

## Testing Requirements
- Unit tests for model creation and relationships
- Integration tests for database connection
- Tests for configuration loading and validation
- Verify both SQLite and PostgreSQL compatibility

## Notes
- Use `UUID` from `sqlalchemy` instead of `PG_UUID` for cross-database compatibility
- Use `Text` or `JSON` types instead of `JSONB` for SQLite compatibility
- Use `String(36)` or `Text` instead of `INET` for IP address storage
- Add proper cascade delete configurations
- Ensure all timestamps use UTC