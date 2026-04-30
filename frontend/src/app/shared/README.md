# Shared Module Documentation

## Overview

The shared module architecture provides reusable components, services, interceptors, and utilities used across the Angular application. This module promotes code reuse, consistent behavior, and centralized error handling.

## Architecture

```
src/app/
├── shared/                          # Shared module directory
│   ├── shared.module.ts             # Main shared module exports
│   ├── shared.spec.ts               # Tests for shared infrastructure
│   ├── shared.service.ts            # Shared service utilities
│   ├── README.md                    # This documentation
│   ├── components/
│   │   └── error-notification/
│   │       └── error-notification.component.ts  # Global error notifications
│   ├── directives/                  # Custom directives (if any)
│   ├── pipes/                       # Custom pipes (if any)
│   └── utils/                       # Shared utility functions
├── core/
│   ├── interceptors/
│   │   ├── http-error.interceptor.ts      # HTTP error interceptor
│   │   └── http-request.interceptor.ts    # HTTP request interceptor
│   └── services/
│       ├── error-handler.service.ts       # Centralized error handling
│       ├── theme.service.ts               # Theme management service
│       ├── auth.service.ts                # Authentication service
│       └── api.service.ts                 # API service
└── modules/
    └── layout/
        ├── layout.module.ts               # Layout module
        ├── layout.component.ts            # Main layout component
        ├── layout.component.html          # Layout template
        └── layout.component.css           # Layout styles
```

## Components

### ErrorNotificationComponent

**Location**: `src/app/shared/components/error-notification/error-notification.component.ts`

The ErrorNotificationComponent provides a centralized, user-friendly error notification system. It listens to the ErrorHandlerService and displays appropriate error messages via Angular Material snackbar.

#### Features
- Automatic error display for HTTP errors (4xx, 5xx)
- Severity-based styling (error, warning, info, success)
- Appropriate icon mapping per status code
- Auto-dismiss timing based on error severity
- Auth error handling with redirect to login
- Configurable action button labels

#### Status Code Mappings

| Status Code | Title         | Icon           | Auto-Delay |
|-------------|---------------|----------------|------------|
| 400         | Bad Request   | error          | 5s         |
| 401         | Unauthorized  | lock           | No         |
| 403         | Forbidden     | lock           | 5s         |
| 404         | Not Found     | search_off     | 5s         |
| 409         | Conflict      | error          | 5s         |
| 422         | Validation    | error          | 5s         |
| 429         | Rate Limited  | hourglass_empty| 8s         |
| 500-504     | Server Error  | server_error   | 10s        |

## Interceptors

### HttpRequestInterceptor

**Location**: `src/app/core/interceptors/http-request.interceptor.ts`

Handles outgoing HTTP requests by:
- Attaching authentication tokens (Bearer token)
- Setting Content-Type and Accept headers for JSON
- Adding request timestamps for telemetry
- Handling request logging

#### Configuration

The interceptor automatically:
1. Retrieves `auth_token` from localStorage
2. Adds `Authorization: Bearer <token>` header when token exists
3. Sets `Content-Type: application/json` for all requests
4. Sets `Accept: application/json` for all requests

### HttpErrorInterceptor

**Location**: `src/app/core/interceptors/http-error.interceptor.ts`

Handles HTTP error responses by:
- Intercepting error responses from the HTTP client
- Delegating to ErrorHandlerService
- Providing consistent error handling across the application
- Handling auth-specific errors (401, 403)

#### Error Flow

```
HTTP Error → HttpErrorInterceptor → ErrorHandlerService → ErrorNotificationComponent
                                                          → AuthService (for auth errors)
```

## Services

### ErrorHandlerService

**Location**: `src/app/core/services/error-handler.service.ts`

Centralized error handling service that:
- Provides `error$` observable for error events
- Provides `authError$` observable for auth errors
- Handles HTTP error response processing
- Maps status codes to user-friendly messages
- Handles validation errors (422)
- Handles server errors (5xx)
- Handles network errors

#### Usage

```typescript
import { ErrorHandlerService } from '@core/services/error-handler.service';

constructor(private errorHandler: ErrorHandlerService) {
    // Handle errors
    this.errorHandler.handleError({
        message: 'Something went wrong',
        statusCode: 500
    });
}

// Subscribe to errors
this.errorHandler.error$.subscribe(error => {
    // Custom error handling
});
```

### ThemeService

**Location**: `src/app/core/services/theme.service.ts`

Theme management service that:
- Supports light/dark theme modes
- Persists theme preference to localStorage
- Applies theme classes to the document body
- Supports automatic theme detection (system preference)
- Provides `themeChange$` observable for theme changes

#### Theme Options
- `light` - Light theme
- `dark` - Dark theme
- `auto` - Auto-detect based on system preference

#### Usage

```typescript
import { ThemeService, ThemeMode } from '@core/services/theme.service';

constructor(private themeService: ThemeService) {
    // Change theme
    this.themeService.setTheme('dark');
    
    // Subscribe to changes
    this.themeService.themeChange$.subscribe(theme => {
        console.log('Theme changed to:', theme);
    });
}
```

#### Theme Variables

The theme system uses CSS custom properties (CSS variables) for theming:

```css
/* Light Theme Variables */
:root, .light-theme {
    --primary-color: #1976d2;
    --accent-color: #ff9800;
    --sidenav-bg: #f5f5f5;
    --topbar-bg: #ffffff;
    --content-bg: #fafafa;
    --text-primary: #212121;
    --border-color: #e0e0e0;
}

/* Dark Theme Variables */
.dark-theme {
    --primary-color: #90caf9;
    --accent-color: #ffb74d;
    --sidenav-bg: #1e1e1e;
    --topbar-bg: #1e1e1e;
    --content-bg: #121212;
    --text-primary: #e0e0e0;
    --border-color: #333333;
}
```

