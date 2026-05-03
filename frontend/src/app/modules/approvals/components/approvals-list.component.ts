import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule as MatProgressSpinnerModule2 } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';
import { ApprovalsService } from '../services/approvals.service';
import { ApprovalRequest, ApprovalFilter } from '../models/approval.model';
import { ApprovalDetailComponent } from './approval-detail.component';
import { BulkActionDialogComponent } from './bulk-action-dialog.component';
import { ConfirmationDialogComponent } from '../../rules/components/confirmation-dialog.component';

@Component({
    selector: 'app-approvals-list',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatDialogModule,
        MatSnackBarModule,
        MatProgressSpinnerModule,
        MatChipsModule,
        MatIconModule,
        MatButtonModule,
        MatInputModule,
        MatFormFieldModule,
        MatSelectModule,
        MatCheckboxModule,
        MatCardModule
    ],
    template: `
        <div class="approvals-container">
            <!-- Header -->
            <div class="header-section">
                <h2>Approval Requests</h2>
                <p>Review and approve firewall rule changes</p>
            </div>

            <!-- Stats cards -->
            <div class="stats-grid" *ngIf="stats">
                <div class="stat-card stat-pending">
                    <div class="stat-icon"><mat-icon>schedule</mat-icon></div>
                    <div class="stat-info">
                        <div class="stat-number">{{ stats.pending }}</div>
                        <div class="stat-label">Pending</div>
                    </div>
                </div>
                <div class="stat-card stat-approved">
                    <div class="stat-icon"><mat-icon>check_circle</mat-icon></div>
                    <div class="stat-info">
                        <div class="stat-number">{{ stats.approved }}</div>
                        <div class="stat-label">Approved</div>
                    </div>
                </div>
                <div class="stat-card stat-rejected">
                    <div class="stat-icon"><mat-icon>cancel</mat-icon></div>
                    <div class="stat-info">
                        <div class="stat-number">{{ stats.rejected }}</div>
                        <div class="stat-label">Rejected</div>
                    </div>
                </div>
                <div class="stat-card stat-total">
                    <div class="stat-icon"><mat-icon>receipt_long</mat-icon></div>
                    <div class="stat-info">
                        <div class="stat-number">{{ stats.total }}</div>
                        <div class="stat-label">Total</div>
                    </div>
                </div>
            </div>

            <!-- Toolbar -->
            <div class="toolbar">
                <button mat-raised-button color="primary" (click)="bulkApproveSelected()" [disabled]="!hasSelectedItems()">
                    <mat-icon>check_circle</mat-icon> Approve Selected
                </button>
                <button mat-raised-button color="warn" (click)="bulkRejectSelected()" [disabled]="!hasSelectedItems()">
                    <mat-icon>cancel</mat-icon> Reject Selected
                </button>
                <div class="spacer"></div>
                <button mat-button (click)="toggleFilters()">
                    <mat-icon>filter_list</mat-icon> {{ showFilters ? 'Hide' : 'Show' }} Filters
                </button>
                <button mat-button (click)="refreshData()">
                    <mat-icon>refresh</mat-icon> Refresh
                </button>
            </div>

            <!-- Filter panel -->
            <div class="filter-panel" *ngIf="showFilters">
                <div class="filter-row">
                    <mat-form-field appearance="outline">
                        <mat-label>Status</mat-label>
                        <mat-select (selectionChange)="applyFilters()" [(value)]="currentFilters.statusFilter">
                            <mat-option value="">All Statuses</mat-option>
                            <mat-option value="pending">Pending</mat-option>
                            <mat-option value="approved">Approved</mat-option>
                            <mat-option value="rejected">Rejected</mat-option>
                            <mat-option value="expired">Expired</mat-option>
                            <mat-option value="timeout">Timed Out</mat-option>
                        </mat-select>
                    </mat-form-field>
                    <mat-form-field appearance="outline">
                        <mat-label>Type</mat-label>
                        <mat-select (selectionChange)="applyFilters()" [(value)]="currentFilters.typeFilter">
                            <mat-option value="">All Types</mat-option>
                            <mat-option value="create">Create</mat-option>
                            <mat-option value="update">Update</mat-option>
                            <mat-option value="delete">Delete</mat-option>
                            <mat-option value="enable">Enable</mat-option>
                            <mat-option value="disable">Disable</mat-option>
                        </mat-select>
                    </mat-form-field>
                    <mat-form-field appearance="outline">
                        <mat-label>Priority</mat-label>
                        <mat-select (selectionChange)="applyFilters()" [(value)]="currentFilters.priorityFilter">
                            <mat-option value="">All Priorities</mat-option>
                            <mat-option value="low">Low</mat-option>
                            <mat-option value="medium">Medium</mat-option>
                            <mat-option value="high">High</mat-option>
                            <mat-option value="urgent">Urgent</mat-option>
                        </mat-select>
                    </mat-form-field>
                    <button mat-raised-button color="primary" (click)="resetFilters()">
                        Reset Filters
                    </button>
                </div>
            </div>

            <!-- Search -->
            <div class="search-bar">
                <mat-form-field appearance="outline" class="search-field">
                    <mat-label>Search approvals</mat-label>
                    <input matInput (keyup)="onSearchChange($event)" placeholder="Search by rule name, requestor, description..." #searchInput>
                    <button mat-icon-button matSuffix *ngIf="searchInput.value" (click)="searchInput.value=''; onSearchChange($event)">
                        <mat-icon>clear</mat-icon>
                    </button>
                </mat-form-field>
            </div>

            <!-- Selection indicator -->
            <div class="selection-info" *ngIf="selectedRows.size > 0">
                <span>{{ selectedRows.size }} request(s) selected</span>
                <button mat-button (click)="clearSelection()">Clear selection</button>
            </div>

            <!-- Loading -->
            <div class="loading-indicator" *ngIf="isLoading">
                <mat-progress-spinner mode="indeterminate" [diameter]="40"></mat-progress-spinner>
                <span>Loading approvals...</span>
            </div>

            <!-- Table -->
            <div class="table-wrapper" *ngIf="!isLoading">
                <table mat-table [dataSource]="dataSource" matSort class="approvals-table">

                    <!-- Selection -->
                    <ng-container matColumnDef="select">
                        <th mat-header-cell *matHeaderCellDef>
                            <mat-checkbox
                                color="primary"
                                [checked]="isAllSelected()"
                                [indeterminate]="!isAllSelected() && hasSelectedItems()"
                                (change)="$event ? toggleAllRows() : null"
                            ></mat-checkbox>
                        </th>
                        <td mat-cell *matCellDef="let row">
                            <mat-checkbox
                                color="primary"
                                [checked]="selectedRows.has(row)"
                                (change)="$event ? toggleRowSelection(row) : null"
                            ></mat-checkbox>
                        </td>
                    </ng-container>

                    <!-- Rule name -->
                    <ng-container matColumnDef="rule_name">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header>Rule</th>
                        <td mat-cell *matCellDef="let item">
                            <a class="rule-link" (click)="viewDetail(item)">{{ item.rule_name }}</a>
                        </td>
                    </ng-container>

                    <!-- Type -->
                    <ng-container matColumnDef="request_type">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header>Type</th>
                        <td mat-cell *matCellDef="let item">
                            <mat-chip color="primary">{{ item.request_type }}</mat-chip>
                        </td>
                    </ng-container>

                    <!-- Status -->
                    <ng-container matColumnDef="status">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header>Status</th>
                        <td mat-cell *matCellDef="let item">
                            <span class="status-badge status-{{ item.status }}">
                                <mat-icon class="status-icon" *ngIf="item.status === 'approved'">check_circle</mat-icon>
                                <mat-icon class="status-icon" *ngIf="item.status === 'rejected'">cancel</mat-icon>
                                <mat-icon class="status-icon" *ngIf="item.status === 'pending'">schedule</mat-icon>
                                {{ item.status | titlecase }}
                            </span>
                        </td>
                    </ng-container>

                    <!-- Priority -->
                    <ng-container matColumnDef="priority">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header>Priority</th>
                        <td mat-cell *matCellDef="let item">
                            <span class="priority-badge priority-{{ item.priority }}">
                                {{ item.priority | titlecase }}
                            </span>
                        </td>
                    </ng-container>

                    <!-- Requestor -->
                    <ng-container matColumnDef="requestor">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header>Requestor</th>
                        <td mat-cell *matCellDef="let item">{{ item.requestor }}</td>
                    </ng-container>

                    <!-- Requested -->
                    <ng-container matColumnDef="requested_at">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header>Requested</th>
                        <td mat-cell *matCellDef="let item">
                            <span class="time-display">{{ item.requested_at | date:'medium' }}</span>
                        </td>
                    </ng-container>

                    <!-- Actions -->
                    <ng-container matColumnDef="actions">
                        <th mat-header-cell *matHeaderCellDef>Actions</th>
                        <td mat-cell *matCellDef="let item">
                            <button mat-icon-button color="primary" (click)="viewDetail(item)" matTooltip="View details">
                                <mat-icon>visibility</mat-icon>
                            </button>
                            <button *ngIf="item.status === 'pending'" mat-icon-button color="primary" (click)="approveItem(item)" matTooltip="Approve">
                                <mat-icon>check_circle</mat-icon>
                            </button>
                            <button *ngIf="item.status === 'pending'" mat-icon-button color="warn" (click)="rejectItem(item)" matTooltip="Reject">
                                <mat-icon>cancel</mat-icon>
                            </button>
                        </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                    <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="data-row"
                        [class.selected-row]="selectedRows.has(row)"></tr>
                </table>

                <!-- Empty state -->
                <div class="empty-state" *ngIf="dataSource.data.length === 0 && !isLoading">
                    <mat-icon class="empty-icon">gavel</mat-icon>
                    <h3>No approval requests found</h3>
                    <p>There are no approval requests matching your criteria.</p>
                </div>

                <mat-paginator
                    [pageSizeOptions]="[5, 10, 25, 50]"
                    showFirstLastButtons
                    aria-label="Select page"
                ></mat-paginator>
            </div>
        </div>
    `,
    styles: [`
        .approvals-container { padding: 20px; max-width: 100%; }
        .header-section { margin-bottom: 24px; }
        .header-section h2 { margin: 0 0 4px 0; font-weight: 500; }
        .header-section p { color: #666; margin: 0; }

        /* Stats cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px;
            border-radius: 8px;
            background: #fff;
            border: 1px solid #e0e0e0;
        }
        .stat-pending { border-left: 4px solid #ff9800; }
        .stat-approved { border-left: 4px solid #4caf50; }
        .stat-rejected { border-left: 4px solid #f44336; }
        .stat-total { border-left: 4px solid #2196f3; }
        .stat-icon { font-size: 24px; width: 24px; height: 24px; }
        .stat-info { flex: 1; }
        .stat-number { font-size: 24px; font-weight: 600; }
        .stat-label { font-size: 12px; color: #999; }

        /* Toolbar */
        .toolbar {
            display: flex; gap: 8px; margin-bottom: 16px;
            flex-wrap: wrap; align-items: center; padding: 12px;
            background: #f5f5f5; border-radius: 8px;
        }
        .spacer { flex: 1; }

        /* Filters */
        .filter-panel {
            background: #fafafa; padding: 16px; border-radius: 8px;
            margin-bottom: 16px; border: 1px solid #e0e0e0;
        }
        .filter-row { display: flex; gap: 16px; flex-wrap: wrap; align-items: center; }
        .filter-row mat-form-field { flex: 1; min-width: 150px; }

        /* Search */
        .search-bar { margin-bottom: 16px; }
        .search-field { width: 100%; max-width: 500px; }

        /* Selection */
        .selection-info {
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 16px; background: #e3f2fd; border-radius: 4px;
            margin-bottom: 16px;
        }

        /* Loading */
        .loading-indicator {
            display: flex; flex-direction: column; align-items: center;
            gap: 16px; padding: 40px;
        }

        /* Table */
        .table-wrapper { position: relative; border-radius: 8px; border: 1px solid #e0e0e0; overflow: hidden; }
        .approvals-table { width: 100%; }
        .data-row.selected-row { background: #e3f2fd; }
        .data-row:hover { background: #f5f5f5; }
        .rule-link { color: #1976d2; cursor: pointer; font-weight: 500; text-decoration: none; }
        .rule-link:hover { text-decoration: underline; color: #1565c0; }

        /* Status badges */
        .status-badge { display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px; border-radius: 4px; font-size: 0.875rem; font-weight: 500; }
        .status-pending { background: #fff3e0; color: #ef6c00; }
        .status-approved { background: #e8f5e9; color: #2e7d32; }
        .status-rejected { background: #ffebee; color: #c62828; }
        .status-expired { background: #f5f5f5; color: #616161; }
        .status-timeout { background: #f5f5f5; color: #616161; }
        .status-icon { font-size: 16px; width: 16px; height: 16px; }

        /* Priority badges */
        .priority-badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
        .priority-low { background: #e3f2fd; color: #1565c0; }
        .priority-medium { background: #fff3e0; color: #ef6c00; }
        .priority-high { background: #ffebee; color: #c62828; }
        .priority-urgent { background: #d50000; color: #fff; }

        /* Time display */
        .time-display { font-size: 0.875rem; color: #666; }

        /* Empty state */
        .empty-state {
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; padding: 60px 20px; text-align: center;
        }
        .empty-icon { font-size: 64px; color: #bdbdbd; margin-bottom: 16px; }
        .empty-state h3 { margin: 0 0 8px 0; color: #616161; }
        .empty-state p { margin: 0 0 16px 0; color: #9e9e9e; }

        @media (max-width: 768px) {
            .toolbar { flex-direction: column; align-items: stretch; }
            .toolbar .spacer { display: none; }
            .filter-row { flex-direction: column; }
        }
    `]
})
export class ApprovalsListComponent implements OnInit {
    displayedColumns: string[] = ['select', 'rule_name', 'request_type', 'status', 'priority', 'requestor', 'requested_at', 'actions'];
    dataSource = new MatTableDataSource<ApprovalRequest>();
    selectedRows = new Set<ApprovalRequest>();

