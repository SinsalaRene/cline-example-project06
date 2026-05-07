/**
 * WorkloadsModule - Manages the workload entities in the Azure Firewall Management system.
 *
 * This module provides full CRUD functionality for workloads including:
 * - Listing workloads with pagination, sorting, and search
 * - Viewing workload details with associated firewall rules
 * - Creating and editing workloads via reactive forms
 * - Deleting workloads with confirmation dialogs
 *
 * @module workloads
 */
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule } from '@angular/material/dialog';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { RouterModule } from '@angular/router';
import { WorkloadsListComponent } from './components/workloads-list.component';
import { WorkloadDetailComponent } from './components/workload-detail.component';
import { WorkloadFormComponent } from './components/workload-form.component';
import { ConfirmationDialogComponent } from './components/confirmation-dialog.component';
import { workloadsRoutes } from './workloads.routing';

/**
 * WorkloadsModule - Provides full CRUD functionality for workload management.
 *
 * Declares all workload-related components and configures routes for:
 * - Listing workloads (`workloads`)
 * - Viewing workload details (`workloads/:id`)
 * - Creating new workloads (`workloads/new`)
 * - Editing existing workloads (`workloads/:id/edit`)
 */
@NgModule({
    /**
     * Components declared by this module, making them available to any module that imports this one.
     */
    declarations: [
        WorkloadsListComponent,
        WorkloadDetailComponent,
        WorkloadFormComponent,
        ConfirmationDialogComponent
    ],
    imports: [
        CommonModule,
        ReactiveFormsModule,
        FormsModule,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatInputModule,
        MatFormFieldModule,
        MatButtonModule,
        MatIconModule,
        MatCardModule,
        MatDialogModule,
        MatCheckboxModule,
        MatSnackBarModule,
        MatProgressSpinnerModule,
        MatSelectModule,
        MatTabsModule,
        MatExpansionModule,
        MatChipsModule,
        MatMenuModule,
        RouterModule.forChild(workloadsRoutes)
    ]
})
export class WorkloadsModule { }