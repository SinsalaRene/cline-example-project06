/**
 * Confirmation dialog data interface for Material dialog configuration.
 *
 * @interface ConfirmationDialogData
 * @description Configuration object passed to the confirmation dialog component
 * containing the dialog title, message, and optional button labels.
 */
export interface ConfirmationDialogData {
    /** Dialog title displayed in the card header. */
    title: string;
    /** Confirmation message displayed in the dialog body. */
    message: string;
    /** Label for the confirm button (defaults to 'Confirm'). */
    confirmLabel?: string;
    /** Label for the cancel button (defaults to 'Cancel'). */
    cancelLabel?: string;
}

/**
 * ConfirmationDialogComponent - A reusable Material confirmation dialog.
 *
 * @component
 * @description Displays a simple confirmation dialog with a title, message,
 * and confirm/cancel buttons. Returns a boolean result through MatDialogRef:
 * - `true` when the user clicks confirm
 * - `false` when the user clicks cancel or closes the dialog
 *
 * @example
 * ```typescript
 * const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
 *     data: {
 *         title: 'Delete Workload',
 *         message: 'Are you sure you want to delete this workload?',
 *         confirmLabel: 'Delete',
 *         cancelLabel: 'Cancel'
 *     }
 * });
 *
 * dialogRef.afterClosed().subscribe(result => {
 *     if (result) {
 *         // User confirmed
 *     }
 * });
 * ```
 */
import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';

/**
 * ConfirmationDialogComponent - A reusable Material confirmation dialog.
 */
@Component({
    selector: 'app-confirmation-dialog',
    standalone: false,
    templateUrl: './confirmation-dialog.component.html',
    styleUrls: ['./confirmation-dialog.component.css']
})
export class ConfirmationDialogComponent {
    /**
     * Creates an instance of ConfirmationDialogComponent.
     *
     * @param data - Dialog configuration from MAT_DIALOG_DATA injection.
     * @param dialogRef - Reference to the Material dialog for closing.
     */
    constructor(
        @Inject(MAT_DIALOG_DATA) public data: ConfirmationDialogData,
        private dialogRef: MatDialogRef<ConfirmationDialogComponent>
    ) { }

    /**
     * Closes the dialog with a confirmed result.
     */
    onConfirm(): void {
        this.dialogRef.close(true);
    }

    /**
     * Closes the dialog with a cancelled (false) result.
     */
    onCancel(): void {
        this.dialogRef.close(false);
    }
}