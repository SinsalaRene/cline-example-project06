# Workloads Module Documentation

## Overview

The Workloads Module is a comprehensive Angular module for managing cloud workload resources within the Azure governance framework. It provides full CRUD (Create, Read, Update, Delete) operations for workloads with integrated rule association capabilities.

## Architecture

### Module Structure

```
frontend/src/app/modules/workloads/
├── models/
│   └── workload.model.ts           # Data models and interfaces
├── services/
│   ├── workloads.service.ts        # API communication layer
│   └── workloads.service.spec.ts   # Service unit tests
├── components/
│   ├── workloads-list.component.ts # Main list view
│   ├── workloads-list.component.html
│   ├── workloads-list.component.css
│   ├── workload-detail.component.ts # Detail view component
│   ├── workload-detail.component.html
│   ├── workload-detail.component.css
│   ├── workload-form.component.ts   # Create/Edit form
│   ├── workload-form.component.html
│   ├── workload-form.component.css
│   ├── confirmation-dialog.component.ts
│   ├── confirmation-dialog.component.html
│   ├── confirmation-dialog.component.css
│   └── workloads-list.spec.ts       # Component tests
├── workloads.module.ts              # Angular module definition
└── workloads.routing.ts             # Route definitions
```

## Components

### WorkloadsListComponent

**Purpose**: Displays a paginated table of all workloads with search and filtering capabilities.

**Features**:
- Paginated table view using Angular Material Table
- Search/filter functionality
- Bulk selection for batch operations
- Delete confirmation dialog
- Navigate to detail view
- Access to create new workload form

**Selector**: `app-workloads-list`

### WorkloadDetailComponent

**Purpose**: Displays detailed information about a single workload and its associated rules.

**Features**:
- Full workload details display
- Associated rules list with association type
- Rule disassociation capability
- Edit workload action
- Delete workload action
- Status and environment badges

**Selector**: `app-workload-detail`

### WorkloadFormComponent

**Purpose**: Form for creating or editing workloads.

**Features**:
- Reactive form with validation
- Support for all workload fields
- Tags management (add/remove)
- Workload type selection
- Environment selection
- Status selection
- Form submission loading states
- Edit and create modes

**Selector**: `app-workload-form`

### ConfirmationDialogComponent

**Purpose**: Generic confirmation dialog for destructive actions.

**Features**:
- Configurable title and message
- Configurable button labels
- Returns confirmation result

**Selector**: `app-confirmation-dialog`

## Data Models

### Workload

```typescript
interface Workload {
    id: string;
    name: string;
    description?: string;
    workload_type: WorkloadType;
    environment: EnvironmentType;
    status: WorkloadStatus;
    tags: Record<string, string>;
    resource_group?: string;
    azure_resource_id?: string;
    owner?: string;
    contact_email?: string;
    created_at: string;
    updated_at: string;
}
```

### WorkloadType

```typescript
type WorkloadType = 'azure' | 'aws' | 'gcp' | 'on_premise';
```

### EnvironmentType

```typescript
type EnvironmentType = 'dev' | 'staging' | 'prod';
```

### WorkloadStatus

```typescript
type WorkloadStatus = 'active' | 'pending' | 'inactive' | 'deleted';
```

## Service Layer

### WorkloadsService

The service provides methods for all workload-related API calls.

**Methods**:

- `getWorkloads(params?)` - Get paginated list of workloads
- `getWorkload(id)` - Get single workload by ID
- `createWorkload(data)` - Create new workload
- `updateWorkload(id, data)` - Update existing workload
- `deleteWorkload(id)` - Delete workload
- `getWorkloadRules(id)` - Get rules associated with workload
- `associateRule(workloadId, ruleId, associationType)` - Associate rule
- `disassociateRule(workloadId, ruleId)` - Disassociate rule

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workloads` | List all workloads |
| GET | `/api/workloads/{id}` | Get single workload |
| POST | `/api/workloads` | Create new workload |
| PUT | `/api/workloads/{id}` | Update workload |
| DELETE | `/api/workloads/{id}` | Delete workload |
| GET | `/api/workloads/{id}/rules` | Get workload rules |
| POST | `/api/workloads/{id}/rules/{ruleId}` | Associate rule |
| DELETE | `/api/workloads/{id}/rules/{ruleId}` | Disassociate rule |

## Routing

The module defines the following routes:

| Path | Component | Description |
|------|-----------|-------------|
| `workloads` | WorkloadsListComponent | List all workloads |
| `workloads/create` | WorkloadFormComponent | Create new workload |
| `workloads/:id` | WorkloadDetailComponent | View workload details |
| `workloads/:id/edit` | WorkloadFormComponent | Edit workload |

## Styling

The module uses Angular Material components for consistent styling. Custom styles are defined in component-specific CSS files.

### Design Patterns

- **Responsive Grid Layouts**: Form fields use responsive grid layouts
- **Status Badges**: Color-coded badges for workload status and environment
- **Loading States**: Spinners and skeleton loading indicators
- **Confirmation Dialogs**: For destructive actions (delete, disassociate)
- **Error Handling**: Form validation errors displayed inline

## Testing

### Unit Tests

Tests are located alongside their source files:
- Service tests: `services/workloads.service.spec.ts`
- Component tests: `components/workloads-list.spec.ts`

**Test Coverage**:
- Service methods (CRUD operations)
- API endpoint verification
- HTTP method verification
- Response handling
- Component instantiation
- Template rendering

## Usage Example

### List Workloads

```typescript
// Navigate to workloads list
this.router.navigate(['/workloads']);
```

### Create Workload

```typescript
// Navigate to create form
this.router.navigate(['/workloads/create']);
```

### View Workload Details

```typescript
// Navigate to workload detail
this.router.navigate(['/workloads', workloadId]);
```

### Edit Workload

```typescript
// Navigate to edit form
this.router.navigate(['/workloads', workloadId, 'edit']);
```

### Associate Rule

```typescript
this.workloadsService.associateRule(
    workloadId, 
    ruleId, 
    'include'
).subscribe(result => {
    // Handle success
});
```

## Dependencies

The module depends on the following Angular Material modules:

- `MatTableModule` - Data table
- `MatPaginatorModule` - Pagination
- `MatSortModule` - Column sorting
- `MatInputModule` - Form inputs
- `MatFormFieldModule` - Form field containers
- `MatButtonModule` - Buttons
- `MatIconModule` - Icons
- `MatCardModule` - Card containers
- `MatDialogModule` - Dialogs
- `MatCheckboxModule` - Checkboxes
- `MatSnackBarModule` - Notifications
- `MatProgressSpinnerModule` - Loading spinners
- `MatSelectModule` - Select dropdowns
- `MatTabsModule` - Tab navigation
- `MatExpansionModule` - Collapsible sections
- `MatChipsModule` - Tag chips
- `MatMenuModule` - Context menus

## Best Practices

1. **Always use the service layer** for API calls rather than making HTTP requests directly
2. **Handle loading states** appropriately in all views
3. **Show confirmation dialogs** for destructive actions
4. **Use reactive forms** for consistent form handling
5. **Validate all inputs** on both client and server side
6. **Display appropriate error messages** for all failure scenarios
7. **Use status badges** for visual status indication
8. **Implement proper route guards** for authentication