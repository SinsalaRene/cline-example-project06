import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
    MatDialog,
    MatDialogModule,
    MatDialogRef,
    MAT_DIALOG_DATA,
    MatDialogActions,
    MatDialogContent,
    MatDialogTitle,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';

/**
 * Data interface passed to the Confirm Dialog via MAT_DIALOG_DATA.
 */
export interface ConfirmDialogData {
    /** Title displayed in the dialog title bar. */
    title: string;
    /** Main message/body text displayed in the dialog content. */
    message: string;
    /** Text for the confirm action button (defaults to "Confirm"). */
    confirmText?: string;
    /** Text for the cancel action button (defaults to "Cancel"). */
    cancelText?: string;
}

/**
 * Default values for dialog button labels.
 */
const DEFAULT_CONFIRM_TEXT = 'Confirm';
const DEFAULT_CANCEL_TEXT = 'Cancel';

/**
 * Confirm Dialog Component
 *
 * A generic confirmation dialog used across all modules for delete confirmations,
 * form submit confirmations, and other user action verifications.
 *
 * Usage:
 * ```typescript
 * const ref = this.dialog.open(ConfirmDialogComponent, {
 *     data: {
 *         title: 'Delete Record',
 *         message: 'Are you sure you want to delete this record?',
 *         confirmText: 'Delete',
 *         cancelText: 'Cancel'
 *     }
 * });
 *
 * ref.afterClosed().subscribe(result => {
 *     if (result) {
 *         // user confirmed
 *     }
 * });
 * ```
 */
@Component({
    selector: 'app-confirm-dialog',
    standalone: true,
    imports: [
        CommonModule,
        MatDialogModule,
        MatDialogActions,
        MatDialogContent,
        MatDialogTitle,
        MatButtonModule,
    ],
    template: `
    <h2 mat-dialog-title>{{ data.title }}</h2>
    <mat-dialog-content>
        <p>{{ data.message }}</p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
        <button mat-button [mat-dialog-close]="false">
            {{ data.cancelText || 'Cancel' }}
        </button>
        <button mat-raised-button color="primary" [mat-dialog-close]="true" autofocus>
            {{ data.confirmText || 'Confirm' }}
        </button>
    </mat-dialog-actions>
  `,
    styles: [],
})
export class ConfirmDialogComponent {
    /**
     * The dialog data injected via MAT_DIALOG_DATA.
     */
    constructor(
        @Inject(MAT_DIALOG_DATA) public data: ConfirmDialogData
    ) { }
}

/**
 * Helper function to open a confirmation dialog.
 *
 * @param dialog - The MatDialog instance to open the dialog with.
 * @param data - The confirmation data (title, message, button texts).
 * @returns A MatDialogRef<boolean> emitting the user's choice.
 *
 * @example
 * ```typescript
 * constructor(private dialog: MatDialog) {}
 *
 * this.confirmDelete() {
 *     const ref = openConfirmDialog(this.dialog, {
 *         title: 'Delete Record',
 *         message: 'Are you sure?',
 *         confirmText: 'Delete',
 *         cancelText: 'Cancel'
 *     });
 *     ref.afterClosed().subscribe(confirmed => {
 *         if (confirmed) { /* proceed *\/ }
 *     });
 * }
 * ```
 */
export function openConfirmDialog(
    dialog: MatDialog,
    data: ConfirmDialogData
): MatDialogRef<ConfirmDialogComponent, boolean> {
    const ref = dialog.open(ConfirmDialogComponent, {
        data: {
            title: data.title,
            message: data.message,
            confirmText: data.confirmText ?? DEFAULT_CONFIRM_TEXT,
            cancelText: data.cancelText ?? DEFAULT_CANCEL_TEXT,
        },
    });
    return ref;
}