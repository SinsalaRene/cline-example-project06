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

## NetworkService

**File**: `network_service.py`

Manages network topology entities including Virtual Networks, Subnets, NSGs, NSG Rules,
External Network Devices, and Network Connections.

#### Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `get_topology_graph()` | Get complete network topology with all nodes and connections | `db` |
| `get_vnets()` | Get all virtual networks with optional filters | `db`, `location`, `resource_group` |
| `get_vnet()` | Get virtual network by ID | `db`, `vnet_id` |
| `create_vnet()` | Create new virtual network | `db`, `name`, `address_space`, `location`, `resource_group`, optional fields |
| `update_vnet()` | Update existing virtual network | `db`, `vnet_id`, `**kwargs` |
| `delete_vnet()` | Delete virtual network | `db`, `vnet_id` |
| `get_subnets()` | Get subnets, optionally filtered by vnet_id | `db`, `vnet_id` |
| `get_subnet()` | Get subnet by ID | `db`, `subnet_id` |
| `create_subnet()` | Create new subnet | `db`, `name`, `address_prefix`, `vnet_id`, optional fields |
| `delete_subnet()` | Delete subnet | `db`, `subnet_id` |
| `get_nsgs()` | Get NSGs, optionally filtered by vnet_id | `db`, `vnet_id` |
| `get_nsg()` | Get NSG by ID | `db`, `nsg_id` |
| `create_nsg()` | Create new NSG | `db`, `name`, `location`, `vnet_id`, `resource_group`, optional fields |
| `update_nsg()` | Update existing NSG | `db`, `nsg_id`, `**kwargs` |
| `delete_nsg()` | Delete NSG | `db`, `nsg_id` |
| `get_nsg_rules()` | Get all rules for an NSG, ordered by priority | `db`, `nsg_id` |
| `create_nsg_rule()` | Create new NSG rule | `db`, `nsg_id`, `name`, `priority`, `direction`, `protocol`, `access`, required fields |
| `update_nsg_rule()` | Update NSG rule | `db`, `rule_id`, `**kwargs` |
| `delete_nsg_rule()` | Delete NSG rule | `db`, `rule_id` |
| `reorder_nsg_rules()` | Reorder NSG rules by priority | `db`, `nsg_id`, `rule_ids` (ordered list) |
| `get_external_devices()` | Get all external network devices | `db` |
| `create_external_device()` | Create new external network device | `db`, `name`, `device_type`, optional fields |
| `update_external_device()` | Update external network device | `db`, `device_id`, `**kwargs` |
| `delete_external_device()` | Delete external network device | `db`, `device_id` |
| `get_connections()` | Get connections with optional source/destination filters | `db`, `source_id`, `source_type`, `dest_id`, `dest_type` |
| `create_connection()` | Create new network connection | `db`, `source_id`, `source_type`, `destination_id`, `destination_type`, `connection_type`, optional fields |
| `delete_connection()` | Delete network connection | `db`, `connection_id` |
| `analyze_impact()` | Analyze impact of NSG rule changes | `db`, `nsg_id`, `updated_rules` |
| `sync_nsg_to_azure()` | Sync NSG configuration to Azure | `db`, `nsg_id` |

#### Impact Analysis

The `analyze_impact` method compares old vs new NSG rules and returns:
- `affected_subnets`: Subnets reachable by changed rules
- `affected_external_devices`: External devices reachable by changed rules
- `before_rules`: Previous rules (serialized)
- `after_rules`: Updated rules (serialized)

This is critical for change management — operators can review which network segments
and external devices will be affected before applying rule changes.

### AzureSyncService

**File**: `azure_sync_service.py`

Manages synchronization between local network entities and Azure resources.

#### Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `sync_nsg_from_azure()` | Sync NSG rules from Azure | `db`, `nsg_id` |
| `sync_nsg_to_azure()` | Push NSG rules to Azure | `db`, `nsg_id` |
| `sync_vnet_from_azure()` | Sync VNet from Azure | `db`, `vnet_id` |
| `sync_all_nsgs()` | Sync all pending NSGs | `db` |

### NotificationService

**File**: `notification_service.py`

Handles notification delivery for events and alerts.

#### Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `send_notification()` | Send a notification | `recipient`, `subject`, `message` |

## Service Dependencies

```
firewall_service.py → app.models.firewall_rule
approval_service.py → app.models.approval
audit_service.py → app.models.audit
network_service.py → app.models.network
azure_sync_service.py → app.models.network, app.integrations.azure_client
notification_service.py → app.models.audit
```

## Changelog

### 2026-06-30 - Service Refactoring

- Converted all services from static methods to class-based DI pattern
- Added proper error handling with try/except and rollback
- Added comprehensive logging throughout
- Added input validation with descriptive error messages
- Added type hints for all method signatures
- Added docstrings following Google-style conventions