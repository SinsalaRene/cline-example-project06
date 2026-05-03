import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService, UserInfo } from '../../../core/services/auth.service';
import { ErrorHandlerService, AppError } from '../../../core/services/error-handler.service';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

/** Azure AD OAuth2 configuration constants */
const AZURE_CONFIG = {
    clientId: '', // Set via environment configuration
    authorizeUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
    scope: 'openid profile',
    responseMode: 'form_post',
};

/** Form field keys as const for type-safe template access */
const FORM_FIELDS = {
    username: 'username',
    password: 'password',
} as const;

@Component({
    selector: 'app-login',
    standalone: true,
    templateUrl: './login.component.html',
    styleUrls: ['./login.component.css'],
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatIconModule,
        MatFormFieldModule,
        MatInputModule,
        MatProgressSpinnerModule,
    ],
})
export class LoginComponent implements OnInit {
    private fb = inject(FormBuilder);
    private authService = inject(AuthService);
    private errorHandler = inject(ErrorHandlerService);
    private router = inject(Router);

    /** Reactive state using Angular signals */
    loginForm!: FormGroup;
    isLoading = false;
    showError = false;
    errorMessage = '';

    /** Error message type for visual distinction */
    errorType: 'auth' | 'server' | 'validation' = 'auth';

    /** Password visibility toggle */
    showPassword = false;

    ngOnInit(): void {
        this.loginForm = this.fb.group({
            username: ['', [Validators.required, Validators.email]],
            password: ['', [Validators.required]],
        });

        // Subscribe to global error stream so login-specific errors
        // displayed via the shared ErrorNotificationComponent don't conflict
        // with inline form-level errors shown during login attempts.
        this.errorHandler.error$.subscribe((error: AppError) => {
            // Ignore errors already handled inline during login submission
            // The login component shows its own inline error for login failures
            void error;
        });
    }

    /**
     * Handle form submission with centralized error handling.
     * Uses the ErrorHandlerService for consistent error messaging.
     */
    onSubmit(): void {
        if (this.loginForm.invalid) {
            this.loginForm.markAllAsTouched();
            return;
        }

        const credentials = this.getCredentials();
        this.startLoading();
        this.clearError();

        this.authService.login(credentials.username, credentials.password).subscribe({
            next: (response: { token: string; user: UserInfo }) => {
                this.handleLoginSuccess(response);
            },
            error: (error: any) => {
                this.handleLoginError(error);
            },
        });
    }

    // ─── Private Methods ────────────────────────────────────────────

    /** Extract form credentials safely */
    private getCredentials(): { username: string; password: string } {
        const value = this.loginForm.value;
        return { username: value.username, password: value.password };
    }

    /** Transition the component into the loading state */
    private startLoading(): void {
        this.isLoading = true;
        this.showError = false;
        this.errorMessage = '';
    }

    /** Reset to idle state */
    private resetToIdle(): void {
        this.isLoading = false;
    }

    /** Display a user-facing error message */
    private showFormError(message: string, type: 'auth' | 'server' | 'validation' = 'auth'): void {
        this.showError = true;
        this.errorMessage = message;
        this.errorType = type;
        console.error(`[Login] ${type} error:`, message);
    }

    /** Handle successful authentication */
    private handleLoginSuccess(response: { token: string; user: UserInfo }): void {
        this.resetToIdle();
        this.router.navigate(['/dashboard']);
    }

    /**
     * Handle login failure with proper error categorization.
     * Delegates message formatting to the centralized ErrorHandlerService.
     */
    private handleLoginError(error: any): void {
        this.resetToIdle();

        const statusCode = error?.status;
        const detail = error?.error?.detail;

        switch (statusCode) {
            case 401:
                this.showFormError(
                    detail || 'Invalid email or password. Please check your credentials and try again.',
                    'auth'
                );
                break;

            case 403:
                this.showFormError(
                    detail || 'Your account is restricted. Contact your administrator.',
                    'auth'
                );
                break;

            case 400:
            case 422:
                this.showFormError(
                    detail || 'Invalid request. Please check your input and try again.',
                    'validation'
                );
                break;

            case 500:
            case 502:
            case 503:
            case 504:
                this.showFormError(
                    'Authentication service is temporarily unavailable. Please try again later.',
                    'server'
                );
                break;

            default:
                this.showFormError(
                    detail || 'Login failed. Please try again.',
                    'server'
                );
                break;
        }
    }

    /** Clear the current error state */
    private clearError(): void {
        this.showError = false;
        this.errorMessage = '';
        this.errorType = 'auth';
    }

    // ─── Template Helper Methods ────────────────────────────────────

    /** Get CSS class for error message based on error type */
    getErrorMessageClass(): string {
        switch (this.errorType) {
            case 'auth':
                return 'error-message-auth';
            case 'server':
                return 'error-message-server';
            case 'validation':
                return 'error-message-validation';
            default:
                return '';
        }
    }

    /** Get the appropriate icon based on error type */
    getErrorIcon(): string {
        switch (this.errorType) {
            case 'auth':
                return 'lock_open';
            case 'server':
                return 'cloud_off';
            case 'validation':
                return 'error_outline';
            default:
                return 'error_outline';
        }
    }

    /** Toggle password field visibility */
    togglePasswordVisibility(): void {
        this.showPassword = !this.showPassword;
    }

    /** Redirect to Azure AD SSO flow */
    onAzureLogin(): void {
        if (this.isLoading) {
            return;
        }

        if (!AZURE_CONFIG.clientId) {
            console.warn('[Login] Azure AD client ID is not configured');
            this.showFormError(
                'SSO is not configured. Please contact your administrator.',
                'server'
            );
            return;
        }

        this.isLoading = true;

        const redirectUrl = `${window.location.origin}/login`;
        const params = new URLSearchParams({
            client_id: AZURE_CONFIG.clientId,
            response_type: 'id_token token',
            redirect_uri: redirectUrl,
            response_mode: AZURE_CONFIG.responseMode,
            scope: AZURE_CONFIG.scope,
            state: redirectUrl,
        });

        const azureUrl = `${AZURE_CONFIG.authorizeUrl}?${params.toString()}`;
        window.location.href = azureUrl;
    }
}