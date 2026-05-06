/**
 * # Audit Module
 *
 * The audit module provides a comprehensive audit log viewing and management
 * system for the Azure Firewall Management application. It tracks all
 * significant system events including rule changes, user authentication
 * events, configuration modifications, and administrative actions.
 *
 * ## Architecture
 *
 * ```
 * ┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
 * │  AuditListComponent │────▶│   AuditService    │────▶│   Backend API   │
 * │  (UI / Filtering)   │     │  (State / Format) │     │  (REST Endpts)  │
 * └─────────────────────┘     └──────────────────┘     └─────────────────┘
 *        │                           │
 *        │                           │────▶ getAuditLogs()     — paginated entries
 *        │                           │────▶ getAuditSummary()   — stats overview
 *        │                           │────▶ exportAsCsv()       — CSV export
 *        │                           │────▶ exportAsJson()      — JSON export
 *        │                           │────▶ filterAuditEntries() — client-side filter
 *        │                           │────▶ getSeverityDisplay() — severity formatting
 *        │                           │────▶ getActionDisplay()   — action formatting
 *        │                           │────▶ getResourceTypeDisplay() — resource labels
 *        │                           │────▶ formatTimestamp()    — date formatting
 *        │                           │────▶ getRelativeTime()    — relative time strings
 * ```
 *
 * ## Module Structure
 *
 * ```
 * audit/
 * ├── components/
 * │   └── audit-list.component.ts   — Main list view with filtering, export, summary
 * ├── models/
 * │   └── audit.model.ts            — TypeScript interfaces and type aliases
 * ├── services/
 * │   └── audit.service.ts          — API communication and formatting helpers
 * ├── audit.module.ts               — Module declaration
 * ├── README.md                     — This file
 * └── audit.spec.ts                 — Unit tests
 * ```
 *
 * ## Features
 *
 * ### Audit List Component
 *
 * - **Date Range Filtering**: Material date pickers for "From" and "To" dates.
 *   Defaults to the last 30 days. Filters are applied on change with a 300ms
 *   debounce.
 *
 * - **Multi-Select Filter Dropdowns**: Filter by action type, resource type, and
 *   severity level. Each dropdown uses `MatSelect` with checkboxes. Selected
 *   filters are shown as removable chips below the dropdowns.
 *
 * - **Export Buttons**: "Export CSV" and "Export JSON" buttons trigger file
 *   downloads using the service's `exportAsCsv()` and `exportAsJson()` methods.
 *   Both accept the current active filters.
 *
 * - **Summary Statistics Card**: Displays total entry count, top 5 actions,
 *   and top 5 resource types as horizontal bar charts. Refetched on every
 *   filter change (debounced).
 *
 * - **Pagination**: Angular Material paginator is wired to the data source.
 *   The 0-based `pageIndex` is automatically mapped to the API's 1-based page
 *   number by adding 1.
 *
 * - **Sorting**: Column headers are sortable via `mat-sort-header`.
 *
 * ### Service Layer
 *
 * The `AuditService` encapsulates all API communication and formatting logic:
 *
 * | Method                    | Purpose                                          |
 * |---------------------------|--------------------------------------------------|
 * | `getAuditLogs()`          | Fetch paginated audit entries from the API       |
 * | `getAuditEntry()`         | Fetch a single audit entry by ID                 |
 * | `searchAuditLogs()`       | Server-side full-text search                     |
 * | `exportAsCsv()`           | Download filtered entries as CSV Blob            |
 * | `exportAsJson()`          | Download filtered entries as JSON Blob           |
 * | `getAuditSummary()`       | Get aggregated statistics                        |
 * | `filterAuditEntries()`    | Client-side filtering of entries array           |
 * | `getSeverityDisplay()`    | Get label, icon, color, and CSS class for severity |
 * | `getActionDisplay()`      | Get human-readable action label                  |
 * | `getResourceTypeDisplay()`| Get human-readable resource type label           |
 * | `formatTimestamp()`       | Format ISO timestamp for display                 |
 * | `getRelativeTime()`       | Get relative time string (e.g., "5m ago")       |
 * | `getUniqueUsers()`        | Extract unique user emails from entries          |
 * | `getUniqueActions()`      | Extract unique actions from entries              |
 * | `getActionIcon()`         | Get Material icon name for an action             |
 * | `getResourceTypeIcon()`   | Get Material icon name for a resource type       |
 * | `isRecent()`              | Check if entry was created within last 2 hours   |
 *
 * ### Data Models
 *
 * | Model              | Description                                       |
 * |--------------------|---------------------------------------------------|
 * | `AuditEntry`       | Single audit log entry with all metadata          |
 * | `AuditFilter`      | Filter criteria object (date, search, types)      |
 * | `AuditListResponse`| Paginated API response with items and pagination  |
 * | `AuditSummary`     | Aggregated statistics by action, type, severity   |
 * | `AuditAction`      | Type alias for action strings (CREATE, UPDATE...) |
 * | `AuditResourceType`| Type alias for resource strings                  |
 * | `AuditSeverity`    | Type alias for severity strings                  |
 *
 * ## Backend API Endpoints
 *
 * | Endpoint                       | Method | Description                     |
 * |--------------------------------|--------|---------------------------------|
 * | `/api/v1/audit`                | GET    | List paginated audit entries    |
 * | `/api/v1/audit/{entry_id}`     | GET    | Get single audit entry          |
 * | `/api/v1/audit/search`         | GET    | Full-text search                |
 * | `/api/v1/audit/export/csv`     | GET    | Export as CSV                   |
 * | `/api/v1/audit/export/json`    | GET    | Export as JSON                  |
 * | `/api/v1/audit/stats`          | GET    | Get summary statistics          |
 *
 * ## Material Dependencies
 *
 * This component requires the following Angular Material modules:
 *
 * - `MatDatepickerModule`, `MatNativeDateModule` — Date pickers
 * - `MatSelectModule`, `MatCheckboxModule` — Multi-select filter dropdowns
 * - `MatChipsModule` — Filter chips and severity badges
 * - `MatTableModule`, `MatPaginatorModule`, `MatSortModule` — Data table
 * - `MatCardModule`, `MatDividerModule` — Layout
 * - `MatProgressSpinnerModule` — Loading indicator
 * - `MatSnackBarModule` — Notification toasts
 * - `MatIconModule` — Icon displays
 * - `MatFormFieldModule`, `MatInputModule` — Form fields
 * - `MatButtonModule` — Action buttons
 *
 * All of these are imported directly in the standalone component, so no
 * additional module configuration is needed beyond ensuring the Material
 * packages are installed.
 *
 * @module audit
 * @documentationVersion 2.0
 */