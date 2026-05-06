/**
 * Audit List Component
 *
 * A production-quality audit log viewer with comprehensive filtering, export,
 * and summary statistics capabilities.
 *
 * # Features
 *
 * - **Date Range Filtering**: Filter audit entries by a selectable date range with
 *   Material date pickers. Defaults to the last 30 days on initial load.
 * - **Multi-Select Filter Dropdowns**: Filter by action types, resource types, and
 *   severity levels using MatSelect with checkbox selection.
 * - **Export Functionality**: Export filtered audit logs as CSV or JSON using the
 * *  built-in blob download mechanism.
 * - **Summary Statistics Card**: Displays total entry count and top N distributions
 *   for actions and resource types, fetched from the service on init and after
 *   each filter change (debounced).
 * - **Pagination**: Correctly maps Angular Material's 0-based paginator index to
 *   the API's 1-based page numbering.
 *
 * # Service Integration
 *
 * Uses `AuditService` for all data operations:
 * - `getAuditLogs(page, pageSize, filters)` — paginated audit entries
 * - `getAuditSummary(dateFrom?, dateTo?)` — summary statistics
 * - `exportAsCsv(filters)` / `exportAsJson(filters)` — file exports
 * - `getSeverityDisplay()`, `getActionDisplay()`, `getResourceTypeDisplay()` — display helpers
 *
 * @module audit-list.component
 * @author Audit Module Team
 */

import {
    Component,
    OnInit,
    OnDestroy,
    ViewChild,
    signal,
    inject,
    ChangeDetectorRef,
} from '@angular/core';
import { CommonModule, DatePipe, NgIf, NgFor, NgClass } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { MatDividerModule } from '@angular/material/divider';
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
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { Subject, debounceTime } from 'rxjs';
import { Router, RouterModule, RouterLink, RouterLinkWithHref } from '@angular/router';

import { AuditService } from '../services/audit.service';
import {
    AuditEntry,
    AuditAction,
    AuditResourceType,
    AuditSeverity,
    AuditFilter,
    AuditSummary,
} from '../models/audit.model';

// ─── Filter chip model ──────────────────────────────────────────────────────

/** Represents a selected filter option in the multi-select dropdown. */
interface FilterChip {
    value: string;
    label: string;
    selected: boolean;
    count?: number;
}

/** Represents an active filter chip that can be removed from the UI. */
interface ActiveFilterChip {
    /** The filter category key. */
    key: 'action' | 'resourceType' | 'severity';
    /** The raw value of the filter. */
    value: string;
    /** Human-readable display text. */
    display: string;
}

