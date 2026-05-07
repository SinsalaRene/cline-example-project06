import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { Router, RouterModule } from '@angular/router';
import { WorkloadsService, PaginatedResponse } from '../services/workloads.service';
import { Workload } from '../models/workload.model';
import { ConfirmationDialogComponent } from '../components/confirmation-dialog.component';

/**
 * Display interface for the workload table.
 *
 * @interface WorkloadDisplay
 * @description A simplified view of a workload used exclusively for table display,
 * containing only the columns visible in the workload list.
 */
interface WorkloadDisplay {
    id: string;
    name: string;
    workload_type: string;
    environment: string;
    status: string;
    owner?: string;
    rule_count?: number;
    created_at: string;
}

/**
 * WorkloadsListComponent - Displays a paginated, sortable, and searchable table of workloads.
 *
 * @component
 * @description Renders a data table with the following features:
 * - Pagination via MatPaginator
 * - Column sorting via MatSort
 * - Text search for workload names
 * - Status filter dropdown
 * - Multi-select bulk operations (bulk delete)
 * - Individual row actions (edit, view, delete)
 *
 * @example
 * ```html
 * <!-- Used within WorkloadsModule, navigates to: -->
 * /workloads          → List
 * /workloads/new      → Create form
 * /workloads/:id      → Detail view
 * /workloads/:id/edit → Edit form
 * ```
 */
@Component({
    selector: 'app-workloads-list',
    standalone: false,
    templateUrl: './workloads-list.component.html',
    styleUrls: ['./workloads-list.component.css']
})
export class WorkloadsListComponent implements OnInit {
    /**
     * Table column definitions in display order.
     */
    displayedColumns: string[] = ['select', 'name', 'workload_type', 'environment', 'status', 'rule_count', 'owner', 'actions'];
    /**
     * Data source bound to the Material table.
     */
    dataSource = new MatTableDataSource<WorkloadDisplay>();
    /**
     * Indicates whether workload data is currently being loaded.
     */
    isLoading = false;
    /**
     * Total number of workloads available on the server.
     */
    totalCount = 0;
    /**
     * Current page number (1-based).
     */
    currentPage = 1;
    /**
     * Number of items per page.
     */
    pageSize = 50;
    /**
     * Total number of pages calculated from total count.
     */
    totalPages = 0;

    /**
     * Search filter text for filtering workload names.
     */
    searchFilter = '';
    /**
     * Status filter for filtering by workload status.
     */
    statusFilter = '';

    /**
     * Set of selected workload IDs for bulk operations.
     */
    selection = new Set<string>();

    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    /**
     * Creates an instance of WorkloadsListComponent.
     * @param workloadsService - Service for workload CRUD operations.
     * @param dialog - Angular Material dialog service for confirmation dialogs.
     * @param snackBar - Angular Material snackbar for toast notifications.
     * @param router - Angular Router for navigation between workload views.
     */
    constructor(
        private workloadsService: WorkloadsService,
        private dialog: MatDialog,
        private snackBar: MatSnackBar,
        private router: Router
    ) { }

    /**
     * Initializes the component and loads the first page of workloads.
     */
    ngOnInit(): void {
        this.loadWorkloads();
    }

    /**
     * Initializes paginator and sort bindings after view initialization.
     */
    ngAfterViewInit(): void {
        this.dataSource.paginator = this.paginator;
        this.dataSource.sort = this.sort;
    }

    /**
     * Loads workloads from the service with current filter parameters.
     *
     * @param page - Page number to load.
     */
    loadWorkloads(page = 1): void {
        this.isLoading = true;
        this.workloadsService.getWorkloads(page, this.pageSize, this.statusFilter || undefined, this.searchFilter || undefined)
            .subscribe({
                next: (response: PaginatedResponse<Workload>) => {
                    this.dataSource.data = response.items.map(w => ({
                        id: w.id,
                        name: w.name,
                        workload_type: w.workload_type,
                        environment: w.environment,
                        status: w.status,
                        owner: w.owner,
                        rule_count: w.rule_count,
                        created_at: w.created_at
                    }));
                    this.totalCount = response.total;
                    this.currentPage = response.page;
                    this.pageSize = response.pageSize;
                    this.totalPages = response.totalPages;
                    this.isLoading = false;
                },
                error: (error) => {
                    this.isLoading = false;
                    this.snackBar.open('Error loading workloads: ' + error.message, 'Close', { duration: 3000 });
                }
            });
    }

