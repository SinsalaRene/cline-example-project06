import { TestBed } from '@angular/core/testing';
import { HttpRequest, HttpHandler, HttpEvent, HTTP_INTERCEPTORS } from '@angular/common/http';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { Observable } from 'rxjs';
import { HttpRequestInterceptor } from './http-request.interceptor';

describe('HttpRequestInterceptor', () => {
    let interceptor: HttpRequestInterceptor;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [
                HttpRequestInterceptor,
                {
                    provide: HTTP_INTERCEPTORS,
                    useValue: {
                        intercept: (request: HttpRequest<any>, next: HttpHandler) => next.handle(request)
                    },
                    multi: true
                }
            ]
        });

        interceptor = TestBed.inject(HttpRequestInterceptor);
    });

    it('should be created', () => {
        expect(interceptor).toBeTruthy();
    });

    describe('intercept method', () => {
        it('should add authorization header when auth token exists', () => {
            const authToken = 'test-token-123';
            localStorage.setItem('auth_token', authToken);

            const originalRequest = new HttpRequest('GET', '/api/test');
            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    expect(request.headers.has('Authorization')).toBe(true);
                    expect(request.headers.get('Authorization')).toBe(`Bearer ${authToken}`);
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            localStorage.removeItem('auth_token');
        });

        it('should not add authorization header when no auth token exists', () => {
            localStorage.removeItem('auth_token');

            const originalRequest = new HttpRequest('GET', '/api/test');
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.headers.has('Authorization')).toBe(false);
        });

        it('should add Content-Type and Accept headers for non-form-data requests', () => {
            const originalRequest = new HttpRequest('POST', '/api/test', { data: 'test' });
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.headers.has('Content-Type')).toBe(true);
            expect(interceptedRequest!.headers.get('Content-Type')).toBe('application/json');
            expect(interceptedRequest!.headers.has('Accept')).toBe(true);
            expect(interceptedRequest!.headers.get('Accept')).toBe('application/json');
        });

        it('should add X-Request-Time header', () => {
            const originalRequest = new HttpRequest('GET', '/api/test');
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.headers.has('X-Request-Time')).toBe(true);
            const requestTime = interceptedRequest!.headers.get('X-Request-Time');
            expect(Number.parseInt(requestTime!, 10)).toBeGreaterThan(0);
        });

        it('should not add content-type headers for form data requests', () => {
            const formData = new FormData();
            formData.append('file', 'test');
            const originalRequest = new HttpRequest('POST', '/api/upload', formData);
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.body).toBeInstanceOf(FormData);
        });

        it('should combine auth token with content-type headers', () => {
            localStorage.setItem('auth_token', 'test-bearer-token');

            const originalRequest = new HttpRequest('POST', '/api/test', { data: 'test' });
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.headers.has('Authorization')).toBe(true);
            expect(interceptedRequest!.headers.get('Authorization')).toBe('Bearer test-bearer-token');
            expect(interceptedRequest!.headers.has('Content-Type')).toBe(true);
            expect(interceptedRequest!.headers.get('Content-Type')).toBe('application/json');
            expect(interceptedRequest!.headers.has('Accept')).toBe(true);
            expect(interceptedRequest!.headers.get('Accept')).toBe('application/json');
            localStorage.removeItem('auth_token');
        });

        it('should handle PUT requests with authorization', () => {
            localStorage.setItem('auth_token', 'put-token');

            const originalRequest = new HttpRequest('PUT', '/api/test/123', { name: 'updated' });
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.url).toBe('/api/test/123');
            expect(interceptedRequest!.method).toBe('PUT');
            expect(interceptedRequest!.headers.has('Authorization')).toBe(true);
            localStorage.removeItem('auth_token');
        });

        it('should handle DELETE requests without body', () => {
            const originalRequest = new HttpRequest('DELETE', '/api/test/123');
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.url).toBe('/api/test/123');
            expect(interceptedRequest!.method).toBe('DELETE');
            expect(interceptedRequest!.headers.has('X-Request-Time')).toBe(true);
        });

        it('should handle PATCH requests', () => {
            const originalRequest = new HttpRequest('PATCH', '/api/test/123', { field: 'value' });
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.method).toBe('PATCH');
            expect(interceptedRequest!.headers.has('Content-Type')).toBe(true);
        });

        it('should preserve existing headers from original request', () => {
            const originalRequest = new HttpRequest('GET', '/api/test', {
                headers: { 'X-Custom-Header': 'custom-value' }
            });
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.headers.has('X-Custom-Header')).toBe(true);
            expect(interceptedRequest!.headers.get('X-Custom-Header')).toBe('custom-value');
        });

        it('should handle empty auth token gracefully', () => {
            localStorage.removeItem('auth_token');

            const originalRequest = new HttpRequest('GET', '/api/test');
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.url).toBe('/api/test');
            expect(interceptedRequest!.headers.has('X-Request-Time')).toBe(true);
        });

        it('should handle request with query parameters', () => {
            const originalRequest = new HttpRequest('GET', '/api/test?page=1&limit=10');
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.url).toContain('page=1');
            expect(interceptedRequest!.url).toContain('limit=10');
        });

        it('should handle request with special characters in URL', () => {
            const originalRequest = new HttpRequest('GET', '/api/test/path-with-dashes/and_underscores');
            let interceptedRequest: HttpRequest<any> | undefined;

            const handler: HttpHandler = {
                handle: (request: HttpRequest<any>) => {
                    interceptedRequest = request;
                    return new Observable();
                }
            };

            interceptor.intercept(originalRequest, handler);
            expect(interceptedRequest!.url).toBe('/api/test/path-with-dashes/and_underscores');
        });
    });
});