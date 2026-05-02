import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';

describe('ApiService', () => {
    let service: ApiService;
    let httpTestingController: HttpTestingController;
    let authService: jasmine.SpyObj<AuthService>;

    beforeEach(() => {
        const authServiceSpy = jasmine.createSpyObj('AuthService', ['isAuthenticated']);

        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [
                ApiService,
                { provide: AuthService, useValue: authServiceSpy }
            ]
        });

        service = TestBed.inject(ApiService);
        httpTestingController = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpTestingController.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('get', () => {
        it('should make GET request to the correct URL', () => {
            service.get('test').subscribe();
            const req = httpTestingController.expectOne('/api/test');
            expect(req.request.method).toBe('GET');
            req.flush({ data: 'test' });
        });

        it('should handle GET request errors', () => {
            service.get('test').subscribe({
                next: () => fail('should have failed'),
                error: () => { }
            });
            const req = httpTestingController.expectOne('/api/test');
            req.flush({ error: 'Not found' }, { status: 404, statusText: 'Not Found' });
        });
    });

    describe('post', () => {
        it('should make POST request with body', () => {
            service.post('test', { name: 'test' }).subscribe();
            const req = httpTestingController.expectOne('/api/test');
            expect(req.request.method).toBe('POST');
            expect(req.request.body).toEqual({ name: 'test' });
            req.flush({ data: 'created' });
        });
    });

    describe('put', () => {
        it('should make PUT request with body', () => {
            service.put('test/1', { name: 'updated' }).subscribe();
            const req = httpTestingController.expectOne('/api/test/1');
            expect(req.request.method).toBe('PUT');
            expect(req.request.body).toEqual({ name: 'updated' });
            req.flush({ data: 'updated' });
        });
    });

    describe('delete', () => {
        it('should make DELETE request', () => {
            service.delete('test/1').subscribe();
            const req = httpTestingController.expectOne('/api/test/1');
            expect(req.request.method).toBe('DELETE');
            req.flush({});
        });
    });
});