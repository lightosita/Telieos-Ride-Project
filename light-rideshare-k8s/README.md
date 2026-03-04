#README.md

  # RideShare Pro - Kubernetes Deployment

  A production-grade microservices ride-sharing platform deployed on Amazon EKS.

  ## Overview

  RideShare Pro is a microservices-based ride-sharing platform built for the African market. It handles unpredictable traffic spikes, maintains high
  availability, and scales efficiently using Kubernetes on AWS EKS.

  ## Services

  | Service | Technology | Port | Description |
  |---------|-----------|------|-------------|
  | Rider Service | TypeScript/Node.js | 3001 | Rider profiles, ride requests, status tracking |
  | Driver Service | TypeScript/Node.js | 3003 | Driver profiles, vehicle management, availability |
  | Trip Service | Python/Flask | 3005 | Trip lifecycle, state transitions, history |
  | Matching Service | Go/Gin | 3004 | Real-time rider-driver matching |
  | Email Service | Python/Flask | 3002 | Transactional emails via Azure Communication Services |
  | Frontend | Next.js | 3000 | User-facing web application |

  ## Infrastructure

  - **Cluster:** AWS EKS 1.33 (light-rideshare-cluster)
  - **Nodes:** t3.medium, Multi-AZ (us-east-1a, us-east-1b)
  - **Database:** Amazon RDS PostgreSQL 17 (managed)
  - **Cache:** Upstash Redis (managed, TLS-enabled)
  - **Ingress:** NGINX Ingress Controller with NLB
  - **TLS:** cert-manager with Let's Encrypt
  - **Secrets:** AWS Secrets Manager + External Secrets Operator
  - **DNS:** Route 53 (www.teleiosdupsy.space)

  ## Quick Start

  See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step deployment instructions.

  ## Directory Structure

  light-rideshare-k8s/
  ├── README.md
  ├── ARCHITECTURE.md
  ├── DEPLOYMENT.md
  ├── aws/
  │   └── storage-classes.yaml
  ├── platform/
  │   ├── ingress/
  │   │   └── ingress-rules.yaml
  │   ├── secrets/
  │   │   ├── secret-store.yaml
  │   │   └── external-secrets.yaml
  │   ├── autoscaling/
  │   │   └── cluster-autoscaler.yaml
  │   └── security/
  │       └── pod-disruption-budgets.yaml
  ├── stateful/
  │   ├── redis/
  │   │   └── redis-cluster.yaml
  │   └── postgres/
  │       └── postgres-primary-replica.yaml
  └── applications/
      ├── rider-service/
      ├── driver-service/
      ├── trip-service/
      ├── matching-service/
      ├── email-service/
      └── frontend/

  ## Prerequisites

  - AWS CLI v2
  - kubectl
  - eksctl
  - helm
  - Docker