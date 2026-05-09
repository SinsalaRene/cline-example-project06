import { Injectable, inject } from '@angular/core';
import {
    HTTP_INTERCEPTORS,
    HttpInterceptor,
    HttpRequest,
    HttpHandler,
    HttpEvent,
    HttpHeaders,
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';

/**
 * Generates a UUID v4 identifier string.
 * Used to create unique request IDs for traceability.
 *
 * @returns A UUID v4 string in the format xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
 */
function generateUuid(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

/**
 * HTTP Request Interceptor
 *
 * Adds authentication tokens, request IDs, and correlation IDs to outgoing HTTP requests.
 * Ensures consistent request formatting and traceability across the application.
 *
 * Headers added:
 * - X-Request-ID: A unique UUID v4 per request for request-level tracing.
 * - X-Correlation-ID: A correlation ID for distributed tracing (inherited from header if present).
 * - Authorization: Bearer token from AuthService when user is authenticated.
 * - Content-Type: application/json (for non-FormData requests).
 * - Accept: application/json
 *
 * @example
 * // Requests will automatically include:
 * // X-Request-ID: a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d
 * // X-Correlation-ID: same-as-above-or-from-incoming
 * // Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
 */
@Injectable()
export class HttpRequestInterceptor implements HttpInterceptor {
    private authService = inject(AuthService);

    /**
     * Intercepts HTTP requests and adds required headers.
     *
     * @param request - The outgoing HTTP request.
     * @param next - The next interceptor or HTTP handler.
     * @returns An observable of the HTTP event stream.
     */
    intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
        // Generate a unique request ID for this request
        const requestId = generateUuid();

        // Check if AuthService is available and user is logged in
        let authHeader: string | null = null;
        if (this.authService && this.authService.isLoggedIn()) {
            const token = localStorage.getItem('auth_token');
            if (token) {
                authHeader = `Bearer ${token}`;
            }
        }

        // Clone the request and add headers
        const clonedRequest = request.clone({
            setHeaders: {
                // Always add Content-Type and Accept for JSON requests (skip for FormData)
                ...(!request.headers.has('Content-Type') &&
                    !(request.body instanceof FormData)
                    ? {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                    }
                    : {}),
                // Add request ID for traceability
                'X-Request-ID': requestId,
                // Add correlation ID (same as request ID, or from incoming header)
                'X-Correlation-ID': request.headers.get('X-Correlation-ID') || requestId,
                // Add authorization header if available
                ...(authHeader ? { 'Authorization': authHeader } : {}),
            },
        });

        return next.handle(clonedRequest);
    }
}

/**
 * Factory to provide the interceptor with its dependencies.
 *
 * @param authService - The AuthService instance for authentication.
 * @returns An interceptor function.
 */
export function HttpRequestInterceptorFactory(authService: AuthService) {
    return (request: HttpRequest<any>, next: HttpHandler) => {
        // Create a new interceptor instance for each request to get fresh auth state
        const interceptor = new HttpRequestInterceptorWithAuth(authService);
        return interceptor.intercept(request, next);
    };
}

/**
 * Internal interceptor class that takes AuthService via constructor for factory injection.
 * @internal
 */
class HttpRequestInterceptorWithAuth implements HttpInterceptor {
    constructor(private authService: AuthService) { }

    intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
        const requestId = generateUuid();

        let authHeader: string | null = null;
        if (this.authService && this.authService.isLoggedIn()) {
            const token = localStorage.getItem('auth_token');
            if (token) {
                authHeader = `Bearer ${token}`;
            }
        }

        const clonedRequest = request.clone({
            setHeaders: {
                ...(!request.headers.has('Content-Type') &&
                    !(request.body instanceof FormData)
                    ? {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                    }
                    : {}),
                'X-Request-ID': requestId,
                'X-Correlation-ID': request.headers.get('X-Correlation-ID') || requestId,
                ...(authHeader ? { 'Authorization': authHeader } : {}),
            },
        });

        return next.handle(clonedRequest);
    }
}

/**
 * Provider token for the HTTP request interceptor.
 * Use this in app.module.ts to register the interceptor.
 *
 * @example
 * ```typescript
 * providers: [
 *     {
 *         provide: HTTP_INTERCEPTORS,
 *         useClass: HttpRequestInterceptor,
 *         multi: true,
 *     },
 * ]
 * ```
 */
export const HTTP_REQUEST_INTERCEPTOR_PROVIDER = {
    provide: HTTP_INTERCEPTORS,
    useClass: HttpRequestInterceptor,
    multi: true,
};