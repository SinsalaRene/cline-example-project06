/**
 * Audit Detail Component
 *
 * Displays detailed information about a single audit log entry.
 * Shows entry metadata, changes made, request/response details,
 * and any associated audit information.
 *
 * # Usage
 *
 * ```typescript
 * import { AuditDetailComponent } from './components/audit-detail.component';
 *
 * // Open from another component
 * this.dialog.open(AuditDetailComponent, {
 *     data: { entry: auditEntry }
 * });
 * ```
 */

import { Component, Inject, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { AuditService } from '../services/audit.service';
import { AuditEntry } from '../models/audit.model';

interface AuditDetailData {
    entry: AuditEntry;
}

@Component({
    selector: 'app-audit-detail',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatDialogModule,
        MatSnackBarModule,
        MatProgressSpinnerModule,
        MatIconModule,
        MatButtonModule,
        MatCardModule,
        MatTabsModule,
        MatExpansionModule,
        MatChipsModule,
        MatDividerModule
    ],
    template: `
        <div class="detail-dialog">
            <!-- Dialog header -->
            <div class="dialog-header">
                <div class="header-left">
                    <h2 mat-dialog-title>Audit Entry Details</h2>
                    <div class="header-badges">
                        <span class="severity-badge severity-{{ entry?.severity }}" *ngIf="entry">
                            <mat-icon *ngIf="entry?.severity === 'error'">error</mat-icon>
                            <mat-icon *ngIf="entry?.severity === 'warning'">warning</mat-icon>
                            <mat-icon *ngIf="entry?.severity === 'info'">info</mat-icon>
                            <mat-icon *ngIf="entry?.severity === 'success'">check_circle</mat-icon>
                            {{ entry?.severity | titlecase }}
                        </span>
                        <span class="result-badge" [class.success]="entry?.success" [class.failure]="!entry?.success" *ngIf="entry">
                            <mat-icon *ngIf="entry?.success">check_circle</mat-icon>
                            <mat-icon *ngIf="!entry?.success">cancel</mat-icon>
                            {{ entry?.success ? 'Success' : 'Failed' }}
                        </span>
                        <span class="action-badge" *ngIf="entry">
                            <mat-icon>{{ auditService.getActionIcon(entry.action) }}</mat-icon>
                            {{ auditService.getActionDisplay(entry.action) }}
                        </span>
                    </div>
                </div>
                <button mat-icon-button mat-dialog-close>
                    <mat-icon>close</mat-icon>
                </button>
            </div>

            <!-- Loading -->
            <div class="loading-state" *ngIf="isLoading">
                <mat-progress-spinner mode="indeterminate" [diameter]="50"></mat-progress-spinner>
                <p>Loading audit entry details...</p>
            </div>

            <!-- Content -->
            <div class="dialog-content" *ngIf="!isLoading && entry">
                <mat-tab-group>
                    <!-- Overview Tab -->
                    <mat-tab label="Overview">
                        <div class="detail-section">
                            <div class="detail-item">
                                <div class="detail-label">Entry ID</div>
                                <div class="detail-value id-value">
                                    {{ entry.id }}
                                    <button mat-icon-button class="copy-id-btn" (click)="copyId()" matTooltip="Copy ID">
                                        <mat-icon>content_copy</mat-icon>
                                    </button>
                                </div>
                            </div>

                            <div class="detail-item">
                                <div class="detail-label">Timestamp</div>
                                <div class="detail-value">{{ entry.timestamp | date:'medium' }}</div>
                                <div class="detail-relative">{{ entry.timestamp | date:'shortTime' }} ({{ auditService.getRelativeTime(entry.timestamp) }})</div>
                            </div>

                            <div class="detail-item">
                                <div class="detail-label">User</div>
                                <div class="detail-value">
                                    <div class="user-info">
                                        <span class="user-name">{{ entry.displayName || entry.user }}</span>
                                        <span class="user-email" *ngIf="entry.user">{{ entry.user }}</span>
                                    </div>
                                </div>
                            </div>

                            <div class="detail-item" *ngIf="entry.ipAddress">
                                <div class="detail-label">IP Address</div>
                                <div class="detail-value ip-address">{{ entry.ipAddress }}</div>
                            </div>

                            <div class="detail-item" *ngIf="entry.httpMethod">
                                <div class="detail-label">HTTP Method</div>
                                <div class="detail-value">
                                    <span class="http-method method-{{ entry.httpMethod }}">{{ entry.httpMethod }}</span>
                                </div>
                            </div>

                            <div class="detail-item" *ngIf="entry.path">
                                <div class="detail-label">Path</div>
                                <div class="detail-value path-value">{{ entry.path }}</div>
                            </div>

                            <div class="detail-item" *ngIf="entry.statusCode">
                                <div class="detail-label">Status Code</div>
                                <div class="detail-value status-code status-code-{{ entry.statusCode }}">
                                    {{ entry.statusCode }}
                                </div>
                            </div>

                            <div class="detail-item" *ngIf="entry.durationMs !== undefined">
                                <div class="detail-label">Duration</div>
                                <div class="detail-value">{{ auditService.formatDuration(entry.durationMs) }}</div>
                            </div>

                            <div class="detail-item" *ngIf="entry.requestId">
                                <div class="detail-label">Request ID</div>
                                <div class="detail-value request-id">{{ entry.requestId }}</div>
                            </div>

                            <div class="detail-item full-width">
                                <div class="detail-label">Description</div>
                                <div class="detail-value description">{{ entry.description }}</div>
                            </div>
                        </div>
                    </mat-tab>

                    <!-- Changes Tab -->
                    <mat-tab label="Changes" *ngIf="entry.changes?.length">
                        <div class="changes-section" *ngIf="entry.changes?.length">
                            <ng-container *ngFor="let change of entry.changes">
                                <div class="change-item" *ngIf="change.field">
                                    <div class="change-header">
                                        <div class="change-field">{{ change.field }}</div>
                                        <div class="change-tags">
                                            <span class="change-tag" *ngIf="change.oldValue && change.newValue">Modified</span>
                                            <span class="change-tag tag-added" *ngIf="!change.oldValue && change.newValue">Added</span>
                                            <span class="change-tag tag-removed" *ngIf="change.oldValue && !change.newValue">Removed</span>
                                        </div>
                                    </div>
                                    <div class="change-diff" *ngIf="change.oldValue !== undefined && change.newValue !== undefined">
                                        <div class="diff-old">
                                            <div class="diff-label">Old Value</div>
                                            <pre class="diff-content">{{ formatValue(change.oldValue) }}</pre>
                                        </div>
                                        <div class="diff-arrow">→</div>
                                        <div class="diff-new">
                                            <div class="diff-label">New Value</div>
                                            <pre class="diff-content">{{ formatValue(change.newValue) }}</pre>
                                        </div>
                                    </div>
                                    <div class="change-single-value" *ngIf="change.oldValue === undefined && change.newValue === undefined">
                                        <div class="diff-label">{{ change.field }}</div>
                                        <pre class="diff-content">{{ formatValue(change.description || change.field) }}</pre>
                                    </div>
                                    <div class="change-single-value" *ngIf="change.oldValue === undefined && change.newValue !== undefined">
                                        <div class="diff-label">New Value</div>
                                        <pre class="diff-content">{{ formatValue(change.newValue) }}</pre>
                                    </div>
                                    <div class="change-single-value" *ngIf="change.oldValue !== undefined && change.newValue === undefined">
                                        <div class="diff-label">Previous Value</div>
                                        <pre class="diff-content">{{ formatValue(change.oldValue) }}</pre>
                                    </div>
                                    <div class="change-description" *ngIf="change.description">
                                        {{ change.description }}
                                    </div>
                                </div>
                            </ng-container>
                        </div>
                        <div class="no-changes" *ngIf="!entry.changes?.length">
                            <mat-icon class="empty-icon">info</mat-icon>
                            <p>No change details available for this entry.</p>
                        </div>
                    </mat-tab>

                    <!-- Details Tab -->
                    <mat-tab label="Details">
                        <div class="details-section">
                            <!-- Request Details -->
                            <mat-expansion-panel class="detail-expansion" *ngIf="entry.details">
                                <mat-expansion-panel-header>
                                    <mat-panel-title>
                                        <mat-icon>input</mat-icon>
                                        Request Details
                                    </mat-panel-title>
                                </mat-expansion-panel-header>
                                <div class="detail-content">
                                    <ng-container *ngIf="entry.details?.requestBody">
                                        <div class="detail-item">
                                            <div class="detail-label">Request Body</div>
                                            <pre class="json-content">{{ formatValue(entry.details.requestBody) }}</pre>
                                        </div>
                                    </ng-container>
                                    <ng-container *ngIf="entry.details?.queryParams">
                                        <div class="detail-item">
                                            <div class="detail-label">Query Parameters</div>
                                            <pre class="json-content">{{ formatValue(entry.details.queryParams) }}</pre>
                                        </div>
                                    </ng-container>
                                    <ng-container *ngIf="entry.details?.headers">
                                        <div class="detail-item">
                                            <div class="detail-label">Headers</div>
                                            <pre class="json-content">{{ formatValue(entry.details.headers) }}</pre>
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
                            <mat-expansion-panel class="detail-expansion" *ngIf="entry.details?.responseBody">
                                <mat-expansion-panel-header>
                                    <mat-panel-title>
                                        <mat-icon>output</mat-icon>
                                        Response Details
                                    </mat-panel-title>
                                </mat-expansion-panel-header>
                                <div class="detail-content">
                                    <pre class="json-content">{{ formatValue(entry.details?.responseBody) }}</pre>
                                </div>
                            </mat-expansion-panel>

                            <!-- Result Details -->
                            <mat-expansion-panel class="detail-expansion" *ngIf="entry.result">
                                <mat-expansion-panel-header>
                                    <mat-panel-title>
                                        <mat-icon>assignment</mat-icon>
                                        Operation Result
                                    </mat-panel-title>
                                </mat-expansion-panel-header>
                                <div class="detail-content">
                                    <div class="detail-item">
                                        <div class="detail-label">Success</div>
                                        <div class="detail-value">
                                            <span class="result-badge" [class.success]="entry.result?.success" [class.failure]="!entry.result?.success">
                                                {{ entry.result?.success ? 'Success' : 'Failed' }}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="detail-item" *ngIf="entry.result?.errorMessage">
                                        <div class="detail-label">Error Message</div>
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
                            <mat-expansion-panel class="detail-expansion" *ngIf="entry.metadata">
                                <mat-expansion-panel-header>
                                    <mat-panel-title>
                                        <mat-icon>code</mat-icon>
                                        Raw Metadata
                                    </mat-panel-title>
                                </mat-expansion-panel-header>
                                <div class="detail-content">
                                    <pre class="json-content">{{ formatValue(entry.metadata) }}</pre>
                                </div>
                            </mat-expansion-panel>
                        </div>
                    </mat-tab>
                </mat-tab-group>
            </div>
        </div>

        <!-- Actions -->
        <div class="dialog-actions">
            <button mat-button mat-dialog-close>Close</button>
            <button mat-raised-button color="primary" (click)="copyFullEntry()" *ngIf="entry">
                <mat-icon>content_copy</mat-icon>
                Copy Entry
            </button>
        </div>
    `,
    styles: [`
        .detail-dialog { min-width: 600px; max-width: 90vw; }
        .dialog-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 16px; border-bottom: 1px solid #e0e0e0;
        }
        .header-left { display: flex; flex-direction: column; gap: 8px; }
        .header-badges { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .dialog-content { max-height: 60vh; overflow-y: auto; }
        .loading-state { display: flex; flex-direction: column; align-items: center; padding: 40px; gap: 16px; }

        /* Detail section */
        .detail-section { padding: 16px; }
        .detail-item {
            margin-bottom: 16px; padding-bottom: 16px;
            border-bottom: 1px solid #f0f0f0;
        }
        .detail-label {
            font-size: 12px; color: #999; text-transform: uppercase;
            letter-spacing: 0.5px; margin-bottom: 4px; font-weight: 500;
        }
        .detail-value { font-size: 14px; color: #333; word-break: break-all; }
        .detail-relative { font-size: 12px; color: #999; margin-top: 4px; }

        .id-value { display: flex; align-items: center; gap: 8px; font-family: monospace; font-size: 12px; }
        .copy-id-btn { padding: 0; background: none; border: none; }
        .ip-address { font-family: monospace; color: #666; }
        .path-value { font-family: monospace; font-size: 13px; color: #1976d2; word-break: break-all; }
        .request-id { font-family: monospace; color: #666; }
        .description { line-height: 1.6; white-space: pre-wrap; }

        /* HTTP Method badges */
        .http-method {
            display: inline-flex; align-items: center; justify-content: center;
            padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;
        }
        .method-GET { background: #e3f2fd; color: #1565c0; }
        .method-POST { background: #e8f5e9; color: #2e7d32; }
        .method-PUT { background: #fff3e0; color: #ef6c00; }
        .method-DELETE { background: #ffebee; color: #c62828; }
        .method-PATCH { background: #f3e5f5; color: #7b1fa2; }

        /* Status codes */
        .status-code { font-family: monospace; font-size: 14px; padding: 4px 8px; border-radius: 4px; }
        .status-code-200 { background: #e8f5e9; color: #2e7d32; }
        .status-code-201 { background: #e8f5e9; color: #2e7d32; }
        .status-code-204 { background: #e8f5e9; color: #2e7d32; }
        .status-code-400 { background: #fff3e0; color: #ef6c00; }
        .status-code-401 { background: #ffebee; color: #c62828; }
        .status-code-403 { background: #ffebee; color: #c62828; }
        .status-code-404 { background: #ffebee; color: #c62828; }
        .status-code-500 { background: #ffebee; color: #c62828; }

        /* Badges */
        .severity-badge {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500;
        }
        .severity-error { background: #ffebee; color: #c62828; }
        .severity-warning { background: #fff3e0; color: #ef6c00; }
        .severity-info { background: #e3f2fd; color: #1565c0; }
        .severity-success { background: #e8f5e9; color: #2e7d32; }

        .result-badge {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500;
        }
        .result-badge.success { background: #e8f5e9; color: #2e7d32; }
        .result-badge.failure { background: #ffebee; color: #c62828; }

        .action-badge {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 4px 8px; border-radius: 4px; font-size: 12px;
            background: #f5f5f5;
        }

        /* User info */
        .user-info { display: flex; flex-direction: column; gap: 2px; }
        .user-name { font-size: 14px; font-weight: 500; }
        .user-email { font-size: 12px; color: #666; font-family: monospace; }

        /* Changes section */
        .changes-section { padding: 16px; }
        .change-item { margin-bottom: 24px; padding: 16px; background: #fafafa; border-radius: 8px; border: 1px solid #e0e0e0; }
        .change-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .change-field { font-size: 14px; font-weight: 600; color: #333; }
        .change-tags { display: flex; gap: 4px; }
        .change-tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #e0e0e0; }
        .tag-added { background: #e8f5e9; color: #2e7d32; }
        .tag-removed { background: #ffebee; color: #c62828; }

        .change-diff { display: grid; grid-template-columns: 1fr auto 1fr; gap: 8px; align-items: center; }
        .diff-old, .diff-new { padding: 8px; background: white; border-radius: 4px; border: 1px solid #e0e0e0; }
        .diff-label { font-size: 11px; color: #999; margin-bottom: 4px; }
        .diff-content { font-size: 12px; font-family: monospace; white-space: pre-wrap; word-break: break-all; margin: 0; max-height: 200px; overflow: auto; }
        .diff-arrow { text-align: center; color: #999; font-size: 20px; }

        .change-single-value { padding: 8px; background: white; border-radius: 4px; border: 1px solid #e0e0e0; }
        .change-description { margin-top: 8px; font-size: 13px; color: #666; font-style: italic; }
        .no-changes { text-align: center; padding: 40px; color: #999; }
        .no-changes .empty-icon { font-size: 48px; color: #ccc; }

        /* Details section */
        .details-section { padding: 16px; }
        .detail-expansion { margin-bottom: 8px; border-radius: 8px !important; overflow: hidden; }
        .detail-content { padding: 12px; }
        .json-content {
            font-family: 'Consolas', 'Monaco', monospace; font-size: 12px;
            background: #f5f5f5; padding: 12px; border-radius: 4px;
            white-space: pre-wrap; word-break: break-all; max-height: 300px;
            overflow: auto; margin: 0;
        }
        .detail-value.error { color: #c62828; font-weight: 500; }

        /* Actions */
        .dialog-actions {
            display: flex; justify-content: flex-end; align-items: center;
            padding: 16px; border-top: 1px solid #e0e0e0; gap: 8px;
        }
    `]
})
export class AuditDetailComponent implements OnInit {
    entry: AuditEntry | null = null;
    isLoading = true;

    constructor(
        public dialogRef: MatDialogRef<AuditDetailComponent>,
        @Inject(MAT_DIALOG_DATA) public data: AuditDetailData,
        public auditService: AuditService,
        private snackBar: MatSnackBar,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit(): void {
        if (this.data.entry) {
            this.entry = this.data.entry;
        }
        this.isLoading = false;
    }

    formatValue(value: any): string {
        if (typeof value === 'string') return value;
        try {
            return JSON.stringify(value, null, 2);
        } catch {
            return String(value);
        }
    }

    copyId(): void {
        if (!this.entry?.id) return;
        navigator.clipboard?.writeText(this.entry.id).then(() => {
            this.snackBar.open('Entry ID copied.', 'Close', { duration: 2000 });
        });
    }

    copyFullEntry(): void {
        if (!this.entry) return;
        const entryCopy = { ...this.entry };
        const jsonStr = JSON.stringify(entryCopy, null, 2);
        navigator.clipboard?.writeText(jsonStr).then(() => {
            this.snackBar.open('Entry copied to clipboard.', 'Close', { duration: 2000 });
        }).catch(() => {
            this.snackBar.open('Failed to copy entry.', 'Close', { duration: 2000 });
        });
    }
}