    showFilters = false;
    isLoading = false;
    currentFilters: ApprovalFilter = {
        searchQuery: '',
        statusFilter: '',
        typeFilter: '',
        priorityFilter: ''
    };

    stats = { pending: 0, approved: 0, rejected: 0, total: 0 };

    @ViewChild('searchInput') searchInput!: { value: string };
    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    private allItems: ApprovalRequest[] = [];

    constructor(
        private approvalsService: ApprovalsService,
        private dialog: MatDialog,
        private snackBar: MatSnackBar,
        private router: Router
    ) { }

    ngOnInit(): void {
        this.loadApprovals();
    }

    loadApprovals(): void {
        this.isLoading = true;
        this.approvalsService.getApprovals(1, 20, this.currentFilters).subscribe({
            next: (response) => {
                this.allItems = response.items || [];
                this.dataSource = new MatTableDataSource<ApprovalRequest>(this.allItems);
                this.dataSource.paginator = this.paginator;
                this.applyFilters();
                this.updateStats();
                this.isLoading = false;
            },
            error: (err) => {
                console.error('Error loading approvals:', err);
                this.isLoading = false;
                this.snackBar.open('Error loading approvals. Please try again.', 'Close', { duration: 5000 });
            }
        });
    }

    refreshData(): void {
        this.loadApprovals();
    }

