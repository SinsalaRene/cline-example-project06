/**
 * Audit Detail Component
 *
 * A standalone page component that displays detailed information about a single
 * audit log entry, identified by its ID in the route parameters. Features a
 * card-based layout with formatted JSON diff for old/new values, severity badge,
 * action and resource type labels, timestamp formatting, and a back navigation.
 *
 * # Features
 *
 * - Displays all fields of a single audit entry in a structured layout
 * - Shows `old_value` and `new_value` as formatted JSON diff side-by-side
 * - Uses a before/after visual comparison for the diff
 * - Shows metadata: timestamp (formatted), user, IP address, correlation ID
 * - Has a "Back" button to return to audit list
 * - Shows severity badge using `getSeverityDisplay()`
 * - Shows action label using `getActionDisplay()`
 * - Shows resource type label using `getResourceTypeDisplay()`
 * - Uses `formatTimestamp()` and `getRelativeTime()` for time display
 * - Loading spinner while data is being fetched
 * - Error state with retry button if fetch fails
 *
 * # Routing
 *
 * Route: `/audit/detail/:id`
 *
 * @module audit-detail.component
 * @author Audit Module Team
 */

import { Component, OnInit } from '@angular/core';
import { CommonModule, DatePipe, NgIf, NgFor, NgClass } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';

import { AuditService } from '../services/audit.service';
import {
    AuditEntry,
    AuditAction,
    AuditResourceType,
    AuditSeverity,
    AuditChange
} from '../models/audit.model';

/** Internal model for tracking changes with formatted display values. */
interface ChangeDisplay {
    field: string;
    oldValue: string;
    newValue: string;
    isAdded: boolean;
    isRemoved: boolean;
    isModified: boolean;
    description?: string;
}

