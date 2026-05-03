/**
 * Audit Viewer Component
 *
 * Displays audit log entries with filtering, search, pagination, and export capabilities.
 *
 * # Features
 *
 * - Paginated table display of audit entries
 * - Full-text search across audit fields
 * - Multi-criteria filtering (date range, action, resource type, severity, user, success)
 * - Sortable columns
 * - Export to CSV/JSON
 * - Summary statistics dashboard
 * - Responsive layout
 * - Selection for batch operations
 *
 * # Usage
 *
 * ```typescript
 * // Import directly as standalone component
 * import { AuditViewerComponent } from './audit/components/audit-viewer.component';
 * ```
 */

import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
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
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatStepperModule } from '@angular/material/stepper';
import { MatDividerModule } from '@angular/material/divider';
import { Router } from '@angular/router';
import { AuditService } from '../services/audit.service';
import {
    AuditEntry,
    AuditFilter,
    AuditAction,
    AuditResourceType,
    AuditSeverity,
    AuditSummary
} from '../models/audit.model';
import { AuditDetailComponent } from './audit-detail.component';

@Component({
    selector: 'app-audit-viewer',
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
        MatCardModule,
        MatDatepickerModule,
        MatNativeDateModule,
        MatCheckboxModule,
        MatTabsModule,
        MatExpansionModule,
        MatTooltipModule,
        MatDividerModule
    ],
    template: `
        <div class="audit-container" *ngIf="!isLoading">
            <!-- Header -->
            <div class="header-section">
                <div class="header-top">
                    <div class="title-section">
                        <h2>Audit Log</h2>
                        <p>Track and review all system events and changes</p>
                    </div>
                    <div class="action-buttons">
                        <div class="export-dropdown" *ngIf="filteredEntries.length > 0">
                            <button mat-raised-button color="primary" (click)="toggleExportMenu()" matTooltip="Export audit log">
                                <mat-icon>file_download</mat-icon>
                                Export
                                <mat-icon class="dropdown-arrow">arrow_drop_down</mat-icon>
                            </button>
                            <div class="export-menu" *ngIf="showExportMenu">
                                <button class="export-option" (click)="exportAsCsv()">
                                    <mat-icon>table_chart</mat-icon>
                                    <span>Export as CSV</span>
                                </button>
                                <button class="export-option" (click)="exportAsJson()">
                                    <mat-icon>code</mat-icon>
                                    <span>Export as JSON</span>
                                </button>
                            </div>
                        </div>
                        <button mat-raised-button color="primary" (click)="refreshData()" matTooltip="Refresh audit log">
                            <mat-icon>refresh</mat-icon>
                            Refresh
                        </button>
                    </div>
                </div>
            </div>

            <!-- Summary Cards -->
            <div class="summary-cards" *ngIf="summary">
                <div class="summary-card">
                    <div class="summary-card-header">
                        <span class="summary-card-title">Total Events</span>
                        <mat-icon class="summary-icon">event_note</mat-icon>
                    </div>
                    <div class="summary-card-value">{{ summary.totalCount | number }}</div>
                    <div class="summary-card-subtitle">Across all time</div>
                </div>
                <div class="summary-card summary-success">
                    <div class="summary-card-header">
                        <span class="summary-card-title">Successful</span>
                        <mat-icon class="summary-icon success">check_circle</mat-icon>
                    </div>
                    <div class="summary-card-value success">{{ summary.bySuccess?.['true'] || 0 | number }}</div>
                    <div class="summary-card-subtitle">Succeeded</div>
                </div>
                <div class="summary-card summary-error">
                    <div class="summary-card-header">
                        <span class="summary-card-title">Failed</span>
                        <mat-icon class="summary-icon error">error</mat-icon>
                    </div>
                    <div class="summary-card-value error">{{ summary.bySuccess?.['false'] || 0 | number }}</div>
                    <div class="summary-card-subtitle">Failed</div>
                </div>
                <div class="summary-card summary-warning">
                    <div class="summary-card-header">
                        <span class="summary-card-title">Critical</span>
                        <mat-icon class="summary-icon warning">priority_high</mat-icon>
                    </div>
                    <div class="summary-card-value warning">{{ summary.bySeverity?.['error'] || 0 | number }}</div>
                    <div class="summary-card-subtitle">High severity</div>
                </div>
            </div>

            <!-- Filter Panel -->
            <mat-card class="filter-card">
                <mat-expansion-panel expanded="true" class="filter-panel">
                    <mat-expansion-panel-header>
                        <mat-panel-title>
                            <mat-icon>filter_list</mat-icon>
                            Filters & Search
                        </mat-panel-title>
                        <mat-panel-description>
                            {{ activeFilterCount }} filter(s) active
                        </mat-panel-description>
                    </mat-expansion-panel-header>

                    <form [formGroup]="filterForm" (ngSubmit)="applyFilters()" class="filter-form">
                        <div class="filter-row">
                            <mat-form-field appearance="outline" class="filter-field">
                                <mat-label>Search</mat-label>
                                <input matInput formControlName="searchQuery" placeholder="Search by description, user, IP, etc.">
                            </mat-form-field>

                            <mat-form-field appearance="outline" class="filter-field filter-date">
                                <mat-label>Start Date</mat-label>
                                <input matInput [matDatepicker]="startPicker" formControlName="dateFrom" placeholder="Start date">
                                <mat-hint>MM/DD/YYYY</mat-hint>
                                <mat-datepicker-toggle matSuffix [for]="startPicker"></mat-datepicker-toggle>
                                <mat-datepicker #startPicker></mat-datepicker>
                            </mat-form-field>

                            <mat-form-field appearance="outline" class="filter-field filter-date">
                                <mat-label>End Date</mat-label>
                                <input matInput [matDatepicker]="endPicker" formControlName="dateTo" placeholder="End date">
                                <mat-hint>MM/DD/YYYY</mat-hint>
                                <mat-datepicker-toggle matSuffix [for]="endPicker"></mat-datepicker-toggle>
                                <mat-datepicker #endPicker></mat-datepicker>
                            </mat-form-field>
                        </div>

                        <div class="filter-row">
                            <mat-form-field appearance="outline" class="filter-field">
                                <mat-label>Action</mat-label>
                                <mat-select formControlName="actionFilter" (selectionChange)="applyFilters()" multiple>
                                    <mat-option>--</mat-option>
                                    <mat-option value="CREATE">Create</mat-option>
                                    <mat-option value="UPDATE">Update</mat-option>
                                    <mat-option value="DELETE">Delete</mat-option>
                                    <mat-option value="READ">View</mat-option>
                                    <mat-option value="LOGIN">Login</mat-option>
                                    <mat-option value="LOGOUT">Logout</mat-option>
                                    <mat-option value="APPROVE">Approve</mat-option>
                                    <mat-option value="REJECT">Reject</mat-option>
                                    <mat-option value="IMPORT">Import</mat-option>
                                    <mat-option value="EXPORT">Export</mat-option>
                                    <mat-option value="CONFIGURE">Configure</mat-option>
                                    <mat-option value="DEPLOY">Deploy</mat-option>
                                    <mat-option value="TEST">Test</mat-option>
                                    <mat-option value="EXECUTE">Execute</mat-option>
                                </mat-select>
                            </mat-form-field>

                            <mat-form-field appearance="outline" class="filter-field">
                                <mat-label>Resource Type</mat-label>
                                <mat-select formControlName="resourceTypeFilter" (selectionChange)="applyFilters()" multiple>
                                    <mat-option>--</mat-option>
                                    <mat-option value="FIREWALL_RULE">Firewall Rule</mat-option>
                                    <mat-option value="ACCESS_RULE">Access Rule</mat-option>
                                    <mat-option value="THRESHOLD">Threshold</mat-option>
                                    <mat-option value="WORKSPACE">Workspace</mat-option>
                                    <mat-option value="USER">User</mat-option>
                                    <mat-option value="CONFIGURATION">Configuration</mat-option>
                                    <mat-option value="DEPLOYMENT">Deployment</mat-option>
                                    <mat-option value="APPROVAL">Approval</mat-option>
                                    <mat-option value="RULE_EVALUATION">Rule Evaluation</mat-option>
                                    <mat-option value="BATCH_OPERATION">Batch Operation</mat-option>
                                    <mat-option value="WEBHOOK">Webhook</mat-option>
                                    <mat-option value="NOTIFICATION">Notification</mat-option>
                                </mat-select>
                            </mat-form-field>

                            <mat-form-field appearance="outline" class="filter-field">
                                <mat-label>Severity</mat-label>
                                <mat-select formControlName="severityFilter" (selectionChange)="applyFilters()" multiple>
                                    <mat-option>--</mat-option>
                                    <mat-option value="info">Info</mat-option>
                                    <mat-option value="warning">Warning</mat-option>
                                    <mat-option value="error">Error</mat-option>
                                    <mat-option value="success">Success</mat-option>
                                </mat-select>
                            </mat-form-field>
                        </div>

                        <div class="filter-row">
                            <mat-form-field appearance="outline" class="filter-field">
                                <mat-label>User</mat-label>
                                <mat-select formControlName="userFilter" (selectionChange)="applyFilters()" multiple>
                                    <mat-option>--</mat-option>
                                    <mat-option *ngFor="let user of availableUsers" [value]="user">
                                        {{ user }}
                                    </mat-option>
                                </mat-select>
                            </mat-form-field>

                            <mat-form-field appearance="outline" class="filter-field">
                                <mat-label>Result</mat-label>
                                <mat-select formControlName="successFilter" (selectionChange)="applyFilters()">
                                    <mat-option value="">Any</mat-option>
                                    <mat-option value="true">Success</mat-option>
                                    <mat-option value="false">Failure</mat-option>
                                </mat-select>
                            </mat-form-field>

                            <div class="filter-actions">
                                <button mat-raised-button color="primary" type="submit">
                                    <mat-icon>search</mat-icon>
                                    Apply
                                </button>
                                <button mat-stroked-button type="button" (click)="resetFilters()">
                                    <mat-icon>clear</mat-icon>
                                    Reset
                                </button>
                            </div>
                        </div>
                    </form>
                </mat-expansion-panel>
            </mat-card>

            <!-- Results info -->
            <div class="results-info" *ngIf="!isLoading">
                <span>Showing {{ startIndex + 1 }}-{{ endIndex }} of {{ totalItems }}</span>
                <span>•</span>
                <span>{{ filteredEntries.length }} match(es)</span>
            </div>

            <!-- Audit Table -->
            <div class="table-container" *ngIf="!isLoading && filteredEntries.length > 0">
                <table mat-table [dataSource]="filteredEntries" matSort class="audit-table">

                    <!-- Timestamp column -->
                    <ng-container matColumnDef="timestamp">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header sortActionDescription="Sort by timestamp">
                            Timestamp
                        </th>
                        <td mat-cell *matCellDef="let entry">
                            <div class="timestamp-cell">
                                <div class="timestamp-main">{{ entry.timestamp | date:'medium' }}</div>
                                <div class="timestamp-relative">{{ entry.timestamp | date:'shortTime' }}</div>
                            </div>
                        </td>
                    </ng-container>

                    <!-- Severity column -->
                    <ng-container matColumnDef="severity">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header sortActionDescription="Sort by severity">
                            Severity
                        </th>
                        <td mat-cell *matCellDef="let entry">
                            <div class="severity-badge" [class]="'severity-' + entry.severity">
                                <mat-icon class="severity-icon">{{
                                    entry.severity === 'error' ? 'error' :
                                    entry.severity === 'warning' ? 'warning' :
                                    entry.severity === 'success' ? 'check_circle' : 'info'
                                }}</mat-icon>
                                <span class="severity-label">{{ entry.severity }}</span>
                            </div>
                        </td>
                    </ng-container>

                    <!-- Action column -->
                    <ng-container matColumnDef="action">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header sortActionDescription="Sort by action">
                            Action
                        </th>
                        <td mat-cell *matCellDef="let entry">
                            <div class="action-badge">
                                <mat-icon class="action-icon">{{ auditServiceRef.getActionIcon(entry.action) }}</mat-icon>
                                <span>{{ auditServiceRef.getActionDisplay(entry.action) }}</span>
                            </div>
                        </td>
                    </ng-container>

                    <!-- Resource type column -->
                    <ng-container matColumnDef="resourceType">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header sortActionDescription="Sort by resource type">
                            Resource
                        </th>
                        <td mat-cell *matCellDef="let entry">
                            <span class="resource-type-badge">{{ auditServiceRef.getResourceTypeDisplay(entry.resourceType) }}</span>
                        </td>
                    </ng-container>

                    <!-- Description column -->
                    <ng-container matColumnDef="description">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header sortActionDescription="Sort by description">
                            Description
                        </th>
                        <td mat-cell *matCellDef="let entry" class="description-cell">
                            <div class="description-text" [matTooltip]="entry.description">{{ entry.description }}</div>
                            <div class="resource-id" *ngIf="entry.resourceId">
                                Resource: {{ entry.resourceId }}
                            </div>
                        </td>
                    </ng-container>

                    <!-- User column -->
                    <ng-container matColumnDef="user">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header sortActionDescription="Sort by user">
                            User
                        </th>
                        <td mat-cell *matCellDef="let entry">
                            <div class="user-cell">
                                <span class="user-name">{{ entry.displayName || entry.user }}</span>
                                <span class="user-ip" *ngIf="entry.ipAddress">{{ entry.ipAddress }}</span>
                            </div>
                        </td>
                    </ng-container>

                    <!-- Result column -->
                    <ng-container matColumnDef="success">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header sortActionDescription="Sort by result">
                            Result
                        </th>
                        <td mat-cell *matCellDef="let entry">
                            <div class="result-badge" [class.success]="entry.success" [class.failure]="!entry.success">
                                <mat-icon class="result-icon" [class.success-icon]="entry.success" [class.failure-icon]="!entry.success">
                                    {{ entry.success ? 'check_circle' : 'cancel' }}
                                </mat-icon>
                                <span>{{ entry.success ? 'Success' : 'Failed' }}</span>
                            </div>
                        </td>
                    </ng-container>

                    <!-- Duration column -->
                    <ng-container matColumnDef="duration">
                        <th mat-header-cell *matHeaderCellDef mat-sort-header sortActionDescription="Sort by duration">
                            Duration
                        </th>
                        <td mat-cell *matCellDef="let entry">
                            <span class="duration-badge" *ngIf="entry.durationMs !== undefined">
                                {{ auditServiceRef.formatDuration(entry.durationMs) }}
                            </span>
                        </td>
                    </ng-container>

                    <!-- Actions column -->
                    <ng-container matColumnDef="actions">
                        <th mat-header-cell *matHeaderCellDef>
                            Actions
                        </th>
                        <td mat-cell *matCellDef="let entry">
                            <button mat-icon-button color="primary" (click)="viewDetail(entry)"
                                    matTooltip="View details" matTooltipPosition="above">
                                <mat-icon>visibility</mat-icon>
                            </button>
                            <button mat-icon-button color="accent" (click)="copyEntryId(entry.id)"
                                    matTooltip="Copy ID" matTooltipPosition="above">
                                <mat-icon>content_copy</mat-icon>
                            </button>
                        </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="displayedColumns" class="header-row"></tr>
                    <tr mat-row *matRowDef="let row; columns: displayedColumns;"
                        class="audit-row"
                        (click)="viewDetail(row)"
                        [class.row-clickable]="displayedColumns.length > 0">
                    </tr>
                </table>

                <!-- Empty state -->
                <div class="empty-state" *ngIf="filteredEntries.length === 0 && !isLoading">
                    <mat-icon class="empty-icon">search</mat-icon>
                    <h3>No audit entries found</h3>
                    <p>Try adjusting your search or filter criteria.</p>
                </div>

                <mat-paginator
                    [pageSizeOptions]="[10, 25, 50, 100]"
                    showFirstLastButtons
                    aria-label="Select page"
                    (page)="onPageChange($event)"
                ></mat-paginator>
            </div>
        </div>

        <!-- Loading state -->
        <div class="audit-container loading-state" *ngIf="isLoading">
            <mat-progress-spinner mode="indeterminate" [diameter]="50"></mat-progress-spinner>
            <p>Loading audit entries...</p>
        </div>
    `,
    styles: [`
        .audit-container {
            padding: 24px;
            max-width: 100%;
            min-height: 400px;
        }

        .loading-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 400px;
            gap: 16px;
        }

        /* Header */
        .header-section { margin-bottom: 24px; }
        .header-top { display: flex; justify-content: space-between; align-items: flex-start; }
        .title-section h2 { margin: 0 0 8px 0; font-size: 24px; font-weight: 500; }
        .title-section p { margin: 0; color: #666; font-size: 14px; }
        .action-buttons { display: flex; gap: 8px; }

        /* Export dropdown */
        .export-dropdown { position: relative; display: inline-block; }
        .export-menu {
            position: absolute;
            top: 100%;
            right: 0;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            padding: 8px;
            z-index: 100;
            min-width: 180px;
        }
        .export-option {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border: none;
            background: none;
            cursor: pointer;
            width: 100%;
            text-align: left;
            font-size: 14px;
            color: #333;
            border-radius: 4px;
        }
        .export-option:hover { background: #f5f5f5; }
        .export-option mat-icon { font-size: 18px; width: 18px; height: 18px; }
        .dropdown-arrow { font-size: 18px !important; width: 18px !important; height: 18px !important; }

        /* Summary cards */
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .summary-card {
            padding: 20px;
            border-radius: 12px;
            background: white;
            border: 1px solid #e0e0e0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .summary-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .summary-card-title { font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
        .summary-icon { font-size: 20px !important; width: 20px !important; height: 20px !important; }
        .summary-icon.success { color: #4caf50; }
        .summary-icon.error { color: #f44336; }
        .summary-icon.warning { color: #ff9800; }
        .summary-card-value { font-size: 28px; font-weight: 600; margin-bottom: 4px; }
        .summary-card-value.success { color: #4caf50; }
        .summary-card-value.error { color: #f44336; }
        .summary-card-value.warning { color: #ff9800; }
        .summary-card-subtitle { font-size: 12px; color: #999; }

        /* Filter card */
        .filter-card { margin-bottom: 16px; }
        .filter-panel { border-radius: 8px !important; overflow: hidden; }
        .filter-form { padding: 16px 0; }
        .filter-row { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
        .filter-field { flex: 1; min-width: 150px; }
        .filter-date { min-width: 140px; }
        .filter-actions { display: flex; gap: 8px; align-items: center; }

        /* Results info */
        .results-info {
            display: flex; align-items: center; gap: 8px;
            margin-bottom: 16px; font-size: 14px; color: #666;
        }

        /* Table */
        .table-container {
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            overflow-x: auto;
            background: white;
        }
        .audit-table { width: 100%; }
        .header-row { font-weight: 600; background: #fafafa; }
        .audit-row { cursor: pointer; }
        .audit-row:hover { background: #f5f5f5; }
        .row-clickable:hover { cursor: pointer; }

        /* Cell styles */
        .timestamp-cell { display: flex; flex-direction: column; gap: 2px; }
        .timestamp-main { font-size: 14px; font-weight: 500; }
        .timestamp-relative { font-size: 12px; color: #999; }

        .severity-badge { display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 16px; font-size: 12px; font-weight: 500; }
        .severity-error { background: #ffebee; color: #c62828; }
        .severity-warning { background: #fff3e0; color: #ef6c00; }
        .severity-info { background: #e3f2fd; color: #1565c0; }
        .severity-success { background: #e8f5e9; color: #2e7d32; }
        .severity-icon { font-size: 16px !important; width: 16px !important; height: 16px !important; }
        .severity-label { text-transform: capitalize; }

        .action-badge { display: flex; align-items: center; gap: 6px; font-size: 13px; }
        .action-icon { font-size: 16px !important; width: 16px !important; height: 16px !important; color: #666; }

        .resource-type-badge { font-size: 12px; background: #f5f5f5; padding: 2px 8px; border-radius: 4px; border: 1px solid #e0e0e0; }

        .description-cell { max-width: 300px; }
        .description-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }

        .user-cell { display: flex; flex-direction: column; gap: 2px; }
        .user-name { font-size: 14px; font-weight: 500; }
        .user-ip { font-size: 12px; color: #999; font-family: monospace; }

        .result-badge { display: flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 500; }
        .result-badge.success { color: #4caf50; }
        .result-badge.failure { color: #f44336; }
        .result-icon { font-size: 16px !important; width: 16px !important; height: 16px !important; }
        .success-icon { color: #4caf50; }
        .failure-icon { color: #f44336; }

        .duration-badge { font-size: 12px; font-family: monospace; color: #666; }

        /* Empty state */
        .empty-state {
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; padding: 40px 20px; text-align: center;
        }
        .empty-icon { font-size: 64px; color: #bdbdbd; margin-bottom: 16px; }
        .empty-state h3 { margin: 0 0 8px 0; color: #616161; }
        .empty-state p { margin: 0 0 16px 0; color: #9e9e9e; }

        /* Responsive */
        @media (max-width: 768px) {
            .audit-container { padding: 16px; }
            .header-top { flex-direction: column; gap: 16px; }
            .filter-row { flex-direction: column; }
            .filter-field { min-width: 100%; }
        }
    `]
})
export class AuditViewerComponent implements OnInit {
    readonly displayedColumns: string[] = [
        'timestamp', 'severity', 'action', 'resourceType', 'description',
        'user', 'success', 'duration', 'actions'
    ];