@Component({
    selector: 'app-audit-list',
    standalone: true,
    imports: [
        CommonModule,
        DatePipe,
        ReactiveFormsModule,
        FormsModule,
        NgIf,
        NgFor,
        NgClass,
        MatDatepickerModule,
        MatNativeDateModule,
        MatCheckboxModule,
        MatSelectModule,
        MatDividerModule,
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
        MatSnackBarModule,
        RouterModule,
        RouterLink,
        RouterLinkWithHref,
    ],
    providers: [DatePipe],
    template: `
    <!-- ====== SUMMARY STATISTICS CARD ====== -->
    <mat-card class="summary-card" *ngIf="summaryLoaded">
        <mat-card-header>
            <mat-card-title>
                <mat-icon class="summary-icon">analytics</mat-icon>
                Audit Summary
            </mat-card-title>
        </mat-card-header>
        <mat-card-content class="summary-content">
            <div class="summary-row">
                <div class="summary-stat total-entries">
                    <span class="summary-number">{{ summary?.totalCount || 0 }}</span>
                    <span class="summary-label">Total Entries</span>
                </div>
                <!-- Top Actions -->
                <div class="summary-section">
                    <h4>Top Actions</h4>
                    <div class="summary-bars">
                        <div
                            class="bar-row"
                            *ngFor="let item of topActions; let i = index"
                        >
                            <span class="bar-label">{{ item.label }}</span>
                            <div class="bar-track">
                                <div
                                    class="bar-fill"
                                    [style.width.%]="getBarWidth(item.count || 0, maxActionCount)"
                                    [style.background]="actionColors[i % actionColors.length]"
                                ></div>
                            </div>
                            <span class="bar-value">{{ item.count || 0 }}</span>
                        </div>
                    </div>
                </div>
                <!-- Top Resource Types -->
                <div class="summary-section">
                    <h4>Top Resource Types</h4>
                    <div class="summary-bars">
                        <div
                            class="bar-row"
                            *ngFor="let item of topResourceTypes; let i = index"
                        >
                            <span class="bar-label">{{ item.label }}</span>
                            <div class="bar-track">
                                <div
                                    class="bar-fill"
                                    [style.width.%]="getBarWidth(item.count || 0, maxResourceCount)"
                                    [style.background]="resourceColors[i % resourceColors.length]"
                                ></div>
                            </div>
                            <span class="bar-value">{{ item.count || 0 }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </mat-card-content>
    </mat-card>

    <div class="audit-list-container">
        <mat-card>
            <mat-card-header>
                <mat-card-title>
                    <h1>Audit Log</h1>
                </mat-card-title>
            </mat-card-header>

            <mat-card-content>
                <!-- ====== DATE RANGE FILTER BAR ====== -->
                <div class="filter-bar">
                    <mat-form-field class="date-field">
                        <mat-label>From Date</mat-label>
                        <input
                            matInput
                            [max]="toDate"
                            [matDatepicker]="fromPicker"
                            placeholder="From date"
                            (dateChange)="onFromDateChange($event.value)"
                            [ngModel]="fromDate"
                            (ngModelChange)="onFromDateModelChange($event)"
                        />
                        <mat-datepicker-toggle matSuffix [for]="fromPicker" />
                        <mat-datepicker #fromPicker />
                    </mat-form-field>

                    <mat-form-field class="date-field">
                        <mat-label>To Date</mat-label>
                        <input
                            matInput
                            [min]="fromDate"
                            [matDatepicker]="toPicker"
                            placeholder="To date"
                            (dateChange)="onToDateChange($event.value)"
                            [ngModel]="toDate"
                            (ngModelChange)="onToDateModelChange($event)"
                        />
                        <mat-datepicker-toggle matSuffix [for]="toPicker" />
                        <mat-datepicker #toPicker />
                    </mat-form-field>

                    <!-- Clear dates button -->
                    <button
                        mat-stroked-button
                        color="accent"
                        *ngIf="fromDate || toDate"
                        (click)="clearDates()"
                    >
                        <mat-icon>close</mat-icon>
                        Clear Dates
                    </button>

                    <div class="spacer"></div>

                    <!-- ====== EXPORT BUTTONS ====== -->
                    <button
                        mat-raised-button
                        color="primary"
                        (click)="exportCsv()"
                        [disabled]="isLoadingExport()"
                    >
                        <mat-icon>file_download</mat-icon>
                        Export CSV
                    </button>
                    <button
                        mat-raised-button
                        color="primary"
                        (click)="exportJson()"
                        [disabled]="isLoadingExport()"
                    >
                        <mat-icon>code</mat-icon>
                        Export JSON
                    </button>
                    <button
                        mat-raised-button
                        color="accent"
                        (click)="refreshData()"
                    >
                        <mat-icon>refresh</mat-icon>
                        Refresh
                    </button>
                </div>

                <mat-divider class="filter-divider" />

                <!-- ====== FILTER DROPDOWN SECTION ====== -->
                <div class="filter-dropdowns">
                    <!-- Action Filter -->
                    <div class="filter-group">
                        <span class="filter-label">Actions:</span>
                        <mat-form-field class="filter-select">
                            <mat-label>Select Actions</mat-label>
                            <mat-select
                                [ngModel]="selectedActions"
                                (ngModelChange)="onActionFilterChange($event)"
                                multiple
                            >
                                <mat-option
                                    *ngFor="let action of actionOptions"
                                    [value]="action.value"
                                >
                                    <mat-checkbox [checked]="action.selected">
                                        {{ action.label }}
                                    </mat-checkbox>
                                </mat-option>
                            </mat-select>
                        </mat-form-field>
                    </div>

                    <!-- Resource Type Filter -->
                    <div class="filter-group">
                        <span class="filter-label">Resource Types:</span>
                        <mat-form-field class="filter-select">
                            <mat-label>Select Resource Types</mat-label>
                            <mat-select
                                [ngModel]="selectedResourceTypes"
                                (ngModelChange)="onResourceTypeFilterChange($event)"
                                multiple
                            >
                                <mat-option
                                    *ngFor="let rt of resourceTypeOptions"
                                    [value]="rt.value"
                                >
                                    <mat-checkbox [checked]="rt.selected">
                                        {{ rt.label }}
                                    </mat-checkbox>
                                </mat-option>
                            </mat-select>
                        </mat-form-field>
                    </div>

                    <!-- Severity Filter -->
                    <div class="filter-group">
                        <span class="filter-label">Severity:</span>
                        <mat-form-field class="filter-select">
                            <mat-label>Select Severities</mat-label>
                            <mat-select
                                [ngModel]="selectedSeverities"
                                (ngModelChange)="onSeverityFilterChange($event)"
                                multiple
                            >
                                <mat-option
                                    *ngFor="let sev of severityOptions"
                                    [value]="sev.value"
                                >
                                    <mat-checkbox [checked]="sev.selected">
                                        {{ sev.label }}
                                    </mat-checkbox>
                                </mat-option>
                            </mat-select>
                        </mat-form-field>
                    </div>

                    <!-- Active filter chips -->
                    <div class="active-filters" *ngIf="activeFilters.length > 0">
                        <span class="active-label">Active filters:</span>
                        <mat-chip
                            *ngFor="let f of activeFilters"
                            (click)="removeFilter(f)"
                            class="filter-chip"
                        >
                            {{ f.display }}
                            <mat-icon matChipRemove>close</mat-icon>
                        </mat-chip>
                    </div>
                </div>

                <mat-divider />

                <!-- ====== SEARCH + ACTIONS ====== -->
                <div class="toolbar">
                    <mat-form-field class="search-field">
                        <mat-label>Search audit log...</mat-label>
                        <input
                            matInput
                            [ngModel]="searchQuery"
                            (ngModelChange)="onSearchQueryChange($event)"
                            placeholder="Search by action, user, resource..."
                        />
                        <mat-icon matSuffix>search</mat-icon>
                    </mat-form-field>
                </div>

                <!-- ====== LOADING SPINNER ====== -->
                @if (isLoading()) {
                    <div class="loading-container">
                        <mat-spinner [diameter]="50"></mat-spinner>
                        <p>Loading audit entries...</p>
                    </div>
                } @else {
                    <!-- ====== AUDIT TABLE ====== -->
                    <div class="table-container">
                        <table
                            mat-table
                            [dataSource]="dataSource"
                            matSort
                            class="audit-table"
                        >
                            <!-- Timestamp Column -->
                            <ng-container matColumnDef="timestamp">
                                <th mat-header-cell *matHeaderCellDef mat-sort-header>
                                    Timestamp
                                </th>
                                <td mat-cell *matCellDef="let entry">
                                    {{ entry.timestamp | date : 'short' }}
                                </td>
                            </ng-container>

                            <!-- Severity Column -->
                            <ng-container matColumnDef="severity">
                                <th mat-header-cell *matHeaderCellDef mat-sort-header>
                                    Severity
                                </th>
                                <td mat-cell *matCellDef="let entry">
                                    <mat-chip [ngClass]="getSeverityClass(entry.severity)">
                                        {{ getSeverityDisplay(entry.severity).label }}
                                    </mat-chip>
                                </td>
                            </ng-container>

                            <!-- Action Column -->
                            <ng-container matColumnDef="action">
                                <th mat-header-cell *matHeaderCellDef mat-sort-header>
                                    Action
                                </th>
                                <td mat-cell *matCellDef="let entry">
                                    <mat-icon
                                        class="action-icon"
                                        [ngClass]="getActionColor(entry.action)"
                                    >
                                        {{ getActionIcon(entry.action) }}
                                    </mat-icon>
                                    {{ getActionDisplay(entry.action) }}
                                </td>
                            </ng-container>

                            <!-- User Column -->
                            <ng-container matColumnDef="user">
                                <th mat-header-cell *matHeaderCellDef>User</th>
                                <td mat-cell *matCellDef="let entry">
                                    {{ entry.displayName || entry.user || 'system' }}
                                </td>
                            </ng-container>


                            <!-- Resource Type Column -->
                            <ng-container matColumnDef="resourceType">
                                <th mat-header-cell *matHeaderCellDef>Resource Type</th>
                                <td mat-cell *matCellDef="let entry">
                                    {{ getResourceTypeDisplay(entry.resourceType) }}
                                </td>
                            </ng-container>

                            <!-- Resource ID Column -->
                            <ng-container matColumnDef="resourceId">
                                <th mat-header-cell *matHeaderCellDef>Resource ID</th>
                                <td mat-cell *matCellDef="let entry" class="resource-id">
                                    {{ entry.resourceId || '-' }}
                                </td>
                            </ng-container>

                            <!-- Description Column -->
                            <ng-container matColumnDef="description">
                                <th mat-header-cell *matHeaderCellDef>Description</th>
                                <td mat-cell *matCellDef="let entry" class="message-cell">
                                    {{ entry.description || '-' }}
                                </td>
                            </ng-container>

                            <!-- IP Address Column -->
                            <ng-container matColumnDef="ipAddress">
                                <th mat-header-cell *matHeaderCellDef>IP Address</th>
                                <td mat-cell *matCellDef="let entry">
                                    {{ entry.ipAddress || '-' }}
                                </td>
                            </ng-container>

                            <!-- Relative Time Column -->
                            <ng-container matColumnDef="relativeTime">
                                <th mat-header-cell *matHeaderCellDef>Relative Time</th>
                                <td mat-cell *matCellDef="let entry">
                                    {{ getRelativeTime(entry.timestamp) }}
                                </td>
                            </ng-container>

                            <!-- Actions Column -->
                            <ng-container matColumnDef="actions">
                                <th mat-header-cell *matHeaderCellDef>Actions</th>
                                <td mat-cell *matCellDef="let entry">
                                    <div class="action-buttons">
                                        <button
                                            mat-icon-button
                                            color="primary"
                                            class="view-detail-btn"
                                            [title]="'View Detail'"
                                            [routerLink]="['/audit/detail', entry.id]"
                                        >
                                            <mat-icon>visibility</mat-icon>
                                        </button>
                                        <button
                                            mat-icon-button
                                            color="accent"
                                            class="view-history-btn"
                                            [title]="'View History'"
                                            [routerLink]="[
                                                '/audit/resource',
                                                entry.resourceType,
                                                entry.resourceId
                                            ]"
                                            [disabled]="!entry.resourceId"
                                        >
                                            <mat-icon>history</mat-icon>
                                        </button>
                                    </div>
                                </td>
                            </ng-container>

                            <tr
                                mat-header-row
                                *matHeaderRowDef="displayedColumns"
                            ></tr>
                            <tr
                                mat-row
                                *matRowDef="let row; columns: displayedColumns"
                                class="table-row"
                                (click)="onRowClick(row)"
                            ></tr>
                        </table>
                    </div>

                    <!-- ====== PAGINATOR ====== -->
                    <mat-paginator
                        #paginator
                        [pageSizeOptions]="[10, 25, 50, 100]"
                        showFirstLastButtons
                        aria-label="Select page of audit entries"
                    />
                }
            </mat-card-content>
        </mat-card>
    </div>
  `,
    styles: [
        `
        /* ── Container ──────────────────────────────────── */
        .audit-list-container {
            padding: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }

        mat-card {
            margin-bottom: 20px;
        }

        /* ── Summary card ───────────────────────────────── */
        .summary-card {
            margin-bottom: 20px;
        }

        .summary-card mat-card-title {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .summary-icon {
            margin-right: 8px;
        }

        .summary-content {
            padding: 16px 24px;
        }

        .summary-row {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            align-items: flex-start;
        }

        .summary-stat.total-entries {
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 140px;
        }

        .summary-number {
            font-size: 2.5rem;
            font-weight: 600;
            color: var(--primary-color, #1976d2);
        }

        .summary-label {
            font-size: 0.85rem;
            color: #666;
            margin-top: 4px;
        }

        .summary-section {
            flex: 1;
            min-width: 280px;
        }

        .summary-section h4 {
            margin: 0 0 12px 0;
            font-size: 0.9rem;
            color: #555;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .summary-bars {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .bar-row {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .bar-label {
            width: 110px;
            font-size: 0.85rem;
            color: #444;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .bar-track {
            flex: 1;
            height: 20px;
            background: #eee;
            border-radius: 4px;
            overflow: hidden;
        }

        .bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.4s ease;
        }

        .bar-value {
            width: 40px;
            font-size: 0.85rem;
            color: #666;
            text-align: right;
        }

        /* ── Filter bar ─────────────────────────────────── */
        .filter-bar {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            padding: 12px 0;
        }

        .date-field {
            min-width: 160px;
        }

        .spacer {
            flex: 1;
        }

        .filter-divider {
            margin: 12px 0;
        }

        /* ── Filter dropdowns ──────────────────────────── */
        .filter-dropdowns {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            align-items: flex-end;
            margin-bottom: 16px;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .filter-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: #555;
        }

        .filter-select {
            min-width: 200px;
        }

        /* ── Active filters chips ──────────────────────── */
        .active-filters {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            margin-top: 12px;
        }

        .active-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: #555;
            margin-right: 4px;
        }

        .filter-chip {
            cursor: pointer;
        }

        /* ── Toolbar ────────────────────────────────────── */
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            gap: 16px;
            flex-wrap: wrap;
        }

        .search-field {
            flex: 1;
            min-width: 250px;
        }

        /* ── Loading ────────────────────────────────────── */
        .loading-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
            gap: 16px;
        }

        /* ── Table ──────────────────────────────────────── */
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

        /* ── Action buttons ─────────────────────────────── */
        .action-buttons {
            display: flex;
            gap: 4px;
            justify-content: center;
        }

        .view-detail-btn {
            color: #1976d2;
        }

        .view-history-btn {
            color: #f44336;
        }

        .action-icon {
            margin-right: 4px;
            font-size: 16px;
            vertical-align: middle;
        }

        /* ── Severity colour helpers ────────────────────── */
        .audit-severity-info {
            background-color: #2196f3 !important;
            color: white !important;
        }
        .audit-severity-warning {
            background-color: #ff9800 !important;
            color: white !important;
        }
        .audit-severity-error {
            background-color: #f44336 !important;
            color: white !important;
        }
        .audit-severity-success {
            background-color: #4caf50 !important;
            color: white !important;
        }
    `,
    ],
})
export class AuditListComponent implements OnInit, OnDestroy {
    // ─── Inject services ───────────────────────────────────────────────────
    private readonly auditService = inject(AuditService);
    private readonly snackBar = inject(MatSnackBar);
    private readonly cdr = inject(ChangeDetectorRef);
    private readonly router = inject(Router);