@Component({
    selector: 'app-audit-detail',
    standalone: true,
    imports: [
        CommonModule,
        DatePipe,
        NgIf,
        NgFor,
        NgClass,
        RouterModule,
        MatButtonModule,
        MatIconModule,
        MatCardModule,
        MatDividerModule,
        MatChipsModule,
        MatProgressSpinnerModule,
        MatTabsModule,
        MatExpansionModule,
    ],
    providers: [DatePipe],
    template: `
        <div class="detail-page" *ngIf="entry && !isLoading">
            <!-- Back button -->
            <div class="back-bar">
                <button mat-stroked-button color="primary" routerLink="/audit">
                    <mat-icon>arrow_back</mat-icon>
                    Back to Audit Log
                </button>
                <span class="entry-id-badge">{{ entry.id }}</span>
            </div>

            <!-- Entry header -->
            <mat-card class="entry-header-card">
                <div class="entry-header-content">
                    <div class="entry-header-left">
                        <h1 class="entry-title">
                            <mat-icon class="action-icon">{{ getActionIcon(entry.action) }}</mat-icon>
                            {{ getActionDisplay(entry.action) }}
                        </h1>
                        <p class="entry-description">{{ entry.description }}</p>
                    </div>
                    <div class="entry-header-right">
                        <span class="severity-badge" [ngClass]="getSeverityDisplay(entry.severity).cssClass">
                            <mat-icon>{{ getSeverityDisplay(entry.severity).icon }}</mat-icon>
                            {{ getSeverityDisplay(entry.severity).label }}
                        </span>
                        <span class="resource-badge">
                            <mat-icon>{{ getResourceTypeIcon(entry.resourceType) }}</mat-icon>
                            {{ getResourceTypeDisplay(entry.resourceType) }}
                        </span>
                        <span class="result-badge" [class.success]="entry.success" [class.failure]="!entry.success">
                            <mat-icon>{{ entry.success ? 'check_circle' : 'cancel' }}</mat-icon>
                            {{ entry.success ? 'Success' : 'Failed' }}
                        </span>
                    </div>
                </div>
                <mat-divider />
                <div class="entry-meta">
                    <div class="meta-item">
                        <mat-icon class="meta-icon">schedule</mat-icon>
                        <span>{{ entry.timestamp | date:'medium' }} ({{ getRelativeTime(entry.timestamp) }})</span>
                    </div>
                    <div class="meta-item" *ngIf="entry.user">
                        <mat-icon class="meta-icon">person</mat-icon>
                        <span>{{ entry.displayName || entry.user }}</span>
                    </div>
                    <div class="meta-item" *ngIf="entry.ipAddress">
                        <mat-icon class="meta-icon">network_cell</mat-icon>
                        <span>{{ entry.ipAddress }}</span>
                    </div>
                    <div class="meta-item" *ngIf="entry.requestId">
                        <mat-icon class="meta-icon">link</mat-icon>
                        <span>Correlation: {{ entry.requestId }}</span>
                    </div>
                    <div class="meta-item" *ngIf="entry.httpMethod">
                        <span class="http-method-badge method-{{ entry.httpMethod }}">{{ entry.httpMethod }}</span>
                        <span class="path-value">{{ entry.path || '' }}</span>
                    </div>
                    <div class="meta-item" *ngIf="entry.statusCode">
                        <span class="status-code-badge status-{{ entry.statusCode }}">{{ entry.statusCode }}</span>
                    </div>
                    <div class="meta-item" *ngIf="entry.durationMs !== undefined">
                        <mat-icon class="meta-icon">timer</mat-icon>
                        <span>{{ formatDuration(entry.durationMs) }}</span>
                    </div>
                </div>
            </mat-card>

            <!-- Tabbed content -->
            <mat-tab-group class="detail-tabs">
                <!-- Changes Tab: Diff view -->
                <mat-tab label="Changes" *ngIf="entry.changes?.length">
                    <div class="changes-container">
                        <div class="diff-header">
                            <span class="diff-label-old">Old Value</span>
                            <span class="diff-arrow">→</span>
                            <span class="diff-label-new">New Value</span>
                        </div>
                        <ng-container *ngFor="let change of entry.changes">
                            <div class="change-diff-card" *ngIf="change.field">
                                <div class="change-field-label">{{ change.field }}</div>
                                <div class="change-tags">
                                    <span class="change-tag" *ngIf="change.oldValue !== undefined && change.newValue !== undefined" class="tag-modified">Modified</span>
                                    <span class="change-tag tag-added" *ngIf="change.oldValue === undefined && change.newValue !== undefined">Added</span>
                                    <span class="change-tag tag-removed" *ngIf="change.oldValue !== undefined && change.newValue === undefined">Removed</span>
                                </div>
                                <div class="diff-content" *ngIf="change.oldValue !== undefined && change.newValue !== undefined">
                                    <div class="diff-panel diff-old">
                                        <pre class="diff-value">{{ formatValue(change.oldValue) }}</pre>
                                    </div>
                                    <div class="diff-panel diff-new">
                                        <pre class="diff-value">{{ formatValue(change.newValue) }}</pre>
                                    </div>
                                </div>
                                <div class="single-diff" *ngIf="(change.oldValue === undefined && change.newValue !== undefined) || (change.oldValue !== undefined && change.newValue === undefined)">
                                    <pre class="diff-value">{{ formatValue(change.oldValue ?? change.newValue) }}</pre>
                                </div>
                                <div class="change-description" *ngIf="change.description">
                                    {{ change.description }}
                                </div>
                                <mat-divider class="change-divider" *ngIf="change.field" />
                            </div>
                        </ng-container>
                    </div>
                </mat-tab>

                <!-- Details Tab -->
                <mat-tab label="Details">
                    <div class="details-content">
                        <!-- Request Details -->
                        <mat-expansion-panel class="detail-panel" *ngIf="entry.details" expanded>
                            <mat-expansion-panel-header>
                                <mat-panel-title>
                                    <mat-icon>input</mat-icon>
                                    Request Details
                                </mat-panel-title>
                            </mat-expansion-panel-header>
                            <div class="panel-content">
                                <ng-container *ngIf="entry.details?.requestBody">
                                    <div class="detail-item">
                                        <div class="detail-label">Request Body</div>
                                        <pre class="json-value">{{ formatValue(entry.details.requestBody) }}</pre>
                                    </div>
                                </ng-container>
                                <ng-container *ngIf="entry.details?.queryParams">
                                    <div class="detail-item">
                                        <div class="detail-label">Query Parameters</div>
                                        <pre class="json-value">{{ formatValue(entry.details.queryParams) }}</pre>
                                    </div>
                                </ng-container>
                                <ng-container *ngIf="entry.details?.headers">
                                    <div class="detail-item">
                                        <div class="detail-label">Headers</div>
                                        <pre class="json-value">{{ formatValue(entry.details.headers) }}</pre>
                                    </div>
                                </ng-container>
                                <ng-container *ngIf="entry.details?.userAgent">
                                    <div class="detail-item">
                                        <div class="detail-label">User Agent</div>
                                        <div class="detail-value">{{ entry.details.userAgent }}</div>
                                    </div>
                                </ng-container>
                            </div>
                        </mat-expansion-panel>

                        <!-- Response Details -->
                        <mat-expansion-panel class="detail-panel" *ngIf="entry.details?.responseBody" expanded>
                            <mat-expansion-panel-header>
                                <mat-panel-title>
                                    <mat-icon>output</mat-icon>
                                    Response Details
                                </mat-panel-title>
                            </mat-expansion-panel-header>
                            <div class="panel-content">
                                <pre class="json-value">{{ formatValue(entry.details?.responseBody) }}</pre>
                            </div>
                        </mat-expansion-panel>

                        <!-- Operation Result -->
                        <mat-expansion-panel class="detail-panel" *ngIf="entry.result" expanded>
                            <mat-expansion-panel-header>
                                <mat-panel-title>
                                    <mat-icon>assignment</mat-icon>
                                    Operation Result
                                </mat-panel-title>
                            </mat-expansion-panel-header>
                            <div class="panel-content">
                                <div class="detail-item">
                                    <div class="detail-label">Status</div>
                                    <span class="result-badge" [class.success]="entry.result?.success" [class.failure]="!entry.result?.success">
                                        <mat-icon>{{ entry.result?.success ? 'check_circle' : 'cancel' }}</mat-icon>
                                        {{ entry.result?.success ? 'Success' : 'Failed' }}
                                    </span>
                                </div>
                                <div class="detail-item" *ngIf="entry.result?.errorMessage">
                                    <div class="detail-label">Error</div>
                                    <div class="detail-value error">{{ entry.result.errorMessage }}</div>
                                </div>
                                <div class="detail-item" *ngIf="entry.result?.affectedCount !== undefined">
                                    <div class="detail-label">Affected Items</div>
                                    <div class="detail-value">{{ entry.result.affectedCount }}</div>
                                </div>
                                <div class="detail-item" *ngIf="entry.result?.operationId">
                                    <div class="detail-label">Operation ID</div>
                                    <div class="detail-value">{{ entry.result.operationId }}</div>
                                </div>
                            </div>
                        </mat-expansion-panel>

                        <!-- Raw Metadata -->
                        <mat-expansion-panel class="detail-panel" *ngIf="entry.metadata" expanded>
                            <mat-expansion-panel-header>
                                <mat-panel-title>
                                    <mat-icon>code</mat-icon>
                                    Raw Metadata
                                </mat-panel-title>
                            </mat-expansion-panel-header>
                            <div class="panel-content">
                                <pre class="json-value">{{ formatValue(entry.metadata) }}</pre>
                            </div>
                        </mat-expansion-panel>

                        <!-- Full Entry JSON -->
                        <mat-expansion-panel class="detail-panel">
                            <mat-expansion-panel-header>
                                <mat-panel-title>
                                    <mat-icon>source</mat-icon>
                                    Full Entry JSON
                                </mat-panel-title>
                            </mat-expansion-panel-header>
                            <div class="panel-content">
                                <pre class="json-value">{{ formatValue(entry) }}</pre>
                            </div>
                        </mat-expansion-panel>
                    </div>
                </mat-tab>
            </mat-tab-group>
        </div>

        <!-- Loading state -->
        <div class="loading-state" *ngIf="isLoading">
            <mat-progress-spinner mode="indeterminate" [diameter]="50"></mat-progress-spinner>
            <p>Loading audit entry details...</p>
        </div>

        <!-- Error state -->
        <div class="error-state" *ngIf="loadError">
            <mat-icon class="error-icon">error_outline</mat-icon>
            <h2>Failed to Load Entry</h2>
            <p>{{ loadError }}</p>
            <button mat-raised-button color="primary" (click)="loadEntry()">
                <mat-icon>refresh</mat-icon>
                Retry
            </button>
            <button mat-stroked-button routerLink="/audit">
                <mat-icon>arrow_back</mat-icon>
                Back to Audit Log
            </button>
        </div>

        <!-- Not found state -->
        <div class="not-found" *ngIf="!isLoading && !loadError && !entry">
            <mat-icon class="not-found-icon">not_found</mat-icon>
            <h2>Entry Not Found</h2>
            <p>The audit entry you're looking for does not exist or has been removed.</p>
            <button mat-raised-button color="primary" routerLink="/audit">
                <mat-icon>home</mat-icon>
                Back to Audit Log
            </button>
        </div>
    `,
    styles: [`
        /* ── Page layout ──────────────────────────────────────── */
        .detail-page {
            padding: 24px;
            max-width: 1200px;
            margin: 0 auto;
        }

        /* ── Back bar ─────────────────────────────────────────── */
        .back-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .entry-id-badge {
            font-family: monospace;
            font-size: 13px;
            color: #666;
            background: #f5f5f5;
            padding: 4px 10px;
            border-radius: 4px;
        }

        /* ── Entry header card ────────────────────────────────── */
        .entry-header-card {
            margin-bottom: 20px;
        }

        .entry-header-content {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 16px;
            gap: 16px;
        }

        .entry-header-left {
            flex: 1;
        }

        .entry-title {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 0 0 8px 0;
            font-size: 1.25rem;
            font-weight: 600;
        }

        .action-icon {
            color: var(--primary-color, #1976d2);
        }

        .entry-description {
            margin: 0;
            color: #555;
            font-size: 0.95rem;
        }

        .entry-header-right {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: flex-end;
        }

        /* ── Badges ───────────────────────────────────────────── */
        .severity-badge,
        .resource-badge,
        .result-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 10px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 600;
        }

        .severity-badge mat-icon,
        .resource-badge mat-icon,
        .result-badge mat-icon {
            font-size: 16px;
            width: 16px;
            height: 16px;
        }

        .result-badge.success { background: #e8f5e9; color: #2e7d32; }
        .result-badge.failure { background: #ffebee; color: #c62828; }

        .resource-badge {
            background: #f3e5f5;
            color: #7b1fa2;
        }

        /* ── Meta info ────────────────────────────────────────── */
        .entry-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            padding: 12px 16px;
            font-size: 13px;
            color: #666;
        }

        .meta-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .meta-icon {
            font-size: 16px;
            width: 16px;
            height: 16px;
            color: #999;
        }

        .http-method-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            font-family: monospace;
            margin-right: 6px;
        }

        .method-GET { background: #e3f2fd; color: #1565c0; }
        .method-POST { background: #e8f5e9; color: #2e7d32; }
        .method-PUT { background: #fff3e0; color: #ef6c00; }
        .method-DELETE { background: #ffebee; color: #c62828; }
        .method-PATCH { background: #f3e5f5; color: #7b1fa2; }

        .path-value {
            font-family: monospace;
            font-size: 12px;
            color: #666;
            word-break: break-all;
        }

        .status-code-badge {
            font-family: monospace;
            font-size: 12px;
            padding: 2px 8px;
            border-radius: 4px;
        }

        .status-200 { background: #e8f5e9; color: #2e7d32; }
        .status-201 { background: #e8f5e9; color: #2e7d32; }
        .status-400 { background: #fff3e0; color: #ef6c00; }
        .status-401 { background: #ffebee; color: #c62828; }
        .status-403 { background: #ffebee; color: #c62828; }
        .status-404 { background: #ffebee; color: #c62828; }
        .status-500 { background: #ffebee; color: #c62828; }

        /* ── Tabs ──────────────────────────────────────────────── */
        ::ng-deep .detail-tabs .mat-tab-group {
            border-radius: 8px;
            overflow: hidden;
        }

        .changes-container {
            padding: 16px;
        }

        .diff-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding: 8px 12px;
            background: #f5f5f5;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            color: #666;
        }

        .diff-arrow {
            color: #999;
            font-size: 18px;
        }

        .diff-label-old, .diff-label-new {
            font-weight: 700;
            color: #333;
        }

        .change-diff-card {
            padding: 12px;
            margin-bottom: 8px;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
        }

        .change-field-label {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 8px;
            color: #333;
        }

        .change-tags {
            display: flex;
            gap: 4px;
            margin-bottom: 8px;
        }

        .change-tag {
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            background: #e0e0e0;
            color: #666;
        }

        .tag-added {
            background: #e8f5e9;
            color: #2e7d32;
        }

        .tag-removed {
            background: #ffebee;
            color: #c62828;
        }

        .diff-content {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: 12px;
            margin-top: 8px;
        }

        .diff-panel {
            padding: 8px;
            background: #f9f9f9;
            border-radius: 4px;
            border: 1px solid #e0e0e0;
            max-height: 250px;
            overflow: auto;
        }

        .diff-old {
            border-left: 3px solid #ff9800;
        }

        .diff-new {
            border-left: 3px solid #4caf50;
        }

        .diff-value {
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-all;
            margin: 0;
        }

        .single-diff {
            padding: 8px;
            background: #f9f9f9;
            border-radius: 4px;
            border: 1px solid #e0e0e0;
            max-height: 250px;
            overflow: auto;
        }

        .change-description {
            margin-top: 8px;
            font-size: 13px;
            color: #666;
            font-style: italic;
        }

        .change-divider {
            margin: 12px 0;
        }

        /* ── Details tab ──────────────────────────────────────── */
        .details-content {
            padding: 16px;
        }

        .detail-panel {
            margin-bottom: 8px;
            border-radius: 8px !important;
            overflow: hidden;
        }

        .panel-content {
            padding: 12px;
        }

        .json-value {
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            background: #f5f5f5;
            padding: 12px;
            border-radius: 4px;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 400px;
            overflow: auto;
            margin: 0;
        }

        .detail-item {
            margin-bottom: 12px;
        }

        .detail-label {
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .detail-value {
            font-size: 14px;
            color: #333;
        }

        .detail-value.error {
            color: #c62828;
            font-weight: 500;
        }

        /* ── Loading / error states ───────────────────────────── */
        .loading-state,
        .error-state,
        .not-found {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 400px;
            gap: 16px;
            text-align: center;
        }

        .error-state h2,
        .not-found h2 {
            color: #c62828;
        }

        .error-icon,
        .not-found-icon {
            font-size: 48px;
            color: #c62828;
        }

        .not-found-icon {
            color: #999;
        }

        /* ── Severity CSS class helpers ──────────────────────── */
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
    `],
})
export class AuditDetailComponent implements OnInit {
    entry: AuditEntry | null = null;
    isLoading = true;
    loadError: string | null = null;
    private entryId: string | null = null;

