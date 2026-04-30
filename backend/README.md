# Azure Firewall Management API

FastAPI-based REST API for managing Azure firewall rules with approval workflows, role-based access control (RBAC), and audit trails.

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 13+ (production) or SQLite (development)
- Azure subscription (for full integration)

### Installation

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### API Documentation

Once running, access the interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

### Project Structure

```
backend/
├── app/
│   ├── main.py              # Application entry point, middleware config
│   ├── config.py            # Settings and configuration
│   ├── database.py          # Database connection and session management
│   ├── middleware/          # HTTP middleware components
│   │   ├── request_id.py    # Request ID tracking middleware
│   │   ├── timing.py        # Timing and logging middleware
│   │   ├── exception_handler.py # Exception handling middleware
│   │   └── validation.py    # Input validation middleware
│   ├── api/                 # API route handlers
│   ├── auth/                # Authentication (JWT)
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic services
│   └── utils/               # Utility functions
├── tests/                   # Test suite
├── alembic/               # Database migrations
└── requirements.txt       # Python dependencies
```

### Middleware Pipeline

The application uses a layered middleware pipeline for cross-cutting concerns:

```
Request Flow:
┌─────────────────────────────────────────────────────────────┐
│                    Client Request                            │
└─────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────┐
│  Validation Middleware   → Content-Type, Body Size, JSON     │
└─────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────┐
│  Exception Handler         → Structured Error Responses      │
└─────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────┐
│  Timing Middleware         → Request Duration Logging       │
└─────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────┐
│  Request ID Middleware     → Unique Request Tracking        │
└─────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────┐
│  CORSMiddleware            → CORS Headers                    │
└─────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Route Handler     → Business Logic                 │
└─────────────────────────────────────────────────────────────┘
```

#### Middleware Components

1. **ValidationMiddleware** (`app/middleware/validation.py`)
   - Validates Content-Type headers (requires application/json for POST/PUT/PATCH)
   - Enforces maximum body size (configurable, default 10MB)
   - Parses and validates JSON body content
   - Returns structured error responses with validation details

2. **ExceptionHandlerMiddleware** (`app/middleware/exception_handler.py`)
   - Catches unhandled exceptions before they reach the route handler
   - Returns structured JSON error responses with error codes
   - Includes request ID for correlation
   - In debug mode, includes full traceback and error details
   - Maps exception types to appropriate HTTP status codes

3. **TimingMiddleware** (`app/middleware/timing.py`)
   - Measures and logs request processing time
   - Adds `X-Response-Time` header to responses
   - Redacts sensitive headers (Authorization, Cookie, API keys)
   - Logs at appropriate levels (INFO, WARNING, ERROR) based on status code

4. **RequestIDMiddleware** (`app/middleware/request_id.py`)
   - Generates unique UUID4 request ID for each request
   - Preserves incoming X-Request-ID if provided
   - Adds X-Request-ID to response headers
   - Attaches request ID to request state for downstream use

5. **CORSMiddleware**
   - Configures Cross-Origin Resource Sharing
   - In debug mode, allows all origins
   - In production, restricts to configured allowed hosts

### Request ID Flow

```
Client → POST /api/v1/rules
         Headers: {X-Request-ID: abc-123}

RequestIDMiddleware:
  - Receives X-Request-ID: abc-123
  - Sets request.state.request_id = "abc-123"
  - Logs: "[Request abc-123] POST /api/v1/rules"

TimingMiddleware:
  - Records start time
  - Logs after completion: "[abc-123] POST /api/v1/rules -> 201 (15.42ms)"

ExceptionHandlerMiddleware:
  - Catches any unhandled exceptions
  - Includes request_id in error response

Response:
  Headers: {X-Request-ID: abc-123, X-Response-Time: 15.42ms}
  Body: {...}
```

## API Endpoints

### Health Check
```http
GET /health
```

### Root
```http
GET /
```

### Authentication
See `app/auth/router.py` for full authentication endpoints.

### Firewall Rules
See `app/api/rules.py` for firewall rule endpoints.

### Approvals
See `app/api/approvals.py` for approval workflow endpoints.

### Audit Log
See `app/api/audit.py` for audit log endpoints.

## Testing

```bash
# Run all tests
cd backend
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_middleware.py -v
```

## Configuration

Environment variables are loaded from `.env` file. See `.env.example` for all available settings.

| Setting | Description | Default |
|---------|-------------|---------|
| DATABASE_URL | Database connection string | SQLite file |
| SECRET_KEY | JWT signing key | test-secret-key... |
| DEBUG | Debug mode flag | False |
| ALLOWED_HOSTS | Comma-separated allowed hosts | ["*"] |
| MAX_BODY_SIZE | Maximum request body size (bytes) | 10485760 (10MB) |

## Error Responses

All error responses follow a consistent structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "User-friendly error message",
    "path": "/api/v1/resource",
    "request_id": "uuid-v4-string",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format",
        "type": "validation_error"
      }
    ]
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 422 | Input validation failed |
| INVALID_JSON | 422 | Request body contains invalid JSON |
| UNSUPPORTED_MEDIA_TYPE | 415 | Content-Type must be application/json |
| PAYLOAD_TOO_LARGE | 413 | Request body exceeds maximum size |
| INVALID_CONTENT_LENGTH | 400 | Invalid Content-Length header |
| INVALID_VALUE | 400 | Invalid field value |
| INVALID_TYPE | 400 | Wrong data type |
| MISSING_FIELD | 404 | Required field missing |
| INTERNAL_SERVER_ERROR | 500 | Unexpected server error |

## Logging

The application uses Python's standard logging module. Log format:

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Log level is controlled by the `DEBUG` setting:
- Debug mode: DEBUG level
- Production: INFO level

### Structured Logging with Request IDs

All log entries include the request ID when available, enabling correlation across distributed systems.

## Production Deployment

1. Set `DEBUG=false`
2. Configure `DATABASE_URL` to PostgreSQL connection string
3. Set `SECRET_KEY` to a strong random key
4. Configure `ALLOWED_HOSTS` with your domain
5. Configure Azure credentials for firewall integration
6. Set up reverse proxy (nginx, traefik) in front of the server
7. Enable HTTPS

## Development

### Adding New Middleware

1. Create a new file in `app/middleware/`
2. Subclass `BaseHTTPMiddleware` from Starlette
3. Add to `main.py` in the correct order (earlier = outer)
4. Add tests in `tests/test_middleware.py`