## Layout Module

### LayoutComponent

**Location**: `src/app/modules/layout/layout.component.ts`

The main application layout component that provides:
- Responsive side navigation with collapse/expand
- Top bar with user info and theme toggle
- Main content area for child routes
- Integration with authentication state
- Responsive breakpoints for mobile/desktop

#### Features
- Collapsible side navigation
- Active route highlighting
- User avatar display
- Theme switching in sidebar
- Responsive breakpoints:
  - Mobile: < 768px
  - Tablet: 768px - 1024px
  - Desktop: > 1024px

#### Usage

The LayoutComponent is automatically provided by the LayoutModule:

```typescript
@NgModule({
    imports: [LayoutModule],
})
export class AppModule { }
```

## Shared Module

### SharedModule

**Location**: `src/app/shared/shared.module.ts`

The SharedModule aggregates commonly used Angular and Angular Material modules, providing them to feature modules without needing to import each individually.

#### Exports

The SharedModule exports:
- CommonModule
- FormsModule
- ReactiveFormsModule
- MatTableModule
- MatPaginatorModule
- MatSortModule
- MatInputModule
- MatFormFieldModule
- MatSelectModule
- MatButtonModule
- MatIconModule
- MatCardModule
- MatTabsModule
- MatDialogModule
- MatListModule
- MatProgressSpinnerModule
- MatExpansionModule
- MatChipsModule
- MatSidenavModule
- MatMenuModule
- MatTooltipModule
- MatSnackBarModule

#### Usage

```typescript
import { SharedModule } from '@app/shared/shared.module';

@NgModule({
    imports: [SharedModule],
})
export class FeatureModule { }
```

## Error Handling Architecture

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Application                              │
│                                                                   │
│  ┌─────────────┐    ┌────────────────┐    ┌─────────────────┐   │
│  │ API Service  │    │ AuthService    │    │ Component       │   │
│  │ (HTTP calls) │    │ (auth calls)   │    │ (form submit)   │   │
│  └──────┬──────┘    └────────┬───────┘    └────────┬────────┘   │
│         │                    │                      │            │
│         ▼                    ▼                      ▼            │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              HttpErrorInterceptor                     │       │
│  │  (Intercepts all HTTP errors)                        │       │
│  └──────────────────────┬───────────────────────────────┘       │
│                         │                                        │
│                         ▼                                        │
│  ┌────────────────────────────────┐                            │
│  │        ErrorHandlerService     │                            │
│  │  • error$ observable           │                            │
│  │  • authError$ observable       │                            │
│  │  • handleHttpError()           │                            │
│  │  • handleValidationErrors()    │                            │
│  │  • handleNetworkError()        │                            │
│  └──────────────┬─────────────────┘                            │
│                 │                                                │
│                 ▼                                                │
│  ┌────────────────────────────────┐                            │
│  │   ErrorNotificationComponent   │                            │
│  │   (Angular Material snackbar)  │                            │
│  └────────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### Error Classification

The system classifies errors into three categories:

1. **Authentication Errors** (401, 403)
   - Trigger `authError$` observable
   - Clear authentication state
   - Redirect to login (optional)
   - Display "Session Expired" notification

2. **Validation Errors** (422)
   - Display field-specific error messages
   - Map API validation errors to form fields
   - Display user-friendly messages

3. **General Errors** (4xx, 5xx)
   - Display appropriate error message
   - Map status codes to user-friendly titles
   - Auto-dismiss based on severity

## Testing

### Running Tests

```bash
# Run shared module tests
ng test --include="**/shared/**"

# Run all tests
ng test
```

### Test Coverage

The shared.spec.ts file contains tests for:
- SharedModule exports
- ErrorHandlerService error handling
- HttpErrorInterceptor behavior
- HttpRequestInterceptor behavior
- ThemeService functionality
- ErrorNotificationComponent behavior
- LayoutComponent functionality
- Integration tests between components

## Best Practices

### Using the Error Handler

```typescript
// Good: Use the centralized error handler
this.myService.getData().subscribe({
    next: (data) => { /* handle success */ },
    error: (error) => {
        this.errorHandler.handleHttpError(error);
    }
});

// Good: Use in service methods
getData() {
    return this.http.get('/api/data')
        .pipe(
            catchError(err => {
                this.errorHandler.handleHttpError(err);
                return throwError(() => err);
            })
        );
}
```

### Using the Theme Service

```typescript
// Good: Use the theme service for theme changes
this.themeService.setTheme('dark');

// Good: Subscribe to theme changes
this.themeService.themeChange$.subscribe(theme => {
    // Theme has changed, update UI if needed
});
```

### Using Interceptors

The interceptors are automatically configured in AppModule. No additional setup is required:

```typescript
// The HttpRequestInterceptor automatically adds auth tokens
// The HttpErrorInterceptor automatically handles errors
// No manual configuration needed in components
```

## Migration Guide

### Adding New Shared Components

1. Create the component in the `shared/components/` directory
2. Update the SharedModule to export the new component
3. Update this documentation
4. Add tests in shared.spec.ts

### Adding New Interceptors

1. Create the interceptor in `core/interceptors/`
2. Implement the `HttpInterceptorFn` interface
3. Add to the HTTP_INTERCEPTORS provider array in AppModule
4. Add tests for the interceptor

### Adding New Theme Variants

1. Add the theme variables in layout.component.css
2. Update ThemeService with the new theme option
3. Update this documentation with the new theme configuration

## See Also

- [Angular Material Documentation](https://material.angular.io/)
- [Angular HTTP Interceptors](https://angular.io/guide/http#interceptors)
- [Angular Theme Customization](https://material.angular.io/guide/theming)