    dataSource = new MatTableDataSource<AuditEntry>();
    filteredEntries: AuditEntry[] = [];
    allEntries: AuditEntry[] = [];
    availableUsers: string[] = [];

    isLoading = true;
    summary: AuditSummary | null = null;
    totalItems = 0;
    currentPage = 1;
    pageSize = 10;

    filterForm: FormGroup;
    showExportMenu = false;

    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    // Computed properties for UI
    get startIndex(): number { return (this.currentPage - 1) * this.pageSize; }
    get endIndex(): number { return Math.min(this.currentPage * this.pageSize, this.totalItems); }

    get activeFilterCount(): number {
        const controls = this.filterForm.controls;
        let count = 0;
        if (controls['searchQuery'].value) count++;
        if (controls['dateFrom'].value) count++;
        if (controls['dateTo'].value) count++;
        if (controls['actionFilter'].value?.length) count++;
        if (controls['resourceTypeFilter'].value?.length) count++;
        if (controls['severityFilter'].value?.length) count++;
        if (controls['userFilter'].value?.length) count++;
        if (controls['successFilter'].value) count++;
        return count;
    }

    constructor(
        private auditService: AuditService,
        private dialog: MatDialog,
        private snackBar: MatSnackBar,
        private fb: FormBuilder,
        public auditServiceRef: AuditService // For template access
    ) {
        this.filterForm = this.fb.group({
            searchQuery: [''],
            dateFrom: [null as Date | null],
            dateTo: [null as Date | null],
            actionFilter: [[] as string[]],
            resourceTypeFilter: [[] as string[]],
            severityFilter: [[] as string[]],
            userFilter: [[] as string[]],
            successFilter: ['']
        });
    }

