Email Service - Docker Setup
A microservice for managing email notifications, built with Python and Flask. Containerized with Docker.

🚀 Quick Start with Docker
1. Clone and Navigate
bash
git clone <repository-url>
cd email-service


2. Create Environment File

```env
PORT=3002
AZURE_EMAIL_CONNECTION_STRING=your-azure-email-connection-string-here
SENDER_EMAIL=your-sender-email-here
```

3. Run with Docker

This is a microservice application. The Docker network is **shared across all services**. If `swiftride-net` already exists from another service, skip Step 3a.

```powershell
# 3a. Create a shared Docker network (skip if already exists)
docker network create swiftride-net

# 3b. Build the Email Service image
docker build -t email-service .

# 3c. Run the Email Service container
docker run -d -p 3002:3002 `
  --name email-service `
  --network swiftride-net `
  --env-file .env `
  email-service
```

4. Verify Service

API: http://localhost:3002

Health Check: http://localhost:3002/health

docs: http://localhost:3002/api-docs

 