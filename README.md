<h1 align="center">VyOS Manager</h1>

<p align="center">
  <strong>Enterprise-Grade VyOS Router Management Platform</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/VyOS-1.4%20%7C%201.5-blue?style=flat-square" alt="VyOS Version"/>
  <img src="https://img.shields.io/badge/Python-3.11+-green?style=flat-square&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js" alt="Next.js"/>
  <img src="https://img.shields.io/badge/FastAPI-0.100+-teal?style=flat-square&logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/License-GPL--3.0-orange?style=flat-square" alt="License"/>
</p>

---

## Overview

VyOS Manager is a modern, full-featured web interface for managing VyOS routers at scale. Built with a robust FastAPI backend and a responsive Next.js frontend, it provides enterprise-grade capabilities for network administrators managing single routers or entire fleets.

### Why VyOS Manager?

- **Multi-Instance Management** — Manage dozens of VyOS routers from a single interface
- **Version-Aware** — Full support for VyOS 1.4 LTS and 1.5 Rolling releases
- **Enterprise Security** — RBAC, encrypted credentials, audit logging, CSRF protection
- **Modern UX** — Responsive design, dark mode, real-time updates
- **Production-Ready** — Redis caching, background tasks, comprehensive monitoring

---

## Features

### Network Configuration

| Category | Features |
|----------|----------|
| **Interfaces** | Ethernet, VLAN, Bonding (LACP/802.3ad), Bridge, Tunnel (GRE/IPIP/SIT), VXLAN, Dummy/Loopback, WireGuard |
| **Routing Protocols** | BGP (IPv4/IPv6, EVPN), OSPF/OSPFv3, IS-IS, RIP/RIPng, Babel, OpenFabric |
| **VPN** | IPsec (Site-to-Site, IKEv1/IKEv2), OpenVPN (Server/Client/Site-to-Site), WireGuard |
| **Firewall** | IPv4/IPv6 Rules, Zone-Based Firewall, Address/Network/Port Groups, Global Options |
| **NAT** | Source NAT, Destination NAT, Static NAT, NAT66 (IPv6) |
| **High Availability** | VRRP, Connection Tracking Sync |
| **Policy** | Route Maps, Prefix Lists, Access Lists, AS Path Lists, Community Lists |

### System Management

| Category | Features |
|----------|----------|
| **Services** | DNS Forwarding, NTP, SSH, DHCP Server, DHCP Relay |
| **Configuration** | Backup/Restore, Config Diff, Configuration Templates, Batch Operations |
| **Monitoring** | System Metrics (CPU/Memory/Disk), Interface Traffic, Connection Tracking, Alerting Engine |
| **Logs** | System Logs, Boot Logs, Log Search, Process Filtering |
| **Power** | Reboot, Shutdown, Scheduled Power Actions |

### Security & Access Control

| Feature | Description |
|---------|-------------|
| **Authentication** | JWT-based with refresh tokens, session management |
| **Authorization** | Role-based access (Owner/Admin/Viewer) per site |
| **Encryption** | AES-256 encryption for stored API keys (Fernet) |
| **CSRF Protection** | Token-based protection for all state-changing operations |
| **Rate Limiting** | Distributed rate limiting via Redis |
| **Audit Logging** | Comprehensive logging of configuration changes |
| **Security Headers** | CSP, X-Frame-Options, HSTS support |

---

## Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended)
- OR **Node.js 20+** and **Python 3.11+** (manual setup)
- **VyOS Router** with REST API enabled

### Step 1: Enable VyOS REST API

```bash
configure
set service https api keys id vymanager key YOUR_SECURE_API_KEY
set service https api rest
commit
save
exit
```

### Step 2: Configure Environment

```bash
# Clone the repository
git clone https://github.com/ashimov/VyManager.git
cd VyManager

# Copy environment files
cp frontend/.env.example frontend/.env
cp backend/.env.example backend/.env
```

**Frontend `.env`:**
```env
BETTER_AUTH_SECRET=your-super-secret-key-change-in-production
DATABASE_URL=postgresql://vymanager:vymanager@postgres:5432/vymanager_auth
NEXT_PUBLIC_API_URL=http://backend:8000
```

**Backend `.env`:**
```env
DATABASE_URL=postgresql://vymanager:vymanager@postgres:5432/vymanager_auth
FRONTEND_URL=http://localhost:3000
REDIS_URL=redis://redis:6379/0

# Production only (required)
ENVIRONMENT=development
ENCRYPTION_KEY=  # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
JWT_SECRET=your-jwt-secret
```

