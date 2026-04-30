# Services Documentation

## Overview

This package contains service layer classes that implement the Dependency Injection (DI) pattern for FastAPI integration. All services follow a consistent class-based architecture where database sessions are injected at the method level.

## Architecture

### Service Pattern

All services follow the DI pattern where:
1. Dependencies (like `Session`) are injected at the method level
2. Service instances are created per-request, not singleton
3. Each service has its own logger namespace
4. All methods accept `db: Session` as first parameter

### Usage in FastAPI Routes

```python
from fastapi import APIRouter, Depends, Depends
from sqlalchemy.orm import Session
from app.services.firewall_service import FirewallService
from app.core.deps import get_current_user

router = APIRouter()

@router.get("/rules")
def get_rules(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FirewallService()
    result = service.get_firewall_rules(
        db=db,
        user_id=current_user.id,
    )
    return result
```

## Services

### FirewallService

**File**: `firewall_service.py`

Manages Azure Firewall rules and workload relationships.

#### Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `get_firewall_rules()` | Get paginated firewall rules with filtering | `db`, `user_id`, `workload_id`, `status`, `page`, `page_size` |
| `get_firewall_rule()` | Get single rule by ID | `db`, `rule_id` |
| `create_firewall_rule()` | Create new firewall rule | `db`, `rule_collection_name`, `priority`, `action`, `protocol`, optional fields |
| `update_firewall_rule()` | Update existing rule fields | `db`, `rule_id`, `user_id`, `**kwargs` |
| `delete_firewall_rule()` | Delete firewall rule | `db`, `rule_id` |
| `import_firewall_rules_from_azure()` | Import rules from Azure data source | `db`, `rules_data` |

#### WorkloadService

Embedded service for workload management with methods:
- `get_workloads()` - Get all workloads
- `get_workload()` - Get workload by ID
- `create_workload()` - Create new workload
- `update_workload()` - Update existing workload
- `delete_workload()` - Delete workload

### ApprovalService

**File**: `approval_service.py`

Manages multi-level approval workflows.

#### Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `create_approval_request()` | Create approval request with steps | `db`, `rule_ids`, `change_type`, `description`, `user_id`, `workload_id`, `required_approvals` |
| `approve_step()` | Approve a workflow step | `db`, `step_id`, `approver_id`, `comment` |
| `reject_step()` | Reject a workflow step | `db`, `step_id`, `approver_id`, `comment` |
| `check_and_expire_pending_approvals()` | Expire timed-out approvals | `db` |
| `get_approval_requests()` | Get paginated approval requests | `db`, `user_id`, `status`, `page`, `page_size` |

#### Approval Workflow

The approval service implements a two-stage workflow:
1. **Workload Stakeholder** approval
2. **Security Stakeholder** approval

Each request is created with a configurable timeout (default 48 hours).

### AuditService

**File**: `audit_service.py`

Manages audit logging for all significant actions.

#### Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `log_action()` | Create audit log entry | `db`, `user_id`, `action`, `resource_type`, `resource_id`, `old_value`, `new_value`, `ip_address`, `correlation_id` |
| `get_audit_logs()` | Get paginated audit logs with filtering | `db`, `user_id`, `action`, `resource_type`, `page`, `page_size` |
| `get_audit_for_resource()` | Get audit logs for specific resource | `db`, `resource_type`, `resource_id` |
| `get_audit_for_user()` | Get audit logs for specific user | `db`, `user_id` |
| `export_audit_logs()` | Export all audit logs as serializable dict | `db` |
| `log_firewall_rule_change()` | Convenience method for firewall audit | `db`, `user_id`, `action`, `rule_id`, `old_data`, `new_data`, `ip_address` |
| `log_approval_change()` | Convenience method for approval audit | `db`, `user_id`, `action`, `approval_id`, `old_data`, `new_data` |

## Logging

All services use Python's standard `logging` module with module-level loggers. Log messages are structured with:
- `INFO`: Normal operational messages
- `WARNING`: Non-critical issues
- `ERROR`: Operation failures
- `DEBUG`: Detailed tracing information

### Logger Names

| Service | Logger Name |
|---------|-------------|
| FirewallService | `app.services.firewall_service` |
| ApprovalService | `app.services.approval_service` |
| AuditService | `app.services.audit_service` |

### Configuring Logger Names

Custom logger names can be specified during service initialization:

```python
service = FirewallService(logger_name="my.custom.logger.name")
```

## Error Handling

All services implement consistent error handling:

| Error Type | When Raised |
|------------|-------------|
| `ValueError` | Invalid input parameters (empty names, missing required fields) |
| `Exception` | Database commit/connection failures (with rollback) |

### Custom Exception Messages

All error messages include context information:
- Resource IDs
- Parameter names and values
- Operation context

## Testing

Tests are located in `backend/tests/test_services.py` with test classes:
- `TestFirewallService` - Firewall service tests
- `TestWorkloadService` - Workload service tests
- `TestApprovalService` - Approval service tests
- `TestAuditService` - Audit service tests

### Running Tests

```bash
pytest backend/tests/test_services.py -v
```

## Data Types

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | `UUID` | Stored as UUID in models |
| `rule_ids` | `list[UUID]` | Converted to JSON string for storage |
| `ip_address` | `Optional[str]` | IP address string |
| `correlation_id` | `Optional[UUID]` | Request correlation ID |
| `old_value` | `Optional[dict]` | Serialized as JSON for storage |
| `new_value` | `Optional[dict]` | Serialized as JSON for storage |

## Service Dependencies

```
firewall_service.py → app.models.firewall_rule
approval_service.py → app.models.approval
audit_service.py → app.models.audit
```

## Changelog

### 2026-06-30 - Service Refactoring

- Converted all services from static methods to class-based DI pattern
- Added proper error handling with try/except and rollback
- Added comprehensive logging throughout
- Added input validation with descriptive error messages
- Added type hints for all method signatures
- Added docstrings following Google-style conventions