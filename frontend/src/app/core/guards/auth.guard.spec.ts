import { TestBed } from '@angular/core/testing';
import { Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { AuthGuard, ReverseAuthGuard, PublicGuard, RoleGuard, PermissionGuard } from './auth.guard';

describe('AuthGuard', () => {
    let guard: AuthGuard;
    let authService: jasmine.SpyObj<AuthService>;
    let router: jasmine.SpyObj<Router>;

    beforeEach(() => {
        const authServiceSpy = jasmine.createSpyObj('AuthService', ['isLoggedIn'], { isLoggedIn$: of(false) });
        const routerSpy = jasmine.createSpyObj('Router', ['createUrlTree']);

        TestBed.configureTestingModule({
            providers: [
                AuthGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(AuthGuard);
        authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
        router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is authenticated', () => {
        it('should return true', () => {
            authService.isLoggedIn.and.returnValue(true);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });

    describe('when user is not authenticated', () => {
        it('should redirect to login', () => {
            authService.isLoggedIn.and.returnValue(false);
            router.createUrlTree.and.returnValue({} as UrlTree);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/login']);
        });
    });
});

describe('ReverseAuthGuard', () => {
    let guard: ReverseAuthGuard;
    let authService: jasmine.SpyObj<AuthService>;
    let router: jasmine.SpyObj<Router>;

    beforeEach(() => {
        const authServiceSpy = jasmine.createSpyObj('AuthService', ['isLoggedIn'], { isLoggedIn$: of(false) });
        const routerSpy = jasmine.createSpyObj('Router', ['createUrlTree']);

        TestBed.configureTestingModule({
            providers: [
                ReverseAuthGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(ReverseAuthGuard);
        authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
        router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is already authenticated', () => {
        it('should redirect to dashboard', () => {
            authService.isLoggedIn.and.returnValue(true);
            router.createUrlTree.and.returnValue({} as UrlTree);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/dashboard']);
        });
    });

    describe('when user is not authenticated', () => {
        it('should allow access', () => {
            authService.isLoggedIn.and.returnValue(false);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });
});

describe('PublicGuard', () => {
    let guard: PublicGuard;
    let authService: jasmine.SpyObj<AuthService>;
    let router: jasmine.SpyObj<Router>;

    beforeEach(() => {
        const authServiceSpy = jasmine.createSpyObj('AuthService', ['isLoggedIn'], { isLoggedIn$: of(false) });
        const routerSpy = jasmine.createSpyObj('Router', ['createUrlTree']);

        TestBed.configureTestingModule({
            providers: [
                PublicGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(PublicGuard);
        authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
        router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is authenticated', () => {
        it('should redirect to dashboard', () => {
            authService.isLoggedIn.and.returnValue(true);
            router.createUrlTree.and.returnValue({} as UrlTree);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/dashboard']);
        });
    });

    describe('when user is not authenticated', () => {
        it('should allow access', () => {
            authService.isLoggedIn.and.returnValue(false);
            const result = guard.canActivate({} as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });
});

describe('RoleGuard', () => {
    let guard: RoleGuard;
    let authService: jasmine.SpyObj<AuthService>;
    let router: jasmine.SpyObj<Router>;

    beforeEach(() => {
        const authServiceSpy = jasmine.createSpyObj('AuthService', ['isLoggedIn', 'userSubject'], { userSubject: new BehaviorSubject(null) });
        const routerSpy = jasmine.createSpyObj('Router', ['createUrlTree']);

        TestBed.configureTestingModule({
            providers: [
                RoleGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(RoleGuard);
        authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
        router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is not authenticated', () => {
        it('should redirect to login', () => {
            authService.isLoggedIn.and.returnValue(false);
            router.createUrlTree.and.returnValue({} as UrlTree);
            const result = guard.canActivate({ data: { roles: ['admin'] } } as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/login']);
        });
    });

    describe('when user is authenticated with required role', () => {
        it('should allow access', () => {
            authService.isLoggedIn.and.returnValue(true);
            (authService as any).userSubject.next({ roles: ['admin', 'user'] });
            const result = guard.canActivate({ data: { roles: ['admin'] } } as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });

    describe('when user is authenticated without required role', () => {
        it('should redirect to unauthorized', () => {
            authService.isLoggedIn.and.returnValue(true);
            (authService as any).userSubject.next({ roles: ['user'] });
            router.createUrlTree.and.returnValue({} as UrlTree);
            const result = guard.canActivate({ data: { roles: ['admin'] } } as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/unauthorized']);
        });
    });

    describe('when multiple roles are required', () => {
        it('should allow access if user has any of the required roles', () => {
            authService.isLoggedIn.and.returnValue(true);
            (authService as any).userSubject.next({ roles: ['editor'] });
            const result = guard.canActivate({ data: { roles: ['admin', 'editor'] } } as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });
});

describe('PermissionGuard', () => {
    let guard: PermissionGuard;
    let authService: jasmine.SpyObj<AuthService>;
    let router: jasmine.SpyObj<Router>;

    beforeEach(() => {
        const authServiceSpy = jasmine.createSpyObj('AuthService', ['isLoggedIn', 'hasPermission'], { isLoggedIn$: of(false) });
        const routerSpy = jasmine.createSpyObj('Router', ['createUrlTree']);

        TestBed.configureTestingModule({
            providers: [
                PermissionGuard,
                { provide: AuthService, useValue: authServiceSpy },
                { provide: Router, useValue: routerSpy }
            ]
        });

        guard = TestBed.inject(PermissionGuard);
        authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
        router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
    });

    it('should be created', () => {
        expect(guard).toBeTruthy();
    });

    describe('when user is not authenticated', () => {
        it('should redirect to login', () => {
            authService.isLoggedIn.and.returnValue(false);
            router.createUrlTree.and.returnValue({} as UrlTree);
            const result = guard.canActivate({ data: { permission: 'rules:create' } } as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/login']);
        });
    });

    describe('when no permission is required', () => {
        it('should allow access', () => {
            authService.isLoggedIn.and.returnValue(true);
            const result = guard.canActivate({ data: {} } as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });

    describe('when user has the required permission', () => {
        it('should allow access', () => {
            authService.isLoggedIn.and.returnValue(true);
            authService.hasPermission.and.returnValue(true);
            const result = guard.canActivate({ data: { permission: 'rules:create' } } as any, {} as RouterStateSnapshot);
            expect(result).toBe(true);
        });
    });

    describe('when user lacks required permission', () => {
        it('should redirect to unauthorized', () => {
            authService.isLoggedIn.and.returnValue(true);
            authService.hasPermission.and.returnValue(false);
            router.createUrlTree.and.returnValue({} as UrlTree);
            const result = guard.canActivate({ data: { permission: 'rules:create' } } as any, {} as RouterStateSnapshot);
            expect(router.createUrlTree).toHaveBeenCalledWith(['/unauthorized']);
        });
    });
});