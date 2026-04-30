# Azure Firewall Management Application - Implementation Plan

## 1. Requirements Summary

### 1.1 Core Requirements
- Manage Azure Firewall rules across large landing zones
- View and edit firewall rules with audit trails
- Multi-level approval workflows
- Entra ID (Azure AD) authentication
- Role-based access control (RBAC) tied to workloads
- Multi-level approval flows (workload stakeholder + security stakeholder)
- Python backend
- Angular frontend
- Azure-based infrastructure (container/web app)
- Cloud-provider agnostic architecture

### 1.2 Key Features
- **Firewall Rule Management**: CRUD operations for Azure Firewall rules
- **Landing Zone Scope**: Multi-subscription, multi-resource group support
- **Audit Trail**: Track all changes with who, what, when
- **Approval Workflow**: Configurable multi-stage approval process
- **Entra ID Auth**: Azure AD authentication for all users
- **RBAC**: Workload-bound roles and permissions
- **Multi-level Approvals**: Workload stakeholder + Security stakeholder approval gates

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────┐         ┌─────────────────────────────────────────────────────┐
│                 │         │                    Azure Firewall Management          │
│  Angular SPA    │────────▶│                                                     │
│  (Frontend)     │         │  ┌─────────────────┐  ┌─────────────────────────┐  │
│                 │         │  │                 │  │                         │  │
│  Auth via Entra │         │  │  API Gateway    │  │  Azure Functions /      │  │
│                 │         │  │  (App Service)  │──│  Container Apps         │  │
└─────────────────┘         │  │                 │  │  (Backend API)          │  │
                            │  │                   │  │                         │  │
                            │  │  ┌────────────────┴──┴──────────────────┐     │  │
                            │  │  │     Firewall Service Layer           │     │  │
                            │  │  └────────────────┬──────────────────┘     │  │
                            │  │                   │                        │  │
                            │  │  ┌────────────────┴──┴──────────────────┐     │  │
                            │  │  │     Approval Workflow Engine         │     │  │
                            │  │  └────────────────┬──────────────────┘     │  │
                            │  │                   │                        │  │
                            │  │  ┌────────────────┴──┴──────────────────┐     │  │
                            │  │  │     Audit & Logging Service          │     │  │
                            │  │  └────────────────┬──────────────────┘     │  │
                            │  │                   │                        │  │
                            │  │  ┌────────────────┴──┴──────────────────┐     │  │
                            │  │  │     Azure Firewall Management SDK    │     │  │
                            │  │  └────────────────┬──────────────────┘     │  │
                            │  │                  │                        │  │
                            │  └─────────────────┼────────────────────────┘  │
                            │                    │                           │
                            └────────────────────┼───────────────────────────┘
                                                 │
                                                 ▼
                            ┌─────────────────────────────────────────────┐
                            │                                             │
                            │  Azure Landing Zones (Subscription Hierarchy)│
                            │  ┌──────────┐  ┌──────────┐              │
                            │  │   Hub    │  │   Spoke  │              │
                            │  │ Firewall │  │ Firewall │              │
                            │  └──────────┘  └──────────┘              │
                            └─────────────────────────────────────────────┘
