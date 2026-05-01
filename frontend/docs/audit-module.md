# Audit Module Documentation

## Overview

The Audit Module provides a comprehensive audit log viewing, filtering, searching, and export capability for the application. It enables users to track and review all system events, changes, and actions performed by users.

## Table of Contents

- [Architecture](#architecture)
- [Components](#components)
- [Models](#models)
- [Services](#services)
- [Usage](#usage)
- [Features](#features)
- [API Reference](#api-reference)
- [Testing](#testing)

## Architecture

```
frontend/src/app/modules/audit/
├── models/
│   └── audit.model.ts          # Type definitions and interfaces
├── services/
│   └── audit.service.ts        # Audit data service
├── components/
│   ├── audit-viewer.component.ts   # Main audit viewer
│   └── audit-detail.component.ts   # Detail dialog component
├── audit.module.ts              # Module barrel exports
├── audit.spec.ts                # Unit tests
└── README.md                    # This documentation
```

## Components

### AuditViewerComponent

The main component for displaying audit log entries with filtering and pagination.

**Selector:** `app-audit-viewer`

**Standalone:** Yes

**Inputs:** None (uses internal state management)

**Outputs:** None (uses dialog for detail view)

#### Features

- **Paginated Table Display**: Shows audit entries in a sortable, paginated table with configurable page sizes (10, 25, 50, 100)
- **Full-Text Search**: Search across all audit fields including description, user, IP address, and resource type
- **Multi-Criteria Filtering**:
  - Date range filter (start and end dates)
  - Action type filter (CREATE, UPDATE, DELETE, READ, etc.)
  - Resource type filter (FIREWALL_RULE, USER, CONFIGURATION, etc.)
  - Severity filter (info, warning, error, success)
  - User filter
  - Success/failure filter
- **Summary Statistics Dashboard**: Displays total events, success/failure counts, and severity breakdown
- **Export Functionality**: Export filtered results to CSV or JSON format
- **Responsive Layout**: Adapts to different screen sizes

#### Template Structure

```html
<app-audit-viewer>
  <!-- Header with title and export buttons -->
  <!-- Summary cards (total, success, failure, critical) -->
  <!-- Filter panel with search and criteria -->
  <!-- Audit entries table -->
  <!-- Pagination controls -->
</app-audit-viewer>
```

#### Component Properties

| Property | Type | Description |
|----------|------|-------------|
| `isLoading` | `boolean` | Loading state indicator |
| `filteredEntries` | `AuditEntry[]` | Filtered audit entries displayed |
| `allEntries` | `AuditEntry[]` | All loaded audit entries |
| `availableUsers` | `string[]` | Unique users for filter dropdown |
| `filterForm` | `FormGroup` | Reactive form for filter criteria |
| `summary` | `AuditSummary` | Statistics summary data |
| `totalItems` | `number` | Total count of matching entries |
| `currentPage` | `number` | Current page number |
| `pageSize` | `number` | Items per page |

### AuditDetailComponent

Dialog component that displays detailed information about a single audit entry.

**Selector:** `app-audit-detail`

**Standalone:** Yes

#### Features

- **Overview Tab**: Shows entry metadata (timestamp, user, IP, HTTP method, path, status code, duration)
- **Changes Tab**: Displays field-by-field change diff for UPDATE operations
- **Details Tab**: Shows request/response details, operation result, and raw metadata
- **Copy Functionality**: Copy entry ID or full entry JSON to clipboard

#### Dialog Input

```typescript
interface AuditDetailData {
    entry: AuditEntry;
}
```

#### Usage

```typescript
import { AuditDetailComponent } from './audit/components/audit-detail.component';
import { MatDialog } from '@angular/material/dialog';

constructor(private dialog: MatDialog) {}

viewDetail(entry: AuditEntry) {
    this.dialog.open(AuditDetailComponent, {
        width: '800px',
        maxWidth: '90vw',
        data: { entry }
    });
}
```

## Models

### AuditEntry

The core interface representing a single audit log entry.

```typescript
interface AuditEntry {
    id: string;                    // Unique identifier
    timestamp: string;             // ISO 8601 timestamp
    user: string;                  // User identifier
    displayName?: string;          // Display name
    ipAddress?: string;            // Client IP address
    httpMethod?: string;           // HTTP method
    path?: string;                 // Request path
    statusCode?: number;           // Response status code
    action: AuditAction;           // Action performed
    resourceType: AuditResourceType; // Resource type
    resourceId?: string;           // Resource identifier
    description: string;           // Human-readable description
    details?: AuditDetails;        // Additional details
    severity: AuditSeverity;       // Severity level
    success: boolean;              // Success status
    durationMs?: number;           // Operation duration in ms
    requestId?: string;            // Request correlation ID
    metadata?: Record<string, any>; // Additional metadata
    changes?: AuditChange[];       // Field changes
    result?: AuditResult;          // Operation result
}
```

### AuditAction

Enum of possible audit actions:

```typescript
type AuditAction =
    | 'CREATE'
    | 'UPDATE'
    | 'DELETE'
    | 'READ'
    | 'LOGIN'
    | 'LOGOUT'
    | 'APPROVE'
    | 'REJECT'
    | 'IMPORT'
    | 'EXPORT'
    | 'CONFIGURE'
    | 'DEPLOY'
    | 'TEST'
    | 'EXECUTE';
```

### AuditResourceType

Types of resources that can be audited:

```typescript
type AuditResourceType =
    | 'FIREWALL_RULE'
    | 'ACCESS_RULE'
    | 'THRESHOLD'
    | 'WORKSPACE'
    | 'USER'
    | 'CONFIGURATION'
    | 'DEPLOYMENT'
    | 'APPROVAL'
    | 'RULE_EVALUATION'
    | 'BATCH_OPERATION'
    | 'WEBHOOK'
    | 'NOTIFICATION';
```

### AuditSeverity

Severity levels for audit entries:

```typescript
type AuditSeverity = 'info' | 'warning' | 'error' | 'success';
```

### AuditFilter

Filter criteria for searching audit logs:

```typescript
interface AuditFilter {
    searchQuery: string;
    dateFrom?: string;
    dateTo?: string;
    actionFilter?: AuditAction[];
    resourceTypeFilter?: AuditResourceType[];
    severityFilter?: AuditSeverity[];
    userFilter?: string[];
    successFilter?: boolean;
    resourceIdFilter?: string;
    page?: number;
    pageSize?: number;
}
```

### AuditSummary

Summary statistics for audit data:

```typescript
interface AuditSummary {
    totalCount: number;
    byAction: Record<string, number>;
    byResourceType: Record<string, number>;
    bySeverity: Record<string, number>;
    bySuccess: Record<string, number>;
    byUser: Record<string, number>;
    recentActivity: Array<{ date: string; count: number }>;
    topUsers: Array<{ user: string; count: number }>;
}
```

## Services

### AuditService

Provides methods for retrieving, filtering, searching, and exporting audit logs.

#### Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAuditLogs(page, pageSize, filters?)` | `Observable<AuditListResponse>` | Get paginated audit entries |
| `getAuditEntry(id)` | `Observable<AuditEntry>` | Get a single audit entry by ID |
| `searchAuditLogs(query, limit)` | `Observable<AuditEntry[]>` | Search audit entries by query |
| `getAuditSummary(dateFrom?, dateTo?)` | `Observable<AuditSummary>` | Get audit summary statistics |
| `exportAuditLogs(params)` | `Observable<Blob>` | Export audit logs in specified format |
| `exportAsCsv(filters)` | `Observable<Blob>` | Export as CSV format |
| `exportAsJson(filters)` | `Observable<Blob>` | Export as JSON format |
| `filterAuditEntries(entries, filters)` | `AuditEntry[]` | Client-side filter entries |
| `getSeverityDisplay(severity)` | `{label, color, icon, cssClass}` | Get severity display info |
| `getActionDisplay(action)` | `string` | Get human-readable action name |
| `getResourceTypeDisplay(resourceType)` | `string` | Get human-readable resource type |
| `formatTimestamp(dateString)` | `string` | Format timestamp for display |
| `getRelativeTime(dateString)` | `string` | Get relative time string |
| `formatDuration(ms)` | `string` | Format duration in human-readable format |
| `getActionIcon(action)` | `string` | Get icon for action type |
| `getResourceTypeIcon(resourceType)` | `string` | Get icon for resource type |
| `isRecent(entry)` | `boolean` | Check if entry is recent |
| `getUniqueUsers(entries)` | `string[]` | Get unique users from entries |
| `getUniqueResourceTypes(entries)` | `AuditResourceType[]` | Get unique resource types |
| `getUniqueActions(entries)` | `AuditAction[]` | Get unique actions |

#### Usage

```typescript
import { AuditService } from './services/audit.service';

constructor(private auditService: AuditService) {}

// Get audit logs
this.auditService.getAuditLogs(1, 20, filters).subscribe(response => {
    // Handle response
});

// Export as CSV
this.auditService.exportAsCsv(filters).subscribe(blob => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'audit_log.csv';
    link.click();
});
```

## Features

### Filtering

The Audit Module supports comprehensive filtering capabilities:

1. **Full-Text Search**: Search across all audit fields
2. **Date Range Filter**: Filter by start and end dates
3. **Action Filter**: Filter by specific action types
4. **Resource Type Filter**: Filter by resource types
5. **Severity Filter**: Filter by severity levels
6. **User Filter**: Filter by specific users
7. **Success Filter**: Filter by success/failure status
8. **Resource ID Filter**: Filter by specific resource identifier

Filters can be combined for precise results.

### Export

The module supports exporting audit logs in multiple formats:

1. **CSV Format**: Comma-separated values for spreadsheet applications
2. **JSON Format**: Structured JSON for programmatic processing
3. **PDF Format**: (API-side) Generated PDF documents
4. **XML Format**: (API-side) XML structured data

Export respects all applied filters.

### Summary Statistics

The module displays summary statistics including:

- Total event count
- Success/failure counts
- Severity distribution
- Action type distribution
- Resource type distribution
- Top users performing actions
- Recent activity trends

## Usage

### Basic Integration

```typescript
import { Component } from '@angular/core';
import { AuditViewerComponent } from './audit/components/audit-viewer.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [AuditViewerComponent],
  template: `<app-audit-viewer></app-audit-viewer>`
})
export class DashboardComponent {}
```

### With Routing

```typescript
import { Routes } from '@angular/router';
import { AuditViewerComponent } from './audit/components/audit-viewer.component';

export const routes: Routes = [
    {
        path: 'audit',
        component: AuditViewerComponent
    }
];
```

### Programmatic Navigation

```typescript
import { Router } from '@angular/router';

constructor(private router: Router) {}

navigateToAudit() {
    this.router.navigate(['/audit']);
}
```

## API Integration

### GET /api/v1/audit

Retrieve paginated audit entries.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| page | number | Page number (1-based) |
| page_size | number | Items per page |
| search | string | Search query |
| date_from | string | Start date (ISO 8601) |
| date_to | string | End date (ISO 8601) |
| actions | string | Comma-separated action types |
| resource_types | string | Comma-separated resource types |
| severity | string | Comma-separated severity levels |
| users | string | Comma-separated user identifiers |
| success | boolean | Success/failure filter |

**Response:**

```json
{
    "items": [...],
    "total": 100,
    "page": 1,
    "pageSize": 20,
    "totalPages": 5
}
```

### GET /api/v1/audit/:id

Get a single audit entry by ID.

**Response:** `AuditEntry` object

### GET /api/v1/audit/summary

Get audit summary statistics.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| date_from | string | Start date (ISO 8601) |
| date_to | string | End date (ISO 8601) |

**Response:** `AuditSummary` object

### GET /api/v1/audit/export/:format

Export audit logs.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| format | string | Export format (csv, json, pdf, xml) |

**Response:** Export file as Blob

### GET /api/v1/audit/search

Search audit entries.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| query | string | Search query |
| limit | number | Maximum results |

**Response:** Array of `AuditEntry` objects

## Testing

### Unit Tests

Run unit tests:

```bash
ng test --spec="audit"
```

### Test Coverage

The Audit Module includes comprehensive tests covering:

- Model validation and type checking
- Service methods and error handling
- Component rendering and interactions
- Filter functionality
- Export functionality
- Integration testing

### Running Tests

```bash
# Run all tests
ng test

# Run audit-specific tests
ng test --include="[path-to-audit-specs]"
```

## Best Practices

### Performance

1. **Pagination**: Always use server-side pagination for large datasets
2. **Filter Caching**: Cache filter states for better UX
3. **Lazy Loading**: Load audit entries lazily when component initializes
4. **Debounced Search**: Implement debounced search to reduce API calls

### Security

1. **Authorization**: Ensure users have proper permissions to view audit logs
2. **Data Masking**: Mask sensitive data in audit entries
3. **Access Logging**: Log all audit view actions

### Accessibility

1. **Keyboard Navigation**: Support keyboard navigation for table and filters
2. **Screen Reader**: Provide ARIA labels for interactive elements
3. **Color Contrast**: Ensure sufficient color contrast for severity indicators

## Troubleshooting

### Common Issues

1. **Empty Audit Log**: Check API connectivity and permissions
2. **Filter Not Working**: Verify filter parameter format
3. **Export Not Downloading**: Check browser settings for file downloads

### Debug Mode

Enable debug logging:

```typescript
this.auditService.getAuditLogs(1, 20, filters).subscribe({
    next: (response) => console.log('Audit response:', response),
    error: (err) => console.error('Audit error:', err)
});
```

## Changelog

### Version 1.0.0 (Initial Release)

- Audit viewer component with paginated table display
- Comprehensive filtering and search capabilities
- Export to CSV and JSON formats
- Detail view dialog with change tracking
- Summary statistics dashboard
- Responsive design
- Comprehensive test coverage