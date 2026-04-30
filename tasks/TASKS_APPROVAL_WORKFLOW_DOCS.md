# Approval Workflow Documentation

## Overview

The approval workflow system provides multi-level approval management for firewall rule changes. It supports creating approval requests, multi-step approval chains, timeout handling, escalation logic, and bulk operations.

## Architecture

### Components

1. **ApprovalRequest** - The main entity representing a change request that needs approval
2. **ApprovalStep** - Individual steps in the approval chain
3. **ApprovalService** - Business logic for approval operations
4. **NotificationService** - Handles email, in-app, and webhook notifications
5. **Approval API** - REST endpoints for approval operations

### Approval Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Create      │────>│  Step 1:     │────>│  Step 2:     │
│  Request     │     │  Workload   │     │  Security    │
│              │     │  Stakeholder│     │  Stakeholder │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                      │
                     Pending                   Pending
                           │                      │
                    ┌──────▼──────┐      ┌──────▼──────┐
                    │  Approve    │      │  Approve    │
                    │  or Reject  │      │  or Reject  │
                    └──────┬──────┘      └──────┬──────┘
                           │                      │
                    ┌──────▼──────────────────────▼──────┐
                    │         Final Status               │
                    │  (Approved / Rejected / Expired)  │
                    └───────────────────────────────────┘
```

## Approval Statuses

| Status | Description |
|--------|-------------|
| `pending` | Awaiting approval from required stakeholders |
| `approved` | All required approvals have been granted |
| `rejected` | One or more approvers have rejected the request |
| `expired` | The approval request has timed out |
| `revoked` | The request was revoked by the creator |

## Change Types

| Change Type | Description |
|-------------|-------------|
| `create` | New firewall rule being created |
| `update` | Existing firewall rule being modified |
| `delete` | Firewall rule being removed |

## Approval Roles

| Role | Description |
|------|-------------|
| `workload_stakeholder` | The person/team responsible for the workload |
| `security_stakeholder` | Security team member responsible for firewall policy |

## API Endpoints

### Create Approval Request

```http
POST /api/approvals
Content-Type: application/json

{
  "rule_ids": ["uuid1", "uuid2"],
  "change_type": "create",
  "description": "Add new rule for production workload",
  "workload_id": "uuid",
  "required_approvals": 2
}
```

### Get Approval Request

```http
GET /api/approvals/{approval_id}
```

### Approve Step

```http
POST /api/approvals/{approval_id}/approve
Content-Type: application/json

{
  "comment": "Looks good, approved"
}
```

### Reject Step

```http
POST /api/approvals/{approval_id}/reject
Content-Type: application/json

{
  "comment": "Rule conflicts with existing policy"
}
```

### Add Comment

```http
POST /api/approvals/{approval_id}/comment
Content-Type: application/json

{
  "comment": "Need to verify with security team"
}
```

### List Approvals

```http
GET /api/approvals?page=1&page_size=50&status=pending
```

### Bulk Approve

```http
POST /api/approvals/bulk/approve
Content-Type: application/json

{
  "approval_ids": ["uuid1", "uuid2"],
  "comment": "Bulk approved all pending"
}
```

### Bulk Reject

```http
POST /api/approvals/bulk/reject
Content-Type: application/json

{
  "approval_ids": ["uuid1", "uuid2"],
  "comment": "Bulk rejected - too many changes"
}
```

## Timeout Handling

### Default Timeout

- **Default:** 48 hours
- Configurable via `ApprovalService(default_timeout_hours=N)`
- Timeout period starts from `created_at` timestamp

### Timeout Behavior

1. **Detection**: A background job or manual trigger checks for expired approvals
2. **Expiration**: Pending requests past timeout are marked `expired`
3. **Escalation** (optional): Requests can be escalated to a higher role
4. **Notification**: All stakeholders are notified of expiration

### Timeout API

```python
from app.services.approval_service import ApprovalService

service = ApprovalService(default_timeout_hours=48)

# Expire all timed-out requests
result = service.handle_timeout_escalation(
    db=session,
    timeout_hours=48,  # Override timeout
    escalate_to_role=ApprovalRole.SecurityStakeholder,  # Optional escalation
)

# Result:
{
    "expired_count": 5,
    "escalated_count": 2,
    "details": [...]
}
```

### Scheduled Timeout Check

Use a cron job or background worker to run timeout checks periodically:

```python
import schedule
from app.services.approval_service import ApprovalService

def timeout_check():
    from app.database import get_db
    service = ApprovalService(default_timeout_hours=48)
    
    with next(get_db()) as db:
        result = service.handle_timeout_escalation(db=db)
        print(f"Timed out: {result['expired_count']}")

schedule.every(6).hours.do(timeout_check)
```

## Escalation Logic

### Manual Escalation

```python
from app.services.approval_service import ApprovalService
from app.models.approval import ApprovalRole

service = ApprovalService()
result = service.escalate_approval(
    db=session,
    approval_id=approval_id,
    approver_id=current_user_id,
    new_approver_role=ApprovalRole.SecurityStakeholder,
    reason="Urgent change - stakeholder unavailable"
)
```

### Automatic Escalation

When `handle_timeout_escalation` is called with `escalate_to_role`, timed-out requests are automatically escalated:

1. Request is marked as `expired`
2. A new approval step with the escalated role is created
3. Comment is added: "Auto-escalated after N hours timeout"
4. Notification is sent to the escalated role

### Escalation Chain

```
Original Role ──(timeout)──> Escalated Role ──(timeout)──> Admin Role
    Workload                 Security                      Security Lead