    ngOnInit(): void {
        this.loadAuditLogs();
    }

    loadAuditLogs(page: number = 1): void {
        this.isLoading = true;

        const filterValue = this.filterForm.value;
        const filters: AuditFilter = {
            page,
            pageSize: this.pageSize,
            searchQuery: filterValue.searchQuery || '',
            dateFrom: filterValue.dateFrom ? filterValue.dateFrom.toISOString() : undefined,
            dateTo: filterValue.dateTo ? filterValue.dateTo.toISOString() : undefined,
            actionFilter: filterValue.actionFilter,
            resourceTypeFilter: filterValue.resourceTypeFilter,
            severityFilter: filterValue.severityFilter,
            userFilter: filterValue.userFilter,
            successFilter: filterValue.successFilter !== '' ? filterValue.successFilter === 'true' : undefined
        };

        this.auditService.getAuditLogs(page, this.pageSize, filters).subscribe({
            next: (response) => {
                this.allEntries = response.items ?? [];
                this.totalItems = response.total ?? 0;
                this.currentPage = page;
                this.filteredEntries = [...this.allEntries];
                this.availableUsers = this.auditService.getUniqueUsers(this.allEntries);
                this.isLoading = false;

                if (this.paginator) {
                    this.paginator.length = this.totalItems;
                    this.paginator.pageIndex = page - 1;
                }
            },
            error: (err) => {
                console.error('Error loading audit logs:', err);
                this.isLoading = false;
                this.snackBar.open('Error loading audit log entries. Please try again.', 'Close', { duration: 5000 });
            }
        });

        const dateFromStr = filterValue.dateFrom ? filterValue.dateFrom.toISOString() : undefined;
        const dateToStr = filterValue.dateTo ? filterValue.dateTo.toISOString() : undefined;
        this.auditService.getAuditSummary(dateFromStr, dateToStr).subscribe({
            next: (summary) => {
                this.summary = summary;
            },
            error: () => {
                this.summary = {
                    totalCount: this.allEntries.length,
                    byAction: {},
                    byResourceType: {},
                    bySeverity: {},
                    bySuccess: {},
                    byUser: {},
                    recentActivity: [],
                    topUsers: []
                };
            }
        });
    }

