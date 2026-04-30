import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, tap } from 'rxjs';

export interface UserInfo {
    object_id: string;
    display_name: string;
    email: string;
    roles?: string[];
}

@Injectable({ providedIn: 'root' })
export class AuthService {
    private http = inject(HttpClient);

    private userSubject = new BehaviorSubject<UserInfo | null>(null);
    public user$ = this.userSubject.asObservable();

    public isLoggedIn = signal<boolean>(false);
    public userName = signal<string>('');

    constructor() {
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
            this.userSubject.next(JSON.parse(savedUser));
            this.isLoggedIn.set(true);
            const user = JSON.parse(savedUser);
            this.userName.set(user.display_name);
        }
    }

    login(username: string, password: string): Observable<any> {
        return this.http.post<any>('/api/v1/auth/login', { username, password }).pipe(
            tap(response => {
                localStorage.setItem('auth_token', response.token);
                localStorage.setItem('user', JSON.stringify(response.user));
                this.userSubject.next(response.user);
                this.isLoggedIn.set(true);
                this.userName.set(response.user.display_name);
            })
        );
    }

    loginWithToken(token: string, user: UserInfo) {
        localStorage.setItem('auth_token', token);
        localStorage.setItem('user', JSON.stringify(user));
        this.userSubject.next(user);
        this.isLoggedIn.set(true);
        this.userName.set(user.display_name);
    }

    logout() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        this.userSubject.next(null);
        this.isLoggedIn.set(false);
        this.userName.set('');
    }

    hasRole(role: string): boolean {
        const user = this.userSubject.value;
        return user?.roles?.includes(role) ?? false;
    }

    hasPermission(permission: string): boolean {
        return this.hasRole(permission);
    }
}