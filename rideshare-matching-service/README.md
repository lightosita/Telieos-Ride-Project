# Ride Matching Service

**Language**: Go
**Role**: Real-time ride matching engine
**Communication**: Redis Pub/Sub (for events) + WebSocket (to drivers)
**HTTP API**: None (message-driven only – no Swagger/OpenAPI)

This service listens for new ride requests via Redis Pub/Sub, matches them to nearby/available drivers using geospatial logic, proposes rides via WebSocket to drivers, and publishes outcome events back to Redis.

## Key Dependencies

- **Redis** (for Pub/Sub channels and geospatial driver indexing)
  - Host: `swiftride-redis` (resolves via Docker network)
  - Port: 6379
  - Auth: Password from `.env` (`REDIS_PASSWORD`)

- **Shared Docker Network**: `swiftride-net` (external – all services join this for name resolution)

## Setup & Running (Local Development)

This is a microservice application. The Docker network and Redis instance are **shared across all services**. If `swiftride-net` and `swiftride-redis` are already running from another service, skip straight to Step 2.

1. **Prerequisites**
   - Docker installed
   - Shared network exists:
     ```powershell
     docker network create swiftride-net
     ```
   - Redis running (shared instance – start once):
     ```powershell
     docker run -d `
       --name swiftride-redis `
       --network swiftride-net `
       -p 6379:6379 `
       redis:7-alpine redis-server --requirepass <password>
     ```

2. **Start the service**
   ```powershell
   # Build the Matching Service image
   docker build -t matching-service .

   # Run the Matching Service container
   docker run -d -p 3004:3004 `
     --name matching-service `
     --network swiftride-net `
     --env-file .env `
     matching-service
   ```


## Event Contracts & Flow

### 1. Consumes – Incoming Ride Request
Channel: `ride_request_events`
Event name: `ride.requested`

```json
{
  "event": "ride.requested",
  "data": {
    "ride_request_id": "req_67a4f9b2c1",
    "rider_id": "rider_8f2d9e1a",
    "rider_name": "Chinedu Okeke",
    "rider_rating": 4.82,
    "rider_phone": "+2348123456789",
    "pickup_location": {
      "lat": 6.5244,
      "lng": 3.3792,
      "address": "100 Awolowo Road, Ikoyi"
    },
    "dropoff_location": {
      "lat": 6.6018,
      "lng": 3.3515,
      "address": "Ikeja City Mall"
    },
    "vehicle_type": "standard",
    "fare": 2850.00
  }
}
```

### 2. Publishes – Outgoing Events
All published to channel: `ride_request_events`

| Event | Triggered When | Key Fields Added |
|---|---|---|
| `ride.proposed` | Proposal sent to driver (via WebSocket) | `distance_km`, `duration_min` |
| `ride.accepted` | Driver accepts | `driverInfo` (name, plate, rating, etc.) |
| `ride.timed_out` | No acceptance within 30 seconds | – |
| `ride.no_drivers` | No eligible drivers within 5 km | – |

Example: `ride.accepted`

```json
{
  "event": "ride.accepted",
  "ride_request_id": "req_67a4f9b2c1",
  "rider_id": "rider_8f2d9e1a",
  "rider_name": "Chinedu Okeke",
  "rider_phone": "+2348123456789",
  "rider_rating": 4.82,
  "status": "accepted",
  "driverInfo": {
    "id": "drv_3f8e2d9a",
    "firstName": "Ahmed Yusuf",
    "vehicleType": "standard",
    "rating": 4.91,
    "licensePlate": "LAG-442-KLM"
  },
  "pickup": { "lat": 6.5244, "lng": 3.3792, "address": "100 Awolowo Road" },
  "dropoff": { "lat": 6.6018, "lng": 3.3515, "address": "Ikeja City Mall" },
  "vehicle_type": "standard",
  "estimated_fare": 2850
}
```

### 3. WebSocket – Real-time Proposal to Driver App
Sent directly to the driver's connected WebSocket:

```json
{
  "event": "ride.proposed",
  "distance_km": 2.41,
  "duration_min": 11,
  "data": {
    "ride_request_id": "req_67a4f9b2c1",
    "rider_id": "rider_8f2d9e1a",
    "rider_name": "Chinedu Okeke",
    "rider_rating": 4.82,
    "pickup_address": "100 Awolowo Road, Ikoyi",
    "dropoff_address": "Ikeja City Mall",
    "pickup_location": { "lat": 6.5244, "lng": 3.3792 },
    "dropoff_location": { "lat": 6.6018, "lng": 3.3515 },
    "estimated_fare": 2850,
    "vehicle_type": "standard"
  }
}
```

### 4. Matching Rules (Current Logic)
- Max search radius: 5.0 km
- Vehicle type must match exactly (case-insensitive)
- Only one driver gets the proposal (first eligible in geospatial order)
- Auto-cancel proposal after 30 seconds if no acceptance
- Uses Redis geospatial commands (e.g. GEOADD/GEORADIUS) for driver location matching

### 5. High-Level Flow

```
Rider Service
     ↓
     Publish "ride.requested" → Redis (channel: ride_request_events)
     ↓
Matching Service (subscribes to ride_request_events)
     ↓ Finds nearby drivers (Redis GEO)
     ↓ Sends "ride.proposed" via WebSocket → Driver App
     ↓
Driver accepts → POST /api/v1/ride/accept (to driver or gateway service)
     ↓ Matching Service claims ride (e.g. Redis SetNX lock)
     ↓ Publishes "ride.accepted" → Redis
     ↓ Rider App receives update (via another Pub/Sub or push)
```
