# SwiftRide Frontend (Next.js)

This folder contains the Next.js frontend for the SwiftRide platform.
It is built to run in Docker and connects to backend microservices over the shared `swiftride-net` Docker network.

## 🧱 Architecture

- The frontend is **stateless** — all data lives in backend services.
- Environment variables configure all API endpoints.
- Communicates with backend services via Docker network (`swiftride-net`) in production, and `localhost` ports in development.
- Built for production using a multi-stage Dockerfile.

## 🔗 Environment Variables

Create a `.env` file in this folder (or copy `.env.example`) with the following variables:

| Variable | Default (dev) | Description |
|---|---|---|
| `NEXT_PUBLIC_RIDER_SERVICE_URL` | `http://localhost:3001` | Rider service base URL |
| `NEXT_PUBLIC_DRIVER_SERVICE_URL` | `http://localhost:3003` | Driver service base URL |
| `NEXT_PUBLIC_TRIP_SERVICE_URL` | `http://localhost:3005` | Trip service base URL |
| `NEXT_PUBLIC_MATCHING_SERVICE_URL` | `http://localhost:3004` | Matching service base URL |
| `NEXT_PUBLIC_TRIP_WS_URL` | `ws://localhost:3006` | Trip WebSocket URL |
| `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` | _(required)_ | Mapbox public access token |

> [!IMPORTANT]
> All service URLs should be **bare host:port** values with **no trailing slash and no `/api` suffix**.
> The frontend code adds the correct API path prefix (`/api`, `/api/v1`, etc.) for each request.

Example `.env`:
```env
NEXT_PUBLIC_RIDER_SERVICE_URL=http://localhost:3001
NEXT_PUBLIC_DRIVER_SERVICE_URL=http://localhost:3003
NEXT_PUBLIC_TRIP_SERVICE_URL=http://localhost:3005
NEXT_PUBLIC_MATCHING_SERVICE_URL=http://localhost:3004
NEXT_PUBLIC_TRIP_WS_URL=ws://localhost:3006
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=your_token_here
```

## 📦 Docker Setup

The frontend uses the included `Dockerfile` for a multi-stage build:

| Stage | Description |
|---|---|
| `base` | Node.js Alpine image |
| `deps` | Installs dependencies |
| `builder` | Builds the Next.js application |
| `runner` | Production-ready container with minimal runtime files |

Ensure all backend services and Redis are running on the `swiftride-net` network before starting the frontend.

## 1️⃣ Run with Docker


```powershell
# 1a. Build the Frontend image
docker build -t rideshare-frontend .

# 1b. Run the Frontend container
docker run -d -p 3000:3000 `
  --name rideshare-frontend `
  --env-file .env `
  rideshare-frontend
```

The frontend will be available at **http://localhost:3000**

## 2️⃣ Run Locally (Development)

```bash
npm install
npm run dev
```
