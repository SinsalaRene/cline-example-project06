# Approvals Module Documentation

## Overview

The Approvals Module provides a comprehensive UI for reviewing, approving, and rejecting firewall rule change requests. It supports individual and bulk operations, commenting, filtering, and detailed change visualization.

## Architecture

### Module Structure

```
frontend/src/app/modules/approvals/
├── models/
│   └── approval.model.ts          # TypeScript interfaces and types
├── services/
│   ├── approvals.service.ts       # API integration service
│   └── approvals.service.spec.ts  # Service unit tests
├── components/
│   ├── approvals-list.component.ts    # Main list view
│   ├── approval-detail.component.ts   # Detail dialog
│   ├── approval-comments.component.ts  # Comment system
│   ├── bulk-action-dialog.component.ts # Bulk action dialog
│   └── approvals-list.component.spec.ts # Component tests
├── approvals.module.ts              # Module exports
└── docs/
    └── APPROVALS_MODULE_DOCS.md     # This documentation
```

## Components

### ApprovalsListComponent

The main list view for approval requests.

#### Features
- Pagination with configurable page sizes
- Search across rule names, requestors, and descriptions
- Filter by status, type, and priority
- Bulk selection with multi-select
- Bulk approve/reject operations
- Inline quick approve/reject actions
- Stats dashboard showing approval counts
- Responsive table layout

#### Usage

```typescript
// Standalone usage (recommended)
import { ApprovalsListComponent } from './approvals/approvals-list.component';

// In your template
<app-approvals-list></app-approvals-list>
```

#### Inputs
| Property | Type | Description |
|----------|------|-------------|
| - | - | Component loads data from API directly |

#### Outputs
| Event | Description |
|-------|-------------|
| refresh | Emits when data needs reloading |

### ApprovalDetailComponent

Dialog component showing full details of an approval request.

#### Features
- Overview tab with all request details
- Changes tab showing diff between old and new values
- Comments tab for team discussion
- Approve/Reject actions from detail view
- Expiration warnings
- Priority and status badges

#### Usage

```typescript
// Open from parent component
const dialogRef = this.dialog.open(ApprovalDetailComponent, {
    width: '800px',
    data: { approval: approvalRequest }
});
```

### ApprovalCommentsComponent

Reusable comment system for approval requests.

#### Features
- Comment list with avatars and timestamps
- Comment creation with validation
- Comment deletion
- Notification mode
- Empty state display
- Character limits (1000 chars)

#### Usage

```typescript
<app-approval-comments
    [approvalId]="approval.id"
    [comments]="approval.comments"
    [currentUser]="currentUserId"
    [isPending]="approval.status === 'pending'"
    (commentAdded)="onCommentAdded($event)"
    (commentDeleted)="onCommentDeleted($event)"
></app-approval-comments>
```

#### Inputs
| Property | Type | Description |
|----------|------|-------------|
| approvalId | string | ID of the approval request |
| comments | ApprovalComment[] | Existing comments |
| currentUser | string | Current user's name |
| isPending | boolean | Whether approval is still pending |
| isReply | boolean | Whether in reply mode |
| canDelete | function | Function to check if user can delete |

#### Outputs
| Event | Description |
|-------|-------------|
| commentAdded | Emitted when a comment is added |
| commentDeleted | Emitted with comment ID when deleted |
| clearAllComments | Emitted when all comments should be cleared |

### BulkActionDialogComponent

Dialog for confirming bulk approve/reject operations.

#### Features
- Comment input for bulk actions
- Required reason field
- Priority selector
- Character limits

#### Usage

```typescript
const dialogRef = this.dialog.open(BulkActionDialogComponent, {
    width: '500px',
    data: {
        title: 'Bulk Approve',
        message: `Approve ${count} request(s)?`,
        confirmLabel: 'Approve All',
        type: 'primary',
        showReason: true
    }
});
```

## Service

### ApprovalsService