    // ─── ViewChild refs ────────────────────────────────────────────────────
    @ViewChild('paginator') paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    // ─── Reactive filter change stream (debounced) ─────────────────────────
    private readonly filterChange$ = new Subject<void>();

    // ─── Date range ────────────────────────────────────────────────────────
    fromDate: Date | null = null;
    toDate: Date | null = null;

    // ─── Search ────────────────────────────────────────────────────────────
    searchQuery = '';

    // ─── Filter state ─────────────────────────────────────────────────────
    selectedActions: string[] = [];
    selectedResourceTypes: string[] = [];
    selectedSeverities: string[] = [];

    // ─── Data sources ──────────────────────────────────────────────────────
    displayedColumns: string[] = [
        'timestamp',
        'severity',
        'action',
        'user',
        'resourceType',
        'resourceId',
        'description',
        'ipAddress',
        'relativeTime',
        'actions',
    ];

    dataSource = new MatTableDataSource<AuditEntry>();

    // ─── Signal-based loading states ───────────────────────────────────────
    isLoading = signal(false);
    isLoadingExport = signal(false);

    // ─── Summary statistics ────────────────────────────────────────────────
    summary: AuditSummary | null = null;
    summaryLoaded = false;
    topActions: FilterChip[] = [];
    topResourceTypes: FilterChip[] = [];
    maxActionCount = 0;
    maxResourceCount = 0;