    onSearchChange(event: Event): void {
        this.currentFilters.searchQuery = (event.target as HTMLInputElement).value;
        this.applyFilters();
    }

    applyFilters(): void {
        const searchLower = this.currentFilters.searchQuery.toLowerCase();
        const statusLower = this.currentFilters.statusFilter.toLowerCase();
        const typeLower = this.currentFilters.typeFilter.toLowerCase();
        const priorityLower = this.currentFilters.priorityFilter.toLowerCase();

        this.dataSource.filteredData = this.allItems.filter(item => {
            if (searchLower && !this.matchesSearch(item, searchLower)) return false;
            if (statusLower && item.status.toLowerCase() !== statusLower) return false;
            if (typeLower && item.request_type.toLowerCase() !== typeLower) return false;
            if (priorityLower && item.priority.toLowerCase() !== priorityLower) return false;
            return true;
        });

        if (this.paginator) {
            this.dataSource.paginator = this.paginator;
        }
    }

    private matchesSearch(item: ApprovalRequest, searchLower: string): boolean {
        return (
            (item.rule_name || '').toLowerCase().includes(searchLower) ||
            (item.requestor || '').toLowerCase().includes(searchLower) ||
            (item.description || '').toLowerCase().includes(searchLower) ||
            (item.rejection_reason || '').toLowerCase().includes(searchLower)
        );
    }

