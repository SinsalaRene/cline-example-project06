import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';

export interface BulkActionData {
    title: string;
    message: string;
    confirmLabel: string;
    type: string;
    showReason?: boolean;
    maxReasonLength?: number;
}

@Component({
    selector: 'app-bulk-action-dialog',
    standalone: true,
    imports: [
        ReactiveFormsModule,
        CommonModule,
        MatDialogModule,
        MatButtonModule,
        MatInputModule,
        MatFormFieldModule,
        MatSelectModule,
        MatIconModule
    ],
    template: `
        <div class="bulk-dialog">
            <div class="dialog-title">
                {{ data.title }}
            </div>
            <div class="dialog-message">
                {{ data.message }}
            </div>

            <form [formGroup]="actionForm" class="action-form">
                <!-- Comment -->
                <mat-form-field appearance="outline" class="reason-field" subscriptSizing="dynamic">
                    <mat-label>Comment (optional)</mat-label>
                    <textarea
                        matInput
                        formControlName="comment"
                        placeholder="Add a comment for this action..."
                        rows="3"
                        cdkTextareaAutosize
                    ></textarea>
                    <mat-hint align="end">{{actionForm.get('comment')?.value?.length || 0}}/500</mat-hint>
                </mat-form-field>

                <!-- Reason (required when showReason is true) -->
                <mat-form-field appearance="outline" class="reason-field" *ngIf="data.showReason" subscriptSizing="dynamic">
                    <mat-label>Reason <span class="required">*</span></mat-label>
                    <textarea
                        matInput
                        formControlName="reason"
                        placeholder="Enter the reason for this action..."
                        rows="3"
                        cdkTextareaAutosize
                        required
                    ></textarea>
                    <mat-hint align="end">{{actionForm.get('reason')?.value?.length || 0}}/{{data.maxReasonLength || 500}}</mat-hint>
                    <mat-error *ngIf="actionForm.get('reason')?.hasError('required')" class="reason-error">
                        Reason is required
                    </mat-error>
                </mat-form-field>

                <!-- Priority selector for bulk actions -->
                <mat-form-field appearance="outline" class="priority-field" *ngIf="data.type === 'primary' || data.type === 'warn'">
                    <mat-label>Priority</mat-label>
                    <mat-select formControlName="priority">
                        <mat-option value="low">Low</mat-option>
                        <mat-option value="medium" selected>Medium</mat-option>
                        <mat-option value="high">High</mat-option>
                        <mat-option value="urgent">Urgent</mat-option>
                    </mat-select>
                </mat-form-field>
            </form>

            <div class="dialog-actions">
                <button mat-button [mat-dialog-close]="null">Cancel</button>
                <button
                    mat-raised-button
                    [color]="data.type === 'warn' ? 'warn' : 'primary'"
                    (click)="onConfirm()"
                    [disabled]="!actionForm.valid"
                >
                    {{ data.confirmLabel }}
                </button>
            </div>
        </div>
    `,
    styles: [`
        .bulk-dialog { padding: 16px; min-width: 400px; }
        .dialog-title { font-size: 18px; font-weight: 500; margin-bottom: 8px; }
        .dialog-message { font-size: 14px; color: #666; margin-bottom: 16px; }

        .action-form { margin-bottom: 16px; }
        .reason-field { width: 100%; margin-bottom: 12px; }
        .priority-field { width: 100%; }
        .reason-error { font-size: 12px; }
        .required { color: #d32f2f; }

        .dialog-actions {
            display: flex; justify-content: flex-end; gap: 8px;
            padding-top: 16px; border-top: 1px solid #e0e0e0;
        }
    `]
})
export class BulkActionDialogComponent implements OnInit {
    actionForm: any;

    constructor(
        public dialogRef: MatDialogRef<BulkActionDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: BulkActionData,
        private fb: FormBuilder
    ) {
        this.data = data as BulkActionData;
    }

    ngOnInit(): void {
        this.actionForm = this.fb.group({
            comment: [''],
            reason: [this.data.showReason ? '' : '', [
                this.data.showReason ? Validators.required : () => null
            ]],
            priority: ['medium']
        });

        if (this.data.maxReasonLength) {
            this.actionForm.get('reason')?.setValidators([
                this.data.showReason ? Validators.required : () => null,
                Validators.maxLength(this.data.maxReasonLength)
            ]);
        }
    }

    onConfirm(): void {
        if (this.actionForm.invalid) return;

        this.dialogRef.close({
            confirmed: true,
            reason: this.actionForm.value.reason,
            comment: this.actionForm.value.comment,
            priority: this.actionForm.value.priority
        });
    }
}