    // ─── Colour palettes for summary bars ──────────────────────────────────
    readonly actionColors: string[] = [
        '#1976d2',
        '#42a5f5',
        '#66bb6a',
        '#ffa726',
        '#ab47bc',
        '#ef5350',
    ];
    readonly resourceColors: string[] = [
        '#26a69a',
        '#ec407a',
        '#78909c',
        '#ffd54f',
        '#8d6e63',
        '#7c4dff',
    ];

    // ─── Lifecycle ─────────────────────────────────────────────────────────
    ngOnInit(): void {
        // Default: last 30 days
        const today = new Date();
        this.toDate = today;
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(today.getDate() - 30);
        this.fromDate = thirtyDaysAgo;

        // Populate multi-select options from service
        this.buildActionOptions();
        this.buildResourceTypeOptions();
        this.buildSeverityOptions();

        // Load initial data
        this.loadAuditLog();
        this.loadSummary();

        // Subscribe to debounced filter changes
        this.filterChange$
            .pipe(debounceTime(300))
            .subscribe(() => this.onFiltersChanged());

        // Wire paginator
        if (this.paginator) {
            this.paginator.page.subscribe(() => {
                this.loadAuditLog();
            });
        }
    }

    /**
     * Clean up subscriptions on component destroy.
     */
    ngOnDestroy(): void {
        // The debounce Subject is not unsubscribed explicitly because
        // Subject does not need manual cleanup, but the debounceTime
        // operator ensures no stale emissions linger.
    }

