import { TestBed } from '@angular/core/testing';
import { Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { of, BehaviorSubject } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { AuthGuard, ReverseAuthGuard, PublicGuard, RoleGuard, PermissionGuard } from './auth.guard';

describe('AuthGuard', () => {
    let guard: AuthGuard;
    let authService: jest.Mocked<AuthService>;
    let router: jest.Mocked<Router>;

    beforeEach(() => {
        const authServiceSpy = {
            isLoggedIn: { set: jest.fn() } as unknown as import('@angular/core').WritableSignal<boolean>,
            isLoggedIn$: of(false),
            hasPermission: jest.fn(),
            userSubject: new BehaviorSubject(null)
        };
        const routerSpy = { createUrlTree: jest.fn() };

        TestBed.configureTestingModule({
            providers: [
                AuthGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(AuthGuard);
        authService = TestBed.inject(AuthService) as jest.Mocked<AuthService>;
        router = TestBed.inject(Router) as jest.Mocked<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is authenticated', () => {
        it('should return true', () => {
            (authService as any).isLoggedIn.set(true);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });

    describe('when user is not authenticated', () => {
        it('should redirect to login', () => {
            (authService as any).isLoggedIn.set(false);
            router.createUrlTree.mockReturnValue({} as UrlTree);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/login']);
        });
    });
});

describe('ReverseAuthGuard', () => {
    let guard: ReverseAuthGuard;
    let authService: jest.Mocked<AuthService>;
    let router: jest.Mocked<Router>;

    beforeEach(() => {
        const authServiceSpy = {
            isLoggedIn: { set: jest.fn() } as unknown as import('@angular/core').WritableSignal<boolean>,
            isLoggedIn$: of(false),
            hasPermission: jest.fn(),
            userSubject: new BehaviorSubject(null)
        };
        const routerSpy = { createUrlTree: jest.fn() };

        TestBed.configureTestingModule({
            providers: [
                ReverseAuthGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(ReverseAuthGuard);
        authService = TestBed.inject(ReverseAuthGuard) as any;
        authService = TestBed.inject(AuthService) as jest.Mocked<AuthService>;
        router = TestBed.inject(Router) as jest.Mocked<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is already authenticated', () => {
        it('should redirect to dashboard', () => {
            (authService as any).isLoggedIn.set(true);
            router.createUrlTree.mockReturnValue({} as UrlTree);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/dashboard']);
        });
    });

    describe('when user is not authenticated', () => {
        it('should allow access', () => {
            (authService as any).isLoggedIn.set(false);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });
});

describe('PublicGuard', () => {
    let guard: PublicGuard;
    let authService: jest.Mocked<AuthService>;
    let router: jest.Mocked<Router>;

    beforeEach(() => {
        const authServiceSpy = {
            isLoggedIn: { set: jest.fn() } as unknown as import('@angular/core').WritableSignal<boolean>,
            isLoggedIn$: of(false),
            hasPermission: jest.fn(),
            userSubject: new BehaviorSubject(null)
        };
        const routerSpy = { createUrlTree: jest.fn() };

        TestBed.configureTestingModule({
            providers: [
                PublicGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(PublicGuard);
        authService = TestBed.inject(AuthService) as jest.Mocked<AuthService>;
        router = TestBed.inject(Router) as jest.Mocked<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is authenticated', () => {
        it('should redirect to dashboard', () => {
            (authService as any).isLoggedIn.set(true);
            router.createUrlTree.mockReturnValue({} as UrlTree);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/dashboard']);
        });
    });

    describe('when user is not authenticated', () => {
        it('should allow access', () => {
            (authService as any).isLoggedIn.set(false);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });
});

describe('RoleGuard', () => {
    let guard: RoleGuard;
    let authService: jest.Mocked<AuthService>;
    let router: jest.Mocked<Router>;

    beforeEach(() => {
        const authServiceSpy = {
            isLoggedIn: { set: jest.fn() } as unknown as import('@angular/core').WritableSignal<boolean>,
            isLoggedIn$: of(false),
            hasPermission: jest.fn(),
            userSubject: new BehaviorSubject({ roles: ['admin', 'user'] })
        };
        const routerSpy = { createUrlTree: jest.fn() };

        TestBed.configureTestingModule({
            providers: [
                RoleGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(RoleGuard);
        authService = TestBed.inject(AuthService) as jest.Mocked<AuthService>;
        router = TestBed.inject(Router) as jest.Mocked<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is not authenticated', () => {
        it('should redirect to login', () => {
            (authService as any).isLoggedIn.set(false);
            router.createUrlTree.mockReturnValue({} as UrlTree);
            const result = guard.canActivate({ data: { roles: ['admin'] } } as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/login']);
        });
    });

    describe('when user is authenticated with required role', () => {
        it('should allow access', () => {
            (authService as any).isLoggedIn.set(true);
            (authService as any).userSubject.next({ roles: ['admin', 'user'] });
            const result = guard.canActivate({ data: { roles: ['admin'] } } as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });

    describe('when user is authenticated without required role', () => {
        it('should redirect to unauthorized', () => {
            (authService as any).isLoggedIn.set(true);
            (authService as any).userSubject.next({ roles: ['user'] });
            router.createUrlTree.mockReturnValue({} as UrlTree);
            const result = guard.canActivate({ data: { roles: ['admin'] } } as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/unauthorized']);
        });
    });

    describe('when multiple roles are required', () => {
        it('should allow access if user has any of the required roles', () => {
            (authService as any).isLoggedIn.set(true);
            (authService as any).userSubject.next({ roles: ['editor'] });
            const result = guard.canActivate({ data: { roles: ['admin', 'editor'] } } as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });
});

describe('PermissionGuard', () => {
    let guard: PermissionGuard;
    let authService: jest.Mocked<AuthService>;
    let router: jest.Mocked<Router>;

    beforeEach(() => {
        const authServiceSpy = {
            isLoggedIn: { set: jest.fn() } as unknown as import('@angular/core').WritableSignal<boolean>,
            isLoggedIn$: of(false),
            hasPermission: jest.fn(),
            userSubject: new BehaviorSubject(null)
        };
        const routerSpy = { createUrlTree: jest.fn() };

        TestBed.configureTestingModule({
            providers: [
                PermissionGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(PermissionGuard);
        authService = TestBed.inject(AuthService) as jest.Mocked<AuthService>;
        router = TestBed.inject(Router) as jest.Mocked<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is not authenticated', () => {
        it('should redirect to login', () => {
            (authService as any).isLoggedIn.set(false);
            router.createUrlTree.mockReturnValue({} as UrlTree);
            const result = guard.canActivate({ data: { permission: 'rules:create' } } as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/login']);
        });
    });

    describe('when no permission is required', () => {
        it('should allow access', () => {
            (authService as any).isLoggedIn.set(true);
            const result = guard.canActivate({ data: {} } as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });

    describe('when user has the required permission', () => {
        it('should allow access', () => {
            (authService as any).isLoggedIn.set(true);
            (authService as any).hasPermission.mockReturnValue(true);
            const result = guard.canActivate({ data: { permission: 'rules:create' } } as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });

    describe('when user lacks required permission', () => {
        it('should redirect to unauthorized', () => {
            (authService as any).isLoggedIn.set(true);
            (authService as any).hasPermission.mockReturnValue(false);
            router.createUrlTree.mockReturnValue({} as UrlTree);
            const result = guard.canActivate({ data: { permission: 'rules:create' } } as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/unauthorized']);
        });
    });
});