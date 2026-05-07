# Workloads Module

## Overview

The Workloads module provides CRUD (Create, Read, Update, Delete) management for workload entities within the Azure Firewall Management application. Workloads represent cloud resources (VMs, App Services, Containers, etc.) that are protected by firewall rules.

## Module Structure

```
workloads/
├── README.md                    # This file
├── workloads.module.ts          # Module definition
├── workloads.routing.ts         # Route configuration
├── models/
│   └── workload.model.ts        # TypeScript interfaces and enums
├── services/
│   └── workloads.service.ts     # HTTP service for workload CRUD
└── components/
    ├── workloads-list.component.ts   # Table list with pagination/search
    ├── workload-detail.component.ts  # Detail view with rule associations
    ├── workload-form.component.ts    # Create/edit form
    └── confirmation-dialog.component.ts # Reusable confirmation dialog
```

## Routing

| Route | Component | Description |
|-------|-----------|-------------|
| `/workloads` | WorkloadsListComponent | Paginated table with search, filter, and bulk operations |
| `/workloads/:id` | WorkloadDetailComponent | Detailed view of a single workload |
| `/workloads/new` | WorkloadFormComponent | Create new workload form |
| `/workloads/:id/edit` | WorkloadFormComponent | Edit existing workload form |

## Components

### WorkloadsListComponent

A data table component that displays all workloads with the following features:

- **Pagination**: Configurable page size (default 50 items per page)
- **Sorting**: Click column headers to sort ascending/descending
- **Search**: Text filter for workload names
- **Status filter**: Filter by workload status (active, pending, inactive, deleted)
- **Bulk selection**: Checkbox selection for bulk delete operations
- **Row actions**: Edit, view, and delete buttons per row

### WorkloadDetailComponent

Shows detailed information about a single workload including:

- Workload metadata (name, type, environment, status, owner, etc.)
- Tags displayed as key-value pairs
- Associated firewall rules tab
- Available rules for association tab
- Edit and delete action buttons

### WorkloadFormComponent

Reactive form for creating and editing workloads with:

- **Required fields**: name, workload_type, environment
- **Optional fields**: description, resource_group, azure_resource_id, owner, contact_email
- **Tags**: Key-value pair management for workload metadata
- **Validation**: Client-side validation with visual error feedback
- **Dual mode**: Same component handles both create and edit operations

### ConfirmationDialogComponent

Reusable Material dialog component for confirmation prompts. Accepts a data object with title, message, and optional button labels. Returns `true` on confirm and `false` on cancel.

## Services

### WorkloadsService

Provides HTTP communication with the workload management API backend:

- `getWorkloads(page, pageSize, status?, search?)` - List workloads with pagination
- `getWorkload(id)` - Get single workload by ID
- `createWorkload(data)` - Create a new workload
- `updateWorkload(id, data)` - Update an existing workload
- `deleteWorkload(id)` - Delete a workload
- `bulkDelete(ids)` - Delete multiple workloads
- `getWorkloadRules(workloadId)` - Get associated firewall rules
- `associateRule(workloadId, ruleId, type)` - Link a rule to a workload
- `disassociateRule(workloadId, ruleId)` - Remove rule association

## Models

### Workload

```typescript
interface Workload {
    id: string;
    name: string;
    description?: string;
    workload_type: string;
    resource_group?: string;
    azure_resource_id?: string;
    environment: string;
    status: string;
    owner?: string;
    contact_email?: string;
    tags?: Record<string, string>;
    created_at: string;
    updated_at: string;
    rule_count?: number;
}
```

### Enums

```typescript
enum WorkloadType {
    VM = 'vm',
    APP_SERVICE = 'app_service',
    CONTAINER = 'container',
    FUNCTION = 'function',
    STORAGE = 'storage',
    DATABASE = 'database',
    OTHER = 'other'
}

enum WorkloadStatus {
    ACTIVE = 'active',
    PENDING = 'pending',
    INACTIVE = 'inactive',
    DELETED = 'deleted'
}
```

## Dependencies

- Angular Material (Table, Paginator, Sort, Input, Button, Icon, Card, Dialog, Checkbox, Snackbar, Progress Spinner, Select, Menu, Tabs, Expansion, Chips)
- Reactive Forms (FormGroup, FormBuilder, Validators)
- Router (RouterModule, ActivatedRoute)

## Backend API

The module communicates with the FastAPI backend at `/api/v1/workloads`. See backend API documentation for endpoint details.