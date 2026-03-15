# Trip Service - Docker Setup

A microservice for managing trips and payment data, built with Python and Flask. Containerized with Docker.

## 🚀 Quick Start with Docker

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd trip-service
```

### 2. Create Environment File

Create a `.env` file in the root of trip-service:

```env
# PostgreSQL
DATABASE_URL=postgresql://<username>:<password>@<host>:5432/<database>?sslmode=require

# Redis
REDIS_URL=redis://:<password>@swiftride-redis:6379
REDIS_TLS=false

# Flask app
PORT=3005
DEBUG=True
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Run with Docker

This is a microservice application. The Docker network and Redis instance are **shared across all services**. If `swiftride-net` and `swiftride-redis` are already running from another service, skip straight to Step 3b.

```powershell
# 3a. Create a shared Docker network (skip if already exists)
docker network create swiftride-net

# 3b. Build the Trip Service image
docker build -t trip-service .

# 3c. Run the Trip Service container
docker run -d -p 3005:3005 -p 3006:3006 `
  --name trip-service `
  --network swiftride-net `
  --env-file .env `
  trip-service
```

> **Note:** Port `3005` is for the Flask REST API, port `3006` is for the WebSocket/background service.

### 4. Verify Service

- API: http://localhost:3005
- Docs: http://localhost:3005/api-docs