# Cross-Module Workflow Documentation

## Overview

This document describes the workflow orchestration system introduced in **Task 7.2: Cross-Module Integration**. The workflow system wires together the approval, audit, and notification modules to create a cohesive cross-module integration layer.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                API Layer                                     │
│  (approvals.py, rules.py, audit.py, etc.)                                   │
└────────────────────────┬────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ApprovalService                                       │
│   - Creates approval requests                                                │
│   - Approves/rejects steps                                                  │
│   - Bulk operations                                                          │
│   - Timeout handling                                                         │
└─────────────┬──────────────────────┬───────────────────────┬────────────────┘
              │                      │                       │
              ▼                      ▼                       ▼
┌─────────────────────┐ ┌───────────────────┐ ┌─────────────────────┐
│   ApprovalWorkflow  │ │  AuditWorkflow    │ │  NotificationWorkflow│
│                     │ │                   │ │                     │
│ • apply_approval    │ │ • log_api_operation│ │ • send_approval    │
│ • apply_rule_change │ │ • log_created      │ │ • send_audit       │
│ • apply_rule_delete │ │ • log_updated      │ │ • send_azure_sync  │
│ • apply_rule_clone  │ │ • log_deleted      │ │ • send_system      │
│ • apply_rule_action │ │ • log_azure_sync   │ │ • send_bulk        │
└────────┬────────────┘ └────────┬──────────┘ └────────┬──────────┘
         │                        │                      │
         ▼                        ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Services Layer                                        │
│  • ApprovalService  • AuditService  • NotificationService • FirewallService │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Workflow Components

### 1. ApprovalWorkflow (`backend/app/workflows/approval_workflow.py`)

The ApprovalWorkflow handles the transition from approval approval to rule application. When an approval request is fully approved (all steps completed), this workflow:

1. **Retrieves rule UUIDs** from the approval request's `rule_ids` JSON field
2. **Applies rule changes** based on the `change_type`:
   - `create`: Applies rule action and marks rule as created
   - `update`: Updates existing rule attributes
   - `delete`: Marks rule as deleted (soft delete)
   - `clone`: Creates a copy of the rule
3. **Applies timing constraints**: If the approval has `applied_from` and `applied_until` dates, the rule change is applied within that time window only
4. **Returns an `ApprovalResult`** with status, rule_ids affected, and any errors

#### Key Methods

```python
class ApprovalWorkflow:
    def apply_approval_to_rules(
        self,
        db: Session,
        approval_request: ApprovalRequest,
        rule_ids: list[UUID],
        user_id: UUID,
    ) -> ApprovalResult:
        """Apply approval changes to the specified rules."""
        ...
```

#### Rule Change Actions

| ChangeType | Action | Description |
|------------|--------|-------------|
| CREATE | `create` | Creates a new rule in Azure |
| UPDATE | `update` | Updates an existing rule |
| DELETE | `delete` | Soft-deletes a rule (marks as inactive) |
| CLONE | `clone` | Creates a copy of an existing rule |

#### Timing Constraints

When `approval_request.applied_from` and `approval_request.applied_until` are set, the workflow checks:

```python
now = datetime.now(timezone.utc)
applied_from = approval_request.applied_from
applied_until = approval_request.applied_until

if applied_from and now < applied_from:
    return ApprovalResult(status="pending", ...)
if applied_until and now > applied_until:
    return ApprovalResult(status="expired", ...)
```

### 2. AuditWorkflow (`backend/app/workflows/audit_workflow.py`)

The AuditWorkflow ensures every API operation is logged in the audit trail. It wraps the AuditService to provide a consistent audit logging pattern.

#### Key Methods

| Method | Purpose |
|--------|---------|
| `log_api_operation()` | Generic API operation logging |
| `log_firewall_rule_created()` | Log firewall rule creation |
| `log_firewall_rule_updated()` | Log firewall rule update |
| `log_firewall_rule_deleted()` | Log firewall rule deletion |
| `log_firewall_rule_cloned()` | Log firewall rule cloning |
| `log_approval_created()` | Log approval request creation |
| `log_approval_approved()` | Log approval approval |
| `log_approval_rejected()` | Log approval rejection |
| `log_bulk_operation()` | Log bulk operation summary |
| `log_notification_sent()` | Log notification delivery |
| `log_azure_sync()` | Log Azure sync operation |

#### Audit Data Model

Each audit entry includes:
- `user_id`: Who performed the action
- `action`: What operation was performed (create, update, delete, etc.)
- `resource_type`: Type of resource (firewall_rule, approval_request, etc.)
- `resource_id`: ID of the resource
- `old_value`: Previous state (before the change)
- `new_value`: New state (after the change)
- `metadata`: Additional context (correlation_id, IP address, etc.)

#### Example Usage

```python
audit_wf = AuditWorkflow()
audit_wf.log_firewall_rule_created(
    db=session,
    user_id=user_uuid,
    rule_id=rule_uuid,
    rule_data={"name": "new-rule", "priority": 100},
    correlation_id="req-12345",
)
```

### 3. NotificationWorkflow (`backend/app/workflows/notification_workflow.py`)

The NotificationWorkflow routes notifications to appropriate channels (email, in-app, webhook). It wraps the NotificationService to provide channel-aware delivery.

#### Notification Channels

| Channel | Description | Use Case |
|---------|-------------|----------|
| EMAIL | SMTP-based email | High-priority notifications |
| IN_APP | Database-stored notification | User dashboard |
| WEBHOOK | HTTP POST to webhook URL | Integration with external systems |
| ALL | Send via all enabled channels | Critical events |

