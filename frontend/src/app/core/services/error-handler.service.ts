import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { Subject } from 'rxjs';

/**
 * Context interface for additional error metadata.
 * Provides extra context like request IDs, URLs, etc.
 */
export interface ErrorContext {
    /** Request ID for traceability. */
    requestId?: string;
    /** URL of the request that failed. */
    url?: string;
    /** HTTP method of the request. */
    method?: string;
    /** Additional arbitrary context data. */
    [key: string]: unknown;
}

/**
 * Interface for structured error events.
 * Provides a consistent shape for error reporting across the application.
 */
export interface AppError {
    /** Human-readable error message. */
    message: string;
    /** HTTP status code. */
    statusCode?: number;
    /** Raw error details from the server. */
    errorDetails?: any;
    /** URL where the error occurred. */
    url?: string;
    /** HTTP method used. */
    method?: string;
    /** Unix timestamp of the error. */
    timestamp?: number;
}

/**
 * Centralized Error Handler Service
 *
 * Provides a single point for handling errors throughout the application.
 * Emits error events to any subscribers (UI components can subscribe to display errors).
 *
 * Key methods:
 * - handleHttpError(error) - Handle HTTP errors from interceptor
 * - handleApiError(error, context?) - Handle raw API errors with context
 * - getErrorMessage(error) - Extract clean message from HttpErrorResponse
 * - trackError(error, context?) - Placeholder for error tracking integration
 * - handleAuthError(error?) - Handle authentication errors
 * - handleValidationErrors(errors) - Handle validation errors
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
     *
     * @param error - The structured error object.
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
     * Handle a raw API error (e.g., HttpErrorResponse) with optional context.
     *
     * Extracts a user-friendly message, logs the error, and emits it on the error$ stream.
     *
     * @param error - The raw error object (typically HttpErrorResponse).
     * @param context - Optional context metadata (request ID, URL, method, etc.).
     */
    handleApiError(error: unknown, context?: ErrorContext): void {
        const message = this.getErrorMessage(error);
        const statusCode =
            error instanceof HttpErrorResponse ? error.status : undefined;

        const appError: AppError = {
            message,
            statusCode,
            url: context?.url,
            method: context?.method,
            timestamp: Date.now(),
        };

        this.recordError(appError);
        this.error$.next(appError);

        // Handle auth errors automatically
        if (statusCode === 401) {
            this.handleAuthError(appError);
        }
    }

    /**
     * Handle authentication-specific errors.
     *
     * Clears stored auth token, emits auth error signal, and redirects to login.
     *
     * @param error - Optional error containing auth-related info.
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
     *
     * @param error - The error object.
     */
    handleGenericError(error: AppError): void {
        this.recordError(error);
        this.error$.next(error);
    }

    /**
     * Extract a clean, user-friendly error message from an error object.
     *
     * Handles various error types:
     * - HttpErrorResponse: extracts from error.error?.message, error.message, or status text
     * - Error objects: extracts from error.message or error.name
     * - Strings: returns the string directly
     * - Other: returns a generic message with type info
     *
     * @param error - The error to extract a message from.
     * @returns A clean error message string.
     */
    getErrorMessage(error: unknown): string {
        if (error instanceof HttpErrorResponse) {
            // Extract from backend JSON response
            if (error.error?.message) {
                return String(error.error.message);
            }
            if (error.error?.detail) {
                return String(error.error.detail);
            }
            if (error.error?.error) {
                return String(error.error.error);
            }
            // Fall back to HTTP status text or default
            if (error.statusText) {
                return `${error.statusText}`;
            }
            return `Error ${error.status}: ${error.message}`;
        }

        if (error instanceof Error) {
            return error.message || error.name || 'An unknown error occurred';
        }

        if (typeof error === 'string') {
            return error;
        }

        if (error && typeof error === 'object') {
            const err = error as Record<string, unknown>;
            if (err['message']) {
                return String(err['message']);
            }
            if (err['detail']) {
                return String(err['detail']);
            }
        }

        return 'An unexpected error occurred';
    }

    /**
     * Track an error for external error tracking integration.
     *
     * Placeholder method for integration with services like Sentry, Bugsnag, etc.
     * In production, replace with the actual tracking service call.
     *
     * @param error - The error to track.
     * @param context - Optional context metadata.
     */
    trackError(error: unknown, context?: ErrorContext): void {
        // Placeholder for error tracking integration
        // TODO: Integrate with Sentry, Bugsnag, or similar service
        const trackedError = {
            message: this.getErrorMessage(error),
            stack: error instanceof Error ? error.stack : undefined,
            context: {
                ...context,
                timestamp: Date.now(),
            },
        };

        console.log('[ErrorTracker]', trackedError);
    }

    /**
     * Record error in history with timestamp.
     * Maintains a bounded history to prevent memory leaks.
     *
     * @param error - The error to record.
     * @private
     */
    private recordError(error: AppError): void {
        const errorEntry: AppError = {
            ...error,
            timestamp: error.timestamp || Date.now(),
        };

        this.errorHistory.push(errorEntry);

        // Maintain bounded history
        if (this.errorHistory.length > this.MAX_HISTORY_SIZE) {
            this.errorHistory = this.errorHistory.slice(-this.MAX_HISTORY_SIZE);
        }
    }

    /**
     * Get recent error history.
     *
     * @param count - Number of recent errors to retrieve.
     * @returns Array of recent errors.
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
            timestamp: Date.now(),
        });
    }

    /**
     * Handle validation errors from the server.
     *
     * @param errors - Object containing field validation errors.
     */
    handleValidationErrors(errors: Record<string, string[]>): void {
        const errorMessages = Object.values(errors).flat().join(' ');
        this.handleGenericError({
            message: errorMessages || 'Validation errors occurred.',
            statusCode: 422,
            errorDetails: errors,
        });
    }
}