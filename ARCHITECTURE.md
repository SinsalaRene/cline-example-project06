# Architecture Documentation

Comprehensive architecture documentation for the Azure Firewall Management Application.

## Table of Contents

- [System Architecture](#system-architecture)
- [Component Architecture](#component-architecture)
- [Data Architecture](#data-architecture)
- [API Architecture](#api-architecture)
- [Security Architecture](#security-architecture)
- [Infrastructure Architecture](#infrastructure-architecture)
- [Error Handling Architecture](#error-handling-architecture)
- [Testing Architecture](#testing-architecture)
- [Design Decisions](#design-decisions)

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Client Layer                                  │
│  ┌──────────────────┐     ┌──────────────────────────────────────────┐ │
│  │  Angular SPA     │     │  External Consumers (Postman, Scripts)   │ │
│  │  - Auth Module   │     │  ┌────────────────────────────────────┐ │ │
│  │  - Dashboard     │     │  │  Bearer Token (JWT)                  │ │ │
│  │  - Rules Module  │     │  └────────────────────────────────────┘ │ │
│  │  - Approvals     │     └────────────────┬───────────────────────┘ │ │
│  │  - Audit Module│                         │                         │ │
│  │  - Workloads   │                         │ HTTPS / TLS             │ │
│  │  - Shared      │                         │                         │ │
│  └──────────────────┘                         │                     │ │
└────────────────────────────────────────────────┼─────────────────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        API Gateway Layer                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              Azure App Service / Container Apps                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  Reverse Proxy (nginx/Traefik)                             │  │  │
│  │  │  - TLS Termination                                         │  │  │
│  │  │  - Rate Limiting                                           │  │  │
│  │  │  - Request Routing                                         │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Application Layer                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              FastAPI Application (Python)                         │  │
│  │                                                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │
│  │  │ Auth Module  │  │  API Module │  │  Metrics    │              │  │
│  │  │  - Login     │  │  - Rules    │  │  - Prometheus│              │  │
│  │  │  - Refresh   │  │  - Approvals│  │  - Health    │              │  │
│  │  │  - Logout    │  │  - Audit    │  │  - Status    │              │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │                    Middleware Stack                         │  │  │
│  │  │  Validation → ExceptionHandler → Timing → RequestID → CORS │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │
│  │  │ Services    │  │ Workflows   │  │ Repositories│              │  │
│  │  │ - Firewall  │  │ - Approval  │  │ - CRUD Ops  │              │  │
│  │  │ - Approval  │  │ - Audit     │  │ - Queries   │              │  │
│  │  │ - Audit     │  │ - Notify    │  │             │              │  │
│  │  │ - Azure     │  │             │  │             │              │  │
│  │  │ - Notif.    │  │             │  │             │              │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │  │
│  │                                                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  │
│  │  │ Models      │  │ Schemas     │  │ Integrations│              │  │
│  │  │ - SQLAlchemy│  │ - Pydantic  │  │ - Azure     │              │  │
│  │  │ - ORM       │  │ - Validators│  │ - Email     │              │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                                 │                    │
                                                 │                    │
                                                 ▼                    ▼
┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│         Data Layer                 │  │       External Services            │
│  ┌──────────────────────────────┐ │  │  ┌──────────────────────────────┐ │
│  │ PostgreSQL / SQLite          │ │  │  │ Azure Resource Manager       │ │
│  │  - FirewallRules             │ │  │  │  - NSG Rule CRUD             │ │
│  │  - Users                     │ │  │  │  - Network Watcher           │ │
│  │  - Approvals                 │ │  │  │  - Policy Assignment         │ │
│  │  - AuditLogs                 │ │  │  └──────────────────────────────┘ │ │
│  │  - Workloads                 │ │  │                                    │ │
│  └──────────────────────────────┘ │  │  ┌──────────────────────────────┐ │
│                                    │  │  │ Azure Entra ID (AD)          │ │
│                                    │  │  │  - JWT Validation            │ │
│                                    │  │  │  - User/Group Info           │ │
│                                    │  │  └──────────────────────────────┘ │ │
└────────────────────────────────────┘  └────────────────────────────────────┘
```

### Architectural Patterns

| Pattern | Application | Rationale |
|---------|-------------|-----------|
| **Clean Architecture** | Separation of concerns across layers (API → Services → Repositories → Models) | Testability, maintainability, dependency inversion |
| **Layered Architecture** | Middleware → Routes → Services → Repositories → Database | Clear separation of cross-cutting concerns |
| **CQRS (Read/Write Separation)** | Read paths route through services; write paths use workflows | Separation of mutation complexity from query simplicity |
| **Repository Pattern** | All database access through repository layer | Abstracts persistence details, enables mocking in tests |
| **Service Locator** | DI via FastAPI's `Depends()` | Centralized dependency resolution |
| **State Machine** | Approval workflow state transitions | Enforces valid state changes, prevents invalid transitions |

---

## Component Architecture

### Backend Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI App                              │
│                                                                  │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐     │
│  │  Auth Router   │   │ Rules Router  │   │Approvals      │     │
│  │  POST /login   │   │ GET /rules    │   │ Router        │     │
│  │  POST /refresh │   │ POST /rules   │   │ GET /approvals│     │
│  │  POST /logout  │   │ GET /rules/:id│   │ POST /approvals│    │
│  └───────┬───────┘   └───────┬───────┘   │ POST /approvals│    │
│          │                   │            │ :id/approve     │    │
│          ▼                   ▼            │ POST /approvals│    │
│  ┌───────────────┐   ┌───────────────┐   │ :id/reject      │    │
│  │ Auth Service  │   │ Firewall      │   └───────┬─────────┘    │
│  │ JWT generate  │   │ Service       │            │              │
│  │ Token verify  │   │ CRUD ops      │   ┌────────┴─────────┐  │
│  └───────┬───────┘   │ Validation    │   │ Approval Service  │  │
│          │           │ Azure sync    │   │ State transitions │  │
│  ┌───────┴───────┐   │ Notifications │   └────────┬─────────┘  │
│  │ Azure AD      │   └───────┬───────┘            │              │
│  │ Token Info    │           │                    │              │
│  │ RBAC Check    │   ┌───────┴───────┐   ┌───────┴─────────┐  │
│  └───────────────┘   │ Audit Service │   │ Notification    │  │
│                      │ Event logging │   │ Service         │  │
│                      └───────┬───────┘   │ Email/Slack     │  │
│                              │           │ Dispatch        │  │
│  ┌───────────────┐   ┌───────┴───────┐   └───────┬─────────┘  │
│  │ Middleware    │   │ Repository    │            │              │
│  │ Validation    │   │ Layer         │   ┌────────┴─────────┐  │
│  │ Exception     │   │ FirewallRepo │   │ Workflow Engine   │  │
│  │ Timing        │   │ ApprovalRepo │   │ ApprovalWorkflow  │  │
│  │ Request ID    │   │ AuditRepo    │   │ AuditWorkflow     │  │
│  │ CORS          │   │ WorkloadRepo │   │ NotifyWorkflow    │  │
│  └───────────────┘   └─────────────┘   └──────────────────┘  │
│                                                                  │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐     │
│  │  Models (ORM)  │   │ Schemas       │   │ Integrations  │     │
│  │ FirewallRule   │   │ Pydantic V2   │   │ AzureClient   │     │
│  │ Approval       │   │ Request/Resp  │   │ Notification  │     │
│  │ AuditLog       │   │ Validation    │   │ Email/Slack   │     │
│  │ Workload       │   │ Schemas       │   └───────────────┘     │
│  └───────────────┘   └───────────────┘                         │
│                                                                  │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐     │
│  │ Logging        │   │ Error Tracking│   │ Metrics       │     │
│  │ Structured     │   │ Sentry-like   │   │ Prometheus    │     │
│  │ Request-IDs    │   │ Captures      │   │ Counters/     │     │
│  │ JSON format    │   │ Context       │   │ Histograms    │     │
│  └───────────────┘   └───────────────┘   └───────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### Frontend Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       Angular SPA                                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    App Root                               │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  Layout Component                                   │  │   │
│  │  │  ┌──────────────┐  ┌──────────────────────────┐   │  │   │
│  │  │  │  Navigation   │  │  Content Outlet          │   │  │   │
│  │  │  │  - Sidebar    │  │  Router Outlet           │   │  │   │
│  │  │  │  - Topbar     │  │                          │   │  │   │
│  │  │  └──────────────┘  └──────────────────────────┘   │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Core Modules                           │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │   │
│  │  │ Auth Service  │ │  API Service  │ │ ErrorHandler    │ │   │
│  │  │ - Login       │ │ - HTTP Ops   │ │ - Error Catch   │ │   │
│  │  │ - Token Mgmt  │ │ - Retry      │ │ - Reporting     │ │   │
│  │  │ - RBAC Check  │ │ - Intercepts │ │ - Local Storage│ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘ │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │   │
│  │  │ Auth Guard   │ │ HTTP Request  │ │ HTTP Error      │ │   │
│  │  │ Redirect     │ │ Interceptor  │ │ Interceptor     │ │   │
│  │  │ Refresh     │ │ Auth Headers │ │ Error Mapping   │ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Feature Modules                           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │   │
│  │  │ Auth     │ │ Dashboard│ │ Rules    │ │ Approvals  │ │   │
│  │  │ Module   │ │ Module   │ │ Module   │ │ Module     │ │   │
│  │  │───────── │ │───────── │ │───────── │ │────────────│ │   │
│  │  │ Login    │ │ Stats    │ │ List     │ │ List       │ │   │
│  │  │ Logout   │ │ Charts   │ │ Detail   │ │ Detail     │ │   │
│  │  │          │ │ Activity │ │ Form     │ │ Comments   │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │   │
│  │  ┌──────────┐ ┌──────────┐                              │   │
│  │  │ Audit    │ │ Workloads│                              │   │
│  │  │ Module   │ │ Module   │                              │   │
│  │  │───────── │ │───────── │                              │   │
│  │  │ Log View │ │ List     │                              │   │
│  │  │ Search   │ │ Detail   │                              │   │
│  │  │ Export   │ │ Config   │                              │   │
│  │  └──────────┘ └──────────┘                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Shared Module                            │   │
│  │  ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ │   │
│  │  │ Error Notif.   │ │ Loading Spinner│ │ Confirm Dialog│ │   │
│  │  │ Toast Service  │ │               │ │ Generic Modal │ │   │
│  │  └────────────────┘ └────────────────┘ └──────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Architecture

### Entity Relationship Diagram

```
┌──────────────────┐         ┌──────────────────┐
│     users        │         │     roles        │
│───────────────── │         │───────────────── │
│ id (PK)          │1───────*│ id (PK)          │
│ username          │         │ name             │
│ email             │         │ permissions      │
│ password_hash     │         │                  │
│ created_at        │         └──────────────────┘
│ updated_at        │1───────*
└────────┬─────────┘
         │
         │
┌────────┴─────────┐         ┌──────────────────┐
│    workloads     │         │  firewall_rules   │
│───────────────── │1───────*│───────────────── │
│ id (PK)          │         │ id (PK)          │
│ name             │         │ title             │
│ description      │◄────┐   │ workload_id (FK)  │
│ environment      │     │   │ priority          │
│ subscription_id  │     │   │ source_cidr       │
│ resource_group   │     │   │ dest_cidr         │
│ created_at       │     │   │ protocol          │
└─────────────────┘     │   │ port              │
                        │   │ direction         │
                        │   │ status            │
┌──────────────────┐     │   │ action (allow/deny)
│  audit_logs      │     │   │ approved_by (FK)│
│───────────────── │     │   │ created_at       │
│ id (PK)          │     │   │ updated_at       │
│ entity_type      │     └──►│ entity_id        │
│ entity_id        │         └──────────────────┘
│ action           │
│ performed_by     │
│ details          │
│ created_at       │
└──────────────────┘

┌──────────────────┐         ┌──────────────────┐
│   approvals      │         │ approval_comments │
│───────────────── │1───────*│───────────────── │
│ id (PK)          │         │ id (PK)          │
│ rule_id (FK)     │         │ approval_id (FK) │
│ requester_id (FK)│         │ user_id (FK)     │
│ approver_id (FK) │         │ comment          │
│ status            │         │ created_at       │
│ state            │         └──────────────────┘
│ created_at       │
│ updated_at       │
└──────────────────┘
```

### Data Flow Diagrams

#### Write Path (Firewall Rule Creation)

```
Client Request
     │
     ▼
┌─────────────────┐
│ Validation MW   │ → Validate schema, content-type, size
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Auth Service    │ → Verify JWT, check RBAC
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Firewall Service│ → Validate priority, check duplicates
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Workflow Engine │ → Check if approval required
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 ┌────┐   ┌──────────┐
 │ No │→  │ Create   │
 │Yes │   │ directly│
 └┬───┘   └──────────┘
   │
   ▼
┌──────────────┐
│ Create       │
│ Approval     │
│ (pending)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Audit Log    │
│ Record       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Repository   │
│ Write to DB  │
└──────┬───────┘
       │
       ▼
  Response
```

#### Read Path (List Firewall Rules)

```
Client Request (GET /api/v1/rules)
        │
        ▼
┌─────────────────┐
│ Auth Service    │ → Verify JWT, extract user
└────────┬────────┘
        │
        ▼
┌─────────────────┐
│ Service Layer   │ → Query with filters
└────────┬────────┘
        │
        ▼
┌─────────────────┐
│ Repository Layer│ → Execute SQL query
└────────┬────────┘
        │
        ▼
┌─────────────────┐
│ Map to Models   │ → Transform rows to objects
└────────┬────────┘
        │
        ▼
┌─────────────────┐
│ Schema Validate │ → Pydantic response schema
└────────┬────────┘
        │
        ▼
   Response (JSON)
```

---

## API Architecture

### Request Lifecycle

```
┌─────────┐     ┌────────────┐     ┌────────────┐     ┌──────────┐
│  Client  │────▶│ Validation │────▶│ Exception  │────▶│ Timing   │
│          │     │ Middleware │     │ Handler    │     │ MW       │
└─────────┘     └────────────┘     └────────────┘     └──────────┘
                                                   │
                                                   ▼
┌─────────┐     ┌────────────┐     ┌────────────┐     ┌──────────┐
│  Client  │◀───│  CORS      │◀───│  Request   │◀───│  Router  │
│          │     │ Middleware │     │ ID MW      │     │ Handler  │
└─────────┘     └────────────┘     └────────────┘     └──────────┘
```

### Middleware Pipeline Order

```
1. ValidationMiddleware   - Validates Content-Type, body size, JSON parsing
2. ExceptionHandlerMW     - Catches unhandled exceptions
3. TimingMiddleware       - Measures request duration, adds X-Response-Time
4. RequestIDMiddleware    - Generates/propagates UUID request IDs
5. CORSMiddleware         - Sets CORS headers
6. FastAPI Router         - Dispatches to route handler
```

### API Versioning Strategy

The application uses URL path versioning (`/api/v1/`). Future version migrations will follow this pattern:

```
/api/v1/rules  →  /api/v2/rules  →  /api/v3/rules
```

---

## Security Architecture

### Authentication Flow

```
┌─────────┐     ┌────────────┐     ┌────────────┐     ┌──────────┐
│  Client  │────▶│ Auth API   │────▶│ Azure AD   │────▶│ JWT      │
│          │     │ /login     │     │ Validate   │     │ Sign      │
└─────────┘     └────────────┘     └────────────┘     └──────────┘
                                                        │
                                                        ▼
                                               ┌──────────────────┐
                                               │ JWT Token Pair   │
                                               │ - Access Token   │
                                               │ - Refresh Token  │
                                               └──────────────────┘
```

### Authorization Matrix

| Role | Rules CRUD | Approvals | Audit View | Config |
|------|------------|-----------|------------|--------|
| FirewallReader | Read only | View own | View own | No |
| FirewallWriter | Create/Read | Request | View own | No |
| FirewallApprover | Read | Approve/Reject | View all | No |
| FirewallAdmin | All | All | All | Yes |
| Auditor | Read only | View all | All | No |

### JWT Token Structure

```json
{
  "sub": "user-uuid",
  "username": "john.doe",
  "roles": ["FirewallAdmin"],
  "permissions": ["rules:read", "rules:write", "approvals:approve"],
  "exp": 1700000000,
  "jti": "unique-token-id"
}
```

---

## Infrastructure Architecture

### Deployment Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                      Azure Resource Group                        │
│                                                                  │
│  ┌─────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │ Azure ACR   │    │ Container Apps  │    │ Azure Database │  │
│  │             │    │                 │    │ for PostgreSQL │  │
│  │ firewall-mgmt│   │  ┌───────────┐  │    │                │  │
│  │ latest       │◀── │  Backend    │  │    │ firewall-mgmt  │  │
│  │ (build)     │    │  App (8000) │  │    │ (Postgres 14)  │  │
│  │             │    │  ┌───────────┐  │    │                │  │
│  │ frontend-mgmt│   │  Frontend   │  │    └────────────────┘  │
│  │ latest       │    │  (443)     │  │              │          │
│  └─────────────┘    └─────────────┘  │              │          │
│                                      │  ┌───────────┐ │          │
│                                      │  │ Log       │ │          │
│                                      │  │ Analytics │ │          │
│                                      │  │ (optional)│ │          │
│                                      │  └───────────┘ │          │
│                                      └────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Container Architecture

```dockerfile
# Backend (multi-stage)
Stage 1: python:3.11-slim → Install deps, compile
Stage 2: python:3.11-slim → Run uvicorn
```

```yaml
# docker-compose.yml (development)
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres]
  
  frontend:
    build: ./frontend
    ports: ["4200:80"]
    depends_on: [backend]
  
  postgres:
    image: postgres:15
    environment: {POSTGRES_DB: firewall_mgmt}
    volumes: [pgdata:/var/lib/postgresql/data]

volumes: {pgdata:}
```

---

## Error Handling Architecture

### Error Hierarchy

```
HTTP Exception
├── 4xx Client Errors
│   ├── 400 Bad Request → ValidationMiddleware
│   ├── 401 Unauthorized → Auth middleware
│   ├── 403 Forbidden → RBAC check
│   ├── 404 Not Found → Repository not found
│   ├── 409 Conflict → Priority conflict
│   └── 429 Too Many Requests → Rate limiter
└── 5xx Server Errors
    ├── 500 Internal Error → ExceptionHandlerMW
    └── 503 Service Unavailable → Health check fails
```

### Error Response Format

```json
{
  "error": {
    "code": "PRIORITY_CONFLICT",
    "message": "A rule with priority 100 already exists",
    "path": "/api/v1/rules",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-01-15T10:30:00+00:00",
    "details": [
      {
        "field": "priority",
        "message": "Conflict with rule ID abc123"
      }
    ]
  }
}
```

---

## Testing Architecture

### Test Pyramid

```
        /\
       /  \
      /    \        E2E Tests (Protractor/Cypress)
     /______\
    /        \      Integration Tests (pytest, test endpoints with DB)
   /__________\
  /            \    Unit Tests (pytest, Jest - isolate services/components)
 /______________\
```

### Test File Organization

```
backend/tests/
├── conftest.py                 # Shared fixtures, database setup
├── test_*                      # Test modules
├── test_auth.py               # Auth service unit tests
├── test_rules_api.py          # Rules endpoint integration tests
├── test_approvals_api.py      # Approvals endpoint tests
├── test_middleware.py         # Middleware unit tests
└── test_integration.py        # Full workflow integration tests

frontend/src/app/
├── core/services/*.spec.ts    # Service unit tests
├── modules/*/*.spec.ts        # Component unit tests
└── shared/*.spec.ts           # Shared component tests
```

---

## Design Decisions

### Why FastAPI?

| Factor | Rationale |
|--------|-----------|
| Performance | Async-first, built on Starlette (ASGI) |
| Auto-generated docs | OpenAPI/Swagger built-in |
| Type safety | Pydantic schemas for request/response validation |
| Ecosystem | Rich plugin ecosystem, fast-growing community |

### Why Angular?

| Factor | Rationale |
|--------|-----------|
| Enterprise adoption | Large Angular shops, proven at scale |
| TypeScript-first | Type-safe client-side development |
| CLI tooling | Scaffolding, building, testing in one tool |
| RxJS | Reactive programming for complex async flows |

### Why SQLAlchemy + Alembic?

| Factor | Rationale |
|--------|-----------|
| ORM maturity | Battle-tested, widely used |
| Migration tooling | Alembic is the de facto standard for Python |
| Flexibility | Works with any SQLAlchemy-supported database |

### Why Repository Pattern?

| Factor | Rationale |
|--------|-----------|
| Testability | Repositories can be mocked in service unit tests |
| Abstraction | Switch databases without changing business logic |
| Single source of truth | All SQL lives in one place |