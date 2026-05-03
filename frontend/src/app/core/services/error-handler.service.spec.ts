import { TestBed } from '@angular/core/testing';
import { ErrorHandlerService } from './error-handler.service';
import { Router } from '@angular/router';

describe('ErrorHandlerService', () => {
    let service: ErrorHandlerService;
    let router: jest.Mocked<Router>;

    beforeEach(() => {
        const routerSpy = { navigate: jest.fn(), url: '' };

        TestBed.configureTestingModule({
            providers: [
                ErrorHandlerService,
                { provide: Router, useValue: routerSpy }
            ]
        });

        service = TestBed.inject(ErrorHandlerService);
        router = TestBed.inject(Router) as jest.Mocked<Router>;
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('handleHttpError', () => {
        it('should handle HTTP errors with correct structure', () => {
            const error = {
                message: 'Internal Server Error',
                statusCode: 500,
                url: '/api/test',
                method: 'GET'
            };

            // Subscribe to capture the emitted error
            let emittedError: any;
            service.error$.subscribe((e: any) => emittedError = e);

            service.handleHttpError(error);

            expect(emittedError).toBeDefined();
            expect(emittedError.message).toBe('Internal Server Error');
            expect(emittedError.statusCode).toBe(500);
        });

        it('should return user-friendly error messages', () => {
            const error = {
                message: 'Connection timeout',
                statusCode: 0,
                url: '/api/test',
                method: 'GET'
            };

            let emittedError: any;
            service.error$.subscribe((e: any) => emittedError = e);

            service.handleHttpError(error);

            expect(emittedError).toBeDefined();
            expect(emittedError.message).toContain('Unable to connect');
        });

        it('should handle network errors gracefully', () => {
            const error = {
                message: 'Network Error',
                statusCode: 0,
                url: '/api/test',
                method: 'GET'
            };

            let emittedError: any;
            service.error$.subscribe((e: any) => emittedError = e);

            service.handleHttpError(error);

            expect(emittedError).toBeDefined();
        });
    });

    describe('handleAuthError', () => {
        it('should handle authentication errors', () => {
            service.handleAuthError();
            expect(router.navigate).toHaveBeenCalledWith(['/login']);
        });

        it('should handle forbidden errors', () => {
            // For 403, navigate to /unauthorized
            (router as any).url = '';
            service.handleAuthError({ statusCode: 403 } as any);
            expect(router.navigate).toHaveBeenCalledWith(['/unauthorized']);
        });
    });

    describe('error$', () => {
        it('should emit errors to subscribers', () => {
            const error = {
                message: 'Test error',
                statusCode: 500,
                url: '/api/test',
                method: 'GET'
            };

            let emittedError: any;
            service.error$.subscribe((e: any) => emittedError = e);

            service.handleHttpError(error);
            expect(emittedError.message).toBe('Test error');
        });
    });

    describe('authError$', () => {
        it('should emit auth error signal', () => {
            let emittedAuthError: boolean = false;
            service.authError$.subscribe(() => emittedAuthError = true);

            service.handleAuthError();
            expect(emittedAuthError).toBe(true);
        });
    });

    describe('getErrorHistory', () => {
        it('should return recent error history', () => {
            const error1 = { message: 'Error 1', statusCode: 500, url: '/api/test', method: 'GET' };
            const error2 = { message: 'Error 2', statusCode: 500, url: '/api/test', method: 'GET' };

            let capturedError: any;
            service.error$.subscribe((e: any) => capturedError = e);

            service.handleHttpError(error1);
            service.handleHttpError(error2);

            const history = service.getErrorHistory(10);
            expect(history.length).toBe(2);
        });
    });

    describe('clearHistory', () => {
        it('should clear error history', () => {
            const error = { message: 'Test error', statusCode: 500, url: '/api/test', method: 'GET' };

            let capturedError: any;
            service.error$.subscribe((e: any) => capturedError = e);

            service.handleHttpError(error);
            service.clearHistory();

            const history = service.getErrorHistory(10);
            expect(history.length).toBe(0);
        });
    });
});
