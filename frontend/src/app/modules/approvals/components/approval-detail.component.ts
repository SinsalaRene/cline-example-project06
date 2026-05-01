import { Component, Inject, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatSelectModule } from '@angular/material/select';
import { ApprovalsService } from '../services/approvals.service';
import { ApprovalRequest, ApprovalComment } from '../models/approval.model';
import { ApprovalCommentsComponent } from './approval-comments.component';

@Component({
    selector: 'app-approval-detail',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatDialogModule,
        MatSnackBarModule,
        MatProgressSpinnerModule,
        MatIconModule,
        MatButtonModule,
        MatInputModule,
        MatFormFieldModule,
        MatCardModule,
        MatTabsModule,
        MatChipsModule,
        MatExpansionModule,
        MatSelectModule,
        ApprovalCommentsComponent
    ],
    template: `
        <div class="detail-dialog">
            <!-- Dialog header -->
            <div class="dialog-header">
                <div class="header-left">
                    <h2 mat-dialog-title>Approval Details</h2>
                    <div class="header-badges" *ngIf="approval">
                        <span class="status-badge status-{{ approval.status }}" *ngIf="approval">
                            <mat-icon *ngIf="approval.status === 'approved'">check_circle</mat-icon>
                            <mat-icon *ngIf="approval.status === 'rejected'">cancel</mat-icon>
                            <mat-icon *ngIf="approval.status === 'pending'">schedule</mat-icon>
                            {{ approval.status | titlecase }}
                        </span>
                        <span class="priority-badge priority-{{ approval.priority }}" *ngIf="approval">
                            {{ approval.priority | titlecase }}
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
                <p>Loading approval details...</p>
            </div>

            <!-- Content -->
            <div class="dialog-content" *ngIf="!isLoading && approval">
                <mat-tab-group>
                    <!-- Overview Tab -->
                    <mat-tab label="Overview">
                        <div class="detail-section">
                            <div class="detail-item">
                                <div class="detail-label">Request ID</div>
                                <div class="detail-value">{{ approval.id }}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Rule Name</div>
                                <div class="detail-value">{{ approval.rule_name }}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Request Type</div>
                                <div class="detail-value">
                                    <mat-chip>{{ approval.request_type }}</mat-chip>
                                </div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Requestor</div>
                                <div class="detail-value">{{ approval.requestor }}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Requested At</div>
                                <div class="detail-value">{{ approval.requested_at | date:'medium' }}</div>
                            </div>
                            <div class="detail-item" *ngIf="approval.due_at">
                                <div class="detail-label">Due At</div>
                                <div class="detail-value">{{ approval.due_at | date:'medium' }}</div>
                                <div class="due-warning" *ngIf="isExpired()">
                                    <mat-icon class="warning-icon">warning</mat-icon>
                                    This request has expired
                                </div>
                            </div>
                            <div class="detail-item" *ngIf="approval.description">
                                <div class="detail-label">Description</div>
                                <div class="detail-value description">{{ approval.description }}</div>
                            </div>
                            <div class="detail-item" *ngIf="approval.rejection_reason">
                                <div class="detail-label">Rejection Reason</div>
                                <div class="detail-value rejection">{{ approval.rejection_reason }}</div>
                            </div>
                            <div class="detail-item" *ngIf="approval.approved_by">
                                <div class="detail-label">Approved By</div>
                                <div class="detail-value">{{ approval.approved_by }}</div>
                            </div>
                            <div class="detail-item" *ngIf="approval.approved_at">
                                <div class="detail-label">Approved At</div>
                                <div class="detail-value">{{ approval.approved_at | date:'medium' }}</div>
                            </div>
                        </div>
                    </mat-tab>

                    <!-- Changes Tab -->
                    <mat-tab label="Changes">
                        <div class="changes-section" *ngIf="approval.metadata?.rule_changes">
                            <div class="change-item" *ngIf="approval.metadata?.rule_changes">
                                <div class="change-label">Field</div>
                                <div class="change-value">{{ approval.metadata.rule_changes.field }}</div>
                            </div>
                            <div class="change-item" *ngIf="approval.metadata?.rule_changes?.old_value !== undefined">
                                <div class="change-label">Old Value</div>
                                <div class="change-value change-old">
                                    <pre>{{ formatValue(approval.metadata.rule_changes.old_value) }}</pre>
                                </div>
                            </div>
                            <div class="change-item" *ngIf="approval.metadata?.rule_changes?.new_value !== undefined">
                                <div class="change-label">New Value</div>
                                <div class="change-value change-new">
                                    <pre>{{ formatValue(approval.metadata.rule_changes.new_value) }}</pre>
                                </div>
                            </div>
                        </div>
                        <div class="no-changes" *ngIf="!approval.metadata?.rule_changes">
                            <mat-icon class="empty-icon">info</mat-icon>
                            <p>No change details available</p>
                        </div>
                    </mat-tab>

                    <!-- Comments Tab -->
                    <mat-tab label="Comments">
                        <app-approval-comments
                            [approvalId]="approval.id"
                            [comments]="approval.comments"
                            [currentUser]="currentUser"
                            [isPending]="approval.status === 'pending'"
                            (commentAdded)="onCommentAdded($event)"
                            (commentDeleted)="onCommentDeleted($event)"
                        ></app-approval-comments>
                    </mat-tab>
                </mat-tab-group>
            </div>
        </div>

        <!-- Action bar -->
        <div class="dialog-actions" *ngIf="!isLoading && approval?.status === 'pending'">
            <div class="actions-left">
                <button mat-raised-button color="primary" (click)="approve()" [disabled]="isProcessing">
                    <mat-icon>check_circle</mat-icon>
                    Approve
                </button>
                <button mat-raised-button color="warn" (click)="reject()" [disabled]="isProcessing">
                    <mat-icon>cancel</mat-icon>
                    Reject
                </button>
            </div>
            <button mat-button mat-dialog-close>Close</button>
        </div>

        <div class="dialog-actions closed" *ngIf="!isLoading && approval?.status !== 'pending'">
            <span class="closed-label">This request has been {{ approval?.status | titlecase }}</span>
            <button mat-button mat-dialog-close>Close</button>
        </div>
    `,
    styles: [`
        .detail-dialog { min-width: 600px; }
        .dialog-header {
            display: flex; justify-content: space-between; align-items: center;
        }
        .header-left { display: flex; flex-direction: column; gap: 8px; }
        .header-badges { display: flex; gap: 8px; align-items: center; }
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
            letter-spacing: 0.5px; margin-bottom: 4px;
        }
        .detail-value { font-size: 14px; color: #333; word-break: break-all; }
        .detail-value.description { line-height: 1.5; }
        .detail-value.rejection { color: #d32f2f; font-weight: 500; }
        .due-warning {
            display: flex; align-items: center; gap: 4px;
            color: #ff9800; font-size: 12px; margin-top: 4px;
        }
        .warning-icon { font-size: 16px; width: 16px; height: 16px; }

        /* Changes section */
        .changes-section { padding: 16px; }
        .change-item {
            margin-bottom: 16px; padding: 12px;
            background: #f5f5f5; border-radius: 8px;
        }
        .change-label { font-size: 12px; color: #666; margin-bottom: 4px; }
        .change-value { font-size: 14px; font-weight: 500; }
        .change-old { color: #d32f2f; }
        .change-new { color: #2e7d32; }
        .change-value pre { margin: 0; white-space: pre-wrap; word-break: break-all; }
        .no-changes { text-align: center; padding: 40px; color: #999; }
        .no-changes .empty-icon { font-size: 48px; color: #ccc; }

        /* Status badge */
        .status-badge {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500;
        }
        .status-pending { background: #fff3e0; color: #ef6c00; }
        .status-approved { background: #e8f5e9; color: #2e7d32; }
        .status-rejected { background: #ffebee; color: #c62828; }
        .status-icon { font-size: 16px; width: 16px; height: 16px; }
        .priority-badge {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500;
        }
        .priority-low { background: #e3f2fd; color: #1565c0; }
        .priority-medium { background: #fff3e0; color: #ef6c00; }
        .priority-high { background: #ffebee; color: #c62828; }
        .priority-urgent { background: #d50000; color: #fff; }

        /* Actions */
        .dialog-actions {
            display: flex; justify-content: space-between; align-items: center;
            padding: 16px; border-top: 1px solid #e0e0e0;
        }
        .actions-left { display: flex; gap: 8px; }
        .closed { justify-content: center; }
        .closed-label { font-size: 14px; color: #666; }
    `]
})
export class ApprovalDetailComponent implements OnInit {
    approval: ApprovalRequest | null = null;
    isLoading = true;
    currentUser = 'Admin User';
    isProcessing = false;
    comments: ApprovalComment[] = [];

