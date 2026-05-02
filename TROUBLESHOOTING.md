# Troubleshooting Guide

Common issues and their solutions for the Azure Firewall Management Application.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Installation Issues](#installation-issues)
- [Database Issues](#database-issues)
- [Backend Issues](#backend-issues)
- [Frontend Issues](#frontend-issues)
- [Authentication Issues](#authentication-issues)
- [Azure Integration Issues](#azure-integration-issues)
- [API Issues](#api-issues)
- [Performance Issues](#performance-issues)
- [Deployment Issues](#deployment-issues)
- [Debugging Tools](#debugging-tools)

---

## Quick Reference

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| App won't start | Missing dependencies | `pip install -r requirements.txt` |
| Database errors | Migration mismatch | `alembic upgrade head` |
| 401 Unauthorized | Expired/invalid JWT | Re-authenticate |
| CORS errors | Host mismatch | Check `ALLOWED_HOSTS` |
| Slow responses | Database index missing | Check query plans |
| Memory high | Memory leak | Review service code |

---

## Installation Issues

### `ModuleNotFoundError: No module named 'fastapi'`

**Cause:** Dependencies are not installed.

```bash
# Solution: Install dependencies
cd backend
pip install -r requirements.txt
```

### `pip install: command not found`

**Cause:** Python is not installed or not in PATH.

```bash
# Verify Python installation
python --version
# or
python3 --version

# Install Python 3.11+ if missing
# Ubuntu/Debian
sudo apt update && sudo apt install python3.11 python3.11-venv python3.11-distutils

# macOS
brew install python@3.12

# Windows
winget install Python.Python.3.12
```

### `npm: command not found`

**Cause:** Node.js is not installed.

```bash
# Verify Node.js installation
node --version
npm --version

# Install Node.js 18+
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash
nvm install 20
nvm use 20

# Using apt (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### `ng: command not found`

**Cause:** Angular CLI is not installed globally.

```bash
# Install Angular CLI
npm install -g @angular/cli@17
ng version
```

---

## Database Issues

### `sqlalchemy.exc.OperationalError: no such table: firewall_rules`

**Cause:** Database tables have not been created.

```bash
# Solution: Run migrations
cd backend
alembic upgrade head

# If tables exist but schema is wrong, reset:
# WARNING: This deletes all data!
rm firewall_mgmt.db
alembic upgrade head
```

### `sqlalchemy.exc.IntegrityError: NOT NULL constraint failed`

**Cause:** Data integrity violation — likely a migration was applied out of order or data was inserted manually.

```bash
# Check current migration state
alembic current

# Verify migration history
alembic history

# Re-run migrations to fix
alembic upgrade head

# If still failing, inspect the failing migration
cat alembic/versions/0001_initial_schema.py
```

### `sqlite3.OperationalError: database is locked`

**Cause:** SQLite does not support concurrent writes.

```bash
# Solution 1: Use PostgreSQL for production
# Set in .env:
DATABASE_URL=postgresql://user:password@host:5432/firewall_mgmt

# Solution 2: For development, ensure single-process access
# Close any other processes using the database
lsof +D . | grep firewall_mgmt.db

# Solution 3: Increase SQLite timeout
# In backend/.env
SQLITE_POOL_TIMEOUT=30
```

### `psycopg2.OperationalError: FATAL: password authentication failed`

**Cause:** Wrong database credentials.

```bash
# Verify credentials in .env
cat backend/.env | grep DATABASE_URL

# Test connection manually
psql "postgresql://user:password@host:5432/firewall_mgmt"

# If password is wrong, reset it
# For Azure PostgreSQL:
az postgres flexible-server update \
  --name firewall-mgmt-db \
  --resource-group firewall-mgmt-rg \
  --admin-password '<new-password>'
```

### `FATAL: database "firewall_mgmt" does not exist`

**Cause:** The database has not been created.

```bash
# Create the database
createdb firewall_mgmt

# Or via psql
psql -U postgres
CREATE DATABASE firewall_mgmt;
\q

# Then run migrations
alembic upgrade head
```

### `relation "alembic_version" already exists`

**Cause:** Alembic was previously initialized but with a different schema version.

```bash
# Solution: Align Alembic with existing state
# 1. Check current state in DB
psql -d firewall_mgmt -c "SELECT * FROM alembic_version;"

# 2. Set the version manually to match
psql -d firewall_mgmt -c "UPDATE alembic_version SET version_num='0001_initial_schema';"

# 3. Verify
alembic current
```

---

## Backend Issues

### `uvicorn: command not found`

**Cause:** Backend dependencies are not installed.

```bash
cd backend
pip install -r requirements.txt

# Or use venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### `uvicorn: error while loading shared library`

**Cause:** Python shared library issue on Linux.

```bash
# Solution: Use Python to run uvicorn directly
python -m uvicorn app.main:app --reload
```

### `ImportError: cannot import name '...' from 'app.services'`

**Cause:** Circular import or missing file.

```bash
# Check for circular imports
grep -r "from app" app/services/

# Verify all files exist
ls -la app/services/

# Restart the server
uvicorn app.main:app --reload
```

### `fastapi.exceptions.RequestValidationError`

**Cause:** Request body failed Pydantic validation.

```bash
# Check the request body against the schema
# See Swagger UI for expected format:
curl http://localhost:8000/openapi.json | python -m json.tool

# Example correct request:
curl -X POST http://localhost:8000/api/v1/rules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Allow HTTP",
    "source_cidr": "0.0.0.0/0",
    "dest_cidr": "10.0.0.0/24",
    "protocol": "tcp",
    "port": 80,
    "action": "allow",
    "priority": 100,
    "direction": "inbound"
  }'
```

### `uvicorn.error.LifespanError: Error on startup`

**Cause:** Database connection failed or environment variables missing.

```bash
# Check .env file exists
ls -la backend/.env

# Verify required variables
cat backend/.env | grep -E "(DATABASE_URL|SECRET_KEY|AZURE_TENANT_ID)"

# Test database connection
python -c "from app.database import init_db; init_db(); print('OK')"

# Check for missing env vars
python -c "from app.config import settings; print(settings.model_dump_json(indent=2))"
```

### High memory usage (Backend)

```bash
# Check running processes
ps aux | grep uvicorn

# Check memory usage
docker stats firewall-mgmt-backend

# If running in Docker, adjust limits
# In docker-compose.yml or deployment config:
memory: 512M
cpus: 2

# Enable garbage collection tuning in .env
PYTHON_GCOPT_THRESHOLD=3,10,1000
```

---

## Frontend Issues

### `ERROR Error: Unexpected token < in JSON at position 0`

**Cause:** Backend returned an HTML error page instead of JSON (usually 500 error).

```bash
# Check backend logs
docker logs firewall-mgmt-backend --tail 100

# Verify backend is healthy
curl http://localhost:8000/health

# Check CORS settings in .env
cat backend/.env | grep ALLOWED_HOSTS
```

### `ERROR [ng] Invalid configuration: Cannot find module '@angular/compiler-cli'`

**Cause:** Angular dependencies are not installed properly.

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
ng build
```

### `ERROR [ng] Build error - Cannot invert baseHref in angular.json`

**Cause:** Configuration mismatch.

```bash
# Verify angular.json baseHref
cat frontend/angular.json | grep baseHref

# Fix: Set baseHref correctly
# In angular.json:
# "baseHref": "/" or ""
```

### `ERROR TypeError: Cannot read properties of undefined (reading 'navigate')`

**Cause:** Router is not initialized in the component.

```typescript
// Check that RouterModule is imported in the module
import { RouterModule } from '@angular/router';

@NgModule({
  imports: [RouterModule],
  // ...
})
```

### `WARNING: Dev server hot replacement is disabled`

**Cause:** TypeScript compiler errors prevent hot reload.

```bash
# Fix TypeScript errors
cd frontend
ng serve --verbose

# Or build to see all errors
ng build 2>&1 | grep ERROR
```

---

## Authentication Issues

### `401 Unauthorized: Not authenticated`

**Cause:** Missing or invalid JWT token.

```bash
# Verify token is included in request
curl -H "Authorization: Bearer <your-token>" http://localhost:8000/api/v1/rules

# Check token is not expired
# Decode JWT payload:
echo <your-token> | cut -d'.' -f2 | base64 -d 2>/dev/null | python -m json.tool

# Re-authenticate
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### `403 Forbidden: Insufficient permissions`

**Cause:** User lacks required role.

```bash
# Check user roles in database
psql -d firewall_mgmt -c "SELECT id, username, role FROM users WHERE username = 'admin';"

# Update user role
psql -d firewall_mgmt -c "UPDATE users SET role = 'FirewallAdmin' WHERE username = 'admin';"

# Re-login to get new token with updated roles
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### `401: Token has expired`

**Cause:** Access token expired, need to refresh.

```bash
# Use refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh-token>"}'

# If refresh fails, re-authenticate
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### `CORS error: No 'Access-Control-Allow-Origin' header`

**Cause:** Frontend domain not in ALLOWED_HOSTS.

```bash
# Update .env
ALLOWED_HOSTS=http://localhost:4200,http://localhost:4100

# Or allow all (development only)
ALLOWED_HOSTS=*

# Restart backend
docker compose restart backend
# or
pkill -f uvicorn && cd backend && uvicorn app.main:app --reload
```

---

## Azure Integration Issues

### `azure.core.exceptions.ClientAuthenticationError: No credentials`

**Cause:** Azure credentials are missing or invalid.

```bash
# Check .env
cat backend/.env | grep -E "(AZURE_TENANT|AZURE_CLIENT)"

# Verify credentials
az account show --tenant <tenant-id>

# If credentials are rotated:
# 1. Get new credentials from Azure Portal
# 2. Update .env
# 3. Restart backend
docker compose restart backend
```

### `azure.core.exceptions.ResourceNotFoundError: The resource was not found`

**Cause:** Resource group or firewall does not exist.

```bash
# Verify resource group exists
az group show --name <resource-group> --query name -o tsv

# Verify firewall exists
az network firewall show \
  --resource-group <resource-group> \
  --name <firewall-name>

# Check AZURE_RESOURCE_GROUP in .env
cat backend/.env | grep AZURE_RESOURCE_GROUP
```

### `azure.core.exceptions.HttpResponseError: Operation 'NetworkRuleSetRead' not allowed`

**Cause:** Service principal lacks required permissions.

```bash
# Assign Contributor role to service principal
az role assignment create \
  --role "Network Contributor" \
  --assignee <client-id> \
  --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>

# Or assign at subscription level
az role assignment create \
  --role "Azure Network Contributor" \
  --assignee <client-id> \
  --scope /subscriptions/<subscription-id>
```

---

## API Issues

### `429 Too Many Requests`

**Cause:** Rate limit exceeded.

```bash
# Check rate limit headers in response
curl -sI http://localhost:8000/api/v1/rules
# Look for:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 0
# X-RateLimit-Reset: 1700000000

# Reduce request frequency or increase limits in .env
RATE_LIMIT_API=200/1min

# For login endpoint
RATE_LIMIT_LOGIN=10/5min
```

### `409 Conflict: A rule with priority XXX already exists`

**Cause:** Priority conflict — each priority can only have one rule.

```bash
# Check existing rules for the conflicting priority
curl http://localhost:8000/api/v1/rules | python -m json.tool | grep priority

# Use a different priority value
curl -X POST http://localhost:8000/api/v1/rules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Allow HTTPS",
    "priority": 200,
    ...
  }'
```

### `500 Internal Server Error`

**Cause:** Unhandled exception on the backend.

```bash
# Check backend logs
docker logs firewall-mgmt-backend --tail 200

# Or check application logs (JSON format)
grep "ERROR" backend/*.log

# Enable debug mode for full traceback
DEBUG=true
uvicorn app.main:app --reload

# Check for specific error patterns
docker logs firewall-mgmt-backend 2>&1 | grep -E "(Exception|Error|Traceback)" | tail -20
```

### `503 Service Unavailable`

**Cause:** Database connection pool exhausted or service not ready.

```bash
# Check database health
psql -U postgres -d firewall_mgmt -c "SELECT 1;"

# Check connection pool size
cat backend/.env | grep POOL

# Increase pool size if needed
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Check backend health
curl -v http://localhost:8000/health
```

---

## Performance Issues

### Slow API responses

```bash
# Check response times
curl -o /dev/null -s -w "Time: %{time_total}s\n" http://localhost:8000/api/v1/rules

# Check database query performance
psql -d firewall_mgmt -c "
EXPLAIN ANALYZE SELECT * FROM firewall_rules;
"

# Add indexes for frequently queried columns
psql -d firewall_mgmt -c "
CREATE INDEX IF NOT EXISTS idx_firewall_rules_status ON firewall_rules(status);
CREATE INDEX IF NOT EXISTS idx_firewall_rules_priority ON firewall_rules(priority);
CREATE INDEX IF NOT EXISTS idx_firewall_rules_workload ON firewall_rules(workload_id);
"

# Check for N+1 queries in service code
# Review service layer for batch operations
grep -r "session.query\|db.execute" app/services/
```

### High CPU usage

```bash
# Check CPU usage
docker stats firewall-mgmt-backend

# Identify slow queries
psql -d firewall_mgmt -c "
SELECT query, calls, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"

# Reduce worker count in production
# In deployment config:
WORKER_COUNT=4
```

---

## Deployment Issues

### `az: command not found`

**Cause:** Azure CLI is not installed.

```bash
# Install Azure CLI
# macOS
brew update && brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
winget install Microsoft.AzureCLI

# Verify
az --version
```

### `docker: permission denied`

**Cause:** User not in Docker group.

```bash
# Add user to Docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Verify
docker ps
```

### `Error: container image already exists`

**Cause:** Cached image conflicts.

```bash
# Remove existing image
docker rmi firewallmgtrac.azurecr.io/firewall-mgmt-backend:latest

# Rebuild
docker compose build backend
docker compose up -d backend
```

### `Error: resource group not found`

**Cause:** Resource group was deleted or name is incorrect.

```bash
# List all resource groups
az group list --query "[].name" -o table

# Create if missing
az group create --name firewall-mgmt-rg --location eastus
```

### `Error: Container app already exists`

**Cause:** Old container app was not deleted.

```bash
# Delete existing app
az containerapp delete \
  --name firewall-mgmt-api \
  --resource-group firewall-mgmt-rg \
  --yes

# Or list existing apps
az containerapp list --resource-group firewall-mgmt-rg -o table
```

---

## Debugging Tools

### Backend Debugging

```bash
# Enable debug mode for verbose logging
DEBUG=true

# Get detailed request/response logs
curl -v http://localhost:8000/api/v1/rules \
  -H "Authorization: Bearer <token>"

# Enable SQLAlchemy query logging
python -c "
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
"

# Profile API endpoint
python -c "
import cProfile
import pstats
cProfile.run('from app.main import app', 'api_profile')
pstats.Stats('api_profile').print_stats()
"
```

### Frontend Debugging

```bash
# Enable Angular DevTools
# Install in Chrome/Firefox: https://addons.mozilla.org/firefox/addon/angular-devtools/

# Enable debug logging
# In main.ts:
import { enableProdMode } from '@angular/core';
enableProdMode(); // Set to false for debug mode

# View HTTP requests in browser DevTools
# Network tab → Filter by API domain

# Check component state
ng build --configuration development --source-map
```

### Network Debugging

```bash
# Check if backend is accessible
curl -v http://localhost:8000/health

# Check CORS headers
curl -sI http://localhost:8000/api/v1/rules \
  -H "Origin: http://localhost:4200"

# Test Azure connectivity
curl -v https://management.azure.com/ \
  -H "Authorization: Bearer $(az account get-access-token --query accessToken -o tsv)"

# Verify Docker network
docker network ls
docker network inspect firewall_net
```

### Log Analysis

```bash
# View all logs
docker compose logs

# Follow backend logs
docker compose logs -f backend

# Filter by error level
docker compose logs 2>&1 | grep -i "error"

# Count errors
docker compose logs 2>&1 | grep -c -i "error"

# Extract request IDs for correlation
docker compose logs 2>&1 | grep -oP '"request_id": "\K[^"]+' | sort | uniq