Provides all API integration for the approvals module.

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `getApprovals(page, pageSize, filters)` | `Observable<ApprovalListResponse>` | Get paginated approval list |
| `getApproval(id)` | `Observable<ApprovalRequest>` | Get single approval |
| `approve(id, data?)` | `Observable<ApprovalRequest>` | Approve an approval |
| `reject(id, data?)` | `Observable<ApprovalRequest>` | Reject an approval |
| `addComment(approvalId, text)` | `Observable<ApprovalComment>` | Add comment |
| `getComments(approvalId)` | `Observable<ApprovalComment[]>` | Get comments |
| `deleteComment(approvalId, commentId)` | `Observable<void>` | Delete comment |
| `bulkApprove(ids, comment?)` | `Observable<BulkActionResult>` | Bulk approve |
| `bulkReject(ids, reason, comment?)` | `Observable<BulkActionResult>` | Bulk reject |
| `isExpired(approval)` | `boolean` | Check if expired |
| `getStatusDisplay(status)` | `{label, color, icon}` | Get status UI info |
| `getPriorityDisplay(priority)` | `{label, color, icon}` | Get priority UI info |

#### Usage

```typescript
constructor(private approvalsService: ApprovalsService) {}

loadApprovals() {
    this.approvalsService.getApprovals(1, 20, filters).subscribe({
        next: (response) => {
            this.approvals = response.items;
        },
        error: (err) => {
            console.error('Failed to load approvals:', err);
        }
    });
}
```

## Data Models

### ApprovalRequest

```typescript
interface ApprovalRequest {
    id: string;
    rule_name: string;
    rule_id: string;
    requestor: string;
    request_type: 'create' | 'update' | 'delete' | 'enable' | 'disable';
    status: 'pending' | 'approved' | 'rejected' | 'expired' | 'timeout';
    description?: string;
    requested_at: string;
    due_at?: string;
    approved_by?: string;
    approved_at?: string;
    rejection_reason?: string;
    comments: ApprovalComment[];
    metadata: ApprovalMetadata;
    priority: 'low' | 'medium' | 'high' | 'urgent';
}
```

### ApprovalComment

```typescript
interface ApprovalComment {
    id: string;
    author: string;
    text: string;
    created_at: string;
}
```

### ApprovalFilter

```typescript
interface ApprovalFilter {
    searchQuery: string;
    statusFilter: string;
    typeFilter: string;
    priorityFilter: string;
}
```

## Status Values

| Status | Description |
|--------|-------------|
| `pending` | Awaiting approval |
| `approved` | Approved by authorized user |
| `rejected` | Rejected with reason |
| `expired` | Past deadline without action |
| `timeout` | System timeout |

## Priority Values

| Priority | Color | Description |
|----------|-------|-------------|
| `low` | Blue | Non-urgent changes |
| `medium` | Orange | Standard priority |
| `high` | Red | Important changes |
| `urgent` | Dark red | Time-critical changes |

## Request Types

| Type | Description |
|------|-------------|
| `create` | New firewall rule creation |
| `update` | Existing rule modification |
| `delete` | Rule removal |
| `enable` | Enable a disabled rule |
| `disable` | Disable an active rule |

## UI Features

### Stats Cards
The list view includes four stat cards showing counts for:
- Pending approvals (orange)
- Approved count (green)
- Rejected count (red)
- Total count (blue)

### Status Badges
Status badges display with appropriate colors:
- Pending: `#ff9800` (orange)
- Approved: `#4caf50` (green)
- Rejected: `#f44336` (red)
- Expired/Timeout: `#9e9e9e` (gray)

### Priority Badges
Priority badges display with appropriate colors:
- Low: `#2196f3` (blue)
- Medium: `#ff9800` (orange)
- High: `#f44336` (red)
- Urgent: `#d50000` (dark red)

## Accessibility

- All interactive elements have proper ARIA labels
- Keyboard navigation for table rows
- Color contrast meets WCAG AA standards
- Screen reader announcements for actions
- Focus management for dialogs

## Error Handling

The module handles common error scenarios:
- Network failures show snackbar notifications
- Empty states display helpful messages
- Validation errors shown inline
- Rate limiting handled with retry logic

## Best Practices

1. **Always use the standalone components** - They are fully self-contained and tree-shakeable
2. **Use the service for API calls** - Don't inject HttpClient directly into your components
3. **Handle errors at the component level** - Use the snackBar for user feedback
4. **Respect the filter state** - Filters persist until reset
5. **Use bulk operations for efficiency** - When handling many approvals

## Related Modules

- [Rules Module](../rules/docs/RULES_MODULE_USAGE.md) - Firewall rule management
- Auth Module - Authentication and guards
- Dashboard Module - Overview and metrics