#### Key Methods

| Method | Purpose |
|--------|---------|
| `send_approval_notification()` | Send approval status notifications |
| `send_bulk_approval_notifications()` | Send to multiple recipients |
| `send_audit_notification()` | Send audit event notifications |
| `send_azure_sync_notification()` | Send Azure sync status notifications |
| `send_system_notification()` | Send general system notifications |
| `send_multi_channel()` | Send via all channels |

#### Notification Types

| Type | Channel | Priority |
|------|---------|----------|
| APPROVAL_APPROVED | Email + In-App | High |
| APPROVAL_REJECTED | Email + In-App | High |
| AUDIT_LOG | In-App | Low |
| AZURE_SYNC | Email | Medium |
| SYSTEM | Configurable | Configurable |

#### Example Usage

```python
notify_wf = NotificationWorkflow()
result = notify_wf.send_approval_notification(
    db=session,
    approval_request=approval,
    notification_type=NotificationType.APPROVAL_APPROVED,
    channel=NotificationChannel.EMAIL,
    recipient_email="user@example.com",
    recipient_name="User Name",
)
```

## Integration Points

### ApprovalService → Workflows

The `ApprovalService` is updated to use workflows automatically:

1. **On `approve_step()` completion** (all steps done):
   - `ApprovalWorkflow.apply_approval_to_rules()` is called
   - `AuditWorkflow.log_approval_approved()` is called
   - `NotificationWorkflow.send_approval_notification()` is called

2. **On `reject_step()` completion**:
   - `AuditWorkflow.log_approval_rejected()` is called

3. **On `bulk_approve()` completion**:
   - `AuditWorkflow.log_bulk_operation()` is called
   - `NotificationWorkflow.send_approval_notification()` is called

4. **On `handle_timeout_escalation()` completion**:
   - `AuditWorkflow.log_api_operation()` is called

### Cross-Module Flow

```
1. User creates approval request
   → AuditWorkflow.log_approval_created()
   → NotificationWorkflow.send_approval_notification(APPROVAL_REQUEST_CREATED)

2. Approver approves first step
   → AuditWorkflow.log_approval_approved() (partial)

3. All steps complete → approval fully approved
   → ApprovalWorkflow.apply_approval_to_rules()
   → AuditWorkflow.log_approval_approved() (final)
   → NotificationWorkflow.send_approval_notification(APPROVAL_APPROVED)

4. Rules are applied to Azure (if timing constraints met)
   → AuditWorkflow.log_azure_sync()
   → NotificationWorkflow.send_azure_sync_notification()
```

## Configuration

### Service Initialization

The `ApprovalService` accepts workflow instances:

```python
from app.services.approval_service import ApprovalService
from app.workflows import ApprovalWorkflow, AuditWorkflow, NotificationWorkflow

approval_wf = ApprovalWorkflow()
audit_wf = AuditWorkflow()
notify_wf = NotificationWorkflow()

service = ApprovalService(
    approval_workflow=approval_wf,
    audit_workflow=audit_wf,
    notification_workflow=notify_wf,
)
```

### Notification Configuration

The `NotificationService` is configured via environment variables:

```python
NotificationService(
    smtp_host=os.getenv("SMTP_HOST", "localhost"),
    smtp_port=int(os.getenv("SMTP_PORT", "587")),
    smtp_user=os.getenv("SMTP_USER", ""),
    smtp_password=os.getenv("SMTP_PASSWORD", ""),
    from_email=os.getenv("FROM_EMAIL", "noreply@example.com"),
    use_tls=True,
    enable_email=os.getenv("ENABLE_EMAIL", "true").lower() == "true",
    enable_in_app=os.getenv("ENABLE_IN_APP", "true").lower() == "true",
    enable_webhook=os.getenv("ENABLE_WEBHOOK", "false").lower() == "true",
    webhook_url=os.getenv("WEBHOOK_URL", ""),
)
```

## Testing

Tests are located in `backend/tests/test_workflows.py` and cover:

1. **ApprovalWorkflow**:
   - Rule creation via approval
   - Rule update via approval
   - Rule deletion via approval
   - Rule cloning via approval
   - Timing constraint enforcement
   - Error handling

2. **AuditWorkflow**:
   - API operation logging
   - Firewall rule operations
   - Approval lifecycle events
   - Bulk operation logging
   - Azure sync logging
   - Error handling

3. **NotificationWorkflow**:
   - Approval notification delivery
   - Audit notification delivery
   - Azure sync notification delivery
   - Multi-channel delivery
   - Bulk notification delivery
   - Error handling

## Error Handling

All workflows implement graceful error handling:

1. **AuditWorkflow**: Catches exceptions and returns `False` instead of raising
2. **NotificationWorkflow**: Catches exceptions and returns `NotificationResult(success=False, error=...)`
3. **ApprovalWorkflow**: Continues applying rules even if some fail

The `ApprovalService` catches workflow exceptions and logs them without failing the main operation:

```python
try:
    self._approval_workflow.apply_approval_to_rules(...)
except Exception:
    self._logger.exception("Failed to apply approval to rules via workflow")
```

## Future Enhancements

1. **Async notification delivery**: Use Celery/RQ for background email sending
2. **Notification throttling**: Prevent notification storms
3. **Notification deduplication**: Avoid duplicate notifications
4. **Custom notification templates**: Per-user notification preferences
5. **Notification retry**: Retry failed deliveries with exponential backoff
6. **Notification analytics**: Track delivery rates and response times