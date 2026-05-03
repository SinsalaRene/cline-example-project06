import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { ErrorHandlerService, AppError } from '../../../core/services/error-handler.service';
import { Subscription } from 'rxjs';

/**
 * ErrorNotification Component
 *
 * Global error notification component that listens to the ErrorHandlerService
 * and displays user-friendly error messages.
 *
 * This component is designed to be placed once in the application root layout
 * to catch and display errors from anywhere in the application.
 */
@Component({
    selector: 'app-error-notification',
    standalone: true,
    imports: [CommonModule, MatIconModule, MatButtonModule],
    template: `
    <div
      *ngIf="currentError"
      class="error-notification"
      [class]="'error-severity-' + getErrorClass()"
    >
      <div class="error-notification-content">
        <span class="error-icon">{{ getErrorIcon() }}</span>
        <div class="error-text">
          <span class="error-title">{{ errorTitle }}</span>
          <span class="error-message">{{ currentError?.message }}</span>
        </div>
      </div>
      <button mat-button class="error-action" (click)="dismissError()">
        {{ actionLabel }}
      </button>
    </div>
  `,
    styles: [`
    :host {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 10000;
      display: block;
    }

    .error-notification {
      min-width: 320px;
      max-width: 480px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      padding: 16px 20px;
      background: #ffebee;
      color: #c62828;
      border-left: 4px solid #c62828;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .error-notification-content {
      display: flex;
      align-items: center;
      flex: 1;
      gap: 8px;
    }

    .error-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      flex-shrink: 0;
    }

    .error-text {
      flex: 1;
      min-width: 0;
    }

    .error-title {
      display: block;
      font-weight: 600;
      font-size: 14px;
      margin-bottom: 0;
    }

    .error-message {
      display: block;
      font-size: 13px;
      line-height: 1.4;
      opacity: 0.85;
      word-break: break-word;
    }

    .error-action {
      margin-left: 8px;
      font-weight: 600;
      text-transform: none;
      letter-spacing: normal;
    }

    /* Severity-specific styles */
    .error-severity-error {
      border-left-color: #c62828;
    }

    .error-severity-warning {
      border-left-color: #e65100;
      background: #fff3e0;
      color: #bf360c;
    }

    .error-severity-info {
      border-left-color: #1976d2;
      background: #e3f2fd;
      color: #0d47a1;
    }

    .error-severity-success {
      border-left-color: #2e7d32;
      background: #e8f5e9;
      color: #1b5e20;
    }
  `]
})
export class ErrorNotificationComponent implements OnInit, OnDestroy {
    /** Current error being displayed */
    currentError: AppError | null = null;

    /** Error title for display */
    errorTitle = 'Error';

    /** Action button label */
    actionLabel = 'Dismiss';

    /** Error action callback */
    errorAction?: () => void;

    /** Subscription to error events */
    private errorSubscription?: Subscription;

    /** Subscription to auth error events */
    private authErrorSubscription?: Subscription;

    /** Timer for auto-dismiss */
    private autoDismissTimer?: ReturnType<typeof setTimeout>;

    constructor(
        private errorHandler: ErrorHandlerService
    ) { }

    ngOnInit(): void {
        // Subscribe to HTTP errors
        this.errorSubscription = this.errorHandler.error$.subscribe((error: AppError) => {
            this.displayError(error);
        });

        // Subscribe to auth errors
        this.authErrorSubscription = this.errorHandler.authError$.subscribe(() => {
            this.errorTitle = 'Session Expired';
            this.actionLabel = 'Login';
            this.errorAction = () => {
                this.dismissError();
                // Trigger auth flow
                this.errorHandler.handleHttpError({
                    message: 'Session expired. Please log in again.',
                    statusCode: 401
                });
            };
        });
    }

    ngOnDestroy(): void {
        this.errorSubscription?.unsubscribe();
        this.authErrorSubscription?.unsubscribe();
        this.clearAutoDismissTimer();
    }

    /**
     * Display an error notification.
     */
    displayError(error: AppError): void {
        // Clear any existing timer
        this.clearAutoDismissTimer();

        this.currentError = error;
        this.errorTitle = this.getTitleForStatusCode(error.statusCode);

        // Auto-dismiss after delay based on severity
        const delay = this.getAutoDismissDelay(error.statusCode);
        if (delay > 0) {
            this.autoDismissTimer = setTimeout(() => {
                this.dismissError();
            }, delay);
        }
    }

    /**
     * Dismiss the current error notification.
     */
    dismissError(): void {
        this.currentError = null;
        this.errorTitle = 'Error';
        this.actionLabel = 'Dismiss';
        this.errorAction = undefined;
        this.clearAutoDismissTimer();
    }

    /**
     * Get the appropriate icon for the error severity.
     */
    getErrorIcon(): string {
        const statusCode = this.currentError?.statusCode;

        if (statusCode === 401 || statusCode === 403) {
            return '\u{1F512}'; // Lock emoji
        }

        if (statusCode === 404) {
            return '\u{1F50D}'; // Search off emoji
        }

        if (statusCode && statusCode >= 500) {
            return '\u{1F5A5}'; // Server error emoji
        }

        if (statusCode === 429) {
            return '\u{23F3}'; // Hourglass emoji
        }

        return '\u2715'; // Error emoji
    }

    /**
     * Get the appropriate title for the status code.
     */
    private getTitleForStatusCode(statusCode?: number): string {
        switch (statusCode) {
            case 400:
                return 'Bad Request';
            case 401:
                return 'Unauthorized';
            case 403:
                return 'Forbidden';
            case 404:
                return 'Not Found';
            case 409:
                return 'Conflict';
            case 422:
                return 'Validation Error';
            case 429:
                return 'Rate Limited';
            case 500:
            case 502:
            case 503:
            case 504:
                return 'Server Error';
            default:
                return 'Error';
        }
    }

    /**
     * Get auto-dismiss delay based on severity.
     */
    private getAutoDismissDelay(statusCode?: number): number {
        // Don't auto-dismiss auth errors
        if (statusCode === 401) {
            return 0;
        }

        // Server errors - show longer
        if (statusCode && statusCode >= 500) {
            return 10000; // 10 seconds
        }

        // Rate limiting - show longer
        if (statusCode === 429) {
            return 8000; // 8 seconds
        }

        // Default: show for 5 seconds
        return 5000;
    }

    /**
     * Get CSS class for the error severity.
     */
    getErrorClass(): string {
        const statusCode = this.currentError?.statusCode;

        if (statusCode === 401) {
            return 'error-severity-error';
        }

        if (statusCode === 429) {
            return 'error-severity-warning';
        }

        return 'error-severity-error';
    }

    /**
     * Clear the auto-dismiss timer.
     */
    private clearAutoDismissTimer(): void {
        if (this.autoDismissTimer) {
            clearTimeout(this.autoDismissTimer);
            this.autoDismissTimer = undefined;
        }
    }
}