    resetFilters(): void {
        this.currentFilters = { searchQuery: '', statusFilter: '', typeFilter: '', priorityFilter: '' };
        this.dataSource.filter = '';
        this.dataSource.filteredData = this.allItems;
    }

    toggleFilters(): void {
        this.showFilters = !this.showFilters;
    }

    updateStats(): void {
        this.stats = {
            pending: this.allItems.filter(i => i.status === 'pending').length,
            approved: this.allItems.filter(i => i.status === 'approved').length,
            rejected: this.allItems.filter(i => i.status === 'rejected').length,
            total: this.allItems.length
        };
    }

    // Selection
    isAllSelected(): boolean {
        const len = this.dataSource.filteredData?.length ?? 0;
        return len > 0 && this.selectedRows.size === len;
    }
    hasSelectedItems(): boolean { return this.selectedRows.size > 0; }
    toggleAllRows(): void {
        const data = this.dataSource.filteredData ?? this.dataSource.data;
        if (this.selectedRows.size === data.length) {
            this.selectedRows.clear();
        } else {
            data.forEach((item: ApprovalRequest) => this.selectedRows.add(item));
        }
    }
    toggleRowSelection(item: ApprovalRequest): void {
        this.selectedRows.has(item) ? this.selectedRows.delete(item) : this.selectedRows.add(item);
    }
    clearSelection(): void { this.selectedRows.clear(); }

