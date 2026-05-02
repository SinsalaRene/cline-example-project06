# Azure Firewall Management Application

A comprehensive solution for managing Azure Firewall rules with approval workflows, RBAC, and audit trails.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Key Features](#key-features)
- [Development](#development)
- [Database Setup](#database-setup)
- [Deployment](#deployment)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Architecture Overview

```
┌─────────────────┐         ┌─────────────────────────────────────────────────────┐
│  Angular SPA    │────────▶│  API Gateway / App Service                         │
│  (Frontend)     │         │  ┌─────────────────────────────────┐                │
│                 │         │  │  Backend API (FastAPI)          │                │
│  Auth via       │         │  │  (Python/SQLAlchemy)            │                │
│  Entra ID       │         │  │  ┌────────┬────────┬────────┐  │                │
│                 │         │  │  │  Auth   │  API   │  Work  │  │                │
│  JWT Tokens     │         │  │  │Module │ Modules│ flows │  │                │
│                 │         │  │  └────────┴────────┴────────┘  │                │
└─────────────────┘         │  └─────────────────────────────────┘                │
                            └─────────────────────────────────────────────────────┘
                                     │                    │
                            ┌────────┴───┐       ┌────────┴─────────┐
                            │ Azure API  │       │ PostgreSQL /     │
                            │ (Network   │       │ SQLite (dev)     │
                            │  Watcher)  │       │                    │
                            └────────────┘       └────────────────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Angular 17+ | SPA with SSR support |
| Backend | FastAPI (Python 3.11+) | REST API with auto-generated OpenAPI docs |
| Database | PostgreSQL 13+ | Production data store |
| Auth | Azure Entra ID (JWT) | User authentication & RBAC |
| Infrastructure | Docker + Azure Container Apps | Containerized deployment |
| Migrations | Alembic | Database schema management |
| Testing | pytest + Jest | Unit, integration, and E2E tests |

## Project Structure

```
├── backend/                        # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point, middleware, routers
│   │   ├── config.py               # Configuration management (env vars)
│   │   ├── database.py             # Database connection & session management
│   │   ├── logging.py              # Structured logging with request IDs
│   │   ├── error_tracking.py       # Error tracking & reporting
│   │   ├── api/                    # API route handlers
│   │   │   ├── rules.py            # Firewall rule CRUD + bulk operations
│   │   │   ├── approvals.py        # Approval workflow endpoints
│   │   │   ├── audit.py            # Audit log endpoints
│   │   │   ├── health.py           # Health check probes
│   │   │   └── metrics.py          # Prometheus-compatible metrics
│   │   ├── auth/                   # Authentication module
│   │   │   ├── router.py           # Login/logout/token refresh endpoints
│   │   │   └── auth_service.py     # JWT token generation & validation
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── firewall_rule.py    # Firewall rule model
│   │   │   ├── approval.py         # Approval workflow model
│   │   │   └── audit.py            # Audit log model
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/               # Business logic layer
│   │   │   ├── firewall_service.py # Rule creation, update, deletion logic
│   │   │   ├── approval_service.py # Approval workflow orchestration
│   │   │   ├── audit_service.py    # Audit trail recording
│   │   │   ├── azure_sync_service.py # Azure API integration
│   │   │   └── notification_service.py # Email/Slack notifications
│   │   ├── repositories/           # Data access layer
│   │   ├── middleware/             # HTTP middleware stack
│   │   │   ├── validation.py       # Request body validation
│   │   │   ├── exception_handler.py # Structured error responses
│   │   │   ├── timing.py           # Request duration tracking
│   │   │   └── request_id.py       # UUID request ID propagation
│   │   ├── workflows/              # State machine workflows
│   │   │   ├── approval_workflow.py # Approval state transitions
│   │   │   ├── audit_workflow.py   # Audit event processing
│   │   │   └── notification_workflow.py # Notification dispatch
│   │   └── integrations/           # External service integrations
│   │       └── azure_client.py     # Azure Resource Manager API client
│   ├── tests/                      # Test suite
│   ├── alembic/                    # Database migration scripts
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile                  # Backend container image
├── frontend/                       # Angular frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/               # Singleton services, guards, interceptors
│   │   │   ├── modules/            # Feature modules
│   │   │   │   ├── auth/           # Login/logout
│   │   │   │   ├── dashboard/      # Main dashboard
│   │   │   │   ├── rules/          # Firewall rule management
│   │   │   │   ├── approvals/      # Approval workflows
│   │   │   │   ├── audit/          # Audit log viewer
│   │   │   │   └── workloads/      # Workload management
│   │   │   └── shared/             # Shared components & pipes
│   │   └── main.ts                 # Angular bootstrap
│   ├── angular.json                # Angular CLI configuration
│   ├── package.json                # Node dependencies
│   └── tsconfig.json               # TypeScript configuration
├── docs/                           # Additional documentation
│   ├── AZURE_INTEGRATION.md        # Azure setup guide
│   ├── CROSS_MODULE_WORKFLOWS.md   # Workflow documentation
│   └── TESTING_DOCUMENTATION.md    # Testing strategies
├── tasks/                          # Task tracking
├── README.md                       # This file
├── ARCHITECTURE.md                 # Detailed architecture documentation
├── DEPLOYMENT.md                   # Deployment guide
├── CONTRIBUTING.md                 # Contribution guidelines
└── TROUBLESHOOTING.md              # Troubleshooting guide
```

## Quick Start

### Prerequisites

- **Python** 3.11+ (backend)
- **Node.js** 18+ and **npm** 9+ (frontend)
- **Angular CLI** 17+ (frontend development server)
- **PostgreSQL** 13+ (production; optional for development)
- **Docker** & **Docker Compose** (optional, for containerized deployment)

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# or
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (see Environment Variables below)

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

The API is now available at `http://localhost:8000`.

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server (runs at http://localhost:4200)
ng serve

# Build for production
ng build --configuration production
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up --build

# Or build individual images
docker build -t firewall-mgmt-backend ./backend
docker build -t firewall-mgmt-frontend ./frontend
```

## Environment Variables

Copy `.env.example` from the backend directory and configure your settings:

```bash
cp backend/.env.example backend/.env
```

### Required Variables

```env
# ─── Azure Configuration ───
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here
AZURE_SUBSCRIPTION_ID=your-subscription-id-here
AZURE_RESOURCE_GROUP=your-resource-group-name

# ─── Database Configuration ───
# Development (SQLite - default):
DATABASE_URL=sqlite:///./firewall_mgmt.db

# Production (PostgreSQL):
# DATABASE_URL=postgresql://user:password@host:5432/firewall_mgmt

# ─── Security ───
SECRET_KEY=your-secret-key-at-least-32-characters-long

# ─── Application ───
DEBUG=false
LOG_FORMAT=json
ALLOWED_HOSTS=*
```

For a complete list of all available settings, see `backend/.env.example`.

## API Documentation

Once the backend is running, access the interactive API documentation:

| Endpoint | URL | Description |
|----------|-----|-------------|
| Swagger UI | `http://localhost:8000/docs` | Interactive API explorer with request/response examples |
| ReDoc | `http://localhost:8000/redoc` | Static documentation view |
| Prometheus Metrics | `http://localhost:8000/metrics` | Application metrics in Prometheus format |

### API Endpoints Summary

| Module | Methods | Path | Description |
|--------|---------|------|-------------|
| Auth | POST | `/api/v1/auth/login` | Authenticate and receive JWT token |
| Auth | POST | `/api/v1/auth/refresh` | Refresh an expired token |
| Rules | GET | `/api/v1/rules` | List all firewall rules |
| Rules | POST | `/api/v1/rules` | Create a new firewall rule |
| Rules | GET | `/api/v1/rules/{id}` | Get a specific rule |
| Rules | PUT | `/api/v1/rules/{id}` | Update a rule |
| Rules | DELETE | `/api/v1/rules/{id}` | Delete a rule |
| Rules | POST | `/api/v1/rules/bulk` | Bulk create/update rules |
| Approvals | GET | `/api/v1/approvals` | List approval requests |
| Approvals | POST | `/api/v1/approvals` | Create approval request |
| Approvals | POST | `/api/v1/approvals/{id}/approve` | Approve a request |
| Approvals | POST | `/api/v1/approvals/{id}/reject` | Reject a request |
| Audit | GET | `/api/v1/audit` | Search audit log entries |
| Health | GET | `/health` | Health check probe |

See Swagger UI for the complete endpoint reference with request/response schemas.

## Key Features

- **Firewall Rule Management**: Full CRUD operations for Azure NSG rules with priority validation
- **Approval Workflows**: Multi-step approval process with configurable approvers and escalation
- **RBAC**: Role-based access control with Azure Entra ID integration
- **Audit Trail**: Complete audit logging of all operations with correlation IDs
- **JWT Authentication**: Secure token-based auth with refresh token rotation
- **Rate Limiting**: Configurable rate limits per endpoint (login, API, refresh)
- **Structured Logging**: JSON-formatted logs with request IDs for distributed tracing
- **Health Checks**: Kubernetes-compatible readiness/liveness probes
- **Metrics**: Prometheus-compatible application metrics (request count, latency, errors)
- **Error Tracking**: Centralized error capture with context enrichment
- **Input Validation**: Middleware-level request body and content-type validation
- **Bulk Operations**: Batch create/update for efficient rule management

## Development

### Backend Development

```bash
# Run tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Lint code
ruff check .

# Format code
black .

# Generate OpenAPI schema manually
python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))"
```

### Frontend Development

```bash
# Run unit tests
ng test

# Run end-to-end tests
ng e2e

# Lint code
ng lint

# Build for production
ng build --configuration production
```

### Database Setup

#### Development (SQLite)

The application uses SQLite by default for development — no additional setup required:

```bash
DATABASE_URL=sqlite:///./firewall_mgmt.db
```

#### Production (PostgreSQL)

```bash
DATABASE_URL=postgresql://user:password@host:5432/firewall_mgmt
```

#### Database Migrations

```bash
cd backend

# Initialize Alembic (first time only)
alembic init alembic

# Create a new migration after model changes
alembic revision --autogenerate -m "Add new table"

# Apply all pending migrations
alembic upgrade head

# Rollback the last migration
alembic downgrade -1

# View migration history
alembic history
```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for a comprehensive deployment guide.

### Quick Azure Deploy

```bash
# Login to Azure
az login

# Build and push to Azure Container Registry
az acr login --name youracr
docker build -t youracr.azurecr.io/firewall-mgmt:latest ./backend
docker push youracr.azurecr.io/firewall-mgmt:latest

# Deploy to Container Apps
az containerapp up \
  --name firewall-mgmt \
  --resource-group your-rg \
  --image youracr.azurecr.io/firewall-mgmt:latest \
  --target-port 8000 \
  --env-vars AZURE_TENANT_ID=... SECRET_KEY=...
```

## Testing

```bash
# Backend tests
cd backend
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest --cov=app               # With coverage
pytest tests/test_rules_api.py  # Specific test file

# Frontend tests
cd frontend
ng test                         # Run unit tests
ng test --watch=false           # Run once (CI mode)
ng test --code-coverage         # With coverage report
```

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues and solutions.

### Common Issues

| Issue | Likely Cause | Solution |
|-------|-------------|----------|
| `ModuleNotFoundError` | Missing dependencies | Run `pip install -r requirements.txt` |
| Migration errors | Schema mismatch | Run `alembic upgrade head` |
| CORS errors | Frontend/backend port mismatch | Check `ALLOWED_HOSTS` in `.env` |
| 401 Unauthorized | Expired/missing JWT token | Re-authenticate via `/auth/login` |
| Database locked | SQLite concurrent access | Switch to PostgreSQL or use single process |

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed contribution guidelines.

Quick start:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest` / `ng test`)
5. Commit with [Conventional Commits](https://www.conventionalcommits.org/)
6. Push and submit a Pull Request

## License

MIT