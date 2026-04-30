# Auth Module Documentation

## Overview

The authentication module provides a complete authentication system for the Azure Firewall Manager application. It includes login/logout functionality, route guards for protecting routes, and role-based access control (RBAC).

## Architecture

### File Structure

```
frontend/src/app/
├── modules/auth/
│   ├── auth.module.ts                    # Auth module
│   ├── login/
│   │   ├── login.component.ts            # Login component logic
│   │   ├── login.component.html          # Login form template
│   │   ├── login.component.css           # Login form styles
│   │   └── login.component.spec.ts       # Login component tests
│   ├── logout/
│   │   └── logout.component.ts           # Logout component logic
│   └── directives/
│       └── role.directive.ts             # Role-based directive
└── core/guards/
    ├── auth.guard.ts                     # Auth guards (5 guards)
    └── auth.guard.spec.ts                # Auth guards tests
```

## Auth Flow

### 1. User Navigates to Protected Route

```
User -> /rules
       ↓
    AuthGuard.canActivate()
       ↓
    Is user logged in?
       ├── Yes  -> Allow navigation
       └── No   -> Redirect to /login
```

### 2. Login Process

```
User enters credentials
       ↓
    LoginComponent.onSubmit()
       ↓
    AuthService.login(username, password)
       ↓
    API Call: POST /api/v1/auth/login
       ↓
    ┌─────────────────────┐
    │ Response Status     │
    ├─────────────────────┤
    │ 200 OK:             │
    │ - Save token        │
    │ - Save user data    │
    │ - Set isLoggedIn    │
    │ - Navigate /dashboard│
    ├─────────────────────┤
    │ 401 Unauthorized:   │
    │ - Show error        │
    │ - "Invalid creds"   │
    ├─────────────────────┤
    │ 403 Forbidden:      │
    │ - Show error        │
    │ - "Access denied"   │
    └─────────────────────┘
```

### 3. Logout Process

```
User clicks logout
       ↓
    LogoutComponent.ngOnInit()
       ↓
    AuthService.logout()
       ↓
    - Remove auth_token from localStorage
    - Remove user data from localStorage
    - Set isLoggedIn to false
    - Clear userSubject
       ↓
    Navigate to /login
```

## Auth Guards

### AuthGuard
- **Purpose**: Protect routes that require authentication
- **Behavior**: If not logged in, redirect to `/login`
- **Usage**: `canActivate: [AuthGuard]`

### ReverseAuthGuard
- **Purpose**: Prevent authenticated users from accessing public-only routes
- **Behavior**: If logged in, redirect to `/dashboard`; if not logged in, allow access
- **Usage**: Protect routes that should redirect authenticated users

### PublicGuard
- **Purpose**: Allow unauthenticated users to access public routes (e.g., login page)
- **Behavior**: If logged in, redirect to `/dashboard`; if not logged in, allow access
- **Usage**: Protect the login page from authenticated users

### RoleGuard
- **Purpose**: Restrict routes to users with specific roles
- **Behavior**: Check if user has required roles from route data
- **Usage**:
  ```typescript
  {
    path: 'admin',
    canActivate: [RoleGuard],
    data: { roles: ['admin'] }
  }
  ```

### PermissionGuard
- **Purpose**: Restrict routes to users with specific permissions
- **Behavior**: Check if user has required permission
- **Usage**:
  ```typescript
  {
    path: 'settings',
    canActivate: [PermissionGuard],
    data: { permission: 'settings:write' }
  }
  ```

## AuthService

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `isLoggedIn` | `Signal<boolean>` | Reactive login state |
| `userName` | `Signal<string>` | Current user's display name |
| `user$` | `Observable<UserInfo>` | Observable stream of user info |

### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `login()` | `username, password` | `Observable<any>` | Authenticate user |
| `loginWithToken()` | `token, user` | `void` | Login with existing token |
| `logout()` | None | `void` | Clear auth state and redirect |
| `hasRole()` | `role: string` | `boolean` | Check if user has role |
| `hasPermission()` | `permission: string` | `boolean` | Check if user has permission |
| `handleAuthError()` | None | `void` | Handle auth error (logout + emit) |

### User Info Interface

```typescript
interface UserInfo {
    object_id: string;    // Azure AD object ID
    display_name: string; // User's display name
    email: string;        // User's email
    roles?: string[];     // User's roles
}
```

## Role Directive

### Usage

The `*appRole` directive conditionally renders content based on user roles:

```html
<!-- Show to admins only -->
<div *appRole="'admin'">Admin content</div>

<!-- Show to admins OR editors -->
<div *appRole="['admin', 'editor']">Restricted content</div>
```

### How It Works

1. The directive receives role(s) from its input
2. On initialization (`ngOnInit`), it checks if the current user has any of the required roles
3. If the user has access, the template is rendered
4. If not, the template is cleared (hidden)

## State Persistence

Authentication state is persisted in `localStorage`:

- `auth_token`: JWT token or session token
- `user`: Serialized user info object

On page reload, the `AuthService` constructor checks for saved user data and restores the auth state.

## Route Configuration

### Current Routes

```typescript
const routes: Routes = [
    { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
    { path: 'login', component: LoginComponent },
    { path: 'logout', component: LogoutComponent },
    // Protected routes...
    {
        path: 'rules',
        canActivate: [AuthGuard],
        loadChildren: () => import('./rules')
    },
    // Fallback
    { path: '**', redirectTo: '/dashboard' }
];
```

## Testing

### Login Component Tests

The login component tests cover:
- Component creation and initialization
- Form validation (empty fields, invalid emails)
- Submit behavior (loading state, API calls, error handling)
- Password visibility toggle
- Azure AD login redirect

### Auth Guards Tests

The auth guards tests cover:
- Guard creation and injection
- Authenticated user behavior
- Unauthenticated user behavior
- Role-based access control
- Permission-based access control

### Running Tests

```bash
npm run test
```

## Security Considerations

1. **Token Storage**: Tokens are stored in `localStorage` for persistence
2. **Token Expiration**: Implement token refresh mechanism
3. **XSS Protection**: Sanitize user input in login form
4. **CSRF Protection**: Use http-only cookies when possible
5. **Role Validation**: Always validate roles on the server side as well

## Integration Points

### Backend API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | Authenticate user |
| `/api/v1/auth/logout` | POST | Logout user |
| `/api/v1/auth/me` | GET | Get current user info |

### Azure AD Integration

For Azure AD SSO, the login component includes an `onAzureLogin()` method that redirects to Microsoft's OAuth2 endpoint:

```
https://login.microsoftonline.com/common/oauth2/v2.0/authorize?
  client_id={CLIENT_ID}
  &response_type=id_token+token
  &redirect_uri={REDIRECT_URI}
  &scope=openid+profile
  &state={REDIRECT_URI}