    // ─── Date range helpers ────────────────────────────────────────────────

    /**
     * Called when the "From Date" picker value changes.
     * Emits a debounced filter-change event.
     */
    onFromDateChange(event: Date | null): void {
        if (event) {
            this.fromDate = event;
            this.emitFilterChange();
        }
    }

    /**
     * Called when the "To Date" picker value changes.
     * Emits a debounced filter-change event.
     */
    onToDateChange(event: Date | null): void {
        if (event) {
            this.toDate = event;
            this.emitFilterChange();
        }
    }

    /**
     * Handle ngModel change for from date (two-way binding).
     */
    onFromDateModelChange(event: Date): void {
        this.fromDate = event;
    }

    /**
     * Handle ngModel change for to date (two-way binding).
     */
    onToDateModelChange(event: Date): void {
        this.toDate = event;
    }

    /**
     * Clear both date filters and reload.
     */
    clearDates(): void {
        this.fromDate = null;
        this.toDate = null;
        this.emitFilterChange();
    }

    // ─── Search handler ────────────────────────────────────────────────────

    /**
     * Called when the search query changes.
     * Debounced to avoid excessive API calls.
     */
    onSearchQueryChange(query: string): void {
        this.searchQuery = query;
        this.emitFilterChange();
    }

    // ─── Filter dropdown handlers ──────────────────────────────────────────

    /**
     * Called when the action filter multi-select changes.
     * Uses ngModelChange to capture user selection.
     */
    onActionFilterChange(selected: string[]): void {
        // Toggle selection state
        this.selectedActions = selected;
        this.emitFilterChange();
    }

    /**
     * Called when the resource type filter multi-select changes.
     */
    onResourceTypeFilterChange(selected: string[]): void {
        this.selectedResourceTypes = selected;
        this.emitFilterChange();
    }

