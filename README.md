# Ping ⚡

> A production-ready real-time chat application, built phase by phase — to understand what happens when systems need to scale.

It's a deliberate exercise in **High Level System Design**, **concurrency**, and **multi-threading** — built with the goal of watching each architectural decision either hold up or break.

**Live Demo:** [16.112.64.12.nip.io/chatapp/](http://16.112.64.12.nip.io/chatapp/)

---

## Features

- Real-time direct and group messaging over WebSocket
- Google OAuth 2.0 + username/password authentication
- Group management with admin roles, member add/remove, and promotion
- Message receipts tracking
- Fully responsive UI — mobile and desktop
- JWT-based session management

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | Python, FastAPI (async), SQLAlchemy (async) |
| Database | PostgreSQL (`asyncpg`) |
| Auth | Google OAuth 2.0, bcrypt, JWT |
| Infrastructure | AWS EC2 (t3.micro), Nginx (reverse proxy + static server) |
| CI/CD | GitHub Actions |
| Testing | `pytest-asyncio` (integration), k6 (load) |
| Future | C++ (connection manager), gRPC |

---

## Architecture — A Phased Journey

The architecture isn't fixed. It evolves deliberately across phases, each one motivated by a real bottleneck encountered in the previous one.

---

### Phase 1 — Single Service (Current)

```
Browser
  │
  ▼
Nginx  ──────────────────────►  Static Frontend (React/Vite build)
  │
  ▼
FastAPI (Uvicorn/Gunicorn)
  │               │
  ▼               ▼
PostgreSQL     WebSocket
(RDS)          Connection Manager
               (Python, in-process)
```

A single FastAPI server running on an **AWS t3.micro** instance handles everything — REST APIs, WebSocket connections, and serves as the origin for Nginx to proxy. The connection manager lives inside the Python process, which means it shares the GIL. It works. And it has limits that become visible under load.

Load testing with **k6** is run at each phase. Results will be published as HTML reports in the repository as they are completed.

> CI/CD is live from day one. Every push to `main` runs the full integration test suite against a real PostgreSQL instance before any deployment happens.

---

### Phase 2 — C++ Connection Manager (Planned)

The WebSocket connection manager will be extracted into a standalone **C++ service**, communicating with the FastAPI backend over **gRPC**.

The goal is straightforward: Python is not the right tool for managing thousands of concurrent, stateful connections. C++ is. A dedicated service eliminates the GIL entirely, allows fine-grained control over thread pools, and gives the connection layer room to breathe independently of the application logic layer.

```
FastAPI  ──── gRPC ────►  C++ Connection Manager
                              │
                         (Thread pool,
                          raw socket I/O,
                          all CPU cores yours)
```

The t3.micro has 2 vCPUs — both mapped to a single physical core. It's a humbling environment to squeeze concurrency out of. That's exactly the point.

---

### Phase 3 — Horizontal Scaling (Planned)

Once a single node is genuinely optimised, the architecture scales out:

```
                    ┌─────────────────────────────┐
Browser ──► Nginx ──┤  Load Balancer               │
           (L7)     └──┬──────────────┬────────────┘
                       │              │
                  Node 1           Node 2
                FastAPI +        FastAPI +
                C++ ConnMgr      C++ ConnMgr
                       │              │
                       └──────┬───────┘
                              │
                    Gossip Protocol (C++)
                         or Redis
                    (Connection state sync)
```

Multiple connection manager nodes need to know where each connected user lives so messages can be routed correctly across nodes. This will be solved with either a **C++ gossip protocol implementation** or **Redis pub/sub** — the load test results from Phase 2 will decide which.

---

## CI/CD Pipeline

```
Push to main
     │
     ▼
┌─────────────────────────────┐
│  GitHub Actions             │
│                             │
│  1. Spin up PostgreSQL      │
│  2. Run full integration    │
│     test suite              │
│     (pytest-asyncio)        │
│                             │
│  ✓ Pass → Deploy to EC2     │
│  ✗ Fail → Block deploy      │
└─────────────────────────────┘
```

Tests cover authentication (JWT gating, credential login, Google OAuth flow), user APIs, group lifecycle (create, update, add/remove members, admin promotion, delete), and WebSocket message routing.

No merge reaches the server without passing all of them.

---

## Running Locally

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Create a .env file
# DATABASE_URL=postgresql+asyncpg://...
# JWT_SECRET=...
# WEBCLIENT_ID=... (Google OAuth client ID)

uvicorn main:app --reload
```

**Frontend**
```bash
cd frontend
npm install

# Create a .env file
# VITE_API_URL=http://localhost:8000
# VITE_WS_URL=ws://localhost:8000
# VITE_GOOGLE_CLIENT_ID=...

npm run dev
```

**Running Tests**
```bash
cd backend
pytest -v

# Specific test file or class
pytest tests/test_groups.py::TestCreateGroup -v
```

---

## Project Goals

- Build something that handles real concurrency, not just simulated
- Make every architectural decision traceable to a measurable outcome (load test)
- Practice the full lifecycle: design → implement → test → break → redesign

---

## Roadmap

- [x] Phase 1 — FastAPI monolith, WebSocket messaging, full CI/CD
- [x] Integration test suite (auth, users, groups)
- [ ] Phase 1 load test report (k6)
- [ ] Phase 2 — C++ connection manager over gRPC
- [ ] Phase 2 load test report (k6)
- [ ] Phase 3 — Horizontal scaling over 2 aws instances with gossip / Redis
            (or even multiple instances for small duration of 1-2 hrs of load testing) 
- [ ] Phase 3 load test report (k6)
