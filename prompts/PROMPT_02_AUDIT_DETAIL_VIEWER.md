# PROMPT 2: Audit Detail & Viewer Components

## Context

You are working on an Azure Firewall Management application built with Angular (frontend) and FastAPI/Python (backend). The audit module now has enhanced list view (completed in Prompt 1). Next, implement the detail and viewer components for deep audit entry inspection and resource-specific audit history.

**Relevant files for this prompt:**
- `frontend/src/app/modules/audit/audit.module.ts`
- `frontend/src/app/modules/audit/components/audit-list.component.ts`
- `frontend/src/app/modules/audit/services/audit.service.ts`
- `frontend/src/app/modules/audit/models/audit.model.ts`
- `frontend/src/app/modules/audit/components/audit-detail.component.ts` (if exists)
- `frontend/src/app/modules/audit/components/audit-viewer.component.ts` (if exists)

**Known state:**
- Backend API has endpoints: `GET /audit/{id}`, `GET /audit/resource/{resource_id}`, `GET /audit/by-correlation/{correlation_id}`
- AuditService has methods: `getAuditEntry(id)`, `searchAuditLogs(query, limit)`, `filterAuditEntries(entries, filters)`
- AuditListComponent has columns: timestamp, level, action, user_id, resource_type, resource_id, message, ip_address
- The component uses standalone component pattern with inline template

## Task

Create or complete the following components and wire them into routing:

### 1. AuditDetailComponent (`audit-detail.component.ts`)
A detail view for a single audit entry. Features:
- Displays all fields of a single audit entry in a card-based layout
- Shows `old_value` and `new_value` as formatted JSON diff side-by-side
- Uses a "before/after" visual comparison for the diff
- Shows metadata: timestamp (formatted), user, IP address, correlation ID
- Has a "Back" button to return to audit list
- Shows severity badge using existing service method `getSeverityDisplay()`
- Shows action label using existing service method `getActionDisplay()`
- Shows resource type label using `getResourceTypeDisplay()`
- Uses `formatTimestamp()` and `getRelativeTime()` for time display
- Loading spinner while data is being fetched
- Error state with retry button if fetch fails

### 2. AuditViewerComponent (`audit-viewer.component.ts`)
A filtered, sortable view of audit history for a specific resource. Features:
- Takes resource_type and resource_id as route params or input
- Calls `getAuditLogs()` with `resourceIdFilter` param
- Shows same columns as AuditListComponent but filtered to this resource
- Has its own date range picker (default: last 90 days)
- Has "Back" button
- Uses MatPaginator for pagination
- Uses MatSort for column sorting
- Loading and error states

### 3. Routing Configuration
- Add routes in `audit.module.ts` or create a separate routing module:
  - `audit/detail/:id` → AuditDetailComponent
  - `audit/resource/:resourceType/:resourceId` → AuditViewerComponent
- If these component files already exist (even if incomplete), update them to match the spec above

### 4. Navigation Integration
- In AuditListComponent, add a clickable row or icon to navigate to the detail view
- The route should be: `/audit/detail/{entry.id}`
- Add a "View Audit History" button/link that navigates to `/audit/resource/{entry.resourceType}/{entry.resourceId}`

### 5. Update AuditModule
- Declare both new components
- Add RouterModule with the routes
- Export both components for standalone usage

## Quality Checks

1. [ ] AuditDetailComponent renders and shows all fields correctly
2. [ ] old_value/new_value displayed as formatted JSON diff
3. [ ] AuditViewerComponent filters correctly by resource
4. [ ] Both components have proper loading and error states
5. [ ] Routing works: navigate to /audit/detail/:id and /audit/resource/:type/:id
6. [ ] Back buttons work in both components
7. [ ] AuditListComponent has navigation to detail and viewer
8. [ ] No TypeScript compilation errors
9. [ ] Both components documented with JSDoc

## Skills

Before starting, load and activate these skills:

```
use_skill(skill_name="tdd")
```

Follow the TDD skill's red-green-refactor loop. Write unit tests for component routing, navigation logic, and data fetching before implementing the components themselves.

## Documentation Requirements

- Update `frontend/src/app/modules/audit/audit.module.ts` with updated module documentation
- Add inline comments explaining the component architecture decisions