```

### 2.2 Component Breakdown

| Component | Technology | Description |
|-----------|------------|-------------|
| Frontend | Angular 17+ with Angular Material | Single-page application |
| Backend API | Python FastAPI | RESTful API service |
| Auth | Azure Entra ID (OIDC) | JWT token validation |
| Database | Azure Cosmos DB / PostgreSQL | Persistence layer |
| Queue/Event | Azure Service Bus / Redis | Async event handling |
| Audit Store | Azure Blob Storage / Log Analytics | Immutable audit logs |
| Deployment | Azure Container Apps / App Service | Infrastructure as Code |
| CI/CD | GitHub Actions / Azure DevOps | Pipeline automation |

---

## 3. Detailed Component Design

### 3.1 Backend API Structure (`backend/`)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Configuration management
│   ├── dependencies.py          # Dependency injection
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Token validation & parsing
│   │   ├── role_service.py      # RBAC enforcement
│   │   └── entra_id.py          # Entra ID integration
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── firewall_rule.py      # Firewall rule models
│   │   ├── approval.py           # Approval workflow models
│   │   ├── audit.py              # Audit log models
│   │   ├── workload.py          # Workload models
│   │   └── user.py              # User/role models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── firewall_service.py   # Azure Firewall CRUD
│   │   ├── approval_service.py   # Approval workflow orchestration
│   │   ├── audit_service.py      # Audit trail management
│   │   ├── workload_service.py   # Workload management
│   │   ├── rule_validation.py    # Rule conflict detection
│   │   └── azure_client.py       # Azure SDK wrapper
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── rules.py              # Rule CRUD endpoints
│   │   ├── approvals.py           # Approval workflow endpoints
│   │   ├── audit.py               # Audit log endpoints
│   │   ├── workloads.py           # Workload endpoints
│   │   ├── users.py               # User management endpoints
│   │   └── health.py              # Health check endpoints
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base_repository.py    # Base CRUD operations
│   │   ├── rule_repository.py
│   │   ├── approval_repository.py
│   │   ├── audit_repository.py
│   │   └── workload_repository.py
│   │
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── base_workflow.py      # Workflow base class
│   │   ├── approval_workflow.py  # Approval flow engine
│   │   └── notification_service.py
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── azure_firewall.py     # Azure Firewall SDK
│   │   ├── azure_resourcegraph.py # Resource Graph queries
│   │   ├── azure_sentinel.py     # Sentinel integration (optional)
│   │   └── teams.py              # MS Teams notifications
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── firewall_rule.py      # Pydantic schemas
│   │   ├── approval.py           # Approval schemas
│   │   ├── user.py               # User schemas
│   │   └── response.py           # Response schemas
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # Structured logging
│       ├── validators.py         # Custom validators
│       └── helpers.py            # Utility functions
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_firewall_service.py
│   ├── test_approval_workflow.py
│   ├── test_api.py
│   └── fixtures.py
├── requirements.txt
├── pyproject.toml
├── .env.example
└── Dockerfile
```

### 3.2 Frontend Structure (`frontend/`)

```
frontend/
├── src/
│   ├── main.ts
│   ├── app/
│   │   ├── app.component.ts
│   │   ├── app.routes.ts
│   │   │
│   │   ├── core/
│   │   │   ├── core.module.ts
│   │   │   ├── auth/
│   │   │   │   ├── auth.guard.ts
│   │   │   │   ├── auth.service.ts
│   │   │   │   ├── auth.interceptor.ts
│   │   │   │   └── auth.component.ts
│   │   │   ├── services/
│   │   │   │   ├── api.service.ts
│   │   │   │   ├── http.interceptor.ts
│   │   │   │   └── error.handler.ts
│   │   │   └── guards/
│   │   │       ├── role.guard.ts
│   │   │       └── approval.guard.ts
│   │   │
│   │   ├── features/
│   │   │   ├── dashboard/
│   │   │   │   ├── dashboard.component.ts
│   │   │   │   └── dashboard.component.html
│   │   │   ├── rules/
│   │   │   │   ├── rules.component.ts
│   │   │   │   ├── rules.component.html
│   │   │   ├── rules-form/
│   │   │   │   ├── rules-form.component.ts
│   │   │   │   └── rules-form.component.html
│   │   │   ├── approvals/
│   │   │   │   ├── approvals.component.ts
│   │   │   │   └── approvals.component.html
│   │   │   ├── audit/
│   │   │   │   ├── audit.component.ts
│   │   │   │   └── audit.component.html
│   │   │   ├── workloads/
│   │   │   │   ├── workloads.component.ts
│   │   │   │   └── workloads.component.html
│   │   │   └── users/
│   │   │       ├── users.component.ts
│   │   │       └── users.component.html
│   │   │
│   │   ├── shared/
│   │   │   ├── components/
│   │   │   │   ├── confirm-dialog/
│   │   │   │   ├── status-badge/
│   │   │   │   ├── pagination/
│   │   │   │   └── search-filter/
│   │   │   ├── pipes/
│   │   │   ├── directives/
│   │   │   └── models/
│   │   │       ├── firewall-rule.model.ts
│   │   │       ├── approval.model.ts
│   │   │       └── user.model.ts
│   │   │
│   │   └── layout/
│   │       ├── layout.component.ts
│   │       ├── header.component.ts
│   │       └── sidebar.component.ts
│   │
│   ├── assets/
│   ├── styles/
│   ├── environments/
│   │   ├── environment.ts
│   │   └── environment.prod.ts
│   └── index.html
├── angular.json
├── package.json
├── tsconfig.json
├── Dockerfile
└── nginx.conf (for production)
```

### 3.3 Infrastructure as Code (`infrastructure/`)

