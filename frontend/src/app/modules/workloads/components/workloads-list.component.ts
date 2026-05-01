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
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { Router, RouterModule } from '@angular/router';
import { WorkloadsService, PaginatedResponse } from '../services/workloads.service';
import { Workload } from '../models/workload.model';
import { ConfirmationDialogComponent } from '../components/confirmation-dialog.component';

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

@Component({
    selector: 'app-workloads-list',
    standalone: false,
    templateUrl: './workloads-list.component.html',
    styleUrls: ['./workloads-list.component.css']
})
export class WorkloadsListComponent implements OnInit {
    displayedColumns: string[] = ['select', 'name', 'workload_type', 'environment', 'status', 'rule_count', 'owner', 'actions'];
    dataSource = new MatTableDataSource<WorkloadDisplay>();
    isLoading = false;
    totalCount = 0;
    currentPage = 1;
    pageSize = 50;
    totalPages = 0;

    // Filters
    searchFilter = '';
    statusFilter = '';

    selection = new Set<string>();

    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    constructor(
        private workloadsService: WorkloadsService,
        private dialog: MatDialog,
        private snackBar: MatSnackBar,
        private router: Router
    ) { }

    ngOnInit(): void {
        this.loadWorkloads();
    }

    ngAfterViewInit(): void {
        this.dataSource.paginator = this.paginator;
        this.dataSource.sort = this.sort;
    }

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

    applyFilter(): void {
        this.loadWorkloads(1);
    }

    selectAll(): void {
        if (this.dataSource.data.length) {
            this.selection.clear();
            this.dataSource.data.forEach(row => this.selection.add(row.id));
        }
    }

    isSelected(id: string): boolean {
        return this.selection.has(id);
    }

    toggleSelection(id: string): void {
        if (this.selection.has(id)) {
            this.selection.delete(id);
        } else {
            this.selection.add(id);
        }
    }

    createWorkload(): void {
        this.router.navigate(['/workloads', 'create']);
    }

    editWorkload(id: string): void {
        this.router.navigate(['/workloads', id, 'edit']);
    }

    viewWorkload(id: string): void {
        this.router.navigate(['/workloads', id]);
    }

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

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                this.bulkDelete();
            }
        });
    }

    bulkDelete(): void {
        const ids = Array.from(this.selection);
        this.workloadsService.bulkDelete(ids).subscribe({
            next: (result) => {
                this.snackBar.open(`Deleted ${result.success} workload(s)`, 'Close', { duration: 3000 });
                this.selection.clear();
                this.loadWorkloads(this.currentPage);
            },
            error: (error) => {
                this.snackBar.open('Error deleting workloads: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    deleteSingle(id: string, name: string): void {
        const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
            data: {
                title: 'Delete Workload',
                message: `Are you sure you want to delete "${name}"?`,
                confirmLabel: 'Delete',
                cancelLabel: 'Cancel'
            }
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                this.workloadsService.deleteWorkload(id).subscribe({
                    next: () => {
                        this.snackBar.open(`Workload "${name}" deleted`, 'Close', { duration: 3000 });
                        this.loadWorkloads(this.currentPage);
                    },
                    error: (error) => {
                        this.snackBar.open('Error deleting workload: ' + error.message, 'Close', { duration: 3000 });
                    }
                });
            }
        });
    }

    onPageChange(pageEvent: any): void {
        this.loadWorkloads(pageEvent.pageIndex + 1);
    }
}