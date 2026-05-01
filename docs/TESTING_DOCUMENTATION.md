# Testing Documentation - Backend Unit Tests

## Overview

This document provides comprehensive testing documentation for the backend unit tests covering all services, models, auth, config, and schemas.

## Test Structure

### Test Files Organization

```
backend/tests/
├── __init__.py                    # Test package initialization
├── test_models.py                 # Model-level tests
├── test_auth.py                   # Authentication tests
├── test_services.py               # Service layer tests
├── test_config.py                 # Configuration tests
├── test_schemas.py                # Schema validation tests
├── test_approval_service.py       # Approval & Notification service tests
├── test_audit_api.py              # Audit API endpoint tests
├── test_approvals_api.py          # Approvals API endpoint tests
├── test_firewall_api.py           # Firewall API endpoint tests
├── test_middleware.py             # Middleware tests
├── test_rate_limiting.py          # Rate limiting tests
└── conftest.py                    # Shared pytest fixtures
```

## Test Coverage by Component

### 1. Models (`test_models.py`)

| Model | Tests | Coverage |
|-------|-------|----------|
| User | `test_user_model_creation`, `test_user_model_defaults`, `test_user_model_repr`, `test_user_model_validation` | ✓ |
| FirewallRule | `test_firewall_rule_creation`, `test_firewall_rule_status_enum`, `test_firewall_rule_validation` | ✓ |
| FirewallRuleStatus | `test_status_enum_values` | ✓ |
| AuditLog | `test_audit_log_creation`, `test_audit_log_action_enum` | ✓ |
| ApprovalRequest | `test_approval_request_creation`, `test_approval_request_status_enum` | ✓ |
| ApprovalStep | `test_approval_step_creation`, `test_approval_step_status_enum` | ✓ |
| Notification | `test_notification_creation`, `test_notification_type_enum` | ✓ |
| Config | `test_config_model_creation` | ✓ |

**Key test scenarios:**
- Model instantiation with all required fields
- Default value assignment
- Validation constraints
- String representation (`__repr__`)
- Enum value verification

### 2. Authentication (`test_auth.py`)

| Component | Tests | Coverage |
|-----------|-------|----------|
| Auth Service | `test_auth_service_initialization`, `test_create_access_token`, `test_create_refresh_token`, `test_verify_token`, `test_get_current_user` | ✓ |
| Token Blacklisting | `test_blacklist_token`, `test_unblacklist_token`, `test_is_token_blacklisted`, `test_blacklist_duplicate_token`, `test_blacklist_nonexistent_token`, `test_blacklist_with_user_id` | ✓ |
| Token Management | `test_get_blacklisted_token_metadata`, `test_refresh_token`, `test_refresh_token_invalid`, `test_refresh_token_blacklisted` | ✓ |
| Permission Check | `test_check_permission`, `test_check_permission_no_roles` | ✓ |

**Key test scenarios:**
- JWT token creation and validation
- Token expiration handling
- Token blacklist operations
- User identity extraction from tokens
- Permission-based access control

### 3. Services (`test_services.py` + `test_approval_service.py`)

#### FirewallService

| Method | Tests | Coverage |
|--------|-------|----------|
| `get_firewall_rules` | Pagination, filtering by status | ✓ |
| `get_firewall_rule` | Rule retrieval, not-found handling | ✓ |
| `create_firewall_rule` | Creation, validation (name, action, protocol, priority) | ✓ |
| `update_firewall_rule` | Rule updates, not-found handling | ✓ |
| `delete_firewall_rule` | Deletion, not-found handling | ✓ |
| `import_firewall_rules_from_azure` | Bulk import, validation errors, empty list | ✓ |

#### WorkloadService

| Method | Tests | Coverage |
|--------|-------|----------|
| `get_workloads` | Empty result set | ✓ |
| `create_workload` | Creation, validation | ✓ |
| `get_workload` | Not-found handling | ✓ |
| `update_workload` | Updates | ✓ |
| `delete_workload` | Deletion | ✓ |

#### ApprovalService

| Method | Tests | Coverage |
|--------|-------|----------|
| `create_approval_request` | Creation, step generation, validation | ✓ |
| `approve_step` | Step approval, duplicate prevention | ✓ |
| `reject_step` | Step rejection, comment requirement | ✓ |
| `get_approval_requests` | Pagination | ✓ |
| `check_and_expire_pending_approvals` | Timeout handling | ✓ |
| `bulk_approve` | Single, multiple, mixed statuses | ✓ |
| `bulk_reject` | Bulk rejection | ✓ |
| `escalate_approval` | Escalation with role changes | ✓ |
| `handle_timeout_escalation` | Timeout + escalation | ✓ |
| `get_pending_approval_count` | Count verification | ✓ |

#### AuditService

| Method | Tests | Coverage |
|--------|-------|----------|
| `log_action` | Entry creation, JSON serialization | ✓ |
| `get_audit_logs` | Pagination, filtering by action/resource | ✓ |
| `get_audit_for_resource` | Resource-specific logs | ✓ |
| `get_audit_for_user` | User-specific logs | ✓ |
| `export_audit_logs` | Export serialization | ✓ |
| `log_firewall_rule_change` | Convenience method | ✓ |
| `log_approval_change` | Convenience method | ✓ |

#### NotificationService

| Method | Tests | Coverage |
|--------|-------|----------|
| `__init__` | Default and custom configuration | ✓ |
| `NotificationMessage` | Creation, timestamp handling | ✓ |
| `_build_notification_message` | Template building | ✓ |
| `send_approval_notification` | Email, in-app, webhook delivery | ✓ |
| `send_bulk_approval_notification` | Bulk notification | ✓ |
| `send_escalation_notification` | Escalation notification | ✓ |
| `get_notification_history` | History retrieval with pagination | ✓ |