    applyFilters(): void {
        this.currentPage = 1;
        if (this.paginator) {
            this.paginator.firstPage();
        }
        this.loadAuditLogs(1);
    }

    refreshData(): void {
        this.loadAuditLogs(this.currentPage);
    }

    onPageChange(event: any): void {
        const newPage = event.pageIndex + 1;
        this.loadAuditLogs(newPage);
    }

    resetFilters(): void {
        this.filterForm.reset({
            searchQuery: '',
            dateFrom: null,
            dateTo: null,
            actionFilter: [],
            resourceTypeFilter: [],
            severityFilter: [],
            userFilter: [],
            successFilter: ''
        });
        this.filteredEntries = [...this.allEntries];
        this.currentPage = 1;
        this.loadAuditLogs(1);
    }

    viewDetail(entry: AuditEntry): void {
        const dialogRef = this.dialog.open(AuditDetailComponent, {
            width: '800px',
            maxWidth: '90vw',
            data: { entry }
        });
    }

    exportAsCsv(): void {
        this.showExportMenu = false;
        const filters = this.getFilterCriteria();
        this.auditService.exportAsCsv(filters).subscribe({
            next: (blob) => {
                this.downloadFile(blob, 'audit_log.csv');
                this.snackBar.open('Export started - CSV file downloading...', 'Close', { duration: 3000 });
            },
            error: () => {
                this.snackBar.open('Error exporting audit log. Please try again.', 'Close', { duration: 5000 });
            }
        });
    }

