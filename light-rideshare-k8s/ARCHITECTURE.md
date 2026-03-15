#  ARCHITECTURE.md — Telieos Ride (RideShare Pro)

> **Platform:** Production-grade microservices on AWS EKS  
> **Target Market:** African ride-hailing market  
> **Domain:** [www.teleiosdupsy.space](https://www.teleiosdupsy.space)  
> **Cluster:** light-rideshare-cluster (EKS 1.33)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Style & Philosophy](#2-architecture-style--philosophy)
3. [High-Level System Diagram](#3-high-level-system-diagram)
4. [Microservices Breakdown](#4-microservices-breakdown)
5. [Infrastructure Stack](#5-infrastructure-stack)
6. [Kubernetes Architecture](#6-kubernetes-architecture)
7. [Networking & Ingress](#7-networking--ingress)
8. [Data Layer](#8-data-layer)
9. [Secrets Management Architecture](#9-secrets-management-architecture)
10. [Key Flow Sequences](#10-key-flow-sequences)
11. [Scalability & Resilience](#11-scalability--resilience)
12. [Security Architecture](#12-security-architecture)
13. [Design Decisions & Trade-offs](#13-design-decisions--trade-offs)

---

## 1. Project Overview

**Telieos Ride (RideShare Pro)** is a production-grade, cloud-native ride-sharing platform built for the African market — designed from day one to handle unpredictable traffic spikes, mobile-first users on slower networks, and high-concurrency matching demands.

The system is a **polyglot microservices platform**: each service is written in the language best suited to its job (TypeScript for CRUD-heavy services, Python for transactional logic, Go for the high-performance matching engine), all deployed on **Amazon EKS (Elastic Kubernetes Service)**.

### Core Capabilities
- Rider registration, ride requests, and real-time status tracking
- Driver profile management, vehicle registration, and availability toggling
- Intelligent real-time rider-driver matching with geospatial proximity calculation
- Complete trip lifecycle management with state machine transitions
- Transactional email notifications via Azure Communication Services
- Auto-scaling based on demand; Multi-AZ for high availability

---

## 2. Architecture Style & Philosophy

### Pattern: Cloud-Native Microservices on Kubernetes

Each service is:
- **Independently deployable** — update Trip Service without touching Rider Service
- **Independently scalable** — scale Matching Service to 10 replicas during peak hours, keep Email Service at 1
- **Technology-agnostic (polyglot)** — TypeScript, Python, and Go coexist cleanly
- **Fault-isolated** — a crash in Email Service does not affect ride matching
- **Stateless** — all state lives in PostgreSQL or Redis, enabling easy horizontal scaling

### Polyglot Design Rationale
| Service | Language | Reason |
|---------|----------|--------|
| Rider Service | TypeScript/Node.js | Strong typing, fast development for REST CRUD |
| Driver Service | TypeScript/Node.js | Consistent with Rider Service, shared patterns |
| Trip Service | Python/Flask | Rich ecosystem for state machine + business logic |
| Matching Service | Go/Gin | Maximum throughput for real-time geospatial matching |
| Email Service | Python/Flask | Mature templating and email libraries |
| Frontend | Next.js | Server-Side Rendering for fast loads on slower African networks |

---

## 3. High-Level System Diagram

```
┌───────────────────────────────────────────────────┐
│                   CLIENTS                         │
│    Web Browser (Next.js)   |   Mobile App         │
└────────────────┬──────────────────────────────────┘
                 │ HTTPS
┌────────────────▼──────────────────────────────────┐
│              Route 53 DNS                         │
│         www.teleiosdupsy.space                    │
└────────────────┬──────────────────────────────────┘
                 │
┌────────────────▼──────────────────────────────────┐
│        AWS Network Load Balancer (NLB)            │
│           Layer 4 — TCP/TLS passthrough           │
└────────────────┬──────────────────────────────────┘
                 │
┌────────────────▼──────────────────────────────────┐
│         NGINX Ingress Controller                  │
│   TLS termination (cert-manager + Let's Encrypt)  │
└─┬──────────┬──────────┬──────────┬───────────────┘
  │          │          │          │
  ▼          ▼          ▼          ▼
[Rider    [Driver   [Trip      [Matching   [Email
 Svc]      Svc]     Svc]       Svc]        Svc]
TS/Node   TS/Node  Python/    Go/Gin     Python/
:3001     :3003    Flask      :3004      Flask
                   :3005                 :3002
                                    ▼
                             [Frontend]
                             Next.js :3000

         All services connect to:
┌─────────────────────┐   ┌──────────────────────┐
│  Amazon RDS          │   │  Upstash Redis        │
│  PostgreSQL 17       │   │  (Managed, TLS)       │
│  (Managed, Multi-AZ) │   │                       │
└─────────────────────┘   └──────────────────────┘

         Secrets pipeline:
┌──────────────────────────────────────────────────┐
│  AWS Secrets Manager                             │
│     ↑ stores values                             │
│  External Secrets Operator (ESO)                │
│     ↓ syncs to                                  │
│  Kubernetes Secrets → mounted as env vars        │
└──────────────────────────────────────────────────┘
```

---

## 4. Microservices Breakdown

### 4.1 Rider Service — `rideshare-rider-service`
| Property | Detail |
|----------|--------|
| **Language** | TypeScript / Node.js |
| **Port** | 3001 |
| **Responsibility** | Rider profiles, ride request creation, ride status tracking |
| **Key Endpoints** | `POST /riders`, `POST /rides/request`, `GET /rides/:id/status` |
| **Database** | RDS PostgreSQL — `riders`, `ride_requests` tables |
| **Cache** | Upstash Redis — active ride state |

### 4.2 Email Service — `rideshare-email-service`
| Property | Detail |
|----------|--------|
| **Language** | Python / Flask |
| **Port** | 3002 |
| **Responsibility** | Transactional email delivery (confirmations, receipts, alerts) |
| **Key Endpoints** | `POST /emails/send`, `POST /emails/template` |
| **External** | Azure Communication Services |
| **Database** | None (stateless) |

### 4.3 Driver Service — `rideshare-driver-service`
| Property | Detail |
|----------|--------|
| **Language** | TypeScript / Node.js |
| **Port** | 3003 |
| **Responsibility** | Driver profiles, vehicle management, availability & location updates |
| **Key Endpoints** | `POST /drivers`, `PUT /drivers/:id/availability`, `PUT /drivers/:id/location` |
| **Database** | RDS PostgreSQL — `drivers`, `vehicles` tables |
| **Cache** | Upstash Redis — driver live location & availability |

### 4.4 Matching Service — `rideshare-matching-service`
| Property | Detail |
|----------|--------|
| **Language** | Go / Gin |
| **Port** | 3004 |
| **Responsibility** | Real-time geospatial rider-driver matching |
| **Algorithm** | Haversine formula on live driver location data from Redis |
| **Key Endpoints** | `POST /match`, `GET /match/:rideId/status` |
| **Cache** | Upstash Redis — reads live driver locations |
| **Why Go** | Handles thousands of concurrent matching requests with minimal memory; Go goroutines outperform Node/Python event loops for this workload |

### 4.5 Trip Service — `rideshare-trip-service`
| Property | Detail |
|----------|--------|
| **Language** | Python / Flask |
| **Port** | 3005 |
| **Responsibility** | Full trip lifecycle — state transitions, history, fare recording |
| **State Machine** | `REQUESTED → MATCHED → IN_PROGRESS → COMPLETED / CANCELLED` |
| **Key Endpoints** | `POST /trips`, `PUT /trips/:id/state`, `GET /trips/:id`, `GET /trips/history/:riderId` |
| **Database** | RDS PostgreSQL — `trips` table |

### 4.6 Frontend — `rideshare-frontend`
| Property | Detail |
|----------|--------|
| **Language** | Next.js (React) |
| **Port** | 3000 |
| **Responsibility** | Web UI for riders and drivers |
| **Why Next.js** | Server-Side Rendering delivers fast first-page loads on slower mobile connections common in the African market |

---

## 5. Infrastructure Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Container Orchestration | AWS EKS 1.33 | Managed K8s control plane — `light-rideshare-cluster` |
| Compute Nodes | EC2 t3.medium | Multi-AZ: us-east-1a + us-east-1b |
| Database | Amazon RDS PostgreSQL 17 | Managed, Multi-AZ, automated backups |
| Cache | Upstash Redis | Managed, TLS-enabled, serverless billing |
| Load Balancer | AWS NLB | Layer 4 high-throughput |
| Ingress | NGINX Ingress Controller | L7 routing, TLS termination |
| TLS/SSL | cert-manager + Let's Encrypt | Automatic certificate renewal |
| Secrets | AWS Secrets Manager + ESO | GitOps-safe, zero secrets in Git |
| DNS | Route 53 | `www.teleiosdupsy.space` |
| Email | Azure Communication Services | Cross-cloud transactional email |
| Autoscaling | Cluster Autoscaler + HPA | Node-level and pod-level scaling |

---

## 6. Kubernetes Architecture

### Repository Layout (`light-rideshare-k8s/`)
```
light-rideshare-k8s/
├── aws/
│   └── storage-classes.yaml          # EBS storage class definitions
├── platform/
│   ├── ingress/
│   │   └── ingress-rules.yaml        # URL routing rules
│   ├── secrets/
│   │   ├── secret-store.yaml         # ESO → AWS IAM auth config
│   │   └── external-secrets.yaml     # Declares secrets to sync
│   ├── autoscaling/
│   │   └── cluster-autoscaler.yaml   # Node-level auto-scaling
│   └── security/
│       └── pod-disruption-budgets.yaml # Minimum availability guarantees
└── applications/
    ├── rider-service/                 # Deployment + Service + HPA
    ├── driver-service/
    ├── trip-service/
    ├── matching-service/
    ├── email-service/
    └── frontend/
```

### Kubernetes Objects Per Service
| Object | Purpose |
|--------|---------|
| **Deployment** | Declare desired pod count, rolling update strategy |
| **Service** | Stable internal DNS name (e.g., `rider-service`) |
| **HorizontalPodAutoscaler** | Scale pods on CPU/memory metrics |
| **ExternalSecret** | Pull secrets from AWS Secrets Manager into K8s |
| **SecretStore** | Configure ESO's AWS IAM authentication |
| **PodDisruptionBudget** | Guarantee minimum pods during node maintenance |
| **ClusterAutoscaler** | Add/remove EC2 nodes dynamically |

---

## 7. Networking & Ingress

### Traffic Flow
```
www.teleiosdupsy.space
  → Route 53
  → AWS NLB (TCP/TLS)
  → NGINX Ingress Controller (TLS terminated, L7 routing)
      ├── /api/riders/*     → rider-service:3001
      ├── /api/drivers/*    → driver-service:3003
      ├── /api/trips/*      → trip-service:3005
      ├── /api/match/*      → matching-service:3004
      ├── /api/emails/*     → email-service:3002
      └── /*                → frontend:3000
```

### Internal Service Communication
Services call each other using Kubernetes internal DNS:
```
http://rider-service.default.svc.cluster.local:3001
http://trip-service.default.svc.cluster.local:3005
```
No hardcoded IPs — Kubernetes DNS resolves service names to their current ClusterIP automatically.

---

## 8. Data Layer

### Amazon RDS PostgreSQL 17
- AWS-managed: automated backups, patching, Multi-AZ standby replica
- Automatic failover in under 60 seconds if the primary AZ fails
- Each service connects with service-specific credentials from AWS Secrets Manager

### Upstash Redis (TLS)
Two primary use cases:
1. **Driver location cache** — Driver Service writes GPS coordinates every few seconds; Matching Service reads them for proximity calculations. In-memory latency = microseconds vs milliseconds for DB.
2. **Active ride state** — Fast read/write for current ride status without hitting PostgreSQL on every poll.

### Why separate DB and cache?
PostgreSQL is durable and consistent — right for trip history, rider profiles, financial records. Redis is fast and ephemeral — right for live location data that changes constantly and doesn't need to survive a restart.

---

## 9. Secrets Management Architecture

### Pipeline: AWS Secrets Manager → ESO → Kubernetes Secrets → Pods

```
Developer stores secret in AWS Secrets Manager:
  Name: "rideshare/production/rider-service"
  Value: { DB_PASSWORD: "...", JWT_SECRET: "..." }

External Secrets Operator (running as K8s controller):
  Reads: platform/secrets/secret-store.yaml      ← HOW to auth with AWS
  Reads: platform/secrets/external-secrets.yaml  ← WHAT secrets to pull

ESO syncs and creates:
  Kind: Secret
  Name: rider-service-secrets
  Data: DB_PASSWORD=<value>, JWT_SECRET=<value>

Pod spec references the K8s Secret:
  envFrom:
    - secretRef:
        name: rider-service-secrets

Result inside container:
  process.env.DB_PASSWORD  ← injected at runtime, never in image or Git
```

### Why This Architecture Is Production-Grade
- **Zero secrets in Git** — YAML files contain only secret *names*, never *values*
- **Automatic rotation support** — rotate in AWS SM → ESO detects change → K8s Secret updates → pods restart with new value
- **Full audit trail** — AWS CloudTrail logs every read/write of every secret
- **GitOps compatible** — entire cluster state is reproducible from Git

---

## 10. Key Flow Sequences

### Booking a Ride
```
Rider App
  │ 1. POST /api/riders/rides/request { pickup, dropoff }
  ▼
NGINX Ingress → Rider Service (TypeScript)
  │ 2. Creates ride_request record (status: REQUESTED)
  │ 3. POST /match { pickup_lat, pickup_lng }
  ▼
Matching Service (Go)
  │ 4. Reads all available driver locations from Redis
  │ 5. Haversine calc → finds nearest driver
  │ 6. Returns { driver_id, eta_minutes }
  ▼
Rider Service
  │ 7. POST /trips { rider_id, driver_id, pickup, dropoff }
  ▼
Trip Service (Python)
  │ 8. Creates trip record (status: MATCHED)
  │ 9. Notifies Driver Service
  ▼
Driver Service (TypeScript)
  │ 10. Sends in-app notification to driver
  │ 11. Driver accepts → PUT /trips/:id/state { state: IN_PROGRESS }
  ▼
Email Service (Python)
  │ 12. POST /emails/send — confirmation email to rider
```

### Completing a Trip
```
Driver App
  │ 1. PUT /trips/:id/state { state: COMPLETED }
  ▼
Trip Service
  │ 2. Updates state, records end_time, calculates fare
  ▼
Email Service
  │ 3. Sends receipt to rider
  │ 4. Sends earnings summary to driver
```

---

## 11. Scalability & Resilience

### Horizontal Pod Autoscaling
The Matching Service is the hot path — it scales most aggressively:
```yaml
minReplicas: 2
maxReplicas: 10
targetCPUUtilizationPercentage: 60
```

### Node-Level Cluster Autoscaler
When all nodes are saturated, Cluster Autoscaler provisions new EC2 t3.medium nodes automatically. Scales down during off-peak.

### Pod Disruption Budgets
Guarantee minimum availability during rolling deployments and node drains:
```yaml
minAvailable: 1  # At least 1 pod of each service always running
```

### Multi-AZ Resilience
- Pods distributed across us-east-1a and us-east-1b
- RDS has synchronous standby in second AZ; failover < 60s
- If an entire AZ fails, the platform continues serving traffic

---

## 12. Security Architecture

| Layer | Mechanism |
|-------|-----------|
| Transport | TLS/HTTPS via cert-manager + Let's Encrypt (auto-renewed) |
| Secrets | AWS Secrets Manager + ESO — zero secrets in source control |
| AWS IAM | IRSA (IAM Roles for Service Accounts) — pod-level AWS permissions |
| Ingress | NGINX rate limiting, DDoS mitigation at NLB |
| Containers | Non-root user, minimal base images |
| Database | Service-specific credentials, no shared DB superuser |
| Audit | AWS CloudTrail logs all secret access |

---

## 13. Design Decisions & Trade-offs

| Decision | Chosen | Rejected | Why |
|----------|--------|---------|-----|
| Orchestration | AWS EKS (managed) | Self-managed K8s | AWS manages the control plane — eliminates the hardest operational burden |
| Redis | Upstash (serverless) | AWS ElastiCache | No node management, pay-per-request, TLS built-in |
| Email | Azure Communication Services | AWS SES | Simpler onboarding, fewer sandbox restrictions for the African market |
| Matching engine | Go/Gin | Node.js/Python | Go goroutines handle geospatial math at high concurrency without GIL/event-loop constraints |
| Secrets | ESO + AWS Secrets Manager | Sealed Secrets / .env files | Native AWS integration, automatic rotation, full audit trail |
| Frontend | Next.js (SSR) | React SPA (CSR) | SSR delivers faster first paint on slower mobile connections |

