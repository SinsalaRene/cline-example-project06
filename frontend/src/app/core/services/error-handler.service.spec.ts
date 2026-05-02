import { TestBed } from '@angular/core/testing';
import { ErrorHandlerService } from './error-handler.service';
import { Router } from '@angular/router';

describe('ErrorHandlerService', () => {
    let service: ErrorHandlerService;
    let router: jasmine.SpyObj<Router>;

    beforeEach(() => {
        const routerSpy = jasmine.createSpyObj('Router', ['navigate']);

        TestBed.configureTestingModule({
            providers: [
                ErrorHandlerService,
                { provide: Router, useValue: routerSpy }
            ]
        });

        service = TestBed.inject(ErrorHandlerService);
        router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
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

            const result = service.handleHttpError(error);
            expect(result.message).toBe('Internal Server Error');
            expect(result.statusCode).toBe(500);
        });

        it('should return user-friendly error messages', () => {
            const error = {
                message: 'Connection timeout',
                statusCode: 0,
                url: '/api/test',
                method: 'GET'
            };

            const result = service.handleHttpError(error);
            expect(result.message).toContain('Unable to connect');
        });

        it('should handle network errors gracefully', () => {
            const error = {
                message: 'Network Error',
                statusCode: 0,
                url: '/api/test',
                method: 'GET'
            };

            const result = service.handleHttpError(error);
            expect(result.message).toBeDefined();
        });
    });

    describe('handleAuthError', () => {
        it('should handle authentication errors', () => {
            const error = new HttpErrorResponse({
                status: 401,
                error: { message: 'Unauthorized' }
            });

            service.handleAuthError(error);
            expect(router.navigate).toHaveBeenCalledWith(['/login']);
        });

        it('should handle forbidden errors', () => {
            const error = new HttpErrorResponse({
                status: 403,
                error: { message: 'Forbidden' }
            });

            service.handleAuthError(error);
            expect(router.navigate).toHaveBeenCalledWith(['/unauthorized']);
        });
    });

    describe('showErrorNotification', () => {
        it('should display error notification', () => {
            service.showErrorNotification('Test error');
        });
    });
});