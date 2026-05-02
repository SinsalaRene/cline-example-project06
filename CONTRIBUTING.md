# Contributing Guide

Guidelines for contributing to the Azure Firewall Management Application.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Branching Strategy](#branching-strategy)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Code Standards](#code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Review Checklist](#review-checklist)

---

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Report unacceptable behavior to maintainers

---

## Getting Started

### Prerequisites

| Tool | Minimum Version | Recommended |
|------|----------------|-------------|
| Python | 3.11 | 3.12 |
| Node.js | 18 | 20 LTS |
| Angular CLI | 17 | 18 |
| PostgreSQL | 13 | 15 |
| Docker | 24 | 25+ |

### Setup

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/cline-example-project06.git
cd cline-example-project06

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 3. Frontend setup
cd ../frontend
npm install
```

### Running the Full Stack

```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
ng serve

# Terminal 3 - Database (if using Docker)
docker run -d --name pg -e POSTGRES_DB=firewall_mgmt -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15-alpine
```

---

## Branching Strategy

### Git Flow

```
main ──────────────────────────────────────── production
  │
  ├─ develop ──────────────────────────────── staging
  │   │
  │   ├─ feature/FEATURE-BRANCH ──► feature/FEATURE-BRANCH
  │   │                                    merged
  │   └─ fix/BUGFIX-BRANCH ──► fix/BUGFIX-BRANCH
  │                                    merged
  │
  └─ release/vX.Y.Z ──► release/vX.Y.Z
                          merged to both main and develop
```

### Branch Naming Convention

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New feature | `feature/approval-workflow` |
| `fix/` | Bug fix | `fix/auth-token-expiry` |
| `improve/` | Refactoring/improvement | `improve/middleware-performance` |
| `docs/` | Documentation change | `docs/add-troubleshooting-guide` |
| `test/` | Test addition | `test/rule-bulk-operations` |
| `release/` | Release preparation | `release/v1.2.0` |
| `hotfix/` | Production hotfix | `hotfix/critical-security-patch` |

### Branch Protection Rules

```yaml
# .github/settings.yml (conceptual)
branch_prottection:
  main:
    require_pr: true
    required_approvals: 2
    required_status_checks:
      - CI (backend)
      - CI (frontend)
      - Code Coverage
    enforce_admins: true
    prevent_force_push: true
  develop:
    require_pr: true
    required_approvals: 1
```

---

## Commit Guidelines

### Format

```
<type>(<scope>): <subject>

<body> (optional)

<footer> (optional)
```

### Types

| Type | Description | Changelog |
|------|-------------|-----------|
| `feat` | New feature | Added |
| `fix` | Bug fix | Fixed |
| `improve` | Code improvement | Improved |
| `docs` | Documentation only | Documentation |
| `test` | Adding/updating tests | Tests |
| `refactor` | Code refactoring | Refactored |
| `ci` | CI/CD changes | CI/CD |
| `chore` | Housekeeping | Chores |
| `revert` | Revert previous commit | Reverted |

### Examples

```bash
feat(rules): add bulk rule creation endpoint
fix(auth): handle expired refresh tokens gracefully
improve(api): reduce middleware overhead by 40%
docs(readme): update quick start with Docker instructions
test(approvals): add integration test for state machine
refactor(schemas): consolidate Pydantic response models
ci: update GitHub Actions to Node.js 20
chore: bump pytest version
revert: "feat(rules): add bulk rule creation"
```

### Conventional Commits Reference

```bash
# Show last 10 commits with conventional commit format
git log --oneline --no-decorate -10

# Show only feature commits
git log --oneline --grep="feat"

# Show all types
git log --oneline --grep="^(feat|fix|improve|docs|test|refactor|ci|chore)"
```

---

## Pull Request Process

### PR Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## How Has This Been Tested?

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist

- [ ] My code follows the project's style guidelines
- [ ] I have commented my code
- [ ] I have added comments in major blocks
- [ ] I have included a reference to every transformed symbol
- [ ] I have included pertinent test coverage
- [ ] I have updated the documentation (if applicable)
- [ ] All new and existing tests pass
```

### Review Process

```
1. Developer opens PR
       │
       ▼
2. CI pipeline runs (automated)
       │
       ├── Backend tests (pytest)
       ├── Frontend tests (ng test)
       ├── Linting (ruff, ng lint)
       └── Coverage check (min 80%)
       │
       ▼
3. Assigned reviewers (1-2)
       │
       ▼
4. Reviewers provide feedback
       │
       ├── Changes requested → Developer revises
       └── Approved (2 approvals for main, 1 for develop)
       │
       ▼
5. Squash merge to target branch
       │
       ▼
6. CI deploys to staging/production
```

---

## Code Standards

### Python (Backend)

#### Style Guide

Follow [PEP 8](https://peps.python.org/pep-0008/) with project-specific conventions enforced by `ruff` and `black`.

```bash
# Lint
ruff check .

# Format
black .

# Check typing
mypy app/
```

#### File Organization

```python
"""Module docstring: purpose, key behavior."""

# 1. Imports: stdlib first, then third-party, then local
import os
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas import RuleCreateSchema

# 2. Constants
MAX_PRIORITY = 40000
MIN_PRIORITY = 100

# 3. Classes
class FirewallService:
    """Service for managing firewall rules."""
    
    async def create_rule(self, ...) -> FirewallRule:
        """Create a new firewall rule.
        
        Args:
            rule: Rule creation schema
            
        Returns:
            Created firewall rule
            
        Raises:
            ValueError: If priority is out of range
        """
        pass


# 4. Module-level functions
def main():
    """Entry point."""
    pass


if __name__ == "__main__":
    main()
```

#### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Module | lowercase, underscores | `firewall_service.py` |
| Package | lowercase, no underscores | `app/models` |
| Function/method | snake_case | `get_all_rules()` |
| Class | PascalCase | `FirewallRule` |
| Exception | PascalCase + Error | `PriorityConflictError` |
| Constant | UPPER_SNAKE_CASE | `MAX_PRIORITY` |
| Variable | snake_case | `rule_id` |
| Private | leading underscore | `_internal_cache` |

#### Type Hints

Always use type hints for function parameters and return types:

```python
from typing import Optional, List
from pydantic import BaseModel


def get_rule(rule_id: str) -> Optional[FirewallRule]:
    ...

def create_rules(rules: List[RuleCreateSchema]) -> List[FirewallRule]:
    ...
```

### TypeScript/Angular (Frontend)

#### Style Guide

Follow [Angular Style Guide](https://angular.dev/style-guide) with ESLint enforced.

```bash
# Lint
ng lint

# Format
npx prettier --write "src/**/*.ts"
```

#### Component Structure

```typescript
// rules-list.component.ts
@Component({
  selector: 'app-rules-list',
  templateUrl: './rules-list.component.html',
  styleUrls: ['./rules-list.component.css'],
})
export class RulesListComponent implements OnInit, OnDestroy {
  // 1. Inputs/Outputs first
  @Input() workloadId!: string;
  @Output() ruleSelected = new EventEmitter<string>();

  // 2. Public properties
  rules: FirewallRule[] = [];
  loading = false;
  error: string | null = null;

  // 3. Private properties
  private destroy$ = new Subject<void>();
  private subscription = new Subscription();

  constructor(
    private apiService: ApiService,
    private snackBar: MatSnackBar
  ) {}

  // 4. Lifecycle hooks
  ngOnInit(): void {
    this.loadRules();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // 5. Public methods
  loadRules(): void {
    this.loading = true;
    this.apiService.getRules().pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: (rules) => { this.rules = rules; this.loading = false; },
      error: (err) => { this.error = err.message; },
    });
  }

  // 6. Private methods
  private handleError(error: HttpErrorResponse): void {
    this.snackBar.open(error.error?.error?.message || 'Unknown error', 'Close', { duration: 5000 });
  }
}
```

#### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Component class | PascalCase | `RulesListComponent` |
| Component selector | kebab-case | `app-rules-list` |
| Directive/pipe | PascalCase | `RuleFilterPipe` |
| Service class | PascalCase + 'Service' | `ApiService` |
| Interface | PascalCase | `RuleFilter` |
| Type alias | PascalCase | `RuleSortOption` |
| Variable/function | camelCase | `loadRules()` |
| Property | camelCase | `ruleCount` |

---

## Testing Guidelines

### Coverage Requirements

| Layer | Minimum Coverage |
|-------|-----------------|
| Services | 90% |
| API endpoints | 80% |
| Middleware | 100% |
| Schemas | 100% |
| Models | 100% |
| **Overall** | **80%** |

### Writing Tests

#### Backend (pytest)

```python
# test_firewall_service.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.firewall_service import FirewallService
from app.models.firewall_rule import FirewallRule
from app.exceptions import PriorityConflictError


class TestFirewallService:
    """Test cases for FirewallService."""

    @pytest.fixture
    def service(self, db_session):
        """Create a service instance with mocked database session."""
        return FirewallService(db_session)

    @pytest.fixture
    def sample_rule_data(self):
        """Sample rule creation data."""
        return {
            "title": "Allow HTTP",
            "source_cidr": "0.0.0.0/0",
            "dest_cidr": "10.0.0.0/24",
            "protocol": "tcp",
            "port": 80,
            "action": "allow",
            "priority": 100,
        }

    async def test_create_rule_success(self, service, sample_rule_data, mock_repo):
        """Rule is created when priority is available."""
        mock_repo.create_rule.return_value = FirewallRule(id="1", **sample_rule_data)
        
        result = await service.create_rule(sample_rule_data)
        
        assert result.id == "1"
        assert result.title == "Allow HTTP"
        mock_repo.create_rule.assert_called_once()

    async def test_create_rule_priority_conflict(self, service, sample_rule_data, mock_repo):
        """Raises PriorityConflictError when priority exists."""
        mock_repo.create_rule.side_effect = PriorityConflictError("Priority 100 taken")
        
        with pytest.raises(PriorityConflictError, match="Priority 100 taken"):
            await service.create_rule(sample_rule_data)

    @pytest.mark.asyncio
    async def test_list_rules_with_filters(self, service, mock_repo):
        """Filters are applied correctly."""
        mock_repo.list_rules.return_value = [FirewallRule(id="1", title="Allow HTTP")]
        
        result = await service.list_rules(priority=100, status="active")
        
        assert len(result) == 1
        mock_repo.list_rules.assert_called_once(priority=100, status="active")
```

#### Frontend (Jest + Angular)

```typescript
// rules-list.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { RulesListComponent } from './rules-list.component';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { FirewallRule } from '../../shared/models/firewall-rule.model';

describe('RulesListComponent', () => {
  let component: RulesListComponent;
  let fixture: ComponentFixture<RulesListComponent>;
  let mockApiService: jasmine.SpyObj<ApiService>;
  let mockAuthService: jasmine.SpyObj<AuthService>;

  beforeEach(async () => {
    const apiSpy = jasmine.createSpyObj('ApiService', ['getRules']);
    const authSpy = jasmine.createSpyObj('AuthService', ['hasPermission']);

    await TestBed.configureTestingModule({
      declarations: [RulesListComponent],
      imports: [HttpClientTestingModule, MatSnackBarModule],
      providers: [
        { provide: ApiService, useValue: apiSpy },
        { provide: AuthService, useValue: authSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(RulesListComponent);
    component = fixture.componentInstance;
    mockApiService = TestBed.inject(ApiService) as jasmine.SpyObj<ApiService>;
    mockAuthService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit', () => {
    it('should load rules on init', () => {
      const mockRules: FirewallRule[] = [
        { id: '1', title: 'Allow HTTP', priority: 100 } as FirewallRule,
      ];
      mockApiService.getRules.and.returnValue(of(mockRules));

      component.ngOnInit();

      expect(component.rules).toEqual(mockRules);
      expect(component.loading).toBeFalse();
      expect(mockApiService.getRules).toHaveBeenCalled();
    });

    it('should show error on load failure', () => {
      mockApiService.getRules.and.returnValue(throwError(() => new Error('API error')));

      component.ngOnInit();

      expect(component.error).toBeTruthy();
      expect(component.loading).toBeFalse();
    });
  });

  describe('loadRules', () => {
    it('should set loading state while fetching', fakeAsync(() => {
      mockApiService.getRules.and.returnValue(of([]));

      component.loading = true;
      component.loadRules();
      tick();

      expect(component.loading).toBeFalse();
    }));
  });
});
```

### Running Tests

```bash
# Backend - all tests
cd backend
pytest -v

# Backend - specific module
pytest tests/test_firewall_service.py -v

# Backend - with coverage
pytest --cov=app --cov-report=html

# Frontend - all tests
cd frontend
ng test --watch=false

# Frontend - specific component
ng test --watch=false --include='**/rules-list.component.spec.ts'
```

---

## Documentation Standards

### Markdown

```markdown
# Page Title

One-line description.

## Section

Body text with inline `code` and [links](./relative.md).

### Subsection

1. Numbered list for steps
2. Second step

- Bulleted list for items
- Second item

| Column 1 | Column 2 |
|----------|----------|
| Data     | Data     |

```bash
# Code blocks with language hint
echo "hello"
```

```python
def example():
    """Docstring required for all public functions."""
    pass
```

### API Documentation

All public functions and classes must have docstrings:

```python
def get_rules(filters: Optional[Dict] = None) -> List[FirewallRule]:
    """Retrieve firewall rules with optional filtering.
    
    Args:
        filters: Optional filter dictionary with keys:
            - status: Rule status ('active', 'pending', 'inactive')
            - priority: Filter by priority range (min, max)
    
    Returns:
        List of FirewallRule objects matching the filters
        
    Raises:
        DatabaseError: If the database connection fails
        PermissionError: If the user lacks read access
    """
    pass
```

### Architecture Decision Records

Significant architecture changes require an ADR:

```markdown
# ADR-004: Replace requests with httpx

## Status
Accepted

## Context
We are using `requests` for Azure API calls. It is synchronous and blocks the event loop.

## Decision
Use `httpx` for async HTTP calls.

## Consequences
- Async HTTP calls do not block the event loop
- Need to update dependency
- Need to update tests
```

---

## Review Checklist

### For Authors

- [ ] Branch follows naming convention
- [ ] Commits follow Conventional Commits format
- [ ] Code is self-documenting with comments for complex logic
- [ ] All tests pass
- [ ] No linting errors
- [ ] Documentation updated (if API changed)
- [ ] Environment variables documented (if new vars added)
- [ ] Changes tested in local dev environment

### For Reviewers

- [ ] Code follows project style guides
- [ ] Logic is correct and handles edge cases
- [ ] No duplicated code or dead code
- [ ] Tests cover new functionality
- [ ] Documentation is accurate and complete
- [ ] Security considerations addressed (input validation, auth checks)
- [ ] Performance implications considered
- [ ] Breaking changes clearly identified

---

## Getting Help

| Channel | Link |
|---------|------|
| Issues | [github.com/SinsalaRene/.../issues](https://github.com/SinsalaRene/cline-example-project06/issues) |
| Discussions | [github.com/SinsalaRene/.../discussions](https://github.com/SinsalaRene/cline-example-project06/discussions) |
| Documentation | [GitHub Wiki](https://github.com/SinsalaRene/cline-example-project06/wiki) |

---

## Thank You

Thank you for contributing to the Azure Firewall Management Application. Every contribution — from bug fixes to documentation — makes the project better.