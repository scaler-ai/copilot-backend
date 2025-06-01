# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack application template using FastAPI (backend) and React (frontend). The project follows a monorepo structure with Docker Compose for orchestration.

## Essential Commands

### Backend Development
```bash
# Install dependencies and activate environment
cd backend
uv sync
source .venv/bin/activate

# Run development server
fastapi dev app/main.py

# Run tests
bash ./scripts/test.sh

# Run linting
uv run pre-commit run --all-files

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Frontend Development
```bash
# Setup and install
cd frontend
fnm use  # or nvm use
npm install

# Run development server
npm run dev

# Generate API client (run after backend API changes)
./scripts/generate-client.sh
```

### Docker Development
```bash
# Start full stack with hot reload
docker compose watch

# View logs
docker compose logs backend
docker compose logs frontend

# Run backend tests in container
docker compose exec backend bash scripts/tests-start.sh

# Access database
docker compose exec db psql -U postgres -d app
```

## Architecture Overview

### Backend Structure
- **FastAPI** application with SQLModel ORM
- **Authentication**: JWT-based with email verification
- **Database**: PostgreSQL with Alembic migrations
- **Models**: Located in `backend/app/models/` - uses SQLModel for ORM
- **API Routes**: In `backend/app/api/routes/` - RESTful endpoints
- **CRUD Operations**: Centralized in `backend/app/crud.py`
- **Schemas**: Pydantic models in `backend/app/schemas/`
- **Core Config**: `backend/app/core/config.py` - environment variables via Settings class

### Frontend Structure
- **React 18** with TypeScript and Vite
- **API Client**: Auto-generated from OpenAPI spec in `frontend/src/client/`
- **Routing**: TanStack Router with file-based routes in `frontend/src/routes/`
- **State Management**: TanStack Query for server state
- **UI Components**: Chakra UI v3 components in `frontend/src/components/`
- **Authentication**: Custom hook `useAuth()` for auth state management

### Key Integration Points
1. **API Client Generation**: Frontend API client is auto-generated from backend OpenAPI spec
2. **Authentication Flow**: JWT tokens stored in localStorage, sent via Authorization header
3. **Environment Config**: `.env` file for secrets, docker-compose.override.yml for dev settings
4. **CORS**: Configured in backend to allow frontend origin

## Development Workflow

1. **Database Changes**: Create models in `backend/app/models/`, generate migration with alembic
2. **API Changes**: Update routes in `backend/app/api/routes/`, regenerate frontend client
3. **Frontend Features**: Add routes in `frontend/src/routes/`, components in `frontend/src/components/`
4. **Testing**: Backend tests in `backend/app/tests/`, frontend E2E tests in `frontend/tests/`

## Important URLs
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Database Admin: http://localhost:8080
- MailCatcher: http://localhost:1080

## Database Schema
- **Users**: Authentication and profile management
- **Items**: Example CRUD resource with user ownership
- **OAuth States**: CSRF protection for OAuth flows
- All models use UUID primary keys and include timestamps

## Testing Approach
- Backend: Pytest with fixtures for database and authenticated clients
- Frontend: Playwright E2E tests with authentication setup
- Run all tests: `docker compose exec backend bash scripts/tests-start.sh && cd frontend && npx playwright test`