```
infrastructure/
├── terraform/
│   ├── main.tf                    # Provider & resource group setup
│   ├── variables.tf               # Input variables
│   ├── outputs.tf                 # Output values
│   ├── modules/
│   │   ├── app-service/           # Azure App Service / Container App
│   │   ├── database/              # Cosmos DB / PostgreSQL
│   │   ├── key-vault/             # Secrets management
│   │   ├── monitor/               # Application Insights
│   │   └── networking/            # VNet, subnets, firewalls
│   ├── environments/
│   │   ├── dev/                   # Development environment
│   │   ├── staging/               # Staging environment
│   │   └── prod/                  # Production environment
│   └── scripts/
│       ├── deploy.sh              # Deployment script
│       └── init.sh                # Initialization script
│
├── arm/                           # ARM templates (alternative)
└── bicep/                         # Bicep templates (preferred Azure IaC)
```

### 3.4 Database Schema

```sql
-- Workloads
CREATE TABLE workloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    owner_id UUID REFERENCES users(id),
    resource_groups JSONB,
    subscriptions JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Firewall Rules (local cache for audit)
CREATE TABLE firewall_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_collection_name VARCHAR(255) NOT NULL,
    priority INTEGER NOT NULL,
    rule_group_name VARCHAR(255),
    action VARCHAR(20) NOT NULL, -- Allow, Deny
    protocol VARCHAR(20) NOT NULL, -- Http, Https, Tcp, Udp, Icmp
    source_addresses TEXT[],
    destination_fqdns TEXT[],
    source_ip_groups TEXT[],
    destination_ports INTEGER[],
    workload_id UUID REFERENCES workloads(id),
    azure_resource_id TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- active, pending, archived
    change_request_id UUID REFERENCES approval_requests(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Approval Requests
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_ids UUID[] NOT NULL,
    change_type VARCHAR(50) NOT NULL, -- create, update, delete
    description TEXT,
    current_user_id UUID REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, revoked
    workload_id UUID REFERENCES workloads(id),
    required_approvals INTEGER DEFAULT 2,
    current_approval_stage INTEGER DEFAULT 0,
    approval_flow VARCHAR(50) DEFAULT 'multi_level', -- multi_level, parallel
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Approval Steps
CREATE TABLE approval_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_request_id UUID REFERENCES approval_requests(id),
    approver_id UUID REFERENCES users(id),
    approver_role VARCHAR(50) NOT NULL, -- workload_stakeholder, security_stakeholder
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    comments TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit Log (immutable)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id TEXT,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    correlation_id UUID,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Users & Roles (synced from Entra ID)
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    role VARCHAR(100) NOT NULL, -- owner, admin, developer, security_reader, network_admin
    workload_id UUID REFERENCES workloads(id),
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- Approval Workflow Definitions
CREATE TABLE approval_workflow_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    trigger_conditions JSONB, -- workload type, rule priority, etc.
    required_roles TEXT[] NOT NULL, -- ordered list of required approvers
    timeout_hours INTEGER DEFAULT 48,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. API Endpoints Design

### 4.1 Authentication & Authorization

| Method | Endpoint | Description | Auth Required | Roles |
|--------|----------|-------------|---------------|-------|
| GET | `/api/auth/me` | Get current user info | Yes | All |
| POST | `/api/auth/refresh` | Refresh access token | Yes | All |

### 4.2 Firewall Rules

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/rules` | List firewall rules (with pagination) | viewer+ |
| GET | `/api/rules/{id}` | Get single rule details | viewer+ |
| POST | `/api/rules` | Create new rule (creates approval request) | creator+ |
| PUT | `/api/rules/{id}` | Update existing rule (creates approval request) | editor+ |
| DELETE | `/api/rules/{id}` | Delete rule (creates approval request) | editor+ |
| GET | `/api/rules/pending` | List pending rules for approval | viewer+ |
| POST | `/api/rules/import` | Bulk import rules from Azure | admin |
| POST | `/api/rules/export` | Export rules | viewer+ |

### 4.3 Approval Workflows

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/approvals` | List approval requests | viewer+ |
| GET | `/api/approvals/{id}` | Get approval details | viewer+ |
| POST | `/api/approvals/{id}/approve` | Approve request | workload_stakeholder+ |
| POST | `/api/approvals/{id}/reject` | Reject request | security_stakeholder+ |
| POST | `/api/approvals/{id}/comment` | Add comment | All |
| GET | `/api/approvals/{id}/audit` | Get approval audit trail | viewer+ |

### 4.4 Workloads

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/workloads` | List workloads | viewer+ |
| GET | `/api/workloads/{id}` | Get workload details | viewer+ |
| POST | `/api/workloads` | Create workload | admin |
| PUT | `/api/workloads/{id}` | Update workload | admin |
| DELETE | `/api/workloads/{id}` | Delete workload | admin |