```

## Notifications

### Notification Channels

| Channel | Status | Description |
|---------|--------|-------------|
| Email | Supported | SMTP-based email notifications |
| In-App | Supported | Database-stored notifications |
| Webhook | Supported | HTTP POST to configurable URL |

### Notification Types

| Type | Trigger |
|------|---------|
| `approval_request_created` | New approval request created |
| `approval_pending` | Action needed from recipient |
| `approval_approved` | Approval request approved |
| `approval_rejected` | Approval request rejected |
| `approval_expired` | Approval request timed out |
| `approval_escalated` | Request escalated to new role |
| `approval_bulk_completed` | Bulk operation completed |
| `escalation_triggered` | Escalation initiated |

### Configuring Notifications

```python
from app.services.notification_service import NotificationService

service = NotificationService(
    smtp_host="smtp.example.com",
    smtp_port=587,
    smtp_user="notifications@example.com",
    smtp_password="secret",
    from_email="noreply@example.com",
    use_tls=True,
    enable_email=True,
    enable_in_app=True,
    enable_webhook=True,
    webhook_url="https://hooks.example.com/notifications"
)
```

## Bulk Operations

### Bulk Approve

```python
from app.services.approval_service import ApprovalService

service = ApprovalService()
result = service.bulk_approve(
    db=session,
    approval_ids=[id1, id2, id3],
    approver_id=current_user_id,
    comment="Bulk approved all pending changes",
)
# Result: {
#     "approved_ids": ["uuid1", "uuid2"],
#     "rejected_ids": [],
#     "errors": [],
#     "total_processed": 3,
#     "total_approved": 2,
#     "total_rejected": 0
# }
```

### Bulk Reject

```python
result = service.bulk_reject(
    db=session,
    approval_ids=[id1, id2, id3],
    approver_id=current_user_id,
    comment="Bulk rejected - weekend changes",
)
```

## Testing

### Running Tests

```bash
cd backend
python -m pytest tests/test_approval_service.py -v
```

### Test Categories

| Category | Description |
|----------|-------------|
| Timeout Handling | Verifies timeout detection and expiration |
| Bulk Operations | Tests bulk approve/reject scenarios |
| Escalation | Tests manual and automatic escalation |
| Notifications | Tests notification delivery |
| Lifecycle | Tests full approval lifecycle |

## Integration with Firewall Service

### Creating Approval for Rule Change

```python
from app.services.approval_service import ApprovalService
from app.services.firewall_service import FirewallService
from app.models.approval import ChangeType

# Create rule change request
approval_service = ApprovalService()
firewall_service = FirewallService()

# Create approval request
approval = approval_service.create_approval_request(
    db=session,
    rule_ids=[rule_id],
    change_type=ChangeType.Create,
    description="Add rule for production API",
    user_id=current_user_id,
    workload_id=workload_id,
    required_approvals=2,
)

# Apply rule once approved
# (typically done in API route after approval is confirmed)
```

## Database Schema

### approval_requests Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| rule_ids | TEXT (JSON) | List of rule UUIDs |
| change_type | VARCHAR(50) | Type of change |
| description | TEXT | Change description |
| current_user_id | UUID | Request creator |
| status | VARCHAR(50) | Current status |
| workload_id | UUID | Associated workload |
| required_approvals | INTEGER | Required approval count |
| current_approval_stage | INTEGER | Current stage number |
| approval_flow | VARCHAR(50) | Flow type (multi_level) |
| created_at | TIMESTAMP | Creation time |
| completed_at | TIMESTAMP | Completion time |

### approval_steps Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| approval_request_id | UUID | Parent approval request |
| approver_id | UUID | Approver user ID |
| approver_role | VARCHAR(50) | Required role |
| status | VARCHAR(50) | Step status |
| comments | TEXT | Approval/rejection comments |
| approved_at | TIMESTAMP | Approval timestamp |
| created_at | TIMESTAMP | Creation timestamp |

## Best Practices

### Creating Approval Requests

1. Always provide a clear, concise description
2. Include all relevant rule IDs
3. Set appropriate `required_approvals` based on change impact
4. Associate with workload when applicable

### Handling Timeouts

1. Run timeout checks every 6-12 hours
2. Configure escalation role based on organizational hierarchy
3. Review expired requests regularly
4. Use escalation for urgent changes

### Bulk Operations

1. Filter pending requests before bulk operations
2. Document bulk changes in comment
3. Notify stakeholders after bulk operations
4. Review error results for failed items

### Notifications

1. Configure SMTP for email notifications
2. Set up webhook for Slack/Teams integration
3. Test notification delivery in staging
4. Monitor notification delivery rates

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Approvals not expiring | Ensure timeout check runs regularly |
| Notifications not sent | Check SMTP/webhook configuration |
| Escalation not working | Verify escalated role exists |
| Bulk approve failing | Check for already-approved items |

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed approval workflow activity.