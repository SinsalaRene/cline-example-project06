import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';

export interface ApiResponse<T> {
    items?: T[];
    total?: number;
    page?: number;
    pageSize?: number;
    totalPages?: number;
    status?: string;
    detail?: string;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
    private http = inject(HttpClient);
    private baseUrl = '/api/v1';

    private getHeaders(headers?: HttpHeaders): HttpHeaders {
        const token = localStorage.getItem('auth_token');
        if (token) {
            headers = headers?.set('Authorization', `Bearer ${token}`);
        }
        return headers || new HttpHeaders({ 'Content-Type': 'application/json' });
    }

    get<T>(endpoint: string, params?: HttpParams): Observable<ApiResponse<T>> {
        return this.http.get<ApiResponse<T>>(`${this.baseUrl}${endpoint}`, {
            headers: this.getHeaders(),
            params
        }).pipe(
            retry(1),
            catchError(this.handleError)
        );
    }

    post<T>(endpoint: string, body: any): Observable<T> {
        return this.http.post<T>(`${this.baseUrl}${endpoint}`, body, {
            headers: this.getHeaders()
        }).pipe(
            retry(1),
            catchError(this.handleError)
        );
    }

    put<T>(endpoint: string, body: any): Observable<T> {
        return this.http.put<T>(`${this.baseUrl}${endpoint}`, body, {
            headers: this.getHeaders()
        }).pipe(
            retry(1),
            catchError(this.handleError)
        );
    }

    delete<T>(endpoint: string): Observable<T> {
        return this.http.delete<T>(`${this.baseUrl}${endpoint}`, {
            headers: this.getHeaders()
        }).pipe(
            retry(1),
            catchError(this.handleError)
        );
    }

    private handleError(error: any) {
        let errorMessage = 'An error occurred';
        if (error.error?.detail) {
            errorMessage = error.error.detail;
        } else if (error.error?.message) {
            errorMessage = error.error.message;
        }
        return throwError(() => new Error(errorMessage));
    }
}