# Azure Firewall Management Application

A comprehensive solution for managing Azure Firewall rules with approval workflows, RBAC, and audit trails.

## Architecture Overview

```
┌─────────────────┐         ┌─────────────────────────────────────────────────────┐
│  Angular SPA    │────────▶│  API Gateway / App Service                         │
│  (Frontend)     │         │  ┌─────────────────────────┐                        │
│                 │         │  │  Backend API (FastAPI)  │                        │
│  Auth via Entra │         │  │  (Python/SQLAlchemy)    │                        │
│                 │         │  └─────────────────────────┘                        │
└─────────────────┘         └─────────────────────────────────────────────────────┘
```

## Project Structure

```
├── backend/                    # Python FastAPI backend
│   ├── app/                   # Application code
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Configuration management
│   │   ├── database.py       # Database setup
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── api/              # API routes
│   │   ├── auth/             # Authentication
│   │   └── core/             # Core modules
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Container configuration
├── frontend/                   # Angular frontend
│   ├── src/                  # Application source
│   ├── angular.json          # Angular config
│   ├── package.json          # Node dependencies
│   └── tsconfig.json         # TypeScript config
├── infrastructure/             # Terraform/Bicep templates
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Angular CLI 17+
- Docker (optional)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations (if using database)
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
ng serve

# Build for production
ng build --configuration production
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

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
# Azure Configuration
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here
AZURE_SUBSCRIPTION_ID=your-subscription-id-here
AZURE_RESOURCE_GROUP=your-resource-group-name

# Database Configuration
# Development (SQLite):
DATABASE_URL=sqlite:///./firewall_mgmt.db

# Production (PostgreSQL):
# DATABASE_URL=postgresql://user:password@host:5432/firewall_mgmt

# Security
SECRET_KEY=your-secret-key-at-least-16-changes-in-production
```

For a complete list of configuration options, see `backend/.env.example`.

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Key Features

- **Firewall Rule Management**: CRUD operations for Azure Firewall rules
- **Approval Workflows**: Multi-level approval process
- **RBAC**: Role-based access control
- **Audit Trail**: Complete change tracking
- **Entra ID Auth**: Azure AD authentication
- **Workload Management**: Organize rules by workload

## Development

### Backend Development

```bash
# Run tests
pytest

# Lint code
ruff check .

# Format code
black .
```

### Frontend Development

```bash
# Run tests
ng test

# Lint code
ng lint

# Build for production
ng build --configuration production
```

## Database Setup

### Development (SQLite)

The application uses SQLite by default for development. No additional setup is required:

```bash
# The default configuration uses SQLite
DATABASE_URL=sqlite:///./firewall_mgmt.db
```

### Production (PostgreSQL)

For production, configure PostgreSQL:

```bash
DATABASE_URL=postgresql://user:password@host:5432/firewall_mgmt
```

### Database Migrations

The application uses Alembic for database migrations:

```bash
cd backend

# Initialize Alembic (first time only)
alembic init alembic

# Create a new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

See `backend/README.md` for detailed migration instructions.

## Deployment to Azure

### Container Apps

```bash
# Login to Azure
az login

# Build and push to ACR
az acr login --name youracr
docker build -t youracr.azurecr.io/firewall-mgmt:latest ./backend
docker push youracr.azurecr.io/firewall-mgmt:latest

# Deploy to Container Apps
az containerapp up --name firewall-mgmt --resource-group your-rg \
  --image youracr.azurecr.io/firewall-mgmt:latest \
  --target-port 8000
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT