# Fintech Identity Demo (Full Mock)

This repository contains a full-stack hackathon demo for a portable, privacy-preserving digital identity flow.

## What is included

- Node.js backend for mock KYC, VC issuance/verification, ZKP verification, and fraud checks
- React wallet web app with QR-based sharing and mock ZKP proof generation
- Circom circuit for age >= 18 proof (demo)
- Postgres database via Docker Compose

## Quick start

### 1) Start Postgres

```
docker compose up -d
```

### 2) Backend

```
cd backend
npm install
npm run db:setup
npm run dev
```

### 3) Frontend

```
cd frontend
npm install
npm run dev
```

Open the frontend URL shown in the terminal.

## Demo flow

1) Create wallet (client-side DID + key pair)
2) Start KYC -> submit mock liveness
3) Issue VC -> store in wallet
4) Generate mock ZKP -> share via QR
5) Bank verifies VC + ZKP

## Notes

- ZKP is wired for a real Circom circuit, but verification is mocked for speed.
- Replace mock checks with real model inference and attestation when needed.