    constructor(
        public dialogRef: MatDialogRef<ApprovalDetailComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { approval: ApprovalRequest },
        private approvalsService: ApprovalsService,
        private snackBar: MatSnackBar,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit(): void {
        if (this.data.approval) {
            this.approval = this.data.approval;
            this.comments = this.approval.comments || [];
            this.isLoading = false;
        } else {
            this.isLoading = false;
        }
    }

    isExpired(): boolean {
        return this.approval ? this.approvalsService.isExpired(this.approval) : false;
    }

    formatValue(value: any): string {
        if (typeof value === 'string') return value;
        try {
            return JSON.stringify(value, null, 2);
        } catch {
            return String(value);
        }
    }

    approve(): void {
        if (this.isProcessing || !this.approval) return;
        this.isProcessing = true;
        this.approvalsService.approve(this.approval.id).subscribe({
            next: (result) => {
                this.approval = result;
                this.snackBar.open('Request approved.', 'Close', { duration: 3000 });
                this.isProcessing = false;
                this.cdr.markForCheck();
            },
            error: (err) => {
                this.snackBar.open('Error approving request.', 'Close', { duration: 3000 });
                this.isProcessing = false;
            }
        });
    }

    reject(): void {
        if (this.isProcessing || !this.approval) return;
        this.isProcessing = true;
        this.approvalsService.reject(this.approval.id, { reason: 'Rejected from detail view' }).subscribe({
            next: (result) => {
                this.approval = result;
                this.snackBar.open('Request rejected.', 'Close', { duration: 3000 });
                this.isProcessing = false;
                this.cdr.markForCheck();
            },
            error: (err) => {
                this.snackBar.open('Error rejecting request.', 'Close', { duration: 3000 });
                this.isProcessing = false;
            }
        });
    }

    onCommentAdded(event: { text: string; isNotification: boolean }): void {
        this.approvalsService.addComment(this.approval!.id, event.text).subscribe({
            next: (comment) => {
                if (!this.approval) return;
                this.approval.comments = [...(this.approval.comments || []), comment];
                this.snackBar.open('Comment added.', 'Close', { duration: 2000 });
            },
            error: () => this.snackBar.open('Error adding comment.', 'Close', { duration: 3000 })
        });
    }

    onCommentDeleted(commentId: string): void {
        if (!this.approval) return;
        this.approvalsService.deleteComment(this.approval.id, commentId).subscribe({
            next: () => {
                this.approval!.comments = this.approval.comments.filter(c => c.id !== commentId);
                this.snackBar.open('Comment deleted.', 'Close', { duration: 2000 });
            },
            error: () => this.snackBar.open('Error deleting comment.', 'Close', { duration: 3000 })
        });
    }

    getInitials(name: string): string {
        return (name[0] || '').toUpperCase();
    }
}