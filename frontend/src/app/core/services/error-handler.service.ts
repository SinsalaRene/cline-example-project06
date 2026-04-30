import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';

/**
 * Interface for structured error events.
 * Provides a consistent shape for error reporting across the application.
 */
export interface AppError {
    message: string;
    statusCode?: number;
    errorDetails?: any;
    url?: string;
    method?: string;
    timestamp?: number;
}

/**
 * Centralized Error Handler Service
 * Provides a single point for handling errors throughout the application.
 * Emits error events to any subscribers (UI components can subscribe to display errors).
 */
@Injectable({ providedIn: 'root' })
export class ErrorHandlerService {
    /**
     * Observable error stream for components to subscribe to.
     * Components can subscribe to display user-friendly error messages.
     */
    readonly error$ = new Subject<AppError>();

    /**
     * Observable for authentication errors specifically.
     * Components can subscribe to handle auth-specific actions (redirect to login).
     */
    readonly authError$ = new Subject<void>();

    /**
     * Maximum number of errors to retain in history.
     */
    private readonly MAX_HISTORY_SIZE = 50;

    /**
     * Array to store error history for debugging and reference.
     */
    private errorHistory: AppError[] = [];

    constructor(private router: Router) { }

    /**
     * Handle HTTP errors from the HttpErrorInterceptor.
     * @param error The structured error object
     */
    handleHttpError(error: AppError): void {
        this.recordError(error);
        this.error$.next(error);

        // Handle session expired / unauthorized scenarios
        if (error.statusCode === 401) {
            this.handleAuthError(error);
        }
    }

    /**
     * Handle authentication-specific errors.
     * @param error The error containing auth-related info
     */
    handleAuthError(error?: AppError): void {
        // Clear stored auth token
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');

        // Emit auth error signal
        this.authError$.next();

        // Redirect to login if not already there
        if (error && this.router.url !== '/login') {
            this.router.navigate(['/login']);
        }
    }

    /**
     * Handle generic application errors.
     * @param error The error object
     */
    handleGenericError(error: AppError): void {
        this.recordError(error);
        this.error$.next(error);
    }

    /**
     * Record error in history with timestamp.
     * Maintains a bounded history to prevent memory leaks.
     */
    private recordError(error: AppError): void {
        const errorEntry: AppError = {
            ...error,
            timestamp: error.timestamp || Date.now()
        };

        this.errorHistory.push(errorEntry);

        // Maintain bounded history
        if (this.errorHistory.length > this.MAX_HISTORY_SIZE) {
            this.errorHistory = this.errorHistory.slice(-this.MAX_HISTORY_SIZE);
        }
    }

    /**
     * Get recent error history.
     * @param count Number of recent errors to retrieve
     * @returns Array of recent errors
     */
    getErrorHistory(count: number = 10): AppError[] {
        return this.errorHistory.slice(-count);
    }

    /**
     * Clear the error history.
     */
    clearHistory(): void {
        this.errorHistory = [];
    }

    /**
     * Clear the error subject.
     */
    clearError(): void {
        this.error$.complete();
        this.error$.next({
            message: '',
            timestamp: Date.now()
        });
    }

    /**
     * Handle validation errors from the server.
     * @param errors Object containing field validation errors
     */
    handleValidationErrors(errors: Record<string, string[]>): void {
        const errorMessages = Object.values(errors).flat().join(' ');
        this.handleGenericError({
            message: errorMessages || 'Validation errors occurred.',
            statusCode: 422,
            errorDetails: errors
        });
    }
}