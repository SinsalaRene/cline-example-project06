# Deployment Guide

Complete deployment guide for the Azure Firewall Management Application.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Azure Container Apps](#azure-container-apps)
- [Azure Database for PostgreSQL](#azure-database-for-postgresql)
- [Azure Container Registry](#azure-container-registry)
- [Azure App Configuration](#azure-app-configuration)
- [Azure Frontend Deployment](#azure-frontend-deployment)
- [Environment Variables Reference](#environment-variables-reference)
- [Health Checks & Monitoring](#health-checks--monitoring)
- [Rollback Procedures](#rollback-procedures)
- [CI/CD Pipeline](#cicd-pipeline)
- [Security Checklist](#security-checklist)

---

## Prerequisites

### Azure Account

- Azure subscription with contributor permissions
- Azure CLI installed (`az --version`)
- Docker installed and running
- Azure Container Registry (ACR) name

### Tools

```bash
# Azure CLI
az --version

# Docker
docker --version

# Terraform (optional, for infrastructure as code)
terraform --version
```

---

## Local Development

### Prerequisites

```bash
# Required
Python 3.11+
Node.js 18+
PostgreSQL 13+ (optional for production-mode testing)
```

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone https://github.com/SinsalaRene/cline-example-project06.git
cd cline-example-project06

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate          # Linux/Mac
# or
venv\Scripts\activate             # Windows

pip install -r requirements.txt

# 3. Environment configuration
cp .env.example .env
# Edit .env with your settings (see below)

# 4. Database setup (SQLite for dev)
alembic upgrade head

# 5. Start backend
uvicorn app.main:app --reload
```

```bash
# 6. Frontend setup (separate terminal)
cd ../frontend
npm install
ng serve
```

### Verify Installation

```
┌──────────────────────────────────────────────────────────┐
│  Frontend:   http://localhost:4200                       │
│  Backend:    http://localhost:8000                       │
│  Swagger UI: http://localhost:8000/docs                  │
│  ReDoc:      http://localhost:8000/redoc                 │
│  Metrics:    http://localhost:8000/metrics               │
│  Health:     http://localhost:8000/health                │
└──────────────────────────────────────────────────────────┘
```

---

## Docker Deployment

### Development Docker Compose

```yaml
# docker-compose.yml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: firewall-mgmt-backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/firewall_mgmt
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - firewall-net

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: firewall-mgmt-frontend
    ports:
      - "4200:80"
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - firewall-net

  postgres:
    image: postgres:15-alpine
    container_name: firewall-mgmt-postgres
    environment:
      POSTGRES_DB: firewall_mgmt
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/alembic:/app/alembic
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - firewall-net

volumes:
  postgres_data:

networks:
  firewall-net:
    driver: bridge
```

### Build and Run

```bash
# Build all services
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f backend

# Stop all services
docker compose down

# Reset database
docker compose down -v
docker compose up -d
cd backend && alembic upgrade head
```

---

## Azure Container Apps

### Step 1: Create Resource Group

```bash
az group create \
  --name firewall-mgmt-rg \
  --location eastus
```

### Step 2: Create Azure Container Registry

```bash
az acr create \
  --name firewallmgtrac \
  --resource-group firewall-mgmt-rg \
  --sku Basic \
  --admin-enabled true
```

### Step 3: Build and Push Images

```bash
# Login to ACR
az acr login --name firewallmgtrac

# Build backend image
docker build -t firewallmgtrac.azurecr.io/firewall-mgmt-backend:latest \
  -f backend/Dockerfile ./backend

# Push to ACR
docker push firewallmgtrac.azurecr.io/firewall-mgmt-backend:latest

# Build frontend image
docker build -t firewallmgtrac.azurecr.io/firewall-mgmt-frontend:latest \
  -f frontend/Dockerfile ./frontend

# Push to ACR
docker push firewallmgtrac.azurecr.io/firewall-mgmt-frontend:latest
```

### Step 4: Create Container Apps

```bash
# Create backend Container App
az containerapp create \
  --name firewall-mgmt-api \
  --resource-group firewall-mgmt-rg \
  --container-image firewallmgtrac.azurecr.io/firewall-mgmt-backend:latest \
  --target-port 8000 \
  --min-replicas 1 \
  --max-replicas 3 \
  --registry-server firewallmgtrac.azurecr.io \
  --registry-username $(az acr show --name firewallmgtrac --resource-group firewall-mgmt-rg --query "loginServerUser" -o tsv) \
  --registry-password $(az acr credential show --name firewallmgtrac --resource-group firewall-mgmt-rg --query "passwords[0].value" -o tsv) \
  --env-vars \
    AZURE_TENANT_ID=<your-tenant-id> \
    AZURE_CLIENT_ID=<your-client-id> \
    AZURE_CLIENT_SECRET=<your-client-secret> \
    DATABASE_URL=postgresql://<db-user>@<db-host>.postgres.database.azure.com:5432/firewall_mgmt \
    SECRET_KEY=<your-secret-key> \
    DEBUG=false \
  --tags environment=production team=platform \
  --ingress external \
  --frontend-service none
```

```bash
# Create frontend Container App
az containerapp create \
  --name firewall-mgmt-web \
  --resource-group firewall-mgmt-rg \
  --container-image firewallmgtrac.azurecr.io/firewall-mgmt-frontend:latest \
  --target-port 80 \
  --min-replicas 1 \
  --max-replicas 2 \
  --registry-server firewallmgtrac.azurecr.io \
  --registry-username $(az acr show --name firewallmgtrac --resource-group firewall-mgmt-rg --query "loginServerUser" -o tsv) \
  --registry-password $(az acr credential show --name firewallmgtrac --resource-group firewall-mgmt-rg --query "passwords[0].value" -o tsv) \
  --tags environment=production team=platform \
  --ingress external \
  --frontend-service none
```

### Step 5: Configure Environment Variables

```bash
# Get current env vars
az containerapp show \
  --name firewall-mgmt-api \
  --resource-group firewall-mgmt-rg \
  --query "properties.template.containers[0].env" -o json
```

---

## Azure Database for PostgreSQL

### Step 1: Create PostgreSQL Server

```bash
az postgres flexible-server create \
  --name firewall-mgmt-db \
  --resource-group firewall-mgmt-rg \
  --admin-user firewalladmin \
  --admin-password '<strong-password>' \
  --location eastus \
  --sku-name Standard_2_2 \
  --edition GeneralPurpose \
  --storage-size 64 \
  --auth-only
```

### Step 2: Create Database

```bash
az postgres flexible-server db create \
  --name firewall_mgmt \
  --server-name firewall-mgmt-db \
  --resource-group firewall-mgmt-rg \
  --db-name firewall_mgmt
```

### Step 3: Configure Connectivity

```bash
# Set firewall rule for Container Apps
az postgres flexible-server firewall-rule create \
  --name allow-container-apps \
  --server-name firewall-mgmt-db \
  --resource-group firewall-mgmt-rg \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### Step 4: Run Migrations

```bash
# Connect to database
az postgres flexible-server connect \
  --name firewall-mgmt-db \
  --admin-user firewalladmin

# Run alembic migrations
cd backend
DATABASE_URL=postgresql://firewalladmin@firewall-mgmt-db.postgres.database.azure.com:5432/firewall_mgmt
alembic upgrade head
```

---

## Azure Container Registry

### Registry Tiers

| Tier | Cost/month | Max Size | Use Case |
|------|-----------|----------|----------|
| Basic | ~$6.50 | 100 GB | Development |
| Standard | ~$33 | 500 GB | Production |
| Premium | ~$343 | 5 TB | Multi-region, geo-replication |

### Image Tagging Strategy

```
<service>:latest          → Latest development build
<service>:v1.0.0          → Specific release
<service>:sha-<commit>    → Git commit hash
<service>:staging         → Staging environment
<service>:production      → Production environment
```

### Cleanup Old Images

```bash
# List images
az acr repository list --name firewallmgtrac --output json

# Delete old image
az acr repository delete \
  --name firewallmgtrac \
  --image firewall-mgmt-backend:old-tag

# Cleanup untagged images
az acr repository delete --name firewallmgtrac --image "$(az acr repository show-tags --name firewallmgtrac --repository firewall-mgmt-backend --query '[0]' -o tsv)"
```

---

## Azure App Configuration

### Key Vault Integration

```bash
# Create Key Vault
az keyvault create \
  --name firewall-mgmt-kv \
  --resource-group firewall-mgmt-rg \
  --location eastus

# Store secrets
az keyvault secret set \
  --vault-name firewall-mgmt-kv \
  --name SECRET_KEY \
  --value "<your-secret-key>"

az keyvault secret set \
  --vault-name firewall-mgmt-kv \
  --name AZURE_CLIENT_SECRET \
  --value "<client-secret>"

az keyvault secret set \
  --vault-name firewall-mgmt-kv \
  --name DB_PASSWORD \
  --value "<db-password>"

# Grant Container Apps access
az keyvault set-policy \
  --name firewall-mgmt-kv \
  --resource-group firewall-mgmt-rg \
  --spn "<managed-identity-principal-id>" \
  --secret-permissions get list
```

### Link Key Vault to Container App

```bash
az containerapp update \
  --name firewall-mgmt-api \
  --resource-group firewall-mgmt-rg \
  --identity-type SystemAssigned \
  --secrets SECRET_KEY "$(az keyvault secret show --vault-name firewall-mgmt-kv --name SECRET_KEY --query value -o tsv)" \
  AZURE_CLIENT_SECRET "$(az keyvault secret show --vault-name firewall-mgmt-kv --name AZURE_CLIENT_SECRET --query value -o tsv)"
```

---

## Azure Frontend Deployment

### Step 1: Build Frontend

```bash
cd frontend
npm install
ng build --configuration production
```

### Step 2: Deploy to Azure Static Web Apps

```bash
# Install Azure Static Web Apps CLI
npm install -g @azure/static-webapps-cli

# Deploy
swa deploy --env production
```

### Step 3: Configure Custom Domain (optional)

```bash
az staticwebapp custom-domain add \
  --name firewall-mgmt-web \
  --resource-group firewall-mgmt-rg \
  --domain "app.firewall-mgmt.example.com" \
  --accept-ssl-termination true
```

---

## Environment Variables Reference

### Backend Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `sqlite:///./firewall_mgmt.db` | Database connection string |
| `SECRET_KEY` | Yes | | JWT signing key (32+ chars) |
| `DEBUG` | No | `true` | Debug mode flag |
| `LOG_FORMAT` | No | `json` | Log format (`json`/`text`) |
| `ALLOWED_HOSTS` | No | `*` | Comma-separated allowed hosts |
| `AZURE_TENANT_ID` | Yes | | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | Yes | | Azure AD application ID |
| `AZURE_CLIENT_SECRET` | Yes | | Service principal secret |
| `AZURE_SUBSCRIPTION_ID` | Yes | | Azure subscription ID |
| `AZURE_RESOURCE_GROUP` | Yes | | Azure resource group name |
| `MAX_BODY_SIZE` | No | `10485760` | Max request body size (bytes) |
| `RATE_LIMIT_LOGIN` | No | `5/5min` | Login rate limit |
| `RATE_LIMIT_API` | No | `100/1min` | General API rate limit |
| `RATE_LIMIT_REFRESH` | No | `20/5min` | Token refresh rate limit |

### Frontend Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_URL` | Yes | | Backend API base URL |
| `AZURE_TENANT_ID` | Yes | | Azure AD tenant ID for login |
| `APP_ID` | Yes | | Azure AD application/client ID |
| `REDIRECT_URI` | Yes | | OAuth redirect URI |

---

## Health Checks & Monitoring

### Health Check Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/health/livez` | GET | Kubernetes liveness | `200 OK` |
| `/health/readyz` | GET | Kubernetes readiness | `200 OK` (DB connected) |
| `/health` | GET | Application health | `{"status": "healthy"}` |
| `/metrics` | GET | Prometheus metrics | Prometheus text format |

### Health Check Implementation

```python
# /health/livez - Always returns 200 (process is alive)
@app.get("/health/livez")
async def liveness_probe():
    return {"status": "alive"}

# /health/readyz - Returns 503 if DB is not connected
@app.get("/health/readyz")
async def readiness_probe():
    try:
        from app.database import get_db_session
        session = get_db_session()
        session.execute(text("SELECT 1"))
        session.close()
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
```

### Prometheus Metrics

```bash
# Request to metrics endpoint
curl http://localhost:8000/metrics
```

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/rules",status="200"} 1523

# HELP http_request_duration_ms Request duration in milliseconds
# TYPE http_request_duration_ms histogram
http_request_duration_ms_bucket{le="100"} 1500
http_request_duration_ms_bucket{le="500"} 1520
http_request_duration_ms_bucket{le="1000"} 1523
http_request_duration_ms_bucket{le="+Inf"} 1523
```

### Application Insights Integration

```bash
# Link Application Insights to Container App
az containerapp update \
  --name firewall-mgmt-api \
  --resource-group firewall-mgmt-rg \
  --enable-application-insights <app-insights-ingestion-key>
```

---

## Rollback Procedures

### Rollback Container Image

```bash
# Get current image tag
CURRENT_IMAGE=$(az containerapp show \
  --name firewall-mgmt-api \
  --resource-group firewall-mgmt-rg \
  --query "properties.template.containers[0].image" -o tsv)

# Rollback to previous image
PREVIOUS_IMAGE=$(az acr repository show-tags \
  --name firewallmgtrac \
  --repository firewall-mgmt-backend \
  --query "[1]" -o tsv)

az containerapp update \
  --name firewall-mgmt-api \
  --resource-group firewall-mgmt-rg \
  --image "$PREVIOUS_IMAGE"
```

### Rollback Database

```bash
# Rollback last migration
alembic downgrade -1

# Rollback N migrations
alembic downgrade -N
```

---

## CI/CD Pipeline

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to ACR
        run: az acr login --name firewallmgtrac

      - name: Build and push backend
        run: |
          docker build -t firewallmgtrac.azurecr.io/firewall-mgmt-backend:${{ github.sha }} \
            -f backend/Dockerfile ./backend
          docker push firewallmgtrac.azurecr.io/firewall-mgmt-backend:${{ github.sha }}

      - name: Build and push frontend
        run: |
          docker build -t firewallmgtrac.azurecr.io/firewall-mgmt-frontend:${{ github.sha }} \
            -f frontend/Dockerfile ./frontend
          docker push firewallmgtrac.azurecr.io/firewall-mgmt-frontend:${{ github.sha }}

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Login to Azure
        run: az login --service-principal -u ${{ secrets.AZURE_CLIENT_ID }} -p ${{ secrets.AZURE_CLIENT_SECRET }} --tenant ${{ secrets.AZURE_TENANT_ID }}

      - name: Update Container App
        run: |
          az containerapp update \
            --name firewall-mgmt-api \
            --resource-group firewall-mgmt-rg \
            --image firewallmgtrac.azurecr.io/firewall-mgmt-backend:${{ github.sha }}
```

---

## Security Checklist

### Pre-Deployment

- [ ] `SECRET_KEY` is a strong random 32+ character string
- [ ] `DEBUG=false` in production
- [ ] `ALLOWED_HOSTS` restricts to production domains
- [ ] Database uses PostgreSQL (not SQLite)
- [ ] Database password is strong and unique
- [ ] Azure client secret is stored in Key Vault
- [ ] Container registry uses Standard or Premium tier
- [ ] Managed Identity used for ACR authentication
- [ ] TLS/SSL enabled for all endpoints
- [ ] Firewall rules restrict database access
- [ ] Rate limiting is enabled
- [ ] CORS origins are explicitly configured

### Post-Deployment Verification

- [ ] Health checks return `200`
- [ ] API documentation (`/docs`) is disabled in production
- [ ] Error responses don't leak stack traces
- [ ] Prometheus metrics are accessible
- [ ] Application Insights is collecting traces
- [ ] Database connections are encrypted
- [ ] Container Apps use managed identity
- [ ] Network policies restrict outbound traffic
- [ ] Logs are streamed to Log Analytics
- [ ] Alerts are configured for error rates