/**
 * Simple Confirmation Dialog Component
 *
 * A minimal confirmation dialog for use within the external devices module.
 * Provides a reusable confirm/cancel pattern for destructive actions.
 *
 * @module confirmation-dialog
 */

import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';

/**
 * Dialog data interface for the confirmation dialog.
 */
export interface ConfirmationDialogData {
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
}

/**
 * Confirmation Dialog Component.
 *
 * @selector app-confirmation-dialog
 * @standalone
 */
@Component({
    selector: 'app-confirmation-dialog',
    standalone: true,
    imports: [CommonModule, MatDialogModule, MatCardModule, MatButtonModule],
    template: `
    <div class="dialog-container">
      <h2 mat-card-title>{{ data.title }}</h2>
      <mat-card-content>
        <p>{{ data.message }}</p>
      </mat-card-content>
      <div class="dialog-actions">
        <button mat-raised-button (click)="onCancel()">
          {{ data.cancelLabel || 'Cancel' }}
        </button>
        <button mat-raised-button color="warn" (click)="onConfirm()">
          {{ data.confirmLabel || 'Confirm' }}
        </button>
      </div>
    </div>
  `,
    styles: [`
    .dialog-container {
      padding: 24px;
    }

    mat-card-content {
      margin-top: 16px;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 24px;
    }
  `],
})
export class ConfirmationDialogComponent {
    constructor(
        @Inject(MAT_DIALOG_DATA) public data: ConfirmationDialogData,
        private dialogRef: MatDialogRef<ConfirmationDialogComponent>
    ) { }

    onConfirm(): void {
        this.dialogRef.close(true);
    }

    onCancel(): void {
        this.dialogRef.close(false);
    }
}