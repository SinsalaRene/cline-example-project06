import { Component, inject, OnInit, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { ApprovalsService } from '../services/approvals.service';
import { ErrorHandlerService } from '../../../../core/services/error-handler.service';
import { ErrorNotificationService } from '../../../../shared/components/error-notification/error-notification.component';


interface Approval {
    id: string;
    request_type: string;
    resource_id?: string;
    requested_by: string;
    status: string;
    created_at: string;
    updated_at?: string;
    reviewer?: string;
    comments?: string;
}

@Component({
    selector: 'app-approvals-list',
    standalone: true,
    imports: [
        CommonModule,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        MatFormFieldModule,
        MatInputModule,
        MatButtonModule,
        MatIconModule,
        MatProgressSpinnerModule,
        MatChipsModule,
        MatCardModule,
    ],
    template: `
        <div class="approvals-list-container">
            <mat-card>
                <mat-card-header>
                    <mat-card-title>
                        <h1>Approval Requests</h1>
                    </mat-card-title>
                </mat-card-header>

                <mat-card-content>
                    <!-- Search and Actions -->
                    <div class="toolbar">
                        <mat-form-field class="search-field">
                            <mat-label>Search approvals...</mat-label>
                            <input matInput (keyup)="applyFilter($event)" placeholder="Search by type, requester...">
                            <mat-icon matSuffix>search</mat-icon>
                        </mat-form-field>
                        <button mat-raised-button color="primary" (click)="refreshData()">
                            <mat-icon>refresh</mat-icon>
                            Refresh
                        </button>
                    </div>

                    @if (isLoading()) {
                        <div class="loading-container">
                            <mat-spinner diameter="50"></mat-spinner>
                            <p>Loading approval requests...</p>
                        </div>
                    } @else {
                        <!-- Approvals Table -->
                        <div class="table-container">
                            <table mat-table [dataSource]="dataSource" matSort class="approvals-table">
                                <!-- Request Type Column -->
                                <ng-container matColumnDef="request_type">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Request Type</th>
                                    <td mat-cell *matCellDef="let approval">{{ approval.request_type }}</td>
                                </ng-container>

                                <!-- Resource ID Column -->
                                <ng-container matColumnDef="resource_id">
                                    <th mat-header-cell *matHeaderCellDef>Resource ID</th>
                                    <td mat-cell *matCellDef="let approval" class="resource-id">
                                        {{ approval.resource_id || 'N/A' }}
                                    </td>
                                </ng-container>

                                <!-- Requested By Column -->
                                <ng-container matColumnDef="requested_by">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Requested By</th>
                                    <td mat-cell *matCellDef="let approval">{{ approval.requested_by }}</td>
                                </ng-container>

                                <!-- Status Column -->
                                <ng-container matColumnDef="status">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Status</th>
                                    <td mat-cell *matCellDef="let approval">
                                        <mat-chip 
                                            [class.pending-chip]="approval.status === 'pending'" 
                                            [class.approved-chip]="approval.status === 'approved'"
                                            [class.rejected-chip]="approval.status === 'rejected'">
                                            {{ approval.status }}
                                        </mat-chip>
                                    </td>
                                </ng-container>

                                <!-- Reviewer Column -->
                                <ng-container matColumnDef="reviewer">
                                    <th mat-header-cell *matHeaderCellDef>Reviewer</th>
                                    <td mat-cell *matCellDef="let approval">{{ approval.reviewer || '-' }}</td>
                                </ng-container>

                                <!-- Created At Column -->
                                <ng-container matColumnDef="created_at">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Requested</th>
                                    <td mat-cell *matCellDef="let approval">{{ approval.created_at | date:'short' }}</td>
                                </ng-container>

                                <!-- Updated At Column -->
                                <ng-container matColumnDef="updated_at">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Last Updated</th>
                                    <td mat-cell *matCellDef="let approval">{{ approval.updated_at | date:'short' }}</td>
                                </ng-container>

                                <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                                <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="table-row"></tr>
                            </table>
                        </div>

                        <mat-paginator [pageSizeOptions]="[10, 25, 50, 100]" 
                                       showFirstLastButtons 
                                       aria-label="Select page of approvals">
                        </mat-paginator>
                    }
                </mat-card-content>
            </mat-card>
        </div>
    `,
    styles: [`
        .approvals-list-container {
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }

        mat-card {
            margin-bottom: 20px;
        }

        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            gap: 16px;
        }

        .search-field {
            flex: 1;
            max-width: 400px;
        }

        .loading-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
            gap: 16px;
        }

        .table-container {
            overflow-x: auto;
            margin-bottom: 16px;
        }

        .approvals-table {
            width: 100%;
        }

        .table-row {
            cursor: pointer;
        }

        .table-row:hover {
            background-color: rgba(0, 0, 0, 0.04);
        }

        .resource-id {
            font-family: monospace;
            font-size: 12px;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        mat-chip {
            font-size: 12px;
        }

        .pending-chip {
            background-color: #ff9800 !important;
            color: white !important;
        }

        .approved-chip {
            background-color: #4caf50 !important;
            color: white !important;
        }

        .rejected-chip {
            background-color: #f44336 !important;
            color: white !important;
        }
    `]
})
export class ApprovalsListComponent implements OnInit {
    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    displayedColumns: string[] = [
        'request_type',
        'resource_id',
        'requested_by',
        'status',
        'reviewer',
        'created_at',
        'updated_at'
    ];

    dataSource = new MatTableDataSource<Approval>();
    isLoading = signal(true);

    private errorHandler = inject(ErrorHandlerService);
    private errorNotification = inject(ErrorNotificationService);

    constructor(private approvalsService: ApprovalsService) { }

    ngOnInit(): void {
        this.loadApprovals();
    }

    loadApprovals(): void {
        this.isLoading.set(true);
        this.approvalsService.getApprovals().subscribe({
            next: (response: any) => {
                this.dataSource.data = response.items || [];
                this.dataSource.paginator = this.paginator;
                this.dataSource.sort = this.sort;
                this.isLoading.set(false);
            },
            error: (error: any) => {
                this.errorHandler.handleApiError(error, { url: '/api/approvals', method: 'GET' });
                this.errorNotification.showError(this.errorHandler.getErrorMessage(error));
                this.isLoading.set(false);
            }
        });
    }

    applyFilter(event: Event): void {
        const filterValue = (event.target as HTMLInputElement).value;
        this.dataSource.filter = filterValue.trim().toLowerCase();

        if (this.dataSource.paginator) {
            this.dataSource.paginator.firstPage();
        }
    }

    refreshData(): void {
        this.loadApprovals();
    }
}
