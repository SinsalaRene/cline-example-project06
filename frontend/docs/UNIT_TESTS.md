# Frontend Unit Tests Documentation

## Overview

This document describes the unit testing strategy, coverage, and test files for the frontend Angular application.

## Testing Framework

The frontend uses **Jasmine** as the testing framework with **Karma** as the test runner. Angular's built-in testing utilities (`TestBed`, `HttpClientTestingModule`) provide the infrastructure for unit testing Angular applications.

## Test Structure

### Test File Conventions

All test files follow the naming convention `*.spec.ts` and are colocated with their source files. This keeps tests close to the implementation and makes maintenance easier.

### Test Categories

#### 1. Core Services Tests

**Location**: `frontend/src/app/core/services/*.spec.ts`

| Test File | Service Tested | Coverage |
|-----------|---------------|----------|
| `auth.service.spec.ts` | AuthService | Authentication, permissions, roles, token refresh |
| `api.service.spec.ts` | ApiService | CRUD operations, HTTP methods, error handling |
| `error-handler.service.spec.ts` | ErrorHandlerService | HTTP errors, auth errors, notifications |
| `theme.service.spec.ts` | ThemeService | Theme toggling, preference handling |

**Key Test Cases**:
- `login()` - Verifies token storage and redirection
- `logout()` - Verifies session cleanup
- `isAuthenticated()` - Verifies authentication state
- `hasPermission()` - Verifies permission checks
- `hasRole()` - Verifies role-based access
- `refreshToken()` - Verifies token refresh flow
- `getUser()` - Verifies user data retrieval

#### 2. Guard Tests

**Location**: `frontend/src/app/core/guards/*.spec.ts`

| Test File | Guard Tested | Coverage |
|-----------|-------------|----------|
| `auth.guard.spec.ts` | AuthGuard | Route protection, redirect logic |

**Key Test Cases**:
- `canActivate()` - Verifies authentication check
- Redirect to login when not authenticated
- Allow navigation when authenticated

#### 3. Interceptor Tests

**Location**: `frontend/src/app/core/interceptors/*.spec.ts`

| Test File | Interceptor Tested | Coverage |
|-----------|-------------------|----------|
| `http-request.interceptor.spec.ts` | HttpRequestInterceptor | Token injection, header setting |
| `http-error.interceptor.spec.ts` | HttpErrorInterceptor | Error handling, retry logic |

**Key Test Cases**:
- Request token injection
- Error response handling
- Retry on specific status codes
- Header management

#### 4. Module Service Tests

**Location**: `frontend/src/app/modules/*/services/*.spec.ts`

| Test File | Module | Coverage |
|-----------|--------|----------|
| `approvals.service.spec.ts` | Approvals | CRUD, bulk operations, comments |
| `audit.service.spec.ts` | Audit | Log retrieval, filtering, export |
| `dashboard-stat.service.spec.ts` | Dashboard | Stat calculations, caching |

**Key Test Cases for Approvals**:
- `getPendingApprovals()` - Retrieve pending approvals
- `approve()` / `reject()` - Single approval actions
- `bulkApprove()` / `bulkReject()` - Bulk operations
- `getApprovalComments()` / `addComment()` - Comment management

**Key Test Cases for Audit**:
- `getAuditLogs()` - Log retrieval with filtering
- `getAuditEntry()` - Single entry retrieval
- `exportAuditLogs()` - Export functionality

#### 5. Component Tests

**Location**: `frontend/src/app/modules/*/components/*.spec.ts`

| Test File | Component Tested | Coverage |
|-----------|-----------------|----------|
| `app.component.spec.ts` | AppComponent | Bootstrap, initialization |
| `dashboard.component.spec.ts` | DashboardComponent | Data loading, display |
| `approvals-list.component.spec.ts` | ApprovalsListComponent | List rendering, filtering |
| `approval-detail.component.spec.ts` | ApprovalDetailComponent | Detail view, actions |
| `rules-list.component.spec.ts` | RulesListComponent | Rule list, CRUD actions |
| `rule-detail.component.spec.ts` | RuleDetailComponent | Rule detail view |
| `confirmation-dialog.component.spec.ts` | ConfirmationDialogComponent | Dialog actions |
| `login.component.spec.ts` | LoginComponent | Login form, validation |

**Component Test Structure**:
```typescript
describe('ComponentNameComponent', () => {
    let component: ComponentNameComponent;
    let fixture: ComponentFixture<ComponentNameComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            declarations: [ComponentNameComponent],
            imports: [...],
            providers: [...]
        }).compileComponents();

        fixture = TestBed.createComponent(ComponentNameComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => { ... });
});
```

## Running Tests

### All Tests
```bash
ng test
```

### Specific Test File
```bash
ng test --include='**/auth.service.spec.ts'
```

### Headless Mode (CI/CD)
```bash
ng test --watch=false --browsers=ChromeHeadless
```

### With Coverage
```bash
ng test --code-coverage
```

## Test Coverage Goals

| Category | Target Coverage |
|----------|----------------|
| Core Services | 90%+ |
| Guards | 95%+ |
| Interceptors | 90%+ |
| Module Services | 85%+ |
| Component Templates | 80%+ |
| **Overall** | **85%+** |

## Testing Best Practices

1. **Arrange-Act-Assert**: Structure tests with clear setup, action, and assertion phases
2. **Mock Dependencies**: Use spies and mock services to isolate tests
3. **Describe Blocks**: Group related tests with descriptive describe blocks
4. **One Assertion Per Test**: Keep tests focused and failures easy to diagnose
5. **Test Edge Cases**: Include tests for null, empty, and error conditions
6. **Async Testing**: Use `fakeAsync`, `tick`, and `flushMicroTasks` for async operations
7. **HTTP Testing**: Use `HttpClientTestingModule` with `HttpTestingController`

## Mocking Patterns

### Service Mocking
```typescript
const mockService = jasmine.createSpyObj('ServiceName', ['method1', 'method2']);
TestBed.configureTestingModule({
    providers: [{ provide: ServiceName, useValue: mockService }]
});
```

### HTTP Mocking
```typescript
httpTestingController.expectOne('/api/endpoint').flush(mockData);
```

### Router Mocking
```typescript
const mockRouter = jasmine.createSpyObj('Router', ['navigate']);
TestBed.configureTestingModule({
    providers: [{ provide: Router, useValue: mockRouter }]
});
```

## Continuous Integration

Tests run automatically on every commit and pull request. The CI pipeline includes:

1. **Unit Tests** - Full test suite execution
2. **Coverage Report** - Generated after test execution
3. **Build Verification** - Ensures production build succeeds

## Troubleshooting

### Common Issues

1. **Cannot find name 'describe'**: Ensure Jasmine types are available
2. **HttpTestingController not injected**: Verify `HttpClientTestingModule` is imported
3. **Component not found in TestBed**: Ensure component is declared in the testing module
4. **Async timing issues**: Use `fakeAsync` and `tick()` appropriately

## References

- [Angular Testing Documentation](https://angular.io/guide/testing)
- [Jasmine Documentation](https://jasmine.github.io/)
- [Karma Documentation](https://karma-runner.github.io/)