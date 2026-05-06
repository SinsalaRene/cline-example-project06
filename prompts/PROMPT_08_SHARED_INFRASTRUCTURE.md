# PROMPT 8: Shared Infrastructure & Polish

## Context

You are working on an Azure Firewall Management application built with Angular (frontend) and FastAPI/Python (backend). All feature modules are complete. Now implement shared infrastructure components and polish the application.

**Relevant files:**
- `frontend/src/app/shared/shared.module.ts`
- `frontend/src/app/core/`
- `frontend/src/app/modules/*/` — all modules

**Known state:**
- Existing interceptors: `http-request.interceptor.ts`, `http-error.interceptor.ts`
- Existing services: `auth.service.ts`, `api.service.ts`, `error-handler.service.ts`, `theme.service.ts`
- Existing guards: `auth.guard.ts`

## Task

### 1. Loading Spinner Component (`shared/components/loading-spinner/`)
- `loading-spinner.component.ts`: Reusable spinner component with input `size` (small/medium/large) and `mode` (inline/overlay)
- When mode=overlay, uses `position: fixed` to center overlay entire screen
- Uses Angular Material `MatProgressSpinner`
- Template-driven: `<app-loading-spinner [size]="medium" mode="overlay"></app-loading-spinner>`

### 2. Error Notification Component (`shared/components/error-notification/`)
- `error-notification.component.ts`: Component that wraps MatSnackBar
- Exposes methods: `showError(message, duration?)`, `showWarning(message, duration?)`, `showSuccess(message, duration?)`
- Different color/snack bar config per type: red (error), orange (warning), green (success)
- Auto-dismiss with configurable duration (default 5s)

### 3. Confirm Dialog Component (`shared/components/confirm-dialog/`)
- `confirm-dialog.component.ts`: Generic confirmation dialog
- Input: `title`, `message`, `confirmText` (default "Confirm"), `cancelText` (default "Cancel")
- Returns `MatDialogRef<boolean>` with result
- Used across all modules for delete confirmations, form submit confirmations, etc.

### 4. Loading State Directive (`shared/directives/`)
- `loading.directive.ts`: Structural directive that shows spinner while an Observable is falsy
- Usage: `*appLoading="data$ | async"` — shows spinner until observable emits truthy value

### 5. HTTP Interceptor Improvements
- Update `http-error.interceptor.ts`:
  - Extract error message from backend JSON errors
  - Extract request ID from X-Request-ID header for debugging
  - Show error toast notification using MatSnackBar
  - Log to console with request ID
- Update `http-request.interceptor.ts`:
  - Add X-Request-ID header (generate UUID per request)
  - Add Authorization header from AuthService
  - Add X-Correlation-ID header for traceability

### 6. Error Handler Service Update
- Update `error-handler.service.ts`:
  - Method `handleApiError(error, context?)` — logs error, extracts message, returns user-friendly message
  - Method `trackError(error, context?)` — for error tracking integration (placeholder)
  - Method `getErrorMessage(error)` — extracts clean message from HttpErrorResponse

### 7. Error Message Integration
- Update ALL components across all modules to use ErrorNotificationService for toast notifications
- Update ALL forms to show inline error messages using ErrorHandlerService
- Replace any hardcoded console.error calls with ErrorHandler service calls

### 8. Documentation
- Update `frontend/src/app/shared/README.md` with all shared components
- Create `frontend/src/app/core/README.md` explaining core services, interceptors, guards
- Update root `frontend/README.md` with project overview

## Skills

Before starting, load and activate these skills in order:

```
use_skill(skill_name="improve-codebase-architecture")
```

Use this skill to review the existing codebase and ensure shared components follow Angular patterns. Validate that interceptor design, error handling, and shared service patterns align with the rest of the application.

```
use_skill(skill_name="tdd")
```

After the architecture skill, activate TDD. Write unit tests for: HTTP interceptor header injection, error message extraction logic, ConfirmDialog result emission, LoadingDirective with async pipe, and ErrorNotificationService toast display before implementing components.

## Quality Checks

1. [ ] LoadingSpinner component works in inline and overlay mode
2. [ ] ErrorNotificationService shows correct colored toasts per type
3. [ ] ConfirmDialog returns boolean result correctly
4. [ ] Loading directive works with async pipe
5. [ ] HTTP interceptors add all required headers
6. [ ] Error messages extracted from backend JSON responses
7. [ ] All components use ErrorNotificationService (not direct MatSnackBar)
8. [ ] All forms show inline error messages
9. [ ] No TypeScript compilation errors
10. [ ] All shared components documented

## Documentation Requirements

- JSDoc for all shared components
- JSDoc for all interceptors
- Update shared module README
- Update core module README