import { ComponentFixture, TestBed, fakeAsync, tick, flush } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { of, throwError } from 'rxjs';
import { LoginComponent } from './login/login.component';
import { AuthService } from '../../core/services/auth.service';
import { HttpClientModule } from '@angular/common/http';
import { NO_ERRORS_SCHEMA, signal } from '@angular/core';

describe('LoginComponent', () => {
    let component: LoginComponent;
    let fixture: ComponentFixture<LoginComponent>;
    let authService: AuthService;
    let router: Router;

    // Mock AuthService
    const mockAuthService: Partial<AuthService> = {
        isLoggedIn: signal<boolean>(false),
        login: jest.fn().mockReturnValue(of({
            token: 'mock_token',
            user: {
                object_id: 'mock-user-id',
                display_name: 'Test User',
                email: 'test@example.com',
                roles: ['admin']
            }
        })),
        logout: jest.fn(),
        hasRole: () => false,
        hasPermission: () => false,
    };

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                ReactiveFormsModule,
                RouterTestingModule,
                HttpClientModule,
            ],
            declarations: [LoginComponent],
            providers: [
                { provide: AuthService, useValue: mockAuthService },
            ],
            schemas: [NO_ERRORS_SCHEMA],
        }).compileComponents();

        fixture = TestBed.createComponent(LoginComponent);
        component = fixture.componentInstance;
        authService = TestBed.inject(AuthService);
        router = TestBed.inject(Router);
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize the login form', () => {
        expect(component.loginForm).toBeDefined();
        expect(component.loginForm.get('username')).toBeTruthy();
        expect(component.loginForm.get('password')).toBeTruthy();
    });

    it('should mark form as invalid when empty', () => {
        expect(component.loginForm.valid).toBe(false);
    });

    it('should require email field', () => {
        const username = component.loginForm.get('username');
        expect(username?.valid).toBe(false);
    });

    it('should require password field', () => {
        const password = component.loginForm.get('password');
        expect(password?.valid).toBe(false);
    });

    it('should set isLoading to true during submission', () => {
        component.onSubmit();
        expect(component.isLoading).toBe(true);
    });

    it('should call authService.login on submit', () => {
        const loginSpy = jest.spyOn(authService, 'login');
        component.loginForm.setValue({
            username: 'test@example.com',
            password: 'password123'
        });
        component.onSubmit();
        expect(loginSpy).toHaveBeenCalledWith('test@example.com', 'password123');
    });

    it('should not call login if form is invalid', () => {
        const loginSpy = jest.spyOn(authService, 'login');
        component.onSubmit();
        expect(loginSpy).not.toHaveBeenCalled();
    });

    it('should set error message on login failure (401)', () => {
        const error$ = throwError(() => ({ status: 401, error: { detail: 'Invalid credentials' } }));
        jest.spyOn(authService, 'login').mockReturnValue(error$ as any);

        component.loginForm.setValue({
            username: 'test@example.com',
            password: 'wrongpassword'
        });
        component.onSubmit();

        expect(component.isLoading).toBe(false);
        expect(component.showError).toBe(true);
        expect(component.errorMessage).toBe('Invalid email or password. Please check your credentials and try again.');
    });

    it('should handle 403 error with user-friendly message', () => {
        const error$ = throwError(() => ({ status: 403, error: { detail: 'Access denied' } }));
        jest.spyOn(authService, 'login').mockReturnValue(error$ as any);

        component.loginForm.setValue({
            username: 'test@example.com',
            password: 'password123'
        });
        component.onSubmit();

        expect(component.showError).toBe(true);
        expect(component.errorMessage).toBe('Your account is restricted. Contact your administrator.');
    });

    it('should handle unknown errors with fallback message', () => {
        const error$ = throwError(() => ({ status: 500 }));
        jest.spyOn(authService, 'login').mockReturnValue(error$ as any);

        component.loginForm.setValue({
            username: 'test@example.com',
            password: 'password123'
        });
        component.onSubmit();

        expect(component.showError).toBe(true);
        expect(component.errorType).toBe('server');
    });

    it('should handle 503 server error with appropriate message', () => {
        const error$ = throwError(() => ({ status: 503 }));
        jest.spyOn(authService, 'login').mockReturnValue(error$ as any);

        component.loginForm.setValue({
            username: 'test@example.com',
            password: 'password123'
        });
        component.onSubmit();

        expect(component.showError).toBe(true);
        expect(component.errorMessage).toBe('Authentication service is temporarily unavailable. Please try again later.');
        expect(component.errorType).toBe('server');
    });

    it('should handle 422 validation error', () => {
        const error$ = throwError(() => ({ status: 422, error: { detail: 'Bad request body' } }));
        jest.spyOn(authService, 'login').mockReturnValue(error$ as any);

        component.loginForm.setValue({
            username: 'test@example.com',
            password: 'password123'
        });
        component.onSubmit();

        expect(component.showError).toBe(true);
        expect(component.errorType).toBe('validation');
    });

    it('should toggle password visibility', () => {
        expect(component.showPassword).toBe(false);
        component.togglePasswordVisibility();
        expect(component.showPassword).toBe(true);
        component.togglePasswordVisibility();
        expect(component.showPassword).toBe(false);
    });

    it('should call onAzureLogin', () => {
        const originalHref = window.location.href;
        component.onAzureLogin();
        // Azure redirect sets window.location.href
        expect(window.location.href).toContain('login.microsoftonline.com');
    });

    it('should access username form control via loginForm.get()', () => {
        const usernameControl = component.loginForm.get('username');
        expect(usernameControl).toBeDefined();
    });

    it('should access password form control via loginForm.get()', () => {
        const passwordControl = component.loginForm.get('password');
        expect(passwordControl).toBeDefined();
    });
});