### 4.5 Audit

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/api/audit` | List audit entries | viewer+ |
| GET | `/api/audit/resource/{id}` | Get audit for specific resource | viewer+ |
| GET | `/api/audit/export` | Export audit log | viewer+ |

---

## 5. Approval Flow Design

### 5.1 Multi-Level Approval Workflow

```
                    ┌─────────────────────────────────────────────┐
                    │           User Creates/Modifies Rule        │
                    └─────────────┬──────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────────────────────┐
                    │           Create Approval Request           │
                    │   Stage 1: Workload Stakeholder Review      │
                    └─────────────┬──────────────────────────────┘
                                  │
                    ┌─────────────┼──────────────────────────────┐
                    │   Pending    │                            │
                    │   Rejected◄──┼──┐                         │
                    │   Approved──►│  │                         │
                    └─────────────┘  │                         │
                                     │                         │
                    ┌────────────────┼───────────────────┐    │
                    │  Stage 2: Security Stakeholder    │    │
                    │         Review                      │    │
                    └─────────────┬┴────────────────────┘    │
                                │                             │
                    ┌─────────────┼────────────────────┐     │
                    │   Pending   │                    │     │
                    │   Rejected◄─┤─┘                  │     │
                    │   Approved►─┤─┐                  │     │
                    └─────────────┘ │                  │     │
                                    │                  │     │
                    ┌───────────────┼──────────────────┘     │
                    │  Apply Rule to Azure Firewall          │
                    └───────────────┼───────────────────────┘
                                    │
                    ┌───────────────┼───────────────────────┐
                    │   Success     │                        │
                    │   Updated ◄───┤─┐                      │
                    │   Failed ────►┤─┘                      │
                    └───────────────┘                        │
```

### 5.2 Approval Flow Configuration

Each workload can have its own approval workflow definition:

```json
{
  "workflowDefinition": {
    "name": "standard-security-workload",
    "requiredApprovals": [
      {
        "role": "workload_stakeholder",
        "count": 1,
        "description": "Workload owner must approve"
      },
      {
        "role": "security_stakeholder",
        "count": 1,
        "description": "Security team must approve"
      }
    ],
    "timeoutHours": 48,
    "autoEscalation": true,
    "escalationAfterHours": 24
  }
}
```

---

## 6. Technology Stack Details

### 6.1 Backend
- **Framework**: Python 3.12+ with FastAPI
- **ORM**: SQLAlchemy / SQLModel
- **Auth**: python-jose (JWT validation) + Azure AD OpenID Connect
- **HTTP Client**: httpx (for Azure SDK)
- **Validation**: Pydantic v2
- **Testing**: pytest + httpx
- **Linting**: ruff + mypy
- **Container**: Docker with multi-stage builds

### 6.2 Frontend
- **Framework**: Angular 17+ (Standalone components)
- **UI Library**: Angular Material or Tailwind CSS + Headless UI
- **State Management**: Signals or RxJS
- **HTTP Client**: Angular HttpClient with interceptors
- **Auth**: @azure/msal-angular (MSAL for Entra ID)
- **Testing**: Jasmine/Karma or Cypress (E2E)

### 6.3 Infrastructure
- **Compute**: Azure Container Apps or App Service
- **Database**: Azure Cosmos DB (NoSQL) or Azure PostgreSQL
- **Secrets**: Azure Key Vault
- **Monitoring**: Application Insights + Log Analytics
- **CI/CD**: GitHub Actions or Azure DevOps
- **IaC**: Terraform or Bicep

---

## 7. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up project repository structure
- [ ] Configure backend FastAPI project
- [ ] Configure Angular project
- [ ] Set up database schema
- [ ] Implement authentication with Entra ID
- [ ] Create basic project structure and conventions

### Phase 2: Core Backend (Weeks 3-4)
- [ ] Implement Azure Firewall integration
- [ ] Create data models and repositories
- [ ] Implement rule CRUD operations
- [ ] Implement workload management
- [ ] Create basic audit logging

### Phase 3: Approval Workflow (Weeks 5-6)
- [ ] Design and implement approval workflow engine
- [ ] Implement multi-level approval logic
- [ ] Create notification service (email/Teams)
- [ ] Implement approval dashboard endpoints
- [ ] Add audit trail for approval actions

### Phase 4: Frontend Development (Weeks 7-9)
- [ ] Implement dashboard component
- [ ] Implement firewall rules view and edit
- [ ] Implement approval workflow UI
- [ ] Implement audit log viewer
- [ ] Implement workload management UI
- [ ] Add role-based UI elements

### Phase 5: Integration & Testing (Weeks 10-11)
- [ ] End-to-end testing
- [ ] Performance testing
- [ ] Security testing
- [ ] User acceptance testing
- [ ] Bug fixes and refinements

### Phase 6: Deployment & Documentation (Week 12)
- [ ] Infrastructure as Code deployment
- [ ] CI/CD pipeline setup
- [ ] Documentation (user guide, developer guide)
- [ ] Go-live preparation
- [ ] Production deployment

---

## 8. Security Considerations

### 8.1 Authentication & Authorization
- All users authenticate via Azure Entra ID (OpenID Connect)
- Access tokens validated server-side using JWKS
- Role assignments synced from Entra ID groups
- Resource-level authorization based on workload membership
- Short-lived access tokens with refresh tokens

### 8.2 API Security
- All endpoints protected by authentication
- Role-based access control on all operations
- Input validation on all user inputs
- SQL injection prevention via parameterized queries
- Rate limiting on sensitive endpoints

### 8.3 Data Security
- Sensitive data encrypted at rest (AES-256)
- TLS 1.3 for all in-flight data
- Secrets stored in Azure Key Vault
- Audit logs are immutable (append-only)
- PII minimized where possible

### 8.4 Azure Firewall Integration
- Least privilege RBAC on Azure side
- Managed Identity for service authentication
- Dedicated service principal for API access
- Resource Graph queries for efficient scanning

---

## 9. Environment Configuration

### 9.1 Required Environment Variables

```env
# Azure
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id

