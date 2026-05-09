# Shared Module

Central shared infrastructure for the Azure Firewall Management application. This module provides reusable components, directives, and services used across all feature modules.

## Components

### LoadingSpinnerComponent

A reusable loading spinner component that displays a `MatProgressSpinner` in either inline or overlay mode.

**Inputs:**

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `size` | `'small' \| 'medium' \| 'large'` | `'medium'` | The size of the spinner |
| `mode` | `'inline' \| 'overlay'` | `'inline'` | Whether the spinner appears inline or as a full-screen overlay |

**Usage:**

```html
<!-- Inline spinner (medium size) -->
<app-loading-spinner></app-loading-spinner>

<!-- Overlay mode (large size) -->
<app-loading-spinner [size]="large" mode="overlay"></app-loading-spinner>
```

**Features:**
- Uses Angular Material `MatProgressSpinner`
- Supports three sizes: small (24px), medium (48px), large (80px)
- Overlay mode uses `position: fixed` to center the spinner over the entire screen with a semi-transparent backdrop
- Accessible with `role="status"` and `aria-live="polite"`

**JSDoc API:**

```typescript
/**
 * Reusable loading spinner component with configurable size and mode.
 * Displays a Material Design progress spinner inline or as a full-screen overlay.
 */
@Component({
    selector: 'app-loading-spinner',
    templateUrl: './loading-spinner.component.html',
    styleUrls: ['./loading-spinner.component.css'],
    standalone: true,
    imports: [MatProgressSpinnerModule]
})
export class LoadingSpinnerComponent {
    /** The size of the spinner: 'small', 'medium', or 'large'. */
    @Input() size: 'small' | 'medium' | 'large' = 'medium';
    /** The display mode: 'inline' or 'overlay'. */
    @Input() mode: 'inline' | 'overlay' = 'inline';
}
```

---

### ErrorNotificationComponent

A component that wraps Angular Material's `MatSnackBar` to provide centralized toast notifications. Provides a service (`ErrorNotificationService`) that can be injected into any component.

**Service Methods:**

| Method | Parameters | Description |
|--------|-----------|-------------|
| `showError(message, duration?)` | `message: string`, `duration?: number = 5000` | Shows a red error toast |
| `showWarning(message, duration?)` | `message: string`, `duration?: number = 5000` | Shows an orange warning toast |
| `showSuccess(message, duration?)` | `message: string`, `duration?: number = 5000` | Shows a green success toast |

**Usage:**

```typescript
// In any component
constructor(private notificationService: ErrorNotificationService) {}

someMethod() {
    this.notificationService.showError('Something went wrong', 8000);
    this.notificationService.showWarning('Please review your input', 6000);
    this.notificationService.showSuccess('Operation completed successfully');
}
```

**Toast Styles:**

| Type | Color | Default Duration |
|------|-------|-----------------|
| Error | Red (`#f44336`) | 5s |
| Warning | Orange (`#ff9800`) | 5s |
| Success | Green (`#4caf50`) | 5s |

**JSDoc API:**

```typescript
/**
 * Centralized error notification service.
 * Provides methods to show colored toast notifications via MatSnackBar.
 */
export class ErrorNotificationService {
    /**
     * Shows a red error toast notification.
     * @param message - The error message to display.
     * @param duration - Duration in ms before auto-dismiss (default: 5000).
     */
    showError(message: string, duration?: number): void;

    /**
     * Shows an orange warning toast notification.
     * @param message - The warning message to display.
     * @param duration - Duration in ms before auto-dismiss (default: 5000).
     */
    showWarning(message: string, duration?: number): void;

    /**
     * Shows a green success toast notification.
     * @param message - The success message to display.
     * @param duration - Duration in ms before auto-dismiss (default: 5000).
     */
    showSuccess(message: string, duration?: number): void;
}
```

---

### ConfirmDialogComponent

A generic confirmation dialog component using Angular Material's `MatDialog`. Returns a boolean result indicating user confirmation.