    /**
     * Applies the current search and status filters, resetting to page 1.
     */
    applyFilter(): void {
        this.loadWorkloads(1);
    }

    /**
     * Checks if the current user has a specific permission.
     *
     * @param permission - The permission string to check.
     * @returns Always returns true (placeholder for future RBAC integration).
     */
    hasPermission(_permission: string): boolean {
        return true;
    }

    /**
     * Selects or deselects all workloads in the current view.
     *
     * @param all - If true, selects all; if false, deselects all; if null, toggles.
     */
    selectAll(all: boolean | null): void {
        if (this.dataSource.data.length) {
            this.selection.clear();
            this.dataSource.data.forEach((row: { id: string; }) => {
                if (all !== null) {
                    this.selection.add(row.id);
                }
            });
        }
    }

    /**
     * Checks if a workload is currently selected.
     *
     * @param id - The workload ID to check.
     * @returns True if the workload is selected.
     */
    isSelected(id: string): boolean {
        return this.selection.has(id);
    }

    /**
     * Toggles the selection state of a single workload.
     *
     * @param id - The workload ID to toggle.
     */
    toggleSelection(id: string): void {
        if (this.selection.has(id)) {
            this.selection.delete(id);
        } else {
            this.selection.add(id);
        }
    }

    /**
     * Navigates to the create workload form.
     */
    createWorkload(): void {
        this.router.navigate(['/workloads', 'new']);
    }

    /**
     * Navigates to the edit form for the given workload.
     *
     * @param id - The workload ID to edit.
     */
    editWorkload(id: string): void {
        this.router.navigate(['/workloads', id, 'edit']);
    }

    /**
     * Navigates to the detail view for the given workload.
     *
     * @param id - The workload ID to view.
     */
    viewWorkload(id: string): void {
        this.router.navigate(['/workloads', id]);
    }

    /**
     * Opens a confirmation dialog for bulk deleting selected workloads.
     */
    deleteSelected(): void {
        if (this.selection.size === 0) {
            return;
        }

        const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
            data: {
                title: 'Delete Workloads',
                message: `Are you sure you want to delete ${this.selection.size} workload(s)?`,
                confirmLabel: 'Delete',
                cancelLabel: 'Cancel'
            }
        });

        dialogRef.afterClosed().subscribe((result: boolean) => {
            if (result) {
                this.bulkDelete();
            }
        });
    }

    /**
     * Performs bulk deletion of all selected workloads via the service.
     */
    bulkDelete(): void {
        const ids = Array.from(this.selection);
        this.workloadsService.bulkDelete(ids).subscribe({
            next: (result: { success: number }) => {
                this.snackBar.open(`Deleted ${result.success} workload(s)`, 'Close', { duration: 3000 });
                this.selection.clear();
                this.loadWorkloads(this.currentPage);
            },
            error: (error: Error) => {
                this.snackBar.open('Error deleting workloads: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    /**
     * Opens a confirmation dialog for deleting a single workload.
     *
     * @param id - The workload ID to delete.
     * @param name - The workload name displayed in the confirmation message.
     */
    deleteSingle(id: string, name: string): void {
        const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
            data: {
                title: 'Delete Workload',
                message: `Are you sure you want to delete "${name}"?`,
                confirmLabel: 'Delete',
                cancelLabel: 'Cancel'
            }
        });

        dialogRef.afterClosed().subscribe((result: boolean) => {
            if (result) {
                this.workloadsService.deleteWorkload(id).subscribe({
                    next: () => {
                        this.snackBar.open(`Workload "${name}" deleted`, 'Close', { duration: 3000 });
                        this.loadWorkloads(this.currentPage);
                    },
                    error: (error: Error) => {
                        this.snackBar.open('Error deleting workload: ' + error.message, 'Close', { duration: 3000 });
                    }
                });
            }
        });
    }

    /**
     * Handles paginator page changes, reloading workloads for the new page.
     *
     * @param pageEvent - The page event from MatPaginator.
     */
    onPageChange(pageEvent: any): void {
        this.loadWorkloads(pageEvent.pageIndex + 1);
    }
}