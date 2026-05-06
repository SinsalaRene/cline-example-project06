# PROMPT 1: Audit Module Enhancement

## Context

You are working on an Azure Firewall Management application built with Angular (frontend) and FastAPI/Python (backend). The audit module has a service layer with comprehensive methods but the UI is incomplete — it only shows a basic table with no date filtering, no export buttons, no filter dropdowns, and no summary statistics.

**Relevant files for this prompt:**
- `frontend/src/app/modules/audit/components/audit-list.component.ts`
- `frontend/src/app/modules/audit/services/audit.service.ts`
- `frontend/src/app/modules/audit/models/audit.model.ts`
- `frontend/src/app/modules/audit/audit.module.ts`

**Known state:**
- AuditService has methods: `getAuditLogs()`, `searchAuditLogs()`, `exportAuditLogs()`, `getAuditSummary()`, `filterAuditEntries()`, `getSeverityDisplay()`, `getActionDisplay()`, `getResourceTypeDisplay()`, `formatTimestamp()`, `getRelativeTime()`
- AuditListComponent only calls `getAuditLogs(0)` (wrong pagination) and has no date filtering, export, or summary UI
- Backend API has endpoints: `GET /audit`, `GET /audit/search`, `GET /audit/export`, `GET /audit/export/csv`, `GET /audit/stats`
- The AuditFilter interface supports: searchQuery, dateFrom, dateTo, actionFilter, resourceTypeFilter, severityFilter, userFilter, successFilter, resourceIdFilter

## Task

Enhance the AuditListComponent in `frontend/src/app/modules/audit/components/audit-list.component.ts` to provide a complete, production-quality audit log experience:

### 1. Date Range Picker
- Add a date range filter using Angular Material DatePicker (MatDateModule, MatNativeDateModule)
- Show two date inputs: "From" and "To" alongside the search field
- When dates change, call `getAuditLogs()` with the new dateFrom/dateTo params
- Default: show last 30 days

### 2. Filter Dropdowns
- Add filter chips/buttons for: action types, resource types, severity levels
- Use the existing service methods `getSeverityDisplay()`, `getActionDisplay()`, `getResourceTypeDisplay()` for display labels
- Each filter type should be a multi-select dropdown (MatSelect with checkboxes)
- When filters change, call `getAuditLogs()` with updated params

### 3. Export Buttons
- Add "Export CSV" and "Export JSON" buttons
- Wire them to the existing service methods `exportAsCsv(filters)` and `exportAsJson(filters)`
- On success, trigger file download using the returned Blob

### 4. Summary Statistics Card
- Add a summary statistics card above the filter bar
- Call `getAuditSummary()` on component init and after each filter change (debounced)
- Display: total_entries, by_action (top 5), by_resource_type (top 5)
- Use MatCard + simple grid layout for stats display
- Show a loading spinner while fetching

### 5. Fix Pagination
- The component calls `getAuditLogs(0)` which is wrong — Angular Material paginator uses 0-based index but the API uses 1-based page numbers
- Wire up the paginator to trigger `getAuditLogs(page, pageSize, filters)` on page change

### 6. Update AuditModule
- Add MatDateModule, MatChipsModule, MatMenuModule to imports in audit.module.ts
- Ensure all new Material modules are properly imported

## Quality Checks

1. [ ] Date range picker renders and filters work correctly
2. [ ] Filter dropdowns show correct labels using service display methods
3. [ ] Export buttons trigger file downloads with correct content type
4. [ ] Summary stats card loads on init and refreshes when filters change
5. [ ] Pagination correctly maps 0-based paginator to 1-based API
6. [ ] All new Material modules imported in audit.module.ts
7. [ ] No TypeScript compilation errors
8. [ ] Documentation comments added to new methods

## Skills

Before starting, load and activate these skills:

```
use_skill(skill_name="tdd")
```

Follow the TDD skill's red-green-refactor loop for all new test files. Write unit tests for the new filter logic, export methods, and summary statistics service calls before implementing the component changes.

## Documentation Requirements

- Update the JSDoc comment block at the top of the component to reflect new features
- Add a comment block in `frontend/src/app/modules/audit/` explaining the module architecture
