#  DEPLOYMENT.md — Telieos Ride (RideShare Pro)

> **Infrastructure:** AWS EKS 1.33 | **Cluster:** light-rideshare-cluster  
> **Domain:** www.teleiosdupsy.space | **Region:** us-east-1

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository Structure](#2-repository-structure)
3. [Local Development Setup](#3-local-development-setup)
4. [AWS Infrastructure Setup](#4-aws-infrastructure-setup)
5. [EKS Cluster Setup](#5-eks-cluster-setup)
6. [Secrets Setup (AWS Secrets Manager + ESO)](#6-secrets-setup-aws-secrets-manager--eso)
7. [Deploy Platform Components](#7-deploy-platform-components)
8. [Deploy Application Services](#8-deploy-application-services)
9. [DNS & TLS Setup](#9-dns--tls-setup)
10. [CI/CD Pipeline](#10-cicd-pipeline)
11. [Verifying the Deployment](#11-verifying-the-deployment)
12. [Scaling & Updates](#12-scaling--updates)
13. [Teardown](#13-teardown)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Prerequisites

Install all required tools before proceeding:

| Tool | Version | Install |
|------|---------|---------|
| **AWS CLI v2** | 2.x+ | `brew install awscli` / [official installer](https://aws.amazon.com/cli/) |
| **kubectl** | 1.33.x | `brew install kubectl` |
| **eksctl** | 0.180.x+ | `brew tap weaveworks/tap && brew install eksctl` |
| **helm** | 3.x+ | `brew install helm` |
| **Docker** | 24.x+ | [Docker Desktop](https://www.docker.com/products/docker-desktop) |
| **Node.js** | 18.x+ | `brew install node` |

**Verify all tools:**
```bash
aws --version
kubectl version --client
eksctl version
helm version
docker --version
node --version
```

**Configure AWS CLI:**
```bash
aws configure
# AWS Access Key ID: <your key>
# AWS Secret Access Key: <your secret>
# Default region: us-east-1
# Default output: json
```

---

## 2. Repository Structure

```
Telieos-Ride-Project/
├── light-rideshare-k8s/              # All Kubernetes manifests
│   ├── aws/
│   │   └── storage-classes.yaml
│   ├── platform/
│   │   ├── ingress/
│   │   │   └── ingress-rules.yaml
│   │   ├── secrets/
│   │   │   ├── secret-store.yaml     ← ESO auth config
│   │   │   └── external-secrets.yaml ← What to pull from AWS SM
│   │   ├── autoscaling/
│   │   │   └── cluster-autoscaler.yaml
│   │   └── security/
│   │       └── pod-disruption-budgets.yaml
│   └── applications/
│       ├── rider-service/
│       ├── driver-service/
│       ├── trip-service/
│       ├── matching-service/
│       ├── email-service/
│       └── frontend/
├── rideshare-rider-service/          # TypeScript/Node.js
├── rideshare-driver-service/         # TypeScript/Node.js
├── rideshare-trip-service/           # Python/Flask
├── rideshare-matching-service/       # Go/Gin
├── rideshare-email-service/          # Python/Flask
├── rideshare-frontend/               # Next.js
├── rideshare-traffic-script/         # Load testing scripts
└── swiftride-architecture/           # Architecture diagrams
```

---

## 3. Local Development Setup

### Clone the repo
```bash
git clone https://github.com/lightosita/Telieos-Ride-Project.git
cd Telieos-Ride-Project
```

### Run services locally with Docker Compose

Create a `docker-compose.yml` at the root:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: rideshare
      POSTGRES_PASSWORD: localdev123
      POSTGRES_DB: rideshare
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  rider-service:
    build: ./rideshare-rider-service
    ports:
      - "3001:3001"
    environment:
      DATABASE_URL: postgres://rideshare:localdev123@postgres:5432/rideshare
      REDIS_URL: redis://redis:6379
      JWT_SECRET: local_dev_secret
      NODE_ENV: development
    depends_on:
      - postgres
      - redis

  driver-service:
    build: ./rideshare-driver-service
    ports:
      - "3003:3003"
    environment:
      DATABASE_URL: postgres://rideshare:localdev123@postgres:5432/rideshare
      REDIS_URL: redis://redis:6379
      JWT_SECRET: local_dev_secret
      NODE_ENV: development
    depends_on:
      - postgres
      - redis

  trip-service:
    build: ./rideshare-trip-service
    ports:
      - "3005:3005"
    environment:
      DATABASE_URL: postgres://rideshare:localdev123@postgres:5432/rideshare
      NODE_ENV: development
    depends_on:
      - postgres

  matching-service:
    build: ./rideshare-matching-service
    ports:
      - "3004:3004"
    environment:
      REDIS_URL: redis://redis:6379
    depends_on:
      - redis

  email-service:
    build: ./rideshare-email-service
    ports:
      - "3002:3002"
    environment:
      AZURE_COMMUNICATION_CONNECTION_STRING: local_placeholder

  frontend:
    build: ./rideshare-frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:3001

volumes:
  pgdata:
```

```bash
# Start everything
docker compose up --build

# Check status
docker compose ps

# View logs
docker compose logs -f matching-service

# Stop
docker compose down
```

---

## 4. AWS Infrastructure Setup

### Create RDS PostgreSQL 17
```bash
aws rds create-db-instance \
  --db-instance-identifier light-rideshare-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 17 \
  --master-username rideshare \
  --master-user-password <YOUR_SECURE_PASSWORD> \
  --allocated-storage 20 \
  --multi-az \
  --region us-east-1
```

### Store credentials in AWS Secrets Manager
```bash
# Store DB credentials
aws secretsmanager create-secret \
  --name "rideshare/production/database" \
  --secret-string '{
    "DB_HOST": "<rds-endpoint>",
    "DB_PORT": "5432",
    "DB_USER": "rideshare",
    "DB_PASSWORD": "<password>",
    "DB_NAME": "rideshare"
  }'

# Store shared secrets
aws secretsmanager create-secret \
  --name "rideshare/production/shared" \
  --secret-string '{
    "JWT_SECRET": "<your_jwt_secret>",
    "REDIS_URL": "<upstash_redis_url>"
  }'

# Store service-specific secrets
aws secretsmanager create-secret \
  --name "rideshare/production/email-service" \
  --secret-string '{
    "AZURE_COMMUNICATION_CONNECTION_STRING": "<azure_conn_string>"
  }'
```

---

## 5. EKS Cluster Setup

### Create the cluster
```bash
eksctl create cluster \
  --name light-rideshare-cluster \
  --region us-east-1 \
  --version 1.33 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 6 \
  --managed \
  --zones us-east-1a,us-east-1b
```

### Update kubeconfig
```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name light-rideshare-cluster
```

### Verify cluster is running
```bash
kubectl get nodes
# Should show 2 nodes in Ready state
```

### Apply storage classes
```bash
kubectl apply -f light-rideshare-k8s/aws/storage-classes.yaml
```

### Install NGINX Ingress Controller
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --set controller.service.type=LoadBalancer \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"=nlb
```

### Install cert-manager
```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

---

## 6. Secrets Setup (AWS Secrets Manager + ESO)

### Install External Secrets Operator
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

### Configure IRSA (IAM Role for ESO)
```bash
# Create IAM policy for ESO to read Secrets Manager
aws iam create-policy \
  --policy-name ExternalSecretsPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:rideshare/*"
    }]
  }'

# Associate the IAM role with the ESO service account
eksctl create iamserviceaccount \
  --name external-secrets-sa \
  --namespace external-secrets \
  --cluster light-rideshare-cluster \
  --attach-policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/ExternalSecretsPolicy \
  --approve
```

### Deploy the SecretStore and ExternalSecrets
```bash
kubectl apply -f light-rideshare-k8s/platform/secrets/secret-store.yaml
kubectl apply -f light-rideshare-k8s/platform/secrets/external-secrets.yaml

# Verify secrets are synced
kubectl get externalsecrets
kubectl get secrets
```

---

## 7. Deploy Platform Components

```bash
# Cluster Autoscaler
kubectl apply -f light-rideshare-k8s/platform/autoscaling/cluster-autoscaler.yaml

# Pod Disruption Budgets
kubectl apply -f light-rideshare-k8s/platform/security/pod-disruption-budgets.yaml
```

---

## 8. Deploy Application Services

### Build and push Docker images
```bash
# Set your Docker Hub username or ECR registry
REGISTRY=your-dockerhub-username

# Build and push each service
for service in rideshare-rider-service rideshare-driver-service rideshare-trip-service rideshare-matching-service rideshare-email-service rideshare-frontend; do
  docker build -t $REGISTRY/$service:latest ./$service
  docker push $REGISTRY/$service:latest
done
```

### Deploy all services to Kubernetes
```bash
# Deploy each application
kubectl apply -f light-rideshare-k8s/applications/rider-service/
kubectl apply -f light-rideshare-k8s/applications/driver-service/
kubectl apply -f light-rideshare-k8s/applications/trip-service/
kubectl apply -f light-rideshare-k8s/applications/matching-service/
kubectl apply -f light-rideshare-k8s/applications/email-service/
kubectl apply -f light-rideshare-k8s/applications/frontend/

# Check all pods are running
kubectl get pods -w
```

### Apply Ingress rules
```bash
kubectl apply -f light-rideshare-k8s/platform/ingress/ingress-rules.yaml
```

---

## 9. DNS & TLS Setup

### Get the NLB hostname
```bash
kubectl get svc ingress-nginx-controller -n ingress-nginx
# Note the EXTERNAL-IP (NLB DNS name)
```

### Configure Route 53
1. Go to AWS Route 53 → Hosted Zones
2. Find `teleiosdupsy.space`
3. Create an **A record (Alias)**:
   - Name: `www`
   - Value: NLB DNS name from above
   - Routing policy: Simple

### Create Let's Encrypt ClusterIssuer
```yaml
# Apply this manifest
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

```bash
kubectl apply -f cluster-issuer.yaml

# Verify certificate is issued (may take 2-3 minutes)
kubectl get certificate
```

---

## 10. CI/CD Pipeline

### `.github/workflows/deploy.yml`
```yaml
name: Build & Deploy to EKS

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig --name light-rideshare-cluster --region us-east-1

      - name: Build & push rider-service
        run: |
          docker build -t ${{ secrets.DOCKERHUB_USERNAME }}/rideshare-rider-service:${{ github.sha }} ./rideshare-rider-service
          docker push ${{ secrets.DOCKERHUB_USERNAME }}/rideshare-rider-service:${{ github.sha }}

      - name: Deploy to EKS
        run: |
          kubectl set image deployment/rider-service \
            rider-service=${{ secrets.DOCKERHUB_USERNAME }}/rideshare-rider-service:${{ github.sha }}
          kubectl rollout status deployment/rider-service
```

### Required GitHub Secrets
| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM user secret |
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |

---

## 11. Verifying the Deployment

```bash
# All pods running
kubectl get pods

# All services have ClusterIPs
kubectl get svc

# Ingress has an external address
kubectl get ingress

# TLS certificate is issued
kubectl get certificate

# Test live endpoints
curl https://www.teleiosdupsy.space/api/riders/health
curl https://www.teleiosdupsy.space/api/drivers/health
curl https://www.teleiosdupsy.space/api/trips/health
curl https://www.teleiosdupsy.space/api/match/health
```

---

## 12. Scaling & Updates

### Manual scale
```bash
kubectl scale deployment rider-service --replicas=3
```

### Rolling update (zero-downtime)
```bash
kubectl set image deployment/rider-service rider-service=newimage:v2
kubectl rollout status deployment/rider-service

# Rollback if needed
kubectl rollout undo deployment/rider-service
```

### View HPA status
```bash
kubectl get hpa
```

---

## 13. Teardown

```bash
# Delete all application resources
kubectl delete -f light-rideshare-k8s/applications/

# Delete platform components
kubectl delete -f light-rideshare-k8s/platform/

# Delete the EKS cluster (WARNING: destructive)
eksctl delete cluster --name light-rideshare-cluster --region us-east-1

# Delete RDS (WARNING: destructive)
aws rds delete-db-instance \
  --db-instance-identifier light-rideshare-db \
  --skip-final-snapshot
```

---

## 14. Troubleshooting

| Symptom | Command | Fix |
|---------|---------|-----|
| Pod stuck in `Pending` | `kubectl describe pod <name>` | Check node capacity, taints, resource requests |
| Pod in `CrashLoopBackOff` | `kubectl logs <pod> --previous` | Check app startup errors |
| Secrets not syncing | `kubectl describe externalsecret <name>` | Verify IAM role has Secrets Manager access |
| Certificate not issuing | `kubectl describe certificate` | Check cert-manager logs, DNS propagation |
| 502 Bad Gateway | `kubectl logs -n ingress-nginx` | Service name mismatch or pod not ready |
| Can't connect to RDS | Check security groups | Allow inbound 5432 from EKS node security group |

