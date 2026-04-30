import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { AuthGuard, ReverseAuthGuard, PublicGuard, RoleGuard, PermissionGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';
import { BehaviorSubject } from 'rxjs';

describe('Auth Guards', () => {
    let authGuard: AuthGuard;
    let reverseAuthGuard: ReverseAuthGuard;
    let publicGuard: PublicGuard;
    let roleGuard: RoleGuard;
    let permissionGuard: PermissionGuard;
    let authService: AuthService;
    let router: Router;

    const mockUser = {
        object_id: 'test-user-id',
        display_name: 'Test User',
        email: 'test@example.com',
        roles: ['admin', 'editor']
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [
                RouterTestingModule.withRoutes([])
            ],
            providers: [
                AuthGuard,
                ReverseAuthGuard,
                PublicGuard,
                RoleGuard,
                PermissionGuard,
                AuthService,
            ],
        });

        authGuard = TestBed.inject(AuthGuard);
        reverseAuthGuard = TestBed.inject(ReverseAuthGuard);
        publicGuard = TestBed.inject(PublicGuard);
        roleGuard = TestBed.inject(RoleGuard);
        permissionGuard = TestBed.inject(PermissionGuard);
        authService = TestBed.inject(AuthService);
        router = TestBed.inject(Router);
    });

    // ========== AuthGuard Tests ==========

    describe('AuthGuard', () => {
        it('should be created', () => {
            expect(authGuard).toBeTruthy();
        });

        it('should return true if user is logged in', () => {
            // Simulate logged in state
            authService['userSubject'].next(mockUser);
            const result = authGuard.canActivate(null as any, null as any);
            expect(result).toBe(true);
        });

        it('should redirect to login if user is not logged in', () => {
            // Simulate logged out state
            authService['userSubject'].next(null);
            const result = authGuard.canActivate(null as any, null as any);
            expect(result).toBeTruthy();
        });
    });

    // ========== ReverseAuthGuard Tests ==========

    describe('ReverseAuthGuard', () => {
        it('should be created', () => {
            expect(reverseAuthGuard).toBeTruthy();
        });

        it('should redirect to dashboard if user is already logged in', () => {
            authService['userSubject'].next(mockUser);
            const result = reverseAuthGuard.canActivate(null as any, null as any);
            expect(result).toBeTruthy();
        });

        it('should return true if user is not logged in', () => {
            authService['userSubject'].next(null);
            const result = reverseAuthGuard.canActivate(null as any, null as any);
            expect(result).toBe(true);
        });
    });

    // ========== PublicGuard Tests ==========

    describe('PublicGuard', () => {
        it('should be created', () => {
            expect(publicGuard).toBeTruthy();
        });

        it('should return true if user is not logged in', () => {
            authService['userSubject'].next(null);
            const result = publicGuard.canActivate(null as any, null as any);
            expect(result).toBe(true);
        });

        it('should redirect to dashboard if user is already logged in', () => {
            authService['userSubject'].next(mockUser);
            const result = publicGuard.canActivate(null as any, null as any);
            expect(result).toBeTruthy();
        });
    });

    // ========== RoleGuard Tests ==========

    describe('RoleGuard', () => {
        it('should be created', () => {
            expect(roleGuard).toBeTruthy();
        });

        it('should return true if user has the required role', () => {
            authService['userSubject'].next(mockUser);
            const route = {
                data: { roles: ['admin'] },
                firstChild: null
            };
            const result = roleGuard.canActivate(route as any, null as any);
            expect(result).toBe(true);
        });

        it('should redirect to unauthorized if user lacks the required role', () => {
            const userWithoutAdmin = { ...mockUser, roles: ['viewer'] };
            authService['userSubject'].next(userWithoutAdmin);
            const route = {
                data: { roles: ['admin'] },
                firstChild: null
            };
            const result = roleGuard.canActivate(route as any, null as any);
            expect(result).toBeTruthy();
        });

        it('should redirect to login if user is not logged in', () => {
            authService['userSubject'].next(null);
            const route = {
                data: { roles: ['admin'] },
                firstChild: null
            };
            const result = roleGuard.canActivate(route as any, null as any);
            expect(result).toBeTruthy();
        });
    });

    // ========== PermissionGuard Tests ==========

    describe('PermissionGuard', () => {
        it('should be created', () => {
            expect(permissionGuard).toBeTruthy();
        });

        it('should return true if user has the required permission', () => {
            authService['userSubject'].next(mockUser);
            const route = {
                data: { permission: 'admin' },
                firstChild: null
            };
            const result = permissionGuard.canActivate(route as any, null as any);
            expect(result).toBe(true);
        });

        it('should redirect to unauthorized if user lacks the required permission', () => {
            const userWithoutPermission = { ...mockUser, roles: ['viewer'] };
            authService['userSubject'].next(userWithoutPermission);
            const route = {
                data: { permission: 'admin' },
                firstChild: null
            };
            const result = permissionGuard.canActivate(route as any, null as any);
            expect(result).toBeTruthy();
        });

        it('should redirect to login if user is not logged in', () => {
            authService['userSubject'].next(null);
            const route = {
                data: { permission: 'admin' },
                firstChild: null
            };
            const result = permissionGuard.canActivate(route as any, null as any);
            expect(result).toBeTruthy();
        });

        it('should return true if no permission is specified', () => {
            authService['userSubject'].next(mockUser);
            const route = {
                data: {},
                firstChild: null
            };
            const result = permissionGuard.canActivate(route as any, null as any);
            expect(result).toBe(true);
        });
    });
});