**Inputs (via `MAT_DIALOG_DATA`):**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `title` | `string` | Required | Dialog title |
| `message` | `string` | Required | Dialog message body |
| `confirmText` | `string` | `'Confirm'` | Text for the confirm button |
| `cancelText` | `string` | `'Cancel'` | Text for the cancel button |

**Usage:**

```typescript
// Direct usage
const dialogRef = openConfirmDialog({
    title: 'Delete Firewall Rule',
    message: 'Are you sure you want to delete this rule?',
    confirmText: 'Delete',
    cancelText: 'Cancel'
});

dialogRef.afterClosed().subscribe(result => {
    if (result) {
        // User confirmed
        this.deleteRule();
    }
});
```

**JSDoc API:**

```typescript
/**
 * Generic confirmation dialog component.
 * Returns a boolean result via MatDialogRef<boolean>.
 * Used across all modules for delete confirmations, form submit confirmations, etc.
 */
export interface ConfirmDialogData {
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
}

/**
 * Opens a confirm dialog with the given data.
 * @param data - Dialog configuration data.
 * @returns MatDialogRef<boolean> with the result.
 */
function openConfirmDialog(data: ConfirmDialogData): MatDialogRef<boolean>;
```

---

## Directives

### LoadingDirective

A structural directive (`*appLoading`) that shows a loading spinner while an Observable is falsy and renders the content when the Observable emits a truthy value.

**Usage:**

```html
<!-- Basic usage with async pipe -->
<ng-template [appLoading]="data$ | async">
    <div>{{ data?.name }}</div>
</ng-template>

<!-- With explicit null check -->
<ng-template [appLoading]="users$ | async; else loading">
    <div>Users list</div>
</ng-template>

<!-- Combined with inline loading spinner -->
<ng-template [appLoading]="apiData$ | async">
    <app-api-viewer [data]="apiData"></app-api-viewer>
</ng-template>
```

**Features:**
- Shows a `MatProgressSpinner` when the Observable emits `null`, `undefined`, `false`, or empty string
- Renders the projected content when the Observable emits a truthy value
- Compatible with RxJS `async` pipe
- Automatically handles component lifecycle (clears view on destroy)

**JSDoc API:**

```typescript
/**
 * Structural directive that shows a loading spinner while an Observable is falsy.
 * Usage: *appLoading="data$ | async"
 */
@Directive({ selector: '[appLoading]' })
export class LoadingDirective implements ViewRef {
    /**
     * The input value (Observable) to observe.
     * When falsy: shows loading spinner.
     * When truthy: renders the projected content.
     */
    @Input() appLoading: unknown;

    /** Reference to the loading spinner view. */
    private loadingView: ViewRef | null;

    /** Reference to the content view. */
    private contentView: ViewRef | null;
}
```

---

## Architecture

### Component Hierarchy

```
shared/
├── components/
│   ├── loading-spinner/    # Reusable spinner component
│   ├── error-notification/ # Toast notification wrapper
│   └── confirm-dialog/     # Generic confirmation dialog
├── directives/
│   └── loading.directive.ts # Loading state structural directive
└── shared.module.ts       # Module aggregation
```

### Service Dependencies

| Component | Service | Purpose |
|-----------|---------|---------|
| `LoadingSpinnerComponent` | None (self-contained) | Uses `MatProgressSpinner` |
| `ErrorNotificationComponent` | `MatSnackBar` | Shows toast notifications |
| `ConfirmDialogComponent` | `MatDialog` | Opens confirmation dialog |
| `LoadingDirective` | `NgIf`, `NgTemplateOutlet` | Structural directive logic |

### Inter-module Usage

All shared components are exported via `SharedModule` and can be used in any feature module:

```typescript
// In any feature module
import { SharedModule } from '../shared/shared.module';

@NgModule({
    imports: [SharedModule],
    // Components are available via the export
})
export class MyFeatureModule {}
```

### Integration with Interceptors

The `ErrorNotificationService` is used by the `HttpErrorInterceptor` to display toast notifications for HTTP errors, creating a unified error handling experience across the application.