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
- [ ] JWT tokens created and validated correctly
- [ ] Refresh tokens work properly
- [ ] Token revoke/blacklist works
- [ ] Rate limiting on auth endpoints
- [ ] All tests pass
- [ ] Documentation updated

## Notes
- Store refresh tokens in database or Redis
- Implement token rotation
- Add refresh token expiration (e.g., 7 days)
- Access token should remain short-lived (e.g., 8 hours per config)