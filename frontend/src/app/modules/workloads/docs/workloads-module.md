# Workloads Module Documentation

## Overview

The **Workloads** module is part of the Azure Firewall Management application built with Angular. It provides a complete CRUD interface for managing cloud workloads that are protected by firewall rules.

## Module Structure

```
workloads/
├── workloads.module.ts          # Angular module definition
├── workloads.routing.ts         # Route configuration (lazy-loaded)
├── README.md                    # Module overview and documentation
├── docs/
│   └── workloads-module.md      # This detailed documentation
├── models/
│   └── workload.model.ts        # TypeScript interfaces and enums
├── services/
│   └── workloads.service.ts     # HTTP service for API communication
└── components/
    ├── workloads-list.component.ts    # List with pagination and search
    ├── workload-detail.component.ts   # Detail view with rule associations
    ├── workload-form.component.ts     # Create/edit form (reusable)
    └── confirmation-dialog.component.ts  # Reusable confirmation dialog
```

## Architecture

The module follows Angular best practices with:

- **Lazy-loaded routing**: The module is loaded on-demand when users navigate to `/workloads`
- **Reactive forms**: The form component uses `FormGroup` and `FormBuilder` for predictable state management
- **Service layer**: All HTTP communication is centralized in `WorkloadsService`
- **Standalone components**: Components are declared in the module (not standalone) to share Material imports
- **Observable streams**: Services return `Observable` types for reactive data flow

## Routes

| Path | Component | Mode | Description |
|------|-----------|------|-------------|
| `workloads` | WorkloadsListComponent | — | Paginated table of all workloads |
| `workloads/:id` | WorkloadDetailComponent | view | Detail view of a single workload |
| `workloads/new` | WorkloadFormComponent | create | Form to create a new workload |
| `workloads/:id/edit` | WorkloadFormComponent | edit | Form to edit an existing workload |

The `WorkloadFormComponent` is **dual-mode**: it detects whether it's in create or edit mode based on the presence of the `:id` route parameter.

## Data Flow

```
User Action
    ↓
Component (event handler)
    ↓
WorkloadsService (HTTP call)
    ↓
Backend API (/api/v1/workloads)
    ↓
Service returns Observable<T>
    ↓
Component subscribes and updates view
```

## Interfaces

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

| Enum | Values | Description |
|------|--------|-------------|
| `WorkloadType` | `vm`, `app_service`, `container`, `function`, `storage`, `database`, `other` | Cloud resource type |
| `WorkloadStatus` | `active`, `pending`, `inactive`, `deleted` | Lifecycle status |

## API Endpoints

The service communicates with the backend at `/api/v1/workloads`:

| Method | Endpoint | Service Method | Description |
|--------|----------|----------------|-------------|
| GET | `/api/v1/workloads` | `getWorkloads()` | List all workloads with pagination |
| GET | `/api/v1/workloads/:id` | `getWorkload(id)` | Get single workload |
| POST | `/api/v1/workloads` | `createWorkload(data)` | Create new workload |
| PUT | `/api/v1/workloads/:id` | `updateWorkload(id, data)` | Update workload |
| DELETE | `/api/v1/workloads/:id` | `deleteWorkload(id)` | Delete workload |

## Dependencies

### Angular Material
- `MatTableModule` - Data table for the list view
- `MatPaginatorModule` - Pagination controls
- `MatSortModule` - Column sorting
- `MatInputModule` - Input fields
- `MatButtonModule` - Buttons
- `MatIconModule` - Icon buttons
- `MatCardModule` - Card layouts
- `MatDialogModule` - Confirmation dialog
- `MatCheckboxModule` - Row selection
- `MatSnackBar` - Notifications
- `MatProgressSpinnerModule` - Loading indicators
- `MatSelectModule` - Dropdown selects
- `MatTabsModule` - Tabs for detail view
- `MatExpansionModule` - Expandable sections
- `MatChipsModule` - Tags display

### Angular Core
- `ReactiveFormsModule` - Reactive forms
- `RouterModule` - Routing
- `HttpClientModule` - HTTP communication

## Error Handling

The service and components implement layered error handling:

1. **Service layer**: Errors are caught and re-emitted with context
2. **Component layer**: Error subscriptions show snack bar notifications
3. **Form validation**: Required fields show inline error messages

## Testing

Recommended test coverage:

- **WorkloadsService**: HTTP stubs for all CRUD methods
- **WorkloadFormComponent**: Form validation, create/update modes
- **WorkloadsListComponent**: Table rendering, pagination, search
- **ConfirmationDialogComponent**: Dialog open/close/confirm behavior