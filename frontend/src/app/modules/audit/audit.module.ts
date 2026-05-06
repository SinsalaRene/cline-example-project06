/**
 * Audit Module
 *
 * Provides the complete audit log viewing and inspection functionality for the
 * Azure Firewall Management application. This module is responsible for:
 *
 * - **Audit List View**: Paginated, filterable table of audit entries with
 *   summary statistics, export (CSV/JSON), and date range filtering.
 * - **Audit Detail View**: Detailed single-entry inspection showing all fields,
 *   formatted JSON diffs (old vs. new values), and metadata.
 * - **Audit Viewer Component**: Resource-specific audit history with filtering,
 *   sorting, and pagination.
 *
 * # Module Architecture
 *
 * ```
 * audit/
 * ├── audit.module.ts          ← Module declarations & routing
 * ├── models/
 * │   └── audit.model.ts       ← TypeScript interfaces & enums
 * ├── services/
 * │   └── audit.service.ts     ← API communication & display helpers
 * └── components/
 *     ├── audit-list.component.ts       ← Main audit log list (standalone)
 *     ├── audit-detail.component.ts     ← Single entry detail view (standalone)
 *     └── audit-viewer.component.ts     ← Resource-specific audit history (standalone)
 * ```
 *
 * # Component Architecture Decisions
 *
 * All three audit components are implemented as **standalone components** using
 * Angular's modern standalone pattern. This means:
 *
 * 1. Each component independently declares its own imports (Material modules,
 *    CommonModule, RxJS operators, etc.)
 * 2. The module only provides routing and a shared declaration so Angular's
 *    router can lazily load the module at the route level.
 * 3. This approach eliminates the need for intermediate feature modules and
 *    reduces bundle size by allowing tree-shaking of unused components.
 *
 * # Routing
 *
 * Routes are defined inline within the module's `providers` array as a
 * `Routes` configuration. This is a deliberate choice to keep all audit-related
 * routing in a single file while maintaining the standalone component pattern.
 *
 * | Path                                         | Component            | Purpose                        |
 * |----------------------------------------------|---------------------|--------------------------------|
 * | `audit/list` (default)                       | AuditListComponent   | Full audit log with filtering  |
 * | `audit/detail/:id`                           | AuditDetailComponent | Single entry detail inspection |
 * | `audit/resource/:resourceType/:resourceId`  | AuditViewerComponent | Resource-specific history      |
 *
 * @module audit-module
 * @author Audit Module Team
 */

import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { AuditListComponent } from './components/audit-list.component';
import { AuditDetailComponent } from './components/audit-detail.component';
import { AuditViewerComponent } from './components/audit-viewer.component';

/**
 * Route configuration for the audit module.
 *
 * Uses lazy-loaded standalone components. Each route is configured with
 * a `title` for breadcrumbs and potential SEO purposes.
 */
const auditRoutes: Routes = [
    {
        path: '',
        pathMatch: 'full',
        redirectTo: 'list',
    },
    {
        path: 'list',
        title: 'Audit Log List',
        component: AuditListComponent,
    },
    {
        path: 'detail/:id',
        title: 'Audit Entry Detail',
        component: AuditDetailComponent,
    },
    {
        path: 'resource/:resourceType/:resourceId',
        title: 'Resource Audit History',
        component: AuditViewerComponent,
    },
    // Legacy support: allow direct access to /audit for list view
    {
        path: 'detail/:id',
        title: 'Audit Entry Detail',
        component: AuditDetailComponent,
    },
    {
        path: 'resource/:resourceType/:resourceId',
        title: 'Resource Audit History',
        component: AuditViewerComponent,
    },
];

@NgModule({
    imports: [
        CommonModule,
        ReactiveFormsModule,
        RouterModule.forChild(auditRoutes),
        MatButtonModule,
        MatIconModule,
        MatPaginatorModule,
        MatSortModule,
        MatTableModule,
        MatCardModule,
        MatChipsModule,
        MatProgressSpinnerModule,
        MatSnackBarModule,
        MatDatepickerModule,
        MatNativeDateModule,
        MatCheckboxModule,
        MatSelectModule,
        MatDividerModule,
        MatFormFieldModule,
        MatInputModule,
    ],
    declarations: [
        AuditListComponent,
        AuditDetailComponent,
        AuditViewerComponent,
    ],
    exports: [
        AuditListComponent,
        AuditDetailComponent,
        AuditViewerComponent,
    ],
})
export class AuditModule {
    // No constructor needed — routing and declarations are handled by decorators.
}