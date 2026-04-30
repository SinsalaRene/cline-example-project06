import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

export interface LoginResponse {
    token: string;
    user: {
        object_id: string;
        display_name: string;
        email: string;
        roles?: string[];
    };
}

@Component({
    selector: 'app-login',
    standalone: false,
    templateUrl: './login.component.html',
    styleUrls: ['./login.component.css'],
})
export class LoginComponent implements OnInit {
    loginForm!: FormGroup;
    isLoading = false;
    errorMessage = '';
    showPassword = false;

    constructor(
        private fb: FormBuilder,
        private authService: AuthService,
        private router: Router
    ) { }

    ngOnInit(): void {
        this.loginForm = this.fb.group({
            username: ['', [Validators.required, Validators.email]],
            password: ['', [Validators.required]],
        });
    }

    /**
     * Attempt to log in with the provided credentials.
     */
    onSubmit(): void {
        if (this.loginForm.invalid) {
            this.loginForm.markAllAsTouched();
            return;
        }

        const { username, password } = this.loginForm.value;
        this.isLoading = true;
        this.errorMessage = '';

        this.authService.login(username, password).subscribe({
            next: (response: LoginResponse) => {
                this.isLoading = false;
                this.router.navigate(['/dashboard']);
            },
            error: (error: any) => {
                this.isLoading = false;
                if (error?.error?.detail) {
                    this.errorMessage = error.error.detail;
                } else if (error?.status === 401) {
                    this.errorMessage = 'Invalid credentials';
                } else if (error?.status === 403) {
                    this.errorMessage = 'Access denied';
                } else {
                    this.errorMessage = 'Login failed. Please try again.';
                }
            }
        });
    }

    /**
     * Get form control shortcuts for template access.
     */
    get username(): any {
        return this.loginForm.get('username');
    }

    get password(): any {
        return this.loginForm.get('password');
    }

    /**
     * Toggle password visibility.
     */
    togglePasswordVisibility(): void {
        this.showPassword = !this.showPassword;
    }

    /**
     * Handle Azure AD login (single sign-on flow).
     */
    onAzureLogin(): void {
        const redirectUrl = `${window.location.origin}/login`;
        const azureUrl = `https://login.microsoftonline.com/common/oauth2/v2.0/authorize?` +
            `client_id=${encodeURIComponent('YOUR_CLIENT_ID')}` +
            `&response_type=id_token token` +
            `&redirect_uri=${encodeURIComponent(redirectUrl)}` +
            `&response_mode=form_post` +
            `&scope=openid profile` +
            `&state=${encodeURIComponent(redirectUrl)}`;
        window.location.href = azureUrl;
    }
}