### Step 3: Deploy

```bash
docker compose up -d
```

### Step 4: Setup Wizard

1. Open `http://localhost:3000`
2. Create admin account
3. Add your first site and VyOS instance
4. Start managing!

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         VyOS Manager                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Frontend   │    │   Backend    │    │    Redis     │      │
│  │   (Next.js)  │───▶│  (FastAPI)   │───▶│   (Cache)    │      │
│  │   Port 3000  │    │   Port 8000  │    │   Port 6379  │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                                    │
│         │                   │                                    │
│         ▼                   ▼                                    │
│  ┌──────────────┐    ┌──────────────┐                          │
│  │  PostgreSQL  │    │ VyOS Devices │                          │
│  │  (Database)  │    │  (REST API)  │                          │
│  │   Port 5432  │    │   Port 443   │                          │
│  └──────────────┘    └──────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Backend Architecture

```
Request → Middleware Stack → Router → Builder → Mapper → VyOS Device
              │                                    │
              ├─ Authentication                    ├─ VyOS 1.4 Commands
              ├─ CSRF Protection                   └─ VyOS 1.5 Commands
              ├─ Rate Limiting
              └─ Session Resolution
```

### Database Schema

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Users    │────▶│ Permissions │◀────│    Sites    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Sessions   │     │  Instances  │
                    └─────────────┘     └─────────────┘
                                               │
                                               ▼
                    ┌─────────────┐     ┌─────────────┐
                    │ AlertRules  │     │  Backups    │
                    └─────────────┘     └─────────────┘
```

---

## Project Structure

```
VyManager/
├── frontend/                    # Next.js 14 Application
│   ├── src/
│   │   ├── app/                # App Router pages
│   │   │   ├── dashboard/      # Main dashboard
│   │   │   ├── network/        # Network configuration
│   │   │   ├── firewall/       # Firewall management
│   │   │   ├── routing/        # Routing protocols
│   │   │   ├── vpn/            # VPN configuration
│   │   │   ├── system/         # System settings
│   │   │   └── monitoring/     # Monitoring & alerts
│   │   ├── components/         # React components
│   │   │   ├── ui/             # shadcn/ui components
│   │   │   ├── layout/         # Layout components
│   │   │   ├── routing/        # Protocol panels
│   │   │   ├── firewall/       # Firewall components
│   │   │   └── vpn/            # VPN components
│   │   └── lib/
│   │       ├── api/            # API service clients
│   │       └── store/          # Zustand stores
│   └── prisma/                 # Database schema
│
├── backend/                     # FastAPI Application
│   ├── routers/                # API endpoints
│   │   ├── interfaces/         # Interface management
│   │   ├── protocols/          # Routing protocols
│   │   ├── firewall/           # Firewall configuration
│   │   ├── vpn/                # VPN management
│   │   ├── services/           # System services
│   │   ├── monitoring/         # Metrics & alerts
│   │   └── config/             # Config management
│   ├── vyos_mappers/           # Version-specific mappers
│   │   ├── interfaces/         # Interface mappers
│   │   ├── protocols/          # Protocol mappers
│   │   └── services/           # Service mappers
│   ├── middleware/             # Request middleware
│   │   ├── auth.py             # Authentication
│   │   ├── csrf.py             # CSRF protection
│   │   ├── rate_limit.py       # Rate limiting
│   │   └── security_headers.py # Security headers
│   └── services/               # Core services
│       ├── encryption.py       # Credential encryption
│       ├── cache.py            # Redis caching
│       └── alert_engine.py     # Alert evaluation
│
└── docker-compose.yml          # Container orchestration
```

---

## Configuration

### Environment Variables

#### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `FRONTEND_URL` | Yes | - | Frontend URL for CORS |
| `REDIS_URL` | Recommended | `redis://localhost:6379/0` | Redis connection string |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `ENCRYPTION_KEY` | Production | - | Fernet key for credential encryption |
| `JWT_SECRET` | Production | - | Secret for JWT signing |
| `LOG_LEVEL` | No | `DEBUG`/`INFO` | Logging level |
| `SESSION_INACTIVITY_TIMEOUT` | No | `30` | Session timeout in minutes |
| `ALERT_ENGINE_INTERVAL` | No | `30` | Alert evaluation interval in seconds |

#### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `BETTER_AUTH_SECRET` | Yes | - | Authentication secret |
| `NEXT_PUBLIC_API_URL` | Yes | - | Backend API URL |
| `NEXT_PUBLIC_APP_URL` | No | - | Application URL |
| `TRUSTED_ORIGINS` | No | - | Comma-separated allowed origins |

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Generate and set `ENCRYPTION_KEY`
- [ ] Generate and set `JWT_SECRET`
- [ ] Change default database password
- [ ] Configure `REDIS_URL` for distributed rate limiting
- [ ] Enable HTTPS with valid certificates
- [ ] Set `ENABLE_HSTS=true` for HSTS headers
- [ ] Configure backup strategy for PostgreSQL

---

## API Documentation

### Interactive Documentation

When running, access API docs at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /session/connect` | Connect to VyOS instance |
| `GET /vyos/interfaces/ethernet/config` | Get ethernet interfaces |
| `GET /vyos/protocols/bgp/config` | Get BGP configuration |
| `POST /vyos/firewall/ipv4/rules` | Create firewall rule |
| `GET /monitoring/metrics/system` | Get system metrics |
| `POST /vyos/config/backup` | Create configuration backup |

### Version-Aware Capabilities

Each feature exposes capabilities:

```json
GET /vyos/protocols/bgp/capabilities

{
  "version": "1.5",
  "features": {
    "evpn": { "supported": true },
    "flowspec": { "supported": true },
    "segment_routing": { "supported": false }
  }
}
```

---

## Development

### Frontend Development

```bash
cd frontend
npm install
npm run dev          # Development server
npm run build        # Production build
npm run lint         # Run ESLint
npm run type-check   # TypeScript check
```

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Database Migrations

```bash
cd frontend
npx prisma migrate dev --name migration_name
npx prisma migrate deploy
npx prisma studio    # Database GUI
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests (if configured)
cd frontend
npm test
```

---

## Deployment

### Docker Compose (Recommended)

```bash
# Development
docker compose up -d

# Production
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Manual Deployment

1. **Database**: Deploy PostgreSQL 15+
2. **Cache**: Deploy Redis 7+
3. **Backend**: Run with Gunicorn/Uvicorn behind Nginx
4. **Frontend**: Build and serve with Node.js or static export

### Nginx Configuration

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:3000;
}

server {
    listen 443 ssl http2;
    server_name vymanager.example.com;

    ssl_certificate /etc/ssl/certs/vymanager.crt;
    ssl_certificate_key /etc/ssl/private/vymanager.key;

    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Troubleshooting

### Connection Issues

| Problem | Solution |
|---------|----------|
| Cannot connect to VyOS | Verify API key, check network connectivity, ensure port 443 is open |
| SSL certificate errors | Set "Verify SSL" to false for self-signed certificates |
| Authentication failed | Check if API key matches VyOS configuration |

### Database Issues

```bash
# Check PostgreSQL status
docker compose ps postgres

# View database logs
docker compose logs postgres

# Reset database (development only)
docker compose down -v
docker compose up -d
```

### Backend Issues

```bash
# Check backend logs
docker compose logs backend

# Restart backend
docker compose restart backend

# Check environment variables
docker compose exec backend env | grep -E "(DATABASE|REDIS|ENCRYPTION)"
```

### Frontend Issues

```bash
# Clear build cache
cd frontend
rm -rf .next node_modules
npm install
npm run build
```

---

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Follow existing code patterns and architecture
4. Test on both VyOS 1.4 and 1.5
5. Commit with conventional commits: `git commit -m 'feat: add amazing feature'`
6. Push and open a Pull Request

### Code Style

- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Use strict mode, prefer interfaces over types
- **Commits**: Use [Conventional Commits](https://conventionalcommits.org/)

---

## Security

### Reporting Vulnerabilities

Please report security vulnerabilities privately via email or GitHub Security Advisories. Do not open public issues for security concerns.

### Security Features

- All API keys encrypted at rest (AES-256)
- CSRF protection on all state-changing endpoints
- Rate limiting to prevent brute force attacks
- Session timeout and cleanup
- Audit logging for compliance

---

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

## Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/ashimov/VyManager/issues)
- **Documentation**: Check the `docs/` directory

---

## Acknowledgments

- [VyOS Project](https://vyos.io/) for the amazing open-source router platform
- [shadcn/ui](https://ui.shadcn.com/) for the beautiful UI components
- [FastAPI](https://fastapi.tiangolo.com/) for the high-performance API framework
- All contributors who make this project possible

---

<p align="center">
  <strong>Built with love for the VyOS community</strong>
</p>

<p align="center">
  <a href="https://github.com/ashimov/VyManager/stargazers">
    Give us a star on GitHub
  </a>
</p>
