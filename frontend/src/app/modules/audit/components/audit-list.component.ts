import { Component, OnInit, ViewChild, signal } from '@angular/core';
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
import { AuditService } from '../services/audit.service';

interface AuditEntry {
    id: string;
    timestamp: string;
    user_id?: string;
    action: string;
    resource_type?: string;
    resource_id?: string;
    level: string;
    message?: string;
    ip_address?: string;
}

@Component({
    selector: 'app-audit-list',
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
        <div class="audit-list-container">
            <mat-card>
                <mat-card-header>
                    <mat-card-title>
                        <h1>Audit Log</h1>
                    </mat-card-title>
                </mat-card-header>

                <mat-card-content>
                    <!-- Search and Actions -->
                    <div class="toolbar">
                        <mat-form-field class="search-field">
                            <mat-label>Search audit log...</mat-label>
                            <input matInput (keyup)="applyFilter($event)" placeholder="Search by action, user, resource...">
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
                            <p>Loading audit entries...</p>
                        </div>
                    } @else {
                        <!-- Audit Table -->
                        <div class="table-container">
                            <table mat-table [dataSource]="dataSource" matSort class="audit-table">
                                <!-- Timestamp Column -->
                                <ng-container matColumnDef="timestamp">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Timestamp</th>
                                    <td mat-cell *matCellDef="let entry">{{ entry.timestamp | date:'short' }}</td>
                                </ng-container>

                                <!-- Level Column -->
                                <ng-container matColumnDef="level">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Level</th>
                                    <td mat-cell *matCellDef="let entry">
                                        <mat-chip 
                                            [class.info-chip]="entry.level === 'info'" 
                                            [class.warning-chip]="entry.level === 'warning'"
                                            [class.error-chip]="entry.level === 'error'">
                                            {{ entry.level }}
                                        </mat-chip>
                                    </td>
                                </ng-container>

                                <!-- Action Column -->
                                <ng-container matColumnDef="action">
                                    <th mat-header-cell *matHeaderCellDef mat-sort-header>Action</th>
                                    <td mat-cell *matCellDef="let entry">{{ entry.action }}</td>
                                </ng-container>

                                <!-- User Column -->
                                <ng-container matColumnDef="user_id">
                                    <th mat-header-cell *matHeaderCellDef>User</th>
                                    <td mat-cell *matCellDef="let entry">{{ entry.user_id || 'system' }}</td>
                                </ng-container>

                                <!-- Resource Type Column -->
                                <ng-container matColumnDef="resource_type">
                                    <th mat-header-cell *matHeaderCellDef>Resource Type</th>
                                    <td mat-cell *matCellDef="let entry">{{ entry.resource_type || '-' }}</td>
                                </ng-container>

                                <!-- Resource ID Column -->
                                <ng-container matColumnDef="resource_id">
                                    <th mat-header-cell *matHeaderCellDef>Resource ID</th>
                                    <td mat-cell *matCellDef="let entry" class="resource-id">
                                        {{ entry.resource_id || '-' }}
                                    </td>
                                </ng-container>

                                <!-- Message Column -->
                                <ng-container matColumnDef="message">
                                    <th mat-header-cell *matHeaderCellDef>Message</th>
                                    <td mat-cell *matCellDef="let entry" class="message-cell">
                                        {{ entry.message || '-' }}
                                    </td>
                                </ng-container>

                                <!-- IP Address Column -->
                                <ng-container matColumnDef="ip_address">
                                    <th mat-header-cell *matHeaderCellDef>IP Address</th>
                                    <td mat-cell *matCellDef="let entry">{{ entry.ip_address || '-' }}</td>
                                </ng-container>

                                <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                                <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="table-row"></tr>
                            </table>
                        </div>

                        <mat-paginator [pageSizeOptions]="[10, 25, 50, 100]" 
                                       showFirstLastButtons 
                                       aria-label="Select page of audit entries">
                        </mat-paginator>
                    }
                </mat-card-content>
            </mat-card>
        </div>
    `,
    styles: [`
        .audit-list-container {
            padding: 20px;
            max-width: 1600px;
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

        .audit-table {
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
            max-width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .message-cell {
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        mat-chip {
            font-size: 12px;
        }

        .info-chip {
            background-color: #2196f3 !important;
            color: white !important;
        }

        .warning-chip {
            background-color: #ff9800 !important;
            color: white !important;
        }

        .error-chip {
            background-color: #f44336 !important;
            color: white !important;
        }
    `]
})
export class AuditListComponent implements OnInit {
    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    displayedColumns: string[] = [
        'timestamp',
        'level',
        'action',
        'user_id',
        'resource_type',
        'resource_id',
        'message',
        'ip_address'
    ];

    dataSource = new MatTableDataSource<AuditEntry>();
    isLoading = signal(true);

    constructor(private auditService: AuditService) { }

    ngOnInit(): void {
        this.loadAuditLog();
    }

    loadAuditLog(): void {
        this.isLoading.set(true);
        this.auditService.getAuditLogs(0).subscribe({
            next: (response: any) => {
                this.dataSource.data = response.items || [];
                this.dataSource.paginator = this.paginator;
                this.dataSource.sort = this.sort;
                this.isLoading.set(false);
            },
            error: (error: any) => {
                console.error('Error loading audit log:', error);
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
        this.loadAuditLog();
    }
}
