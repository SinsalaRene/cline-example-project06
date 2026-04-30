import { Injectable } from '@angular/core';
import { HttpRequest, HttpHandler, HttpEvent, HttpInterceptor, HTTP_INTERCEPTORS } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { ErrorHandlerService } from '../services/error-handler.service';

/**
 * HTTP Error Interceptor
 * Catches HTTP errors and delegates to the error handler service.
 * Translates HTTP status codes into user-friendly error messages.
 */
@Injectable()
export class HttpErrorInterceptor implements HttpInterceptor {
    constructor(private errorHandler: ErrorHandlerService) { }

    intercept(request: HttpRequest<any>, next: HttpHandler) {
        return next.handle(request).pipe(
            catchError(error => {
                let errorMessage: string;
                let statusCode: number | undefined;
                let errorDetails: any = null;

                if (error.status) {
                    statusCode = error.status;

                    switch (error.status) {
                        case 400:
                            errorMessage = error.error?.detail || error.error?.message || 'Bad Request: Invalid parameters or request body.';
                            errorDetails = error.error;
                            break;
                        case 401:
                            errorMessage = 'Unauthorized: Please log in to continue.';
                            this.errorHandler.handleAuthError(error);
                            break;
                        case 403:
                            errorMessage = 'Forbidden: You do not have permission to access this resource.';
                            errorDetails = error.error;
                            break;
                        case 404:
                            errorMessage = 'Not Found: The requested resource was not found.';
                            errorDetails = error.error;
                            break;
                        case 409:
                            errorMessage = 'Conflict: The resource already exists or conflicts with another resource.';
                            errorDetails = error.error;
                            break;
                        case 422:
                            errorMessage = error.error?.detail || error.error?.message || 'Validation Error: Please check your input.';
                            errorDetails = error.error;
                            break;
                        case 429:
                            errorMessage = 'Too Many Requests: Please wait before trying again.';
                            break;
                        case 500:
                            errorMessage = 'Internal Server Error: Please try again later.';
                            break;
                        case 502:
                            errorMessage = 'Bad Gateway: The server received an invalid response.';
                            break;
                        case 503:
                            errorMessage = 'Service Unavailable: The server is temporarily unavailable.';
                            break;
                        case 504:
                            errorMessage = 'Gateway Timeout: The server took too long to respond.';
                            break;
                        default:
                            errorMessage = `An unexpected error occurred (Status: ${error.status}). Please try again later.`;
                    }
                } else if (error.cause) {
                    errorMessage = `Network Error: ${error.cause?.message || 'Unable to connect to the server.'}`;
                } else {
                    errorMessage = 'An unexpected error occurred. Please check your connection and try again.';
                }

                // Log the error for debugging
                console.error('[HttpErrorInterceptor]', {
                    url: request.url,
                    method: request.method,
                    status: statusCode,
                    error: error,
                    message: errorMessage
                });

                // Handle the error through the centralized error handler
                this.errorHandler.handleHttpError({
                    message: errorMessage,
                    statusCode,
                    errorDetails,
                    url: request.url,
                    method: request.method
                });

                return throwError(() => error);
            })
        );
    }
}

/**
 * Factory to provide the interceptor with its dependencies.
 */
export function HttpErrorInterceptorFactory(errorHandler: ErrorHandlerService) {
    return (request: HttpRequest<any>, next: HttpHandler) => {
        const interceptor = new HttpErrorInterceptor(errorHandler);
        return interceptor.intercept(request, next);
    };
}

/**
 * Provider token for the HTTP error interceptor.
 * Use this in app.module.ts to register the interceptor.
 */
export const HTTP_ERROR_INTERCEPTOR_PROVIDER = {
    provide: HTTP_INTERCEPTORS,
    useClass: HttpErrorInterceptor,
    multi: true,
};