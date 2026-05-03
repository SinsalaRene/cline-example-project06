/**
 * Approvals Module
 *
 * This module provides the approval workflow UI for reviewing and acting on
 * firewall rule change requests. It supports:
 *
 * - List view with search, filtering, and pagination
 * - Bulk approve/reject operations
 * - Detailed approval view with change diff display
 * - Comment system for collaboration
 * - Priority and status badges
 *
 * # Usage
 *
 * Import `ApprovalsListComponent` directly (standalone components) or use the
 * module if you need routing configuration.
 *
 * @example
 * ```typescript
 * import { ApprovalsListComponent } from './approvals/components/approvals-list.component';
 *
 * @NgModule({
 *   imports: [ApprovalsListComponent]
 * })
 * ```
 */

import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ApprovalsListComponent } from './components/approvals-list.component';
import { ApprovalsService } from './services/approvals.service';

const routes: Routes = [
    { path: '', component: ApprovalsListComponent }
];

/**
 * Shared exports for re-use across the application.
 */
@NgModule({
    imports: [
        RouterModule.forChild(routes),
        ApprovalsListComponent
    ],
    providers: [
        ApprovalsService
    ]
})
export class ApprovalsModule { }

export {
    ApprovalsListComponent,
    ApprovalsService
};