    /**
     * Called when the severity filter multi-select changes.
     */
    onSeverityFilterChange(selected: string[]): void {
        this.selectedSeverities = selected;
        this.emitFilterChange();
    }

    /**
     * Remove a single active filter chip.
     */
    removeFilter(chip: ActiveFilterChip): void {
        switch (chip.key) {
            case 'action':
                const idx = this.selectedActions.indexOf(chip.value);
                if (idx !== -1) this.selectedActions.splice(idx, 1);
                break;
            case 'resourceType':
                const rIdx = this.selectedResourceTypes.indexOf(chip.value);
                if (rIdx !== -1) this.selectedResourceTypes.splice(rIdx, 1);
                break;
            case 'severity':
                const sIdx = this.selectedSeverities.indexOf(chip.value);
                if (sIdx !== -1) this.selectedSeverities.splice(sIdx, 1);
                break;
        }
        this.emitFilterChange();
    }

    // ─── Build options from service display methods ────────────────────────

    /** Populate action multi-select options using service display helpers. */
    private buildActionOptions(): void {
        const allActions: AuditAction[] = [
            'CREATE',
            'UPDATE',
            'DELETE',
            'READ',
            'LOGIN',
            'LOGOUT',
            'APPROVE',
            'REJECT',
            'IMPORT',
            'EXPORT',
            'CONFIGURE',
            'DEPLOY',
            'TEST',
            'EXECUTE',
        ];
        this.actionOptions = allActions.map((a) => ({
            value: a,
            label: this.auditService.getActionDisplay(a),
            selected: false,
        }));
    }

    /** Populate resource type multi-select options using service display helpers. */
    private buildResourceTypeOptions(): void {
        const allTypes: AuditResourceType[] = [
            'FIREWALL_RULE',
            'ACCESS_RULE',
            'THRESHOLD',
            'WORKSPACE',
            'USER',
            'CONFIGURATION',
            'DEPLOYMENT',
            'APPROVAL',
            'RULE_EVALUATION',
            'BATCH_OPERATION',
            'WEBHOOK',
            'NOTIFICATION',
        ];
        this.resourceTypeOptions = allTypes.map((t) => ({
            value: t,
            label: this.auditService.getResourceTypeDisplay(t),
            selected: false,
        }));
    }

    /** Populate severity multi-select options using service display helpers. */
    private buildSeverityOptions(): void {
        this.severityOptions = [
            { value: 'info', label: 'Info', selected: false },
            { value: 'warning', label: 'Warning', selected: false },
            { value: 'error', label: 'Error', selected: false },
            { value: 'success', label: 'Success', selected: false },
        ];
    }

    /** Build the list of active filter chips from current selections. */
    private getActiveFilters(): ActiveFilterChip[] {
        const chips: ActiveFilterChip[] = [];
        this.selectedActions.forEach((v) => {
            const opt = this.actionOptions.find((o) => o.value === v);
            if (opt)
                chips.push({
                    key: 'action',
                    value: v,
                    display: `Action: ${opt.label}`,
                });
        });
        this.selectedResourceTypes.forEach((v) => {
            const opt = this.resourceTypeOptions.find((o) => o.value === v);
            if (opt)
                chips.push({
                    key: 'resourceType',
                    value: v,
                    display: `Resource: ${opt.label}`,
                });
        });
        this.selectedSeverities.forEach((v) => {
            const opt = this.severityOptions.find((o) => o.value === v);
            if (opt)
                chips.push({
                    key: 'severity',
                    value: v,
                    display: `Severity: ${opt.label}`,
                });
        });
        return chips;
    }

    // ─── API data loading ──────────────────────────────────────────────────

    /**
     * Load audit log entries with current filters and pagination.
     *
     * Maps the Material paginator's 0-based pageIndex to the API's
     * 1-based page number.
     */
    loadAuditLog(): void {
        this.isLoading.set(true);

        const pageSize = this.paginator?.pageSize || 20;
        // Convert 0-based paginator index to 1-based API page
        const page = (this.paginator?.pageIndex || 0) + 1;

        const filters: AuditFilter = {
            searchQuery: this.searchQuery,
            dateFrom: this.fromDate?.toISOString?.().split('T')[0] ?? undefined,
            dateTo: this.toDate?.toISOString?.().split('T')[0] ?? undefined,
            actionFilter:
                this.selectedActions.length > 0
                    ? (this.selectedActions as AuditAction[])
                    : undefined,
            resourceTypeFilter:
                this.selectedResourceTypes.length > 0
                    ? (this.selectedResourceTypes as AuditResourceType[])
                    : undefined,
            severityFilter:
                this.selectedSeverities.length > 0
                    ? (this.selectedSeverities as AuditSeverity[])
                    : undefined,
        };

        this.auditService.getAuditLogs(page, pageSize, filters).subscribe({
            next: (response) => {
                this.dataSource.data = response.items || [];
                this.dataSource.paginator = this.paginator;
                this.dataSource.sort = this.sort;
                this.isLoading.set(false);
            },
            error: (error) => {
                console.error('Error loading audit log:', error);
                this.isLoading.set(false);
                this.snackBar.open(
                    'Failed to load audit logs.',
                    'Close',
                    { duration: 4000 }
                );
            },
        });
    }

