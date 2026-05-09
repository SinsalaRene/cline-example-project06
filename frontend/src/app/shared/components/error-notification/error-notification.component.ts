import { Component, inject, Injectable } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
    MatSnackBar,
    MatSnackBarConfig,
    MatSnackBarModule,
} from '@angular/material/snack-bar';

/**
 * Configuration for different notification severity types.
 * Each type maps to a specific color scheme and icon configuration.
 */
export type NotificationSeverity = 'error' | 'warning' | 'success';

/**
 * Service that wraps MatSnackBar to provide typed toast methods
 * with distinct visual styling for each severity.
 *
 * @example
 * ```typescript
 * constructor(private notification: ErrorNotificationService) {}
 *
 * this.notification.showError('Failed to save changes');
 * this.notification.showWarning('Session expiring soon', 8000);
 * this.notification.showSuccess('Record saved successfully');
 * ```
 */
@Injectable({ providedIn: 'root' })
export class ErrorNotificationService {
    private snackBar = inject(MatSnackBar);

    /**
     * Default toast duration in milliseconds (5 seconds).
     */
    private readonly DEFAULT_DURATION = 5000;

    /**
     * Shows an error toast notification (red).
     *
     * @param message - The message to display in the snackbar.
     * @param durationMillis - Auto-dismiss duration in ms. Defaults to 5000.
     * @param action - Optional action button label.
     */
    showError(message: string, durationMillis?: number, action?: string): void {
        this.openSnackBar(message, 'error', durationMillis, action);
    }

    /**
     * Shows a warning toast notification (orange).
     *
     * @param message - The message to display in the snackbar.
     * @param durationMillis - Auto-dismiss duration in ms. Defaults to 5000.
     * @param action - Optional action button label.
     */
    showWarning(message: string, durationMillis?: number, action?: string): void {
        this.openSnackBar(message, 'warning', durationMillis, action);
    }

    /**
     * Shows a success toast notification (green).
     *
     * @param message - The message to display in the snackbar.
     * @param durationMillis - Auto-dismiss duration in ms. Defaults to 5000.
     * @param action - Optional action button label.
     */
    showSuccess(message: string, durationMillis?: number, action?: string): void {
        this.openSnackBar(message, 'success', durationMillis, action);
    }

    /**
     * Opens a snackbar with the specified severity configuration.
     *
     * @param message - The snackbar message.
     * @param severity - The severity type determining color/style.
     * @param durationMillis - Optional override for dismiss duration.
     * @param action - Optional action button label.
     * @internal
     */
    private openSnackBar(
        message: string,
        severity: NotificationSeverity,
        durationMillis?: number,
        action?: string
    ): void {
        const duration = durationMillis ?? this.DEFAULT_DURATION;
        const config: MatSnackBarConfig = {
            horizontalPosition: 'right',
            verticalPosition: 'top',
            duration: duration,
            panelClass: `notification-${severity}`,
            data: { severity, message, action },
        };

        this.snackBar.open(message, action || 'CLOSE', config);
    }
}

/**
 * ErrorNotificationComponent
 *
 * Placeholder root component for the error notification system.
 * The actual notification logic is provided by ErrorNotificationService.
 * This component can be placed in the application layout to host any
 * persistent notification UI in the future.
 */
@Component({
    selector: 'app-error-notification',
    standalone: true,
    imports: [CommonModule, MatSnackBarModule],
    template: `<div></div>`,
    styles: [],
    providers: [ErrorNotificationService],
})
export class ErrorNotificationComponent {
    constructor() { }
}