    constructor(
        private route: ActivatedRoute,
        private router: Router,
        private auditService: AuditService,
    ) { }

    ngOnInit(): void {
        this.entryId = this.route.snapshot.paramMap.get('id');
        if (this.entryId) {
            this.loadEntry();
        } else {
            this.isLoading = false;
            this.loadError = 'No entry ID provided in route.';
        }
    }

    /**
     * Load audit entry from backend by ID.
     */
    loadEntry(): void {
        const id = this.entryId;
        if (!id) {
            this.isLoading = false;
            this.loadError = 'No entry ID provided in route.';
            return;
        }

        this.isLoading = true;
        this.loadError = null;

        this.auditService.getAuditEntry(id).subscribe({
            next: (entry: AuditEntry) => {
                this.entry = entry;
                this.isLoading = false;
            },
            error: (err: Error) => {
                console.error('Error loading audit entry:', err);
                this.isLoading = false;
                this.loadError = err.message || 'Failed to load audit entry.';
            }
        });
    }

    /**
     * Format a value for display as formatted JSON.
     */
    formatValue(value: unknown): string {
        if (typeof value === 'string') return value;
        if (value === null || value === undefined) return 'null';
        try {
            return JSON.stringify(value, null, 2);
        } catch {
            return String(value);
        }
    }

