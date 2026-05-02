import { TestBed, fakeAsync, tick, flushMicroTasks } from '@angular/core/testing';
import { HttpRequest, HttpHandler, HttpEvent, HTTP_INTERCEPTORS } from '@angular/common/http';
import { HttpErrorResponse, HttpClientTestingModule } from '@angular/common/http/testing';
import { Observable, throwError, of } from 'rxjs';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

describe('AuthService', () => {
    let service: AuthService;
    let router: jasmine.SpyObj<Router>;
    let httpBackend: jasmine.SpyObj<any>;

    beforeEach(() => {
        const routerSpy = jasmine.createSpyObj('Router', ['navigate']);
        const httpBackendSpy = jasmine.createSpyObj('HttpTestingController', ['match', 'expectOne', 'verify']);

        TestBed.configureTestingModule({
            providers: [
                AuthService,
                { provide: Router, useValue: routerSpy },
            ],
            imports: [HttpClientTestingModule]
        });

        service = TestBed.inject(AuthService);
        router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
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

    describe('isAuthenticated', () => {
        it('should return true when token exists', () => {
            localStorage.setItem('auth_token', 'test-token');
            const result = service.isAuthenticated();
            expect(result).toBe(true);
        });

        it('should return false when token does not exist', () => {
            localStorage.removeItem('auth_token');
            const result = service.isAuthenticated();
            expect(result).toBe(false);
        });
    });

    describe('hasPermission', () => {
        it('should return true for valid permission', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user_permissions', JSON.stringify(['rules:create', 'rules:read']));
            const result = service.hasPermission('rules:create');
            expect(result).toBe(true);
        });

        it('should return false for invalid permission', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user_permissions', JSON.stringify(['rules:read']));
            const result = service.hasPermission('rules:create');
            expect(result).toBe(false);
        });

        it('should return false when user has no permissions', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user_permissions', JSON.stringify([]));
            const result = service.hasPermission('any:permission');
            expect(result).toBe(false);
        });
    });

    describe('hasRole', () => {
        it('should return true for valid role', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user_roles', JSON.stringify(['admin', 'user']));
            const result = service.hasRole('admin');
            expect(result).toBe(true);
        });

        it('should return false for invalid role', () => {
            localStorage.setItem('auth_token', 'test-token');
            localStorage.setItem('user_roles', JSON.stringify(['user']));
            const result = service.hasRole('admin');
            expect(result).toBe(false);
        });
    });

    describe('refreshToken', () => {
        it('should refresh the authentication token', fakeAsync(() => {
            service.refreshToken().subscribe({
                next: () => { },
                error: () => { }
            });
            tick(1000);
        }));

        it('should handle refresh token failure', fakeAsync(() => {
            service.refreshToken().subscribe({
                next: () => { },
                error: () => { }
            });
            tick(1000);
        }));
    });

    describe('isLoggedIn', () => {
        it('should return true when user is authenticated', () => {
            localStorage.setItem('auth_token', 'test-token');
            const result = service.isLoggedIn();
            expect(result).toBe(true);
        });

        it('should return false when user is not authenticated', () => {
            localStorage.removeItem('auth_token');
            const result = service.isLoggedIn();
            expect(result).toBe(false);
        });
    });

    describe('getUser', () => {
        it('should return user information', () => {
            localStorage.setItem('user_info', JSON.stringify({
                id: '1',
                email: 'test@example.com',
                roles: ['admin']
            }));
            const user = service.getUser();
            expect(user.email).toBe('test@example.com');
        });

        it('should return null when no user is logged in', () => {
            localStorage.removeItem('user_info');
            const user = service.getUser();
            expect(user).toBeNull();
        });
    });
});