# Application
SECRET_KEY=your-secret-key
DEBUG=false
ALLOWED_HOSTS=https://your-domain.com

# Database
DATABASE_URL=your-database-connection-string

# Azure Services
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_REGION=eastus

# Notifications
TEAMS_WEBHOOK_URL=your-teams-webhook
SMTP_HOST=your-smtp-host
SMTP_PORT=587

# Frontend
NGINX_PORT=80
API_BASE_URL=https://your-api-domain.com
```

---

## 10. CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && ruff check .
      - run: cd backend && pytest --cov=app/

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci
      - run: cd frontend && npm run build -- --configuration production

  docker-build:
    needs: [backend-test, frontend-build]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: firewall-mgmt:latest

  deploy:
    needs: [docker-build]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - uses: azure/container-apps-deploy-action@v1
        with:
          containerAppName: firewall-mgmt
          resourceGroup: your-resource-group
          image: firewall-mgmt:latest
```

---

## 11. Provider-Agnostic Design

To ensure migratability to other cloud providers:

1. **Abstract Azure SDK**: Create interfaces for cloud provider abstraction
2. **Configuration-driven**: Provider-specific config in separate modules
3. **Infrastructure modules**: Terraform modules for AWS/GCP equivalents
4. **Database abstraction**: Use SQLModel/SQLAlchemy for database independence
5. **Container-first**: Docker containers ensure portability

### Provider Abstraction Layer

```python
# backend/app/integrations/provider.py
from abc import ABC, abstractmethod

class CloudProvider(ABC):
    @abstractmethod
    def get_firewall_rules(self, resource_id: str) -> list:
        pass
    
    @abstractmethod
    def update_firewall_rule(self, rule: FirewallRule) -> bool:
        pass
    
    @abstractmethod
    def delete_firewall_rule(self, rule_id: str) -> bool:
        pass

class AzureProvider(CloudProvider):
    # Azure-specific implementation
    ...

class AWSProvider(CloudProvider):
    # AWS-specific implementation
    ...

class GCPProvider(CloudProvider):
    # GCP-specific implementation
    ...
```

---

## 12. Project File Structure (Top Level)

```
firewall-mgmt/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Angular frontend
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── infrastructure/             # Terraform / Bicep
│   ├── terraform/
│   └── bicep/
├── .github/                    # GitHub Actions
│   └── workflows/
├── docs/                       # Documentation
│   ├── api/
│   ├── architecture/
│   └── user-guide/
├── .gitignore
├── README.md
├── LICENSE
└── CHANGELOG.md
```

---

## 13. Next Steps to Begin Implementation

1. **Initialize repositories** with this structure
2. **Set up Azure resources**:
   - Create Entra ID app registration
   - Configure API permissions (Azure Resource Manager)
   - Create Azure resource group
3. **Scaffold backend** with FastAPI and basic routes
4. **Scaffold frontend** with Angular and authentication
5. **Deploy initial version** to Azure for internal testing