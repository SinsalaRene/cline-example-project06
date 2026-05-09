import { Injectable } from '@angular/core';
import {
    HTTP_INTERCEPTORS,
    HttpInterceptor,
    HttpRequest,
    HttpHandler,
    HttpEvent,
    HttpErrorResponse,
} from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { ErrorHandlerService } from '../services/error-handler.service';
import { ErrorNotificationService } from '../../shared/components/error-notification/error-notification.component';

/**
 * HTTP Error Interceptor
 *
 * Catches HTTP errors and delegates to the error handler service.
 * Extracts error messages from backend JSON responses and includes
 * request IDs for debugging. Shows toast notifications using ErrorNotificationService.
 *
 * Features:
 * - Extracts error message from backend JSON errors (error.error?.detail, error.error?.message)
 * - Extracts X-Request-ID header for debugging correlation
 * - Shows error toast notifications using ErrorNotificationService
 * - Logs to console with request ID and full error context
 *
 * @example
 * // When an error occurs:
 * // 1. Toast notification appears (red for errors)
 * // 2. Console log includes: [HttpErrorInterceptor] [REQ-123] Error message
 * // 3. Error handler processes the error for auth/retry logic
 */
@Injectable()
export class HttpErrorInterceptor implements HttpInterceptor {
    constructor(
        private errorHandler: ErrorHandlerService,
        private notificationService: ErrorNotificationService
    ) { }

    /**
     * Intercepts HTTP requests and handles errors.
     *
     * @param request - The outgoing HTTP request.
     * @param next - The next interceptor or HTTP handler.
     * @returns An observable that throws the error after handling.
     */
    intercept(request: HttpRequest<any>, next: HttpHandler) {
        return next.handle(request).pipe(
            catchError((error: HttpErrorResponse) => {
                // Extract request ID from response header or generate from request
                const requestId =
                    error.headers?.get('X-Request-ID') ||
                    error.headers?.get('X-Correlation-ID') ||
                    request.headers.get('X-Request-ID') ||
                    'unknown';

                let errorMessage: string;
                let statusCode: number | undefined;
                let errorDetails: any = null;

                if (error.status) {
                    statusCode = error.status;

                    switch (error.status) {
                        case 400:
                            // Extract error from backend JSON response
                            errorMessage =
                                error.error?.detail ||
                                error.error?.message ||
                                error.error?.error ||
                                'Bad Request: Invalid parameters or request body.';
                            errorDetails = error.error;
                            break;
                        case 401:
                            errorMessage =
                                error.error?.message ||
                                error.error?.detail ||
                                'Unauthorized: Please log in to continue.';
                            // Cast HttpErrorResponse to AppError-compatible shape for handleAuthError
                            const authError = {
                                message: errorMessage,
                                statusCode: error.status,
                                url: request.url,
                                method: request.method,
                                timestamp: Date.now(),
                            };
                            this.errorHandler.handleAuthError(authError);
                            this.notificationService.showError('Session expired. Please log in again.', 8000);
                            break;
                        case 403:
                            errorMessage =
                                error.error?.message ||
                                error.error?.detail ||
                                'Forbidden: You do not have permission to access this resource.';
                            errorDetails = error.error;
                            this.notificationService.showError(errorMessage, 6000);
                            break;
                        case 404:
                            errorMessage =
                                error.error?.message ||
                                error.error?.detail ||
                                'Not Found: The requested resource was not found.';
                            errorDetails = error.error;
                            this.notificationService.showError(errorMessage, 5000);
                            break;
                        case 409:
                            errorMessage =
                                error.error?.message ||
                                error.error?.detail ||
                                'Conflict: The resource already exists or conflicts with another resource.';
                            errorDetails = error.error;
                            this.notificationService.showWarning(errorMessage, 5000);
                            break;
                        case 422:
                            // Validation error - extract detail messages
                            if (error.error?.detail || error.error?.message) {
                                errorMessage = error.error.detail || error.error.message;
                            } else if (error.error?.errors) {
                                // Format validation errors array into a readable string
                                errorMessage = formatValidationErrors(error.error.errors);
                            } else {
                                errorMessage = 'Validation Error: Please check your input.';
                            }
                            errorDetails = error.error;
                            this.notificationService.showWarning(errorMessage, 8000);
                            break;
                        case 429:
                            errorMessage =
                                error.error?.message ||
                                'Too Many Requests: Please wait before trying again.';
                            this.notificationService.showWarning(errorMessage, 10000);
                            break;
                        case 500:
                            errorMessage =
                                error.error?.message ||
                                'Internal Server Error: Please try again later.';
                            this.notificationService.showError(errorMessage, 8000);
                            break;
                        case 502:
                            errorMessage =
                                error.error?.message ||
                                'Bad Gateway: The server received an invalid response.';
                            this.notificationService.showError(errorMessage, 8000);
                            break;
                        case 503:
                            errorMessage =
                                error.error?.message ||
                                'Service Unavailable: The server is temporarily unavailable.';
                            this.notificationService.showError(errorMessage, 10000);
                            break;
                        case 504:
                            errorMessage =
                                error.error?.message ||
                                'Gateway Timeout: The server took too long to respond.';
                            this.notificationService.showError(errorMessage, 10000);
                            break;
                        default:
                            errorMessage =
                                error.error?.message ||
                                error.error?.detail ||
                                `An unexpected error occurred (Status: ${error.status}). Please try again later.`;
                    }
                } else if (error.message) {
                    errorMessage = `Network Error: ${error.message || 'Unable to connect to the server.'}`;
                    this.notificationService.showError(errorMessage, 10000);
                } else {
                    errorMessage = 'An unexpected error occurred. Please check your connection and try again.';
                    this.notificationService.showError(errorMessage, 8000);
                }

                // Log to console with request ID for debugging
                console.error(
                    `[HttpErrorInterceptor] [${requestId}]`,
                    {
                        url: request.url,
                        method: request.method,
                        status: statusCode,
                        message: errorMessage,
                        requestDetails: errorDetails,
                    }
                );

                // Track the error via the error handler service
                this.errorHandler.trackError(error, {
                    requestId,
                    url: request.url,
                    method: request.method,
                });

                // Handle the error through the centralized error handler
                this.errorHandler.handleApiError(error, {
                    requestId,
                    url: request.url,
                    method: request.method,
                });

                return throwError(() => error);
            })
        );
    }
}

