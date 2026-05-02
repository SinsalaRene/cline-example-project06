# Production Deployment Guide

## Azure Firewall Management API

Comprehensive guide for deploying, monitoring, and operating the Azure Firewall Management API in production.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Database Setup](#database-setup)
5. [Configuration](#configuration)
6. [Building the Application](#building-the-application)
7. [Deployment Options](#deployment-options)
8. [Health Checks & Readiness](#health-checks--readness)
9. [Monitoring & Observability](#monitoring--observability)
10. [Logging](#logging)
11. [Error Tracking](#error-tracking)
12. [Performance Optimization](#performance-optimization)
13. [Security](#security)
14. [Scaling](#scaling)
15. [Backup & Recovery](#backup--recovery)
16. [Troubleshooting](#troubleshooting)
17. [Rollback Procedure](#rollback-procedure)

---

## Overview

This application provides API endpoints for managing Azure firewall rules with approval workflows, role-based access control, and audit trails. It is built with FastAPI and supports structured logging, Prometheus metrics, and Sentry error tracking.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
└──────────────────────┬──────────────────────────────────┘
                       │
            ┌──────────▼──────────┐
            │  Application Server │
            │  (uvicorn workers)  │
            └──────────┬──────────┘
                       │
            ┌──────────▼──────────┐
            │     PostgreSQL DB    │
            │  (Azure Database)   │
            └─────────────────────┘
```

---

## Prerequisites

- **Python 3.11+** (3.12 recommended)
- **PostgreSQL 14+** (Azure Database for PostgreSQL)
- **Azure Container Registry** (optional, for container deployment)
- **Azure App Service** or **Azure Kubernetes Service** (deployment target)
- **Sentry account** (optional, for error tracking)
- **Prometheus/Grafana** (optional, for monitoring)

---

## Environment Setup

### 1. Clone and Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Configure Environment Variables

```bash
# Database (PostgreSQL for production)
DATABASE_URL=postgresql://user:password@hostname:5432/dbname

# Azure Configuration
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_REGION=your-region

# Security
SECRET_KEY=your-production-secret-key-min-16-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
AUTH_RATE_LIMIT_PER_MINUTE=20
RATE_LIMIT_ENABLED=true

# Logging
LOG_FORMAT=json
ENVIRONMENT=production

# Error Tracking (Sentry)
SENTRY_DSN=https://your-sentry-dsn

# Metrics
ENABLE_METRICS=true

# CORS
ALLOWED_HOSTS=your-domain.com,api.your-domain.com
```

---

## Database Setup

### PostgreSQL Migration

```bash
# Run Alembic migrations
alembic upgrade head
```

### Database Backup Configuration

```bash
# Azure PostgreSQL backup
az postgres flexible-server backup \
  --resource-group your-resource-group \
  --server-name your-server-name
```

---

## Configuration

### Production Settings

Edit `backend/app/config.py` for production-specific settings:

```python
# Production defaults
debug = False
log_format = "json"
enable_metrics = True
sentry_sample_rate = 0.1
```

### Environment-Specific Overrides

| Variable | Development | Production |
|----------|-------------|------------|
| DEBUG | true | false |
| LOG_FORMAT | console | json |
| DOC_URL | /docs | (hidden) |
| ENABLE_METRICS | true | true |
| SENTRY_SAMPLE_RATE | 1.0 | 0.1 |

---

## Building the Application

### Container Build

```bash
# Build Docker image
docker build -t registry.azurecr.io/azure-firewall-api:latest .

# Tag and push
docker tag registry.azurecr.io/azure-firewall-api:latest \
  registry.azurecr.io/azure-firewall-api:$(git rev-parse --short HEAD)
docker push registry.azurecr.io/azure-firewall-api:latest
```

### Docker Configuration

```yaml
# docker-compose.yml for local production-like testing
version: '3.8'
services:
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: firewall_db
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## Deployment Options

### Option 1: Azure App Service

```bash
# Create App Service Plan
az appservice plan create \
  --name firewall-api-plan \
  --resource-group your-resource-group \
  --sku B3 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group your-resource-group \
  --plan firewall-api-plan \
  --name firewall-api \
  --deployment-container-image-name registry.azurecr.io/azure-firewall-api:latest

# Configure App Settings
az webapp config appsettings set \
  --resource-group your-resource-group \
  --name firewall-api \
  --settings DATABASE_URL="$DATABASE_URL" \
            AZURE_TENANT_ID="$AZURE_TENANT_ID" \
            SENTRY_DSN="$SENTRY_DSN"
```

### Option 2: Azure Kubernetes Service (AKS)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: azure-firewall-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: api
        image: registry.azurecr.io/azure-firewall-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: api-config
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          limits:
            cpu: "500m"
            memory: "512Mi"
          requests:
            cpu: "250m"
            memory: "256Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: azure-firewall-api
spec:
  selector:
    app: azure-firewall-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  DATABASE_URL: "postgresql://user:pass@host/db"
  AZURE_TENANT_ID: "tenant-id"
  SENTRY_DSN: "sentry-dsn"
```

### Option 3: Bare Metal / VM

```bash
# Systemd service file: /etc/systemd/system/azure-firewall-api.service
[Unit]
Description=Azure Firewall Management API
After=network.target postgresql.service

[Service]
Type=simple
User=api
Group=api
WorkingDirectory=/opt/azure-firewall-api
Environment="PATH=/opt/azure-firewall-api/.venv/bin:/usr/bin"
ExecStart=/opt/azure-firewall-api/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Health Checks & Readiness

### Kubernetes Health Checks

Kubernetes uses the following endpoints for liveness, readiness, and startup probes:

| Probe | Endpoint | Description |
|-------|----------|-------------|
| Liveness | `GET /healthz` | Simple alive check |
| Readiness | `GET /readyz` | Database connectivity check |
| Startup | `GET /startup` | Full initialization check |
| Health | `GET /health` | Comprehensive health status |

### Configuration Manager Integration

```yaml
# Liveness Probe (checks if app is alive)
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3

# Readiness Probe (checks if app is ready to receive traffic)
readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3

# Startup Probe (gives app time to initialize)
startupProbe:
  httpGet:
    path: /startup
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 30
```

---

## Monitoring & Observability

### Prometheus Metrics

The application exposes Prometheus-compatible metrics at `/metrics`:

```bash
# Query metrics
curl http://localhost:8000/metrics
```

#### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by method, path, status |
| `http_request_duration_seconds` | Histogram | Request duration distribution |
| `db_query_total` | Counter | Total database queries by type |
| `db_query_duration_seconds` | Histogram | Database query duration |
| `azure_sync_total` | Counter | Azure sync operations count |
| `azure_sync_duration_seconds` | Histogram | Azure sync duration |
| `errors_total` | Counter | Total errors by type and source |
| `process_start_time_seconds` | Gauge | Application start time (Unix timestamp) |
| `process_cpu_seconds_total` | Counter | CPU time consumed |
| `system_cpu_usage_percent` | Gauge | Current CPU usage percentage |
| `system_memory_total_bytes` | Gauge | Total system memory in bytes |
| `system_memory_available_bytes` | Gauge | Available system memory in bytes |
| `disk_total_bytes` | Gauge | Total disk space in bytes |
| `disk_free_bytes` | Gauge | Free disk space in bytes |

#### Grafana Dashboard

Import the following JSON for Grafana:

```json
{
  "dashboard": {
    "title": "Azure Firewall API",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}} {{status_code}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(errors_total[5m])",
            "legendFormat": "{{error_type}} {{source}}"
          }
        ]
      }
    ]
  }
}
```

---

## Logging

### Log Format

Production logs use JSON formatting:

```json
{
  "timestamp": "2025-01-15T10:30:00.000000+00:00",
  "level": "INFO",
  "logger": "app.api.rules",
  "message": "Created firewall rule",
  "module": "rules",
  "function": "create_rule",
  "line": 42,
  "pid": 12345,
  "tid": 140000000000000,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "span_id": "550e8400e29b41d4",
  "traceparent": "00-550e8400e29b41d4-550e8400e29b41d4-01",
  "extra": {
    "rule_id": "abc123"
  }
}
```

### Log Levels

| Level | Usage |
|-------|-------|
| DEBUG | Detailed diagnostic information |
| INFO | General information and normal operation |
| WARNING | Unexpected but handled situations |
| ERROR | Error events that may be recoverable |
| CRITICAL | Critical errors requiring immediate attention |

### Log Aggregation

Configure log shipping to your preferred service:

#### ELK Stack (Elasticsearch, Logstash, Kibana)

```
# logstash.conf input
input {
  beats {
    port => 5044
  }
  file {
    path => "/var/log/app/application.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
    codec => json
  }
}
```

#### AWS CloudWatch

```bash
# CloudWatch agent config (/aws/cloudwatch/logs/config.json)
{
  "logs": {
    "metrics_collected": {
      "app_metrics": {
        "metrics_namespace": "AzureFirewallAPI"
      }
    }
  }
}
```

---

## Error Tracking

### Sentry Configuration

```bash
# Install Sentry SDK
pip install sentry-sdk

# Configure in .env
SENTRY_DSN=https://your-sentry-dsn@o123456.ingest.sentry.io/789012
```

### Error Categories

| Category | Description |
|----------|-------------|
| `validation` | Input validation errors |
| `authentication` | Auth-related errors (401) |
| `authorization` | Permission errors (403) |
| `database` | Database connection/query errors |
| `external_service` | Azure API errors |
| `timeout` | Request timeout errors |
| `resource_not_found` | 404 errors |
| `rate_limit` | Rate limit exceeded |
| `internal` | Internal server errors (500) |
| `business_logic` | Business rule violations |

### Custom Error Handler

```python
from app.error_tracking import capture_exception, ErrorCategory

try:
    await process_rule(rule_data)
except Exception as e:
    capture_exception(
        error=e,
        category=ErrorCategory.validation.value,
        severity="error",
        context={"rule_id": rule_data.get("id")},
    )
    raise
```

---

## Performance Optimization

### Database Connections

```python
# PostgreSQL connection pool
engine = create_engine(
    database_url,
    pool_size=20,          # Max connections
    pool_recycle=1800,     # Recycle after 30 min
    pool_pre_ping=True,    # Health check on checkout
    max_overflow=10,       # Extra connections for burst
)
```

### Redis Caching (Optional)

```bash
# Add Redis for caching
pip install redis
```

```python
# Cache configuration
CACHE_TTL = 300  # 5 minutes
CACHE_MAX_SIZE = 1000  # Max cached items
```

### Connection Pooling with PgBouncer

```yaml
# pgbouncer config
[databases]
firewall_db = host=postgres-server dbname=firewall_db

[pgbouncer]
pool_mode = transaction
max_client_conn = 100
default_pool_size = 20
```

### Gunicorn Configuration

```python
# gunicorn.conf.py
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
```

---

## Security

### HTTPS/TLS

```bash
# Azure App Service automatic TLS
# No cert needed - Azure handles it
```

### JWT Configuration

```python
# JWT token configuration
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

### Rate Limiting

```bash
# Rate limit configuration
AUTH_RATE_LIMIT_PER_MINUTE=20
RATE_LIMIT_WINDOW=60
RATE_LIMIT_ENABLED=true
```

### CORS Configuration

```python
# CORS allowed origins
ALLOWED_ORIGINS = ["https://your-domain.com"]
```

---

## Scaling

### Horizontal Pod Scaling (Kubernetes)

```bash
# Configure HPA
kubectl autoscale deployment azure-firewall-api \
  --cpu-percent=70 \
  --min=3 \
  --max=10
```

### Azure App Service Scaling

```bash
# Auto-scale based on CPU usage
az monitor autoscale create \
  --resource-group your-resource-group \
  --name firewall-api-autoscale \
  --resource /subscriptions/your-subscription/resourceGroups/your-resource-group/providers/Microsoft.Web/sites/firewall-api \
  --min-count 2 \
  --max-count 10 \
  --count $(az appservice plan show \
    --name firewall-api-plan \
    --resource-group your-resource-group \
    --querysku.name \
    --output tsv)
```

---

## Backup & Recovery

### Database Backups

```bash
# Azure PostgreSQL automated backups
az postgres flexible-server backup list \
  --resource-group your-resource-group \
  --server-name your-server-name

# Restore from backup
az postgres flexible-server restore \
  --resource-group your-resource-group \
  --source-server your-server-name \
  --new-server restored-server-name
```

### Disaster Recovery

```bash
# Export database
pg_dump -h your-server.postgres.database.azure.com \
  -U admin \
  -d firewall_db \
  -F c \
  -f /backup/firewall_db.backup

# Import database
pg_restore -h your-server.postgres.database.azure.com \
  -U admin \
  -d firewall_db \
  /backup/firewall_db.backup
```

---

## Troubleshooting

### Common Issues

#### Database Connection Failures

```bash
# Check database connectivity
psql -h your-server.postgres.database.azure.com -U admin -d firewall_db

# Check connection pool status
curl http://localhost:8000/readyz
```

#### High Memory Usage

```bash
# Check process memory
ps aux | grep uvicorn

# Check system memory
free -h
```

#### High CPU Usage

```bash
# Check CPU usage
top -p $(pgrep -f uvicorn)

# Check active connections
ss -tuln | grep 8000
```

### Logs Location

```bash
# System logs
journalctl -u azure-firewall-api -f

# Application logs (if using file logging)
tail -f /var/log/app/application.log

# Container logs (if using Docker)
docker logs -f <container-id>
```

---

## Rollback Procedure

### Step 1: Identify Current Version

```bash
# Get current deployed version
kubectl get deployments azure-firewall-api -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### Step 2: Rollback to Previous Version

```bash
# Kubernetes rollback
kubectl rollout undo deployment/azure-firewall-api

# Azure App Service rollback
az webapp deployment publish \
  --resource-group your-resource-group \
  --name firewall-api \
  --src-path /path/to/previous/version
```

### Step 3: Verify Rollback

```bash
# Check rollout status
kubectl rollout status deployment/azure-firewall-api

# Verify health
curl http://localhost:8000/healthz
```

---

## Quick Reference

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/healthz` | GET | Liveness probe |
| `/readyz` | GET | Readiness probe |
| `/startup` | GET | Startup check |
| `/health` | GET | Full health check |
| `/health/json` | GET | JSON health check |
| `/health/detailed` | GET | Detailed health check |
| `/health/gc` | POST | Garbage collection trigger |
| `/metrics` | GET | Prometheus metrics |
| `/metrics/json` | GET | Human-readable metrics |
| `/metrics/gc` | POST | Metrics garbage collection |

### Environment Variables Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | Database connection string |
| `SECRET_KEY` | Yes | - | JWT secret key (min 16 chars) |
| `AZURE_TENANT_ID` | Yes | - | Azure tenant ID |
| `AZURE_CLIENT_ID` | Yes | - | Azure client ID |
| `AZURE_CLIENT_SECRET` | Yes | - | Azure client secret |
| `SENTRY_DSN` | No | - | Sentry DSN for error tracking |
| `LOG_FORMAT` | No | `json` | Log format (json/console) |
| `ENABLE_METRICS` | No | `true` | Enable Prometheus metrics |

### Service Account Permissions

The application service account needs these Azure RBAC permissions:

| Role | Scope |
|------|-------|
| Contributor | Resource Group |
| Network Contributor | Resource Group |
| Reader | Subscription |