    // Detail view
    viewDetail(item: ApprovalRequest): void {
        const dialogRef = this.dialog.open(ApprovalDetailComponent, {
            width: '800px',
            data: { approval: item }
        });
    }

    // Quick approve/reject
    approveItem(item: ApprovalRequest): void {
        const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
            data: {
                title: 'Approve Approval Request',
                message: `Are you sure you want to approve "${item.rule_name}"?`,
                confirmLabel: 'Approve',
                type: 'primary'
            }
        });
        dialogRef.afterClosed().subscribe(confirmed => {
            if (confirmed) {
                this.approvalsService.approve(item.id).subscribe({
                    next: () => {
                        this.snackBar.open('Request approved successfully.', 'Close', { duration: 3000 });
                        this.loadApprovals();
                    },
                    error: () => this.snackBar.open('Error approving request.', 'Close', { duration: 3000 })
                });
            }
        });
    }

    rejectItem(item: ApprovalRequest): void {
        const dialogRef = this.dialog.open(BulkActionDialogComponent, {
            width: '500px',
            data: {
                title: 'Reject Approval Request',
                message: `Reject "${item.rule_name}"?`,
                confirmLabel: 'Reject',
                type: 'warn' as any,
                showReason: true
            }
        });
        dialogRef.afterClosed().subscribe(result => {
            if (result?.confirmed) {
                this.approvalsService.reject(item.id, { reason: result.reason || 'No reason provided' }).subscribe({
                    next: () => {
                        this.snackBar.open('Request rejected.', 'Close', { duration: 3000 });
                        this.loadApprovals();
                    },
                    error: () => this.snackBar.open('Error rejecting request.', 'Close', { duration: 3000 })
                });
            }
        });
    }

    // Bulk operations
    bulkApproveSelected(): void {
        const ids: string[] = Array.from(this.selectedRows).map((item: ApprovalRequest, i: number) => item.id);
        const count = ids.length;
        const dialogRef = this.dialog.open(BulkActionDialogComponent, {
            width: '500px',
            data: {
                title: 'Bulk Approve',
                message: `Approve ${count} request(s)?`,
                confirmLabel: 'Approve All',
                type: 'primary',
                showReason: true
            }
        });
        dialogRef.afterClosed().subscribe(result => {
            if (result?.confirmed) {
                this.approvalsService.bulkApprove(ids as string[], result.reason || undefined).subscribe({
                    next: (res) => {
                        this.snackBar.open(`Approved ${res.success} request(s).`, 'Close', { duration: 3000 });
                        this.selectedRows.clear();
                        this.loadApprovals();
                    },
                    error: () => this.snackBar.open('Error bulk approving.', 'Close', { duration: 3000 })
                });
            }
        });
    }

    bulkRejectSelected(): void {
        const ids: string[] = Array.from(this.selectedRows).map((item: ApprovalRequest, i: number) => item.id);
        const count = ids.length;
        const dialogRef = this.dialog.open(BulkActionDialogComponent, {
            width: '500px',
            data: {
                title: 'Bulk Reject',
                message: `Reject ${count} request(s)?`,
                confirmLabel: 'Reject All',
                type: 'warn',
                showReason: true
            }
        });
        dialogRef.afterClosed().subscribe(result => {
            if (result?.confirmed) {
                this.approvalsService.bulkReject(ids as string[], result.reason || 'No reason provided').subscribe({
                    next: (res) => {
                        this.snackBar.open(`Rejected ${res.success} request(s).`, 'Close', { duration: 3000 });
                        this.selectedRows.clear();
                        this.loadApprovals();
                    },
                    error: () => this.snackBar.open('Error bulk rejecting.', 'Close', { duration: 3000 })
                });
            }
        });
    }
}