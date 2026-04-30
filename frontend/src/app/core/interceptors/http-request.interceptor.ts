import { Injectable } from '@angular/core';
import { HttpRequest, HttpHandler, HttpEvent, HttpInterceptor } from '@angular/common/http';
import { Observable } from 'rxjs';

/**
 * HTTP Request Interceptor
 * Adds authentication tokens and common headers to outgoing requests.
 * Ensures consistent request formatting across the application.
 */
@Injectable()
export class HttpRequestInterceptor implements HttpInterceptor {
    intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
        // Get the auth token from localStorage
        const authToken = localStorage.getItem('auth_token');

        // Clone the request and add the authorization header
        let clonedRequest = request;

        if (authToken) {
            clonedRequest = request.clone({
                setHeaders: {
                    Authorization: `Bearer ${authToken}`
                }
            });
        }

        // Set common headers for JSON requests
        if (
            !request.headers.has('Content-Type') &&
            (request.body instanceof FormData === false)
        ) {
            clonedRequest = clonedRequest.clone({
                setHeaders: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });
        }

        // Add request timestamp for debugging
        clonedRequest = clonedRequest.clone({
            setHeaders: {
                'X-Request-Time': Date.now().toString()
            }
        });

        return next.handle(clonedRequest);
    }
}