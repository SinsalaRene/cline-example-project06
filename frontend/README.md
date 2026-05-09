# Azure Firewall Management Application

Angular frontend for the Azure Firewall Management platform. A comprehensive enterprise-grade application for managing Azure Firewall rules, network topology, workloads, and approval workflows.

## Project Overview

This application provides a centralized dashboard for managing Azure Firewall infrastructure including:

- **Dashboard** - Overview of firewall rules, network health, and key metrics
- **Firewall Rules** - Create, edit, delete, and approve firewall rules with workflow
- **Network Topology** - Visualize NSGs, subnets, and network resources
- **Workloads** - Manage Azure workloads and their firewall configurations
- **Audit Log** - Comprehensive audit trail of all actions and changes
- **Approvals** - Workflow-based approval process for firewall rule changes

## Tech Stack

- **Framework:** Angular (latest)
- **UI Components:** Angular Material
- **Language:** TypeScript
- **State Management:** Reactive extensions (RxJS)
- **Testing:** Jasmine / Jest

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── core/                    # Core services, interceptors, guards
│   │   │   ├── guards/              # Route guards (AuthGuard)
│   │   │   ├── interceptors/        # HTTP interceptors (request, error)
│   │   │   └── services/            # Core services (API, auth, error, theme)
│   │   ├── modules/                 # Feature modules
│   │   │   ├── auth/                # Authentication module (login)
│   │   │   ├── dashboard/           # Dashboard module
│   │   │   ├── layout/              # Layout components (sidebar, header)
│   │   │   ├── approvals/           # Approval workflow module
│   │   │   ├── audit/               # Audit log module
│   │   │   ├── network/             # Network topology module
│   │   │   ├── rules/               # Firewall rules module
│   │   │   └── workloads/           # Workload management module
│   │   └── shared/                  # Shared infrastructure
│   │       ├── components/          # Shared components (spinner, notifications, dialogs)
│   │       └── directives/          # Shared directives (loading)
│   ├── styles.css                   # Global styles
│   └── index.html
├── docs/                            # Documentation
├── package.json
├── angular.json
└── tsconfig.json
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm 9+

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
ng serve
```

The application will be available at `http://localhost:4200`.

### Backend API

The frontend expects a running backend API at the configured proxy URL. See the root project README for backend setup instructions.

### Building

```bash
ng build --configuration production
```

The build artifacts will be stored in the `dist/` directory.

## Modules

### Core Module

Core services, interceptors, and guards:
- **AuthService** - Authentication and token management
- **ApiService** - HTTP client with typed responses
- **ErrorHandlerService** - Centralized error handling
- **ThemeService** - Light/dark theme management
- **HttpRequestInterceptor** - Adds auth tokens, request IDs, correlation IDs
- **HttpErrorInterceptor** - Catches errors, shows toasts, logs with request IDs
- **AuthGuard** - Protects authenticated routes

See [core/README.md](src/app/core/README.md) for full documentation.

### Shared Module

Reusable components, directives, and services:
- **LoadingSpinnerComponent** - Inline or overlay loading spinner
- **ErrorNotificationService** - Colored toast notifications (error/warning/success)
- **ConfirmDialogComponent** - Generic confirmation dialog
- **LoadingDirective** - Structural directive for loading states

See [shared/README.md](src/app/shared/README.md) for full documentation.

### Feature Modules

| Module | Path | Description |
|--------|------|-------------|
| Dashboard | `/dashboard` | Overview dashboard with metrics and charts |
| Firewall Rules | `/rules` | Firewall rule management with approval workflow |
| Network | `/network` | Network topology visualization and NSG management |
| Workloads | `/workloads` | Workload configuration and firewall settings |
| Audit | `/audit` | Audit log with filtering and export |
| Approvals | `/approvals` | Approval workflow for rule changes |
| Login | `/login` | User authentication |

## Shared Infrastructure

### Loading Spinner

```html
<!-- Inline spinner -->
<app-loading-spinner [size]="medium"></app-loading-spinner>

<!-- Overlay spinner -->
<app-loading-spinner [size]="large" mode="overlay"></app-loading-spinner>
```

### Error Notifications

```typescript
constructor(private notificationService: ErrorNotificationService) {}

this.notificationService.showError('Error message', 5000);
this.notificationService.showWarning('Warning message', 5000);
this.notificationService.showSuccess('Success message');
```

### Confirm Dialog

```typescript
const dialogRef = openConfirmDialog({
    title: 'Delete Rule',
    message: 'Are you sure?',
    confirmText: 'Delete',
    cancelText: 'Cancel'
});

dialogRef.afterClosed().subscribe(result => {
    if (result) {
        // Confirmed
    }
});
```

### Loading Directive

```html
<ng-template [appLoading]="data$ | async">
    <div>{{ data?.name }}</div>
</ng-template>
```

## Testing

```bash
# Run all tests
ng test

# Run once and exit
ng test --watch=false

# Run with coverage
ng test --watch=false --coverage
```

## Error Handling Architecture

The application uses a centralized error handling pipeline:

1. **HttpErrorInterceptor** catches all HTTP errors
2. Extracts error messages from backend JSON responses
3. Shows toast notifications via `ErrorNotificationService`
4. Logs to console with request ID for debugging
5. Delegates to `ErrorHandlerService` for auth/retry logic

Error types map to toast colors:
- 🔴 Red: Errors (4xx, 500, 502, 503, 504)
- 🟠 Orange: Warnings (409 Conflict, 422 Validation, 429 Rate Limit)
- 🟢 Green: Success messages

## Scripts

```bash
npm run build        # Build for production
npm run test         # Run unit tests
npm run lint         # Run ESLint
npm run serve:proxy  # Start dev server with API proxy