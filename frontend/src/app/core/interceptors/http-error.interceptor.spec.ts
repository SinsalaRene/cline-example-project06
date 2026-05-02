import { TestBed, fakeAsync, tick, flushMicroTasks } from '@angular/core/testing';
import { HttpRequest, HttpHandler, HttpEvent, HttpResponse, HTTP_INTERCEPTORS } from '@angular/common/http';
import { HttpErrorResponse, HttpClientTestingModule } from '@angular/common/http/testing';
import { Observable, throwError, of } from 'rxjs';
import { Router } from '@angular/router';
import { HttpErrorInterceptor, HttpErrorInterceptorFactory } from './http-error.interceptor';
import { ErrorHandlerService } from '../services/error-handler.service';

describe('HttpErrorInterceptor', () => {
    let interceptor: HttpErrorInterceptor;
    let errorHandler: jasmine.SpyObj<ErrorHandlerService>;
    let router: jasmine.SpyObj<Router>;

    beforeEach(() => {
        const errorHandlerSpy = jasmine.createSpyObj('ErrorHandlerService', ['handleHttpError', 'handleAuthError']);
        const routerSpy = jasmine.createSpyObj('Router', ['navigate']);

        TestBed.configureTestingModule({
            providers: [
                HttpErrorInterceptor,
                { provide: ErrorHandlerService, useValue: errorHandlerSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        interceptor = TestBed.inject(HttpErrorInterceptor);
        errorHandler = TestBed.inject(ErrorHandlerService) as jasmine.SpyObj<ErrorHandlerService>;
        router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
    });

    it('should be created', () => {
        expect(interceptor).toBeTruthy();
    });

    describe('intercept method', () => {
        it('should handle 400 errors with detail message', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 400,
                error: { detail: 'Bad Request: Invalid parameters.' },
                statusText: 'Bad Request'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(errorHandler.handleHttpError).toHaveBeenCalled();
                    expect(error.status).toBe(400);
                    done();
                }
            });
        });

        it('should handle 401 errors and call handleAuthError', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 401,
                error: { message: 'Unauthorized' },
                statusText: 'Unauthorized'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(errorHandler.handleAuthError).toHaveBeenCalled();
                    expect(error.status).toBe(401);
                    done();
                }
            });
        });

        it('should handle 403 errors', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 403,
                error: { detail: 'Forbidden' },
                statusText: 'Forbidden'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(403);
                    done();
                }
            });
        });

        it('should handle 404 errors', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 404,
                error: { detail: 'Not Found' },
                statusText: 'Not Found'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(404);
                    done();
                }
            });
        });

        it('should handle 409 errors (conflict)', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 409,
                error: { detail: 'Conflict' },
                statusText: 'Conflict'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(409);
                    done();
                }
            });
        });

        it('should handle 422 errors with detail message', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 422,
                error: { detail: 'Validation Error: Please check your input.' },
                statusText: 'Unprocessable Entity'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(422);
                    done();
                }
            });
        });

        it('should handle 429 errors (too many requests)', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 429,
                error: { message: 'Too Many Requests' },
                statusText: 'Too Many Requests'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(429);
                    done();
                }
            });
        });

        it('should handle 500 errors (internal server error)', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 500,
                error: { message: 'Internal Server Error' },
                statusText: 'Internal Server Error'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(500);
                    done();
                }
            });
        });

        it('should handle 502 errors (bad gateway)', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 502,
                error: { message: 'Bad Gateway' },
                statusText: 'Bad Gateway'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(502);
                    done();
                }
            });
        });

        it('should handle 503 errors (service unavailable)', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 503,
                error: { message: 'Service Unavailable' },
                statusText: 'Service Unavailable'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(503);
                    done();
                }
            });
        });

        it('should handle 504 errors (gateway timeout)', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 504,
                error: { message: 'Gateway Timeout' },
                statusText: 'Gateway Timeout'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(504);
                    done();
                }
            });
        });

        it('should handle network errors (no status)', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                error: { message: 'Cannot connect' },
                statusText: 'Unknown'
            });
            mockError.url = 'http://localhost/api';

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(0);
                    done();
                }
            });
        });

        it('should handle errors with default message', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 599,
                error: { message: 'Unknown Error' },
                statusText: 'Unknown'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error.status).toBe(599);
                    done();
                }
            });
        });

        it('should call errorHandler.handleHttpError with correct parameters', (done) => {
            const mockRequest = new HttpRequest('POST', '/api/test', { data: 'test' });
            const mockError = new HttpErrorResponse({
                status: 500,
                error: { message: 'Internal Server Error' },
                statusText: 'Internal Server Error'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: () => {
                    expect(errorHandler.handleHttpError).toHaveBeenCalled();
                    const callArgs = errorHandler.handleHttpError.calls.first().args[0];
                    expect(callArgs.message).toContain('Internal Server Error');
                    expect(callArgs.statusCode).toBe(500);
                    expect(callArgs.url).toBe('/api/test');
                    expect(callArgs.method).toBe('POST');
                    done();
                }
            });
        });

        it('should re-throw the error after handling', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const mockError = new HttpErrorResponse({
                status: 500,
                error: { message: 'Internal Server Error' },
                statusText: 'Internal Server Error'
            });

            const errorObservable = throwError(() => mockError);

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(error).toBe(mockError);
                    expect(error.status).toBe(500);
                    done();
                }
            });
        });

        it('should handle errors without error property', (done) => {
            const mockRequest = new HttpRequest('GET', '/api/test');
            const errorObservable = throwError(() => new Error('Network error'));

            interceptor.intercept(mockRequest, { handle: () => errorObservable }).subscribe({
                error: (error) => {
                    expect(errorHandler.handleHttpError).toHaveBeenCalled();
                    done();
                }
            });
        });
    });
});

describe('HttpErrorInterceptorFactory', () => {
    it('should create interceptor with provided error handler', () => {
        const errorHandler = new ErrorHandlerService({ navigate: () => { } } as any);
        const factory = HttpErrorInterceptorFactory(errorHandler);

        expect(factory).toBeDefined();
        expect(typeof factory).toBe('function');
    });
});

describe('HTTP_ERROR_INTERCEPTOR_PROVIDER', () => {
    it('should provide the correct token', () => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [
                {
                    provide: HTTP_INTERCEPTORS,
                    useClass: HttpErrorInterceptor,
                    multi: true,
                },
            ],
        });

        const provider = TestBed.inject({} as any);
        expect(TestBed.inject(HttpErrorInterceptor)).toBeTruthy();
    });
});