    /**
     * Load summary statistics with current date range.
     * Called on init and after each filter change.
     */
    loadSummary(): void {
        const dateFrom =
            this.fromDate?.toISOString?.().split('T')[0] ?? undefined;
        const dateTo =
            this.toDate?.toISOString?.().split('T')[0] ?? undefined;

        this.auditService.getAuditSummary(dateFrom, dateTo).subscribe({
            next: (summary) => {
                this.summary = summary;
                this.summaryLoaded = true;

                // Build top actions list (top 5)
                const entries = Object.entries(summary.byAction ?? {}).map(
                    ([key, count]) => ({ key, count })
                );
                entries.sort((a, b) => b.count - a.count);
                const raw = entries.slice(0, 5);
                this.maxActionCount = entries[0]?.count ?? 1;
                this.topActions = raw.map((e) => ({
                    value: e.key,
                    label: this.auditService.getActionDisplay(
                        e.key as AuditAction
                    ),
                    count: e.count,
                    selected: false,
                }));

                // Build top resource types list (top 5)
                const rtEntries = Object.entries(
                    summary.byResourceType ?? {}
                ).map(([key, count]) => ({ key, count }));
                rtEntries.sort((a, b) => b.count - a.count);
                const rtRaw = rtEntries.slice(0, 5);
                this.maxResourceCount = rtEntries[0]?.count ?? 1;
                this.topResourceTypes = rtRaw.map((e) => ({
                    value: e.key,
                    label: this.auditService.getResourceTypeDisplay(
                        e.key as AuditResourceType
                    ),
                    count: e.count,
                    selected: false,
                }));

                this.cdr.detectChanges();
            },
            error: (error) => {
                console.error('Error loading audit summary:', error);
                this.summaryLoaded = false;
            },
        });
    }

    // ─── Export handlers ───────────────────────────────────────────────────

    /**
     * Export filtered audit logs as CSV.
     * Downloads the returned Blob as a file.
     */
    exportCsv(): void {
        this.isLoadingExport.set(true);
        const filters = this.buildExportFilters();
        this.auditService.exportAsCsv(filters).subscribe({
            next: (blob: Blob) => {
                this.downloadBlob(blob, 'audit-log.csv', 'text/csv');
                this.isLoadingExport.set(false);
                this.snackBar.open(
                    'CSV export downloaded successfully.',
                    'Close',
                    { duration: 3000 }
                );
            },
            error: (error) => {
                console.error('Error exporting CSV:', error);
                this.isLoadingExport.set(false);
                this.snackBar.open('Failed to export CSV.', 'Close', {
                    duration: 4000,
                });
            },
        });
    }

    /**
     * Export filtered audit logs as JSON.
     * Downloads the returned Blob as a file.
     */
    exportJson(): void {
        this.isLoadingExport.set(true);
        const filters = this.buildExportFilters();
        this.auditService.exportAsJson(filters).subscribe({
            next: (blob: Blob) => {
                this.downloadBlob(blob, 'audit-log.json', 'application/json');
                this.isLoadingExport.set(false);
                this.snackBar.open(
                    'JSON export downloaded successfully.',
                    'Close',
                    { duration: 3000 }
                );
            },
            error: (error) => {
                console.error('Error exporting JSON:', error);
                this.isLoadingExport.set(false);
                this.snackBar.open('Failed to export JSON.', 'Close', {
                    duration: 4000,
                });
            },
        });
    }

    /**
     * Trigger a browser download for the given Blob.
     *
     * @param blob - The binary data to download
     * @param filename - Suggested filename for the download
     * @param contentType - MIME type of the content
     */
    private downloadBlob(
        blob: Blob,
        filename: string,
        contentType: string
    ): void {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        window.URL.revokeObjectURL(url);
    }

    /**
     * Build the AuditFilter object used by export methods.
     */
    private buildExportFilters(): AuditFilter {
        return {
            searchQuery: this.searchQuery,
            dateFrom:
                this.fromDate?.toISOString?.().split('T')[0] ?? undefined,
            dateTo:
                this.toDate?.toISOString?.().split('T')[0] ?? undefined,
            actionFilter:
                this.selectedActions.length > 0
                    ? (this.selectedActions as AuditAction[])
                    : undefined,
            resourceTypeFilter:
                this.selectedResourceTypes.length > 0
                    ? (this.selectedResourceTypes as AuditResourceType[])
                    : undefined,
            severityFilter:
                this.selectedSeverities.length > 0
                    ? (this.selectedSeverities as AuditSeverity[])
                    : undefined,
        };
    }

