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
import { CommonModule } from '@angular/common';
import { ApprovalsListComponent } from './components/approvals-list.component';
import { ApprovalDetailComponent } from './components/approval-detail.component';
import { BulkActionDialogComponent } from './components/bulk-action-dialog.component';
import { ApprovalCommentsComponent } from './components/approval-comments.component';
import { ApprovalsService } from './services/approvals.service';

/**
 * Shared exports for re-use across the application.
 */
@NgModule({
    imports: [
        CommonModule,
        ApprovalsListComponent,
        ApprovalDetailComponent,
        BulkActionDialogComponent,
        ApprovalCommentsComponent
    ],
    providers: [
        ApprovalsService
    ]
})
export class ApprovalsModule { }

export {
    ApprovalsListComponent,
    ApprovalDetailComponent,
    BulkActionDialogComponent,
    ApprovalCommentsComponent,
    ApprovalsService
};

export * from './models/approval.model';