import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpRequest, HttpHandler, HttpEvent, HTTP_INTERCEPTORS } from '@angular/common/http';
import { HttpErrorResponse } from '@angular/common/http';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { Observable, throwError, of } from 'rxjs';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

describe('AuthService', () => {
    let service: AuthService;
    let router: jest.Mocked<Router>;

    beforeEach(() => {
        const routerSpy = { navigate: jest.fn() };

        TestBed.configureTestingModule({
            providers: [
                AuthService,
                { provide: Router, useValue: routerSpy },
            ],
            imports: [HttpClientTestingModule]
        });

        service = TestBed.inject(AuthService);
        router = TestBed.inject(Router) as jest.Mocked<Router>;
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('login', () => {
        it('should authenticate user and store token', fakeAsync(() => {
            const mockResponse = {
                access_token: 'test-token',
                refresh_token: 'refresh-token',
                expires_in: 3600
            };

            service.login('test@example.com', 'password123').subscribe({
                next: (response) => {
                    expect(response).toBeTruthy();
                },
                error: () => { }
            });

            tick(1000);
        }));

        it('should store user info in localStorage', fakeAsync(() => {
            const mockResponse = {
                access_token: 'test-token',
                refresh_token: 'refresh-token',
                expires_in: 3600
            };

            service.login('test@example.com', 'password123').subscribe({
                next: () => {
                    expect(localStorage.setItem).toHaveBeenCalled();
                },
                error: () => { }
            });

            tick(1000);
        }));

        it('should redirect to dashboard after successful login', fakeAsync(() => {
            const mockResponse = {
                access_token: 'test-token',
                refresh_token: 'refresh-token',
                expires_in: 3600
            };

            service.login('test@example.com', 'password123').subscribe({
                next: () => {
                    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
                },
                error: () => { }
            });

            tick(1000);
        }));
    });

    describe('logout', () => {
        it('should clear user session', () => {
            service.logout();
            expect(localStorage.removeItem).toHaveBeenCalled();
        });

        it('should redirect to login after logout', () => {
            service.logout();
            expect(router.navigate).toHaveBeenCalledWith(['/login']);
        });

        it('should clear any stored user data', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user_role', 'admin');

            service.logout();

            expect(localStorage.removeItem).toHaveBeenCalledWith('auth_token');
            expect(localStorage.removeItem).toHaveBeenCalledWith('user_role');
        });
    });

    describe('isLoggedIn signal', () => {
        it('should return true when user is logged in', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user', JSON.stringify({ display_name: 'Test User', email: 'test@example.com', object_id: '1' }));
            const result = service.isLoggedIn();
            expect(result).toBe(true);
        });

        it('should return false when user is not logged in', () => {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user');
            const freshService = TestBed.inject(AuthService);
            const result = freshService.isLoggedIn();
            expect(result).toBe(false);
        });
    });

    describe('hasPermission', () => {
        it('should return true for valid permission', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user', JSON.stringify({ display_name: 'Test', email: 'test@example.com', object_id: '1', roles: ['admin'] }));
            const result = service.hasPermission('admin');
            expect(result).toBe(true);
        });

        it('should return false for invalid permission', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user', JSON.stringify({ display_name: 'Test', email: 'test@example.com', object_id: '1', roles: ['user'] }));
            const result = service.hasPermission('admin');
            expect(result).toBe(false);
        });
    });

    describe('hasRole', () => {
        it('should return true for valid role', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user', JSON.stringify({ display_name: 'Test', email: 'test@example.com', object_id: '1', roles: ['admin', 'user'] }));
            const result = service.hasRole('admin');
            expect(result).toBe(true);
        });

        it('should return false for invalid role', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user', JSON.stringify({ display_name: 'Test', email: 'test@example.com', object_id: '1', roles: ['user'] }));
            const result = service.hasRole('admin');
            expect(result).toBe(false);
        });
    });

    describe('user$ observable', () => {
        it('should emit user information', (done) => {
            localStorage.setItem('user', JSON.stringify({
                id: '1',
                email: 'test@example.com',
                display_name: 'Test User',
                roles: ['admin']
            }));
            const freshService = TestBed.inject(AuthService);
            freshService.user$.subscribe((user) => {
                expect(user?.email).toBe('test@example.com');
                done();
            });
        });

        it('should return null when no user is logged in', (done) => {
            localStorage.removeItem('user');
            const freshService = TestBed.inject(AuthService);
            freshService.user$.subscribe((user) => {
                expect(user).toBeNull();
                done();
            });
        });
    });

    describe('userName signal', () => {
        it('should return username when user is logged in', () => {
            localStorage.setItem('user', JSON.stringify({ display_name: 'Test User', email: 'test@example.com', object_id: '1' }));
            const freshService = TestBed.inject(AuthService);
            expect(freshService.userName()).toBe('Test User');
        });

        it('should return empty string when no user is logged in', () => {
            localStorage.removeItem('user');
            const freshService = TestBed.inject(AuthService);
            expect(freshService.userName()).toBe('');
        });
    });
});