    /**
     * Get action display label via service.
     */
    getActionDisplay(action: AuditAction): string {
        return this.auditService.getActionDisplay(action);
    }

    /**
     * Get action icon name via service.
     */
    getActionIcon(action: AuditAction): string {
        return this.auditService.getActionIcon(action);
    }

    /**
     * Get resource type display label via service.
     */
    getResourceTypeDisplay(resourceType: AuditResourceType): string {
        return this.auditService.getResourceTypeDisplay(resourceType);
    }

    /**
     * Get resource type icon via service.
     */
    getResourceTypeIcon(resourceType: AuditResourceType): string {
        return this.auditService.getResourceTypeIcon(resourceType);
    }

    /**
     * Get severity display object via service.
     */
    getSeverityDisplay(severity: AuditSeverity): { label: string; color: string; icon: string; cssClass: string } {
        return this.auditService.getSeverityDisplay(severity);
    }

    /**
     * Format timestamp via service.
     */
    formatTimestamp(dateString: string): string {
        return this.auditService.formatTimestamp(dateString);
    }

    /**
     * Get relative time string via service.
     */
    getRelativeTime(dateString: string): string {
        return this.auditService.getRelativeTime(dateString);
    }

    /**
     * Format duration in milliseconds to human-readable string.
     */
    formatDuration(ms: number): string {
        return this.auditService.formatDuration(ms);
    }
}