# Core Module

Core services, interceptors, and guards that provide foundational infrastructure for the Azure Firewall Management application.

## Directory Structure

```
core/
├── guards/
│   └── auth.guard.ts              # Authentication guard
├── interceptors/
│   ├── http-error.interceptor.ts  # HTTP error interceptor
│   └── http-request.interceptor.ts # HTTP request interceptor
└── services/
    ├── api.service.ts             # Core API service
    ├── auth.service.ts            # Authentication service
    ├── error-handler.service.ts   # Centralized error handling
    └── theme.service.ts           # Theme management service
```

## Services

### AuthService

Manages user authentication state and provides methods for login, logout, and token management.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `login(username, password)` | Authenticates user with credentials |
| `logout()` | Clears auth state and redirects to login |
| `isLoggedIn()` | Returns `true` if user has a valid auth token |
| `getToken()` | Returns the current auth token from localStorage |
| `getUser()` | Returns the authenticated user object |
| `getRoles()` | Returns the user's roles |

**Token Storage:**
- Auth token: `localStorage.auth_token`
- User data: `localStorage.auth_user`

**Integration:**
- Used by `HttpRequestInterceptor` to add `Authorization` headers
- Used by `AuthGuard` to protect routes

---

### ApiService

Core API client service that provides methods for making HTTP requests to the backend API.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `get(endpoint, params?)` | Makes a GET request |
| `post(endpoint, body?)` | Makes a POST request |
| `put(endpoint, body?)` | Makes a PUT request |
| `delete(endpoint)` | Makes a DELETE request |
| `patch(endpoint, body?)` | Makes a PATCH request |

**Configuration:**
- Base URL from environment configuration
- Automatically includes auth token via interceptor
- Returns typed observables for type safety

---

### ErrorHandlerService

Centralized error handling service that provides a single point for managing errors across the application.

**Key Methods:**

| Method | Parameters | Description |
|--------|-----------|-------------|
| `handleApiError(error, context?)` | `error`, `context?` | Handles raw API errors with optional context (request ID, URL, method) |
| `getErrorMessage(error)` | `error` | Extracts a clean, user-friendly message from HttpErrorResponse or other error types |
| `trackError(error, context?)` | `error`, `context?` | Placeholder for error tracking integration (Sentry, Bugsnag) |
| `handleAuthError(error?)` | `error?` | Handles auth errors: clears token, redirects to login |
| `handleValidationErrors(errors)` | `errors` | Handles field validation errors from backend |
| `handleGenericError(error)` | `error` | Handles generic application errors |
| `getErrorHistory(count)` | `count` | Returns recent error history (default 10) |

**Error Streams:**
- `error$`: Observable for all errors
- `authError$`: Observable for authentication-specific errors

**Usage:**

```typescript
constructor(private errorHandler: ErrorHandlerService) {}

handleApiCall() {
    try {
        this.apiService.get('/api/resource').subscribe();
    } catch (error) {
        this.errorHandler.handleApiError(error, {
            url: '/api/resource',
            method: 'GET',
            requestId: 'abc123'
        });
    }
}
```

---

### ThemeService

Manages application theme state (light/dark mode).

**Key Methods:**

| Method | Description |
|--------|-------------|
| `getTheme()` | Returns current theme ('light' or 'dark') |
| `setTheme(theme)` | Sets the theme |
| `toggleTheme()` | Toggles between light and dark |

**Storage:**
- Theme preference stored in `localStorage.theme`

---

## Interceptors

### HttpRequestInterceptor

Adds standard headers to all outgoing HTTP requests.

**Headers Added:**

| Header | Value | Source |
|--------|-------|--------|
| `X-Request-ID` | UUID v4 | Generated per request |
| `X-Correlation-ID` | UUID v4 or inherited | Generated or from incoming request |
| `Authorization` | `Bearer {token}` | From `AuthService.isLoggedIn()` |
| `Content-Type` | `application/json` | Default (skipped for FormData) |
| `Accept` | `application/json` | Default |

**JSDoc API:**

```typescript
/**
 * HTTP Request Interceptor
 *
 * Adds authentication tokens, request IDs, and correlation IDs to outgoing HTTP requests.
 * Ensures consistent request formatting and traceability across the application.
 *
 * Headers added:
 * - X-Request-ID: A unique UUID v4 per request for request-level tracing.
 * - X-Correlation-ID: A correlation ID for distributed tracing (inherited from header if present).
 * - Authorization: Bearer token from AuthService when user is authenticated.
 * - Content-Type: application/json (for non-FormData requests).
 * - Accept: application/json
 */
@Injectable()
export class HttpRequestInterceptor implements HttpInterceptor {
    intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>>;
}
```

---

### HttpErrorInterceptor

Catches HTTP errors and handles them through the centralized error handling pipeline.

**Features:**
- Extracts error messages from backend JSON responses (`error.error?.detail`, `error.error?.message`)
- Extracts `X-Request-ID` header for debugging correlation
- Shows toast notifications via `ErrorNotificationService` with appropriate color per status:
  - Red: 4xx errors (400, 401, 403, 404, 500)
  - Orange: 4xx warnings (409 Conflict, 422 Validation, 429 Rate limit)
- Logs to console with request ID: `[HttpErrorInterceptor] [REQ-123] {...}`
- Calls `ErrorHandlerService.handleApiError()` for auth/retry logic

**HTTP Status Handling:**

| Status | Message Prefix | Toast Type |
|--------|---------------|------------|
| 400 | `Bad Request:` | Error (red) |
| 401 | `Unauthorized:` + auth redirect | Error (red) |
| 403 | `Forbidden:` | Error (red) |
| 404 | `Not Found:` | Error (red) |
| 409 | `Conflict:` | Warning (orange) |
| 422 | `Validation Error:` | Warning (orange) |
| 429 | `Too Many Requests:` | Warning (orange) |
| 500 | `Internal Server Error:` | Error (red) |
| 502 | `Bad Gateway:` | Error (red) |
| 503 | `Service Unavailable:` | Error (red) |
| 504 | `Gateway Timeout:` | Error (red) |

**JSDoc API:**

```typescript
/**
 * HTTP Error Interceptor
 *
 * Catches HTTP errors and delegates to the error handler service.
 * Extracts error messages from backend JSON responses and includes
 * request IDs for debugging. Shows toast notifications using ErrorNotificationService.
 *
 * Features:
 * - Extracts error message from backend JSON errors (error.error?.detail, error.error?.message)
 * - Extracts X-Request-ID header for debugging correlation
 * - Shows error toast notifications using ErrorNotificationService
 * - Logs to console with request ID and full error context
 */
@Injectable()
export class HttpErrorInterceptor implements HttpInterceptor {
    intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>>;
}
```

---

## Guards

### AuthGuard

Protects routes from unauthorized access. Redirects unauthenticated users to the login page.

**Usage:**

```typescript
// In routing module
{
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [AuthGuard],
    data: {
        requiredRoles: ['admin', 'user'] // Optional role restriction
    }
}
```

---

## Module Integration

### App Module Registration

Interceptors are registered in `app.module.ts`:

```typescript
providers: [
    {
        provide: HTTP_INTERCEPTORS,
        useClass: HttpRequestInterceptor,
        multi: true,
    },
    {
        provide: HTTP_INTERCEPTORS,
        useClass: HttpErrorInterceptor,
        multi: true,
    },
]
```

### Service Injection

Services are provided at root level (`providedIn: 'root'`) and can be injected anywhere in the application:

```typescript
constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private errorHandler: ErrorHandlerService,
    private themeService: ThemeService
) {}