/**
 * Formats validation errors array into a readable string.
 *
 * @param errors - An array of validation error objects.
 * @returns A formatted error message string.
 * @internal
 */
function formatValidationErrors(errors: any[]): string {
    if (!Array.isArray(errors) || errors.length === 0) {
        return 'Validation Error: Please check your input.';
    }
    return errors
        .map(
            (err: any) =>
                `${err.field || err.param}${err.msg ? `: ${err.msg}` : ''}`
        )
        .join('; ');
}

/**
 * Factory to provide the interceptor with its dependencies.
 *
 * @param errorHandler - The ErrorHandlerService instance.
 * @param notificationService - The ErrorNotificationService instance.
 * @returns An interceptor function.
 */
export function HttpErrorInterceptorFactory(
    errorHandler: ErrorHandlerService,
    notificationService: ErrorNotificationService
) {
    return (request: HttpRequest<any>, next: HttpHandler) => {
        const interceptor = new HttpErrorInterceptor(errorHandler, notificationService);
        return interceptor.intercept(request, next);
    };
}

/**
 * Provider token for the HTTP error interceptor.
 * Use this in app.module.ts to register the interceptor.
 *
 * @example
 * ```typescript
 * providers: [
 *     {
 *         provide: HTTP_INTERCEPTORS,
 *         useClass: HttpErrorInterceptor,
 *         multi: true,
 *     },
 * ]
 * ```
 */
export const HTTP_ERROR_INTERCEPTOR_PROVIDER = {
    provide: HTTP_INTERCEPTORS,
    useClass: HttpErrorInterceptor,
    multi: true,
};