### 4. Configuration (`test_config.py`)

| Component | Tests | Coverage |
|-----------|-------|----------|
| Settings (Pydantic v2) | `test_settings_loads_from_env`, `test_settings_defaults`, `test_settings_database_url`, `test_settings_secret_key_rotation`, `test_settings_debug_mode`, `test_settings_optional_fields` | ✓ |
| Config Module | `test_config_module_loads`, `test_config_settings_access`, `test_config_reload` | ✓ |
| Database Config | `test_database_config`, `test_database_url_construction` | ✓ |

**Key test scenarios:**
- Environment variable loading
- Default value assignment
- Database URL construction
- Secret key rotation handling
- Debug mode configuration

### 5. Schemas (`test_schemas.py`)

| Schema | Tests | Coverage |
|--------|-------|----------|
| FirewallRuleCreate | Creation validation | ✓ |
| FirewallRuleUpdate | Update validation | ✓ |
| FirewallRuleResponse | Response serialization | ✓ |
| PaginationSchema | Pagination metadata | ✓ |
| PaginatedResponse | Response wrapping | ✓ |
| AuditLogResponse | Audit log serialization | ✓ |
| ApprovalCreateRequest | Approval creation | ✓ |
| ApprovalResponse | Approval response | ✓ |
| ApprovalStepResponse | Step response | ✓ |
| TokenBlacklistRequest | Token blacklisting | ✓ |
| UserInfo | User information schema | ✓ |
| UserRole | Role enum values | ✓ |
| RateLimitInfo | Rate limiting info | ✓ |
| UserRoleAssignment | Role assignment | ✓ |
| CreateUserRequest | User creation | ✓ |
| UpdateUserRequest | User updates | ✓ |

## Running Tests

### Prerequisites

```bash
# Install test dependencies
cd backend
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio

# Or install in development mode
pip install -e ".[dev]"
```

### Execute Tests

```bash
# Run all tests
pytest

# Run tests for specific file
pytest backend/tests/test_models.py -v

# Run tests with coverage report
pytest --cov=app --cov-report=term-missing --cov-report=html

# Run specific test class
pytest backend/tests/test_services.py::TestFirewallService -v

# Run specific test method
pytest backend/tests/test_services.py::TestFirewallService::test_service_initialization -v

# Run with verbose output
pytest -v --tb=short

# Run tests matching pattern
pytest -k "approval" -v
```

### CI/CD Integration

Add to your CI/CD pipeline configuration:

```yaml
test:
  script:
    - cd backend
    - pytest --cov=app --cov-report=xml --tb=short
  artifacts:
    reports:
      coverage: coverage.xml
```

## Testing Best Practices

### 1. Isolation

Each test should be independent:
- Use fresh database sessions for each test
- Clean up resources after tests
- Mock external services (SMTP, HTTP clients)

### 2. Fixtures

Use pytest fixtures for reusable test data:
```python
@pytest.fixture
def session():
    """Create a test database session."""
    # Setup
    yield db_session
    # Teardown
```

### 3. Parameterized Tests

Use `pytest.mark.parametrize` for testing multiple inputs:
```python
@pytest.mark.parametrize("status,expected", [
    ("Active", True),
    ("Pending", False),
])
```

### 4. Mocking

Use `unittest.mock` for external dependencies:
```python
@patch("app.services.notification_service.smtplib.SMTP")
def test_send_email(self, mock_smtp):
    # Test with mocked SMTP
```

### 5. Coverage Targets

| Component | Target Coverage |
|-----------|---------------|
| Models | 100% |
| Auth | 90%+ |
| Services | 85%+ |
| Config | 95%+ |
| Schemas | 90%+ |

## Test Data Generation

### UUIDs

```python
import uuid
test_id = uuid.uuid4()
```

### Dates

```python
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)
past = datetime.now(timezone.utc) - timedelta(days=7)
```

### Test Users

```python
test_user_id = uuid.uuid4()
test_admin_id = uuid.uuid4()
```

## Debugging Tests

### Verbose Output

```bash
pytest -vv --tb=long
```

### Capture Output

```bash
pytest -s  # Print stdout/stderr
pytest -rP  # Show print statements
```

### Interactive Debugging

```python
import pdb; pdb.set_trace()
```

### IDE Integration

- **VS Code**: Configure `launch.json` for pytest debugging
- **PyCharm**: Use built-in pytest runner with breakpoints

## Common Test Patterns

### Testing ValueError Exceptions

```python
def test_invalid_input_raises(self):
    with pytest.raises(ValueError, match="expected error"):
        service.method(invalid_input)
```

### Testing Database Operations

```python
def test_create_and_query(self, session):
    # Create
    item = Item(data="test")
    session.add(item)
    session.commit()
    
    # Query
    result = session.query(Item).filter_by(data="test").first()
    assert result is not None
```

### Testing API Responses

```python
def test_api_response_format(self, client):
    response = client.get("/api/endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
```

## Continuous Improvement

### Adding New Tests

1. Identify new functionality or edge cases
2. Write tests following existing patterns
3. Run tests to ensure coverage
4. Document new test cases

### Maintaining Tests

- Remove obsolete tests
- Update tests when models/schemas change
- Refactor slow tests for better performance
- Add integration tests for critical paths

### Measuring Quality

Track these metrics:
- Code coverage percentage
- Test execution time
- Flaky test count
- Test failure rate
- Branch coverage

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/latest/orm/basic_examples.html)
- [Python unittest](https://docs.python.org/3/library/unittest.html)
- [Coverage.py](https://coverage.readthedocs.io/)