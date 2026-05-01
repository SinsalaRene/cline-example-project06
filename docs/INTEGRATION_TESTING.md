# Integration Testing Documentation

## Overview

This document describes the integration testing strategy, test coverage, and execution instructions for the Azure Firewall Management API.

## Test Structure

### Test File Location

Integration tests are located in `backend/tests/test_integration.py`.

### Test Categories

The integration test suite is organized into the following categories:

1. **Health and Root Endpoints** - Basic API availability checks
2. **Authentication Flow** - Login, token refresh, logout, token revocation
3. **Firewall Rules API** - CRUD operations, bulk operations, search, export, clone
4. **Approval API** - Create, approve, reject, comments, history, bulk operations, escalation
5. **Audit API** - Log retrieval, filtering, searching, exporting, statistics
6. **Error Scenarios** - Invalid tokens, missing fields, non-existent resources
7. **End-to-End Workflows** - Complete lifecycle tests
8. **Rate Limiting** - Auth endpoint rate limiting
9. **Middleware** - Request ID, content-type headers
10. **Audit Log Workflow** - Audit log creation during CRUD operations

## Running Tests

### Prerequisites

Ensure you have the required dependencies installed:

```bash
pip install pytest pytest-cov fastapi uvicorn httpx sqlalchemy pyjwt
```

### Execute Integration Tests

```bash
cd backend
python -m pytest tests/test_integration.py -v
```

### With Coverage Report

```bash
python -m pytest tests/test_integration.py -v --cov=app --cov-report=html
```

## Test Coverage Matrix

| Endpoint Category | Endpoint | Method | Test Coverage |
|-------------------|----------|--------|---------------|
| Root | `/` | GET | ✅ |
| Health | `/health` | GET | ✅ |
| Auth | `/api/v1/auth/login` | POST | ✅ |
| Auth | `/api/v1/auth/refresh` | POST | ✅ |
| Auth | `/api/v1/auth/logout` | POST | ✅ |
| Auth | `/api/v1/auth/revoke` | POST | ✅ |
| Auth | `/api/v1/auth/me` | GET | ✅ |
| Rules | `/api/v1/rules` | GET, POST | ✅ |
| Rules | `/api/v1/rules/{id}` | GET, PUT, DELETE | ✅ |
| Rules | `/api/v1/rules/workloads` | GET | ✅ |
| Rules | `/api/v1/rules/workloads/{id}` | GET | ✅ |
| Rules | `/api/v1/rules/search` | GET | ✅ |
| Rules | `/api/v1/rules/bulk` | POST, PUT, DELETE | ✅ |
| Rules | `/api/v1/rules/export` | GET | ✅ |
| Rules | `/api/v1/rules/{id}/clone` | POST | ✅ |
| Rules | `/api/v1/rules/validate` | POST | ✅ |
| Rules | `/api/v1/rules/stats` | GET | ✅ |
| Approvals | `/api/v1/approvals` | GET, POST | ✅ |
| Approvals | `/api/v1/approvals/{id}` | GET | ✅ |
| Approvals | `/api/v1/approvals/{id}/approve` | POST | ✅ |
| Approvals | `/api/v1/approvals/{id}/reject` | POST | ✅ |
| Approvals | `/api/v1/approvals/{id}/comment` | POST | ✅ |
| Approvals | `/api/v1/approvals/{id}/history` | GET | ✅ |
| Approvals | `/api/v1/approvals/bulk/approve` | POST | ✅ |
| Approvals | `/api/v1/approvals/bulk/reject` | POST | ✅ |
| Approvals | `/api/v1/approvals/{id}/escalate` | POST | ✅ |
| Approvals | `/api/v1/approvals/handle-timeouts` | POST | ✅ |
| Approvals | `/api/v1/approvals/pending/count` | GET | ✅ |
| Audit | `/api/v1/audit` | GET | ✅ |
| Audit | `/api/v1/audit/resource/{id}` | GET | ✅ |
| Audit | `/api/v1/audit/user/{id}` | GET | ✅ |
| Audit | `/api/v1/audit/stats` | GET | ✅ |
| Audit | `/api/v1/audit/search` | GET | ✅ |
| Audit | `/api/v1/audit/export` | GET | ✅ |
| Audit | `/api/v1/audit/actions` | GET | ✅ |
| Audit | `/api/v1/audit/resource-types` | GET | ✅ |
| Audit | `/api/v1/audit/by-correlation/{id}` | GET | ✅ |

## Auth Flow Test Scenarios

| Scenario | Description |
|----------|-------------|
| Login Success | Valid credentials return tokens |
| Login Empty Username | Empty username returns 401 |
| Login Empty Password | Empty password returns 401 |
| Token Refresh | Valid refresh token returns new tokens |
| Refresh Invalid Token | Invalid token returns 401 |
| Logout | Valid refresh token is revoked |
| Token Revocation | Access token is revoked |
| Get Me Unauthorized | Unauthenticated /me returns 401 |
| Get Me Authorized | Authenticated /me returns user info |

## Error Scenarios

| Scenario | Expected Status |
|----------|-----------------|
| Invalid Token | 401 |
| Expired Token | 401 |
| Malformed Request Body | 422/400 |
| Missing Required Fields | 422 |
| Non-existent Rule | 404 |
| Non-existent Approval | 404 |
| Empty Bulk IDs | 400 |
| Empty Search Query | 422 |
| Invalid Page Number | 422 |
| Invalid Page Size | 422 |

## End-to-End Workflow Tests

| Workflow | Steps |
|----------|-------|
| Create Rule + Audit | Create rule → Verify audit log entry |
| Create Approval + List | Create approval → List approvals |
| Full Lifecycle | Create rule → Create approval → Check audit |

## Test Database Setup

Tests use a SQLite in-memory database with the following configuration:

- **Database Type**: SQLite (for test isolation)
- **Connection**: Static pool for thread safety
- **Tables**: All models are created automatically via SQLAlchemy

## Middleware Tests

| Middleware | Test |
|------------|------|
| Request ID | Verifies request ID handling |
| Content-Type | Verifies JSON content-type header |

## Adding New Integration Tests

To add new integration tests:

1. Create a new test class following the naming convention `Test{FeatureName}`
2. Place test methods within the class
3. Use the `loginAndGetToken()` helper for authenticated requests
4. Use the `get_auth_headers(token)` helper for header construction
5. Run tests to verify they pass

## Troubleshooting

### Common Issues

1. **Database Connection Errors**: Ensure no other process is using the test database file
2. **Token Validation Failures**: Verify SECRET_KEY is set correctly in environment
3. **Import Errors**: Ensure all dependencies are installed

### Resetting Test Database

```bash
rm -f test_integration.db