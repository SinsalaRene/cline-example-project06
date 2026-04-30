# Task 1.2: Improve Authentication

## Description
Enhance JWT authentication with refresh tokens, proper token validation, and rate limiting.

## Context
Current auth is basic JWT only with no refresh token mechanism. The `auth_service.py` creates tokens but has no refresh logic, no token blacklist, and no rate limiting.

## Files to Modify
- `backend/app/auth/auth_service.py` - Add refresh tokens, validation
- `backend/app/auth/router.py` - Create new auth endpoints
- `backend/app/schemas/user.py` - Add auth schemas
- `backend/app/main.py` - Add auth middleware
- `backend/app/config.py` - Add auth config

## Deliverables

### Code Changes
1. Add refresh token creation and validation
2. Add token blacklist/revoke functionality
3. Add rate limiting for auth endpoints
4. Add proper token expiration handling
5. Create auth endpoints (/auth/login, /auth/refresh, /auth/logout)

### Tests
1. `backend/tests/test_auth.py` - Token creation, validation, refresh, revoke
2. `backend/tests/test_rate_limiting.py` - Rate limit enforcement

### Documentation Updates
1. Update auth flow documentation
2. Update API documentation with auth endpoints

## Acceptance Criteria
- [x] JWT tokens created and validated correctly
- [x] Refresh tokens work properly
- [x] Token revoke/blacklist works
- [x] Rate limiting on auth endpoints
- [x] All tests pass (33/33 tests passing)
- [x] Documentation updated

## Implementation Details

### Authentication Flow
1. **Login**: User sends credentials, receives `access_token` and `refresh_token`
2. **Access Token**: Short-lived JWT (default 30 minutes), used for API authorization
3. **Refresh Token**: Long-lived JWT (7 days), used to obtain new access tokens
4. **Token Refresh**: New pair returned each time (rotation), old refresh token invalidated

### Token Types
- **Access Token** (`type: "access"`):
  - Expiration: Configurable via `access_token_expire_minutes` (default: 30 min)
  - Contains: `sub` (user ID), `type`, `exp`, `jti` (unique ID), `email`, `name`
  - Validated via: `validate_access_token(token)`

- **Refresh Token** (`type: "refresh"`):
  - Expiration: Configurable via `refresh_token_expire_days` (default: 7 days)
  - Contains: `sub` (user ID), `type`, `exp`, `jti`
  - Validated via: `validate_refresh_token(token)`
  - Single-use: invalidated after refresh (rotation)

### Token Blacklist
- Blacklisted tokens are stored in memory (`_token_blacklist` dict)
- Expired entries are automatically cleaned via `cleanup_blacklist()`
- Blacklisted tokens cannot be validated even if still valid per JWT expiry
- Revoke via: `revoke_token(token)` or `revoke_refresh_token(token)`

### Rate Limiting
- Applied to `/auth/login` and `/auth/refresh` endpoints
- Configurable via `auth_rate_limit_per_minute` and `auth_rate_limit_window`
- Per-IP, per-endpoint tracking
- Returns HTTP 429 when limit exceeded
- Window auto-cleanup via `cleanup_rate_limits()`

### API Endpoints
- `POST /api/auth/login` - Authenticate and receive tokens
- `POST /api/auth/refresh` - Refresh access token using refresh token
- `POST /api/auth/logout` - Revoke tokens (blacklist)

### Security Features
- Unique JTI for each token (prevents replay attacks)
- Token rotation (old refresh token invalidated on use)
- Type enforcement (access tokens can't be used as refresh tokens and vice versa)
- Client IP tracking per endpoint for rate limiting

## Test Coverage
- 22 tests for authentication (token creation, validation, refresh, revoke, rotation)
- 11 tests for rate limiting (enforcement, reset, cleanup, middleware)
- Total: 33 tests passing
