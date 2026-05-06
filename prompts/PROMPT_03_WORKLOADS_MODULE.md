# PROMPT 3: Workloads Module Completion

## Context

You are working on an Azure Firewall Management application built with Angular (frontend) and FastAPI/Python (backend). The workloads module has component files but is not wired up to routing and may have incomplete service integration.

**Relevant files for this prompt:**
- `frontend/src/app/modules/workloads/workloads.module.ts`
- `frontend/src/app/modules/workloads/components/workloads-list.component.ts`
- `frontend/src/app/modules/workloads/components/workload-detail.component.ts`
- `frontend/src/app/modules/workloads/components/workload-form.component.ts`
- `frontend/src/app/modules/workloads/components/confirmation-dialog.component.ts`
- `frontend/src/app/modules/workloads/services/workloads.service.ts` (if exists)
- `frontend/src/app/modules/workloads/models/workload.model.ts` (if exists)
- `frontend/src/app/app-routing.module.ts`

**Known state:**
- WorkloadsModule exists with declarations but no routing
- Components: WorkloadsListComponent, WorkloadDetailComponent, WorkloadFormComponent, ConfirmationDialogComponent
- Backend likely has endpoints for CRUD on workloads (check backend routes)

## Task

Complete the workloads module to provide full CRUD functionality:

### 1. Module & Routing
- Create or update a routing module for workloads: `workloads.routing.ts`
- Routes:
  - `workloads` → WorkloadsListComponent
  - `workloads/:id` → WorkloadDetailComponent
  - `workloads/new` → WorkloadFormComponent (create mode)
  - `workloads/:id/edit` → WorkloadFormComponent (edit mode)
- Wire routing into WorkloadsModule
- Update `app-routing.module.ts` to lazy-load workloads module

### 2. WorkloadsService
- Create or update `frontend/src/app/modules/workloads/services/workloads.service.ts`
- Methods: `getWorkloads()`, `getWorkload(id)`, `createWorkload(data)`, `updateWorkload(id, data)`, `deleteWorkload(id)`
- Use HttpClient with proper error handling
- Return Observable types

### 3. Workloads Models
- Create or update `frontend/src/app/modules/workloads/models/workload.model.ts`
- Define Workload interface with: id, name, type, description, status, tags, createdAt, updatedAt

### 4. WorkloadsListComponent
- If incomplete, implement with:
  - MatTable with columns: name, type, status, tags
  - MatPaginator + MatSort
  - Search field
  - "Add Workload" button
  - Edit/Delete action buttons per row
  - Loading spinner
  - Empty state when no workloads

### 5. WorkloadDetailComponent
- Shows workload details in card layout
- Edit button → navigates to edit form
- Delete button → opens ConfirmationDialogComponent
- Shows associated firewall rules if linked

### 6. WorkloadFormComponent
- Reactive form with fields: name, type, description, tags
- Form validation: required name, type must be valid option
- Submit calls service create or update method
- Cancel button returns to list

### 7. ConfirmationDialogComponent
- Material dialog with confirm/cancel buttons
- Shows confirmation message
- Returns boolean result on close

## Quality Checks

1. [ ] WorkloadsModule has proper routing configuration
2. [ ] WorkloadsService has all CRUD methods
3. [ ] WorkloadsListComponent displays data with pagination and search
4. [ ] WorkloadFormComponent validates and submits data
5. [ ] WorkloadDetailComponent shows details and has edit/delete actions
6. [ ] ConfirmationDialogComponent works for delete confirmation
7. [ ] App routing lazy-loads workloads module
8. [ ] No TypeScript compilation errors
9. [ ] All new services/components have JSDoc documentation

## Skills

Before starting, load and activate these skills:

```
use_skill(skill_name="tdd")
```

Follow the TDD skill's red-green-refactor loop. Write unit tests for WorkloadsService CRUD methods, form validation logic, and component routing before implementing the components.

## Documentation Requirements

- Add JSDoc block at top of each new file
- Update workloads module documentation
- Add a README.md in `frontend/src/app/modules/workloads/` explaining the module structure