    exportAsJson(): void {
        this.showExportMenu = false;
        const filters = this.getFilterCriteria();
        this.auditService.exportAsJson(filters).subscribe({
            next: (blob) => {
                this.downloadFile(blob, 'audit_log.json');
                this.snackBar.open('Export started - JSON file downloading...', 'Close', { duration: 3000 });
            },
            error: () => {
                this.snackBar.open('Error exporting audit log. Please try again.', 'Close', { duration: 5000 });
            }
        });
    }

    private getFilterCriteria(): AuditFilter {
        const filterValue = this.filterForm.value;
        return {
            page: 1,
            pageSize: 1000,
            searchQuery: filterValue.searchQuery || '',
            dateFrom: filterValue.dateFrom ? filterValue.dateFrom.toISOString() : undefined,
            dateTo: filterValue.dateTo ? filterValue.dateTo.toISOString() : undefined,
            actionFilter: filterValue.actionFilter,
            resourceTypeFilter: filterValue.resourceTypeFilter,
            severityFilter: filterValue.severityFilter,
            userFilter: filterValue.userFilter,
            successFilter: filterValue.successFilter !== '' ? filterValue.successFilter === 'true' : undefined
        };
    }

    private downloadFile(blob: Blob, filename: string): void {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        window.URL.revokeObjectURL(url);
    }

    copyEntryId(id: string): void {
        navigator.clipboard?.writeText(id).then(() => {
            this.snackBar.open('Entry ID copied to clipboard.', 'Close', { duration: 2000 });
        }).catch(() => {
            this.snackBar.open('Failed to copy ID.', 'Close', { duration: 2000 });
        });
    }

    toggleExportMenu(): void {
        this.showExportMenu = !this.showExportMenu;
    }
}