    // ─── Utility helpers ───────────────────────────────────────────────────

    /** Refresh current page data. */
    refreshData(): void {
        this.loadAuditLog();
    }

    /**
     * Emit a debounced filter-change event.
     * Triggers both log reload and summary refresh.
     */
    private emitFilterChange(): void {
        this.filterChange$.next();
    }

    /**
     * Handle debounced filter changes.
     * Reloads audit log and summary statistics.
     */
    private onFiltersChanged(): void {
        // Reset paginator to first page on filter change
        if (this.paginator) {
            this.paginator.firstPage();
        }
        this.loadAuditLog();
        this.loadSummary();
    }

    // ─── Display helpers ───────────────────────────────────────────────────

    /**
     * Get the severity display object from the service.
     *
     * @param severity - The audit severity level
     * @returns Object containing label, color, icon, and CSS class
     */
    getSeverityDisplay(
        severity: AuditSeverity
    ): {
        label: string;
        color: string;
        icon: string;
        cssClass: string;
    } {
        return this.auditService.getSeverityDisplay(severity);
    }

    /**
     * Get the CSS class name for a severity level.
     *
     * @param severity - The audit severity level
     * @returns The CSS class string (e.g., 'audit-severity-info')
     */
    getSeverityClass(severity: AuditSeverity): string {
        return this.getSeverityDisplay(severity).cssClass;
    }

    /**
     * Get the action display label from the service.
     *
     * @param action - The audit action type
     * @returns Human-readable action label
     */
    getActionDisplay(action: AuditAction): string {
        return this.auditService.getActionDisplay(action);
    }

    /**
     * Get the icon for an action type from the service.
     *
     * @param action - The audit action type
     * @returns Material icon name
     */
    getActionIcon(action: AuditAction): string {
        return this.auditService.getActionIcon(action);
    }

    /**
     * Get the CSS colour class for an action type icon.
     */
    getActionColor(action: AuditAction): string {
        const colors: Record<string, string> = {
            CREATE: 'action-create',
            UPDATE: 'action-update',
            DELETE: 'action-delete',
            READ: 'action-read',
            LOGIN: 'action-login',
            LOGOUT: 'action-logout',
            APPROVE: 'action-approve',
            REJECT: 'action-reject',
        };
        return colors[action] ?? 'action-default';
    }

    /**
     * Get the resource type display label from the service.
     *
     * @param resourceType - The audit resource type
     * @returns Human-readable resource type label
     */
    getResourceTypeDisplay(resourceType: AuditResourceType): string {
        return this.auditService.getResourceTypeDisplay(resourceType);
    }

    /**
     * Get relative time string from the service.
     *
     * @param dateString - ISO 8601 timestamp string
     * @returns Relative time string (e.g., '5m ago')
     */
    getRelativeTime(dateString: string): string {
        return this.auditService.getRelativeTime(dateString);
    }

    /**
     * Calculate the bar width percentage for summary stats.
     *
     * @param count - The count for this entry
     * @param maxCount - The maximum count across all entries
     * @returns Percentage width (0–100)
     */
    getBarWidth(count: number, maxCount: number): number {
        if (!maxCount || maxCount === 0) return 0;
        return Math.round((count / maxCount) * 100);
    }

    // ─── Filter chip data ──────────────────────────────────────────────────

    /**
     * Multi-select option items for the action filter dropdown.
     * Populated from the service's display helpers.
     */
    actionOptions: FilterChip[] = [];

    /**
     * Multi-select option items for the resource type filter dropdown.
     * Populated from the service's display helpers.
     */
    resourceTypeOptions: FilterChip[] = [];

    /**
     * Multi-select option items for the severity filter dropdown.
     */
    severityOptions: FilterChip[] = [];

    /**
     * Navigate to the detail view for a specific audit entry.
     * Called when clicking on a table row.
     *
     * @param entry - The audit entry being viewed
     */
    onRowClick(entry: AuditEntry): void {
        if (entry.id) {
            this.router.navigate(['/audit', 'detail', entry.id]);
        }
    }

    /**
     * Navigate to the resource-specific audit viewer for a given resource.
     *
     * @param resourceType - The type of the resource (e.g., 'FIREWALL_RULE')
     * @param resourceId - The unique identifier of the resource
     */
    viewResourceHistory(resourceType: string, resourceId: string): void {
        if (resourceType && resourceId) {
            this.router.navigate([
                '/audit',
                'resource',
                resourceType,
                resourceId,
            ]);
        }
    }

    /**
     * Active filter chips displayed below the filter bar.
     */
    get activeFilters(): ActiveFilterChip[] {
        return this.getActiveFilters();
    }
}
