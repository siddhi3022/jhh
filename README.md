# RS-SBSM Order & Inventory Microservices

## Overview

This project contains two FastAPI microservices prepared for Git, GitHub, Jenkins and Docker deployment.

- Order Service: port 1001 (container port 8001)
- Inventory Service: port 1002 (container port 8002)
- Synchronous communication: Order Service to Inventory Service using HTTPX
- Authentication: JWT
- Database: SQLite

## Project Structure

```text
RS-SBSM
├── order-service
├── inventory-service
├── requirements.txt
├── docker-compose.yml
├── Jenkinsfile
├── README.md
└── .gitignore
```

## Local Docker Run

```powershell
docker-compose build
docker-compose down --remove-orphans
docker rm -f inventory 2>$null
docker rm -f order 2>$null
docker-compose up -d
docker-compose ps
```

## Swagger

- http://127.0.0.1:1001/docs
- http://127.0.0.1:1002/docs

## Git / GitHub

```powershell
git add .
git commit -m "Update Order Inventory Microservices"
git push origin main
```

## Jenkins Pipeline

GitHub → Jenkins Checkout → Environment → Install Dependencies → Docker Build → Docker Compose Deploy → Final Status

The Jenkins pipeline contains no test or pytest stage.
