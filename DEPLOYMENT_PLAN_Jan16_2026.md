# Hercules SFMS - Production Deployment Plan
**Date**: January 16, 2026  
**Version**: 1.0  
**Status**: Pre-Production

---

# Table of Contents
1. [Pre-Deployment Checklist](#1-pre-deployment-checklist)
2. [Phase 1: Environment Setup](#2-phase-1-environment-setup)
3. [Phase 2: Application Security](#3-phase-2-application-security)
4. [Phase 3: Production Server Setup](#4-phase-3-production-server-setup)
5. [Phase 4: Cybersecurity Hardening](#5-phase-4-cybersecurity-hardening)
6. [Phase 5: Turning Into a Production App](#6-phase-5-turning-into-a-production-app)
7. [Phase 6: Multi-User & Role-Based Access Control](#7-phase-6-multi-user--role-based-access-control)
8. [Post-Deployment Tasks](#8-post-deployment-tasks)
9. [Maintenance Schedule](#9-maintenance-schedule)
10. [Quick Reference Commands](#10-quick-reference-commands)
11. [Troubleshooting](#11-troubleshooting)

---

# 1. Pre-Deployment Checklist

## 1.1 Critical Bug Fixes (Must Complete First)

| # | Bug | File | Status |
|---|-----|------|--------|
| 1 | DM water values treated as totalizers (should be summed) | `scale_service.py` | ⬜ Pending |
| 2 | `/scada/readings` returns only WG HI (should concat HI+LO) | `scada_routes.py` | ⬜ Pending |
| 3 | Palletizers not included in reset prefixes | `scada_routes.py` | ⬜ Pending |

## 1.2 Files to Transfer

```
C3381_Sap/
├── backend/                 # Flask application
│   ├── app.py              # Main entry point
│   ├── database.py         # DB configuration
│   ├── requirements.txt    # Python dependencies
│   ├── routes/             # API endpoints
│   ├── services/           # Business logic
│   ├── models/             # SQLAlchemy models
│   ├── utils/              # Utilities
│   └── public/             # Built React frontend
├── Frontend/client/         # React source (for future changes)
├── scada-emulator/          # ONLY for testing (do not deploy)
└── demo_sap_server.py       # ONLY for testing (do not deploy)
```

## 1.3 Production Environment Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **OS** | Windows Server 2019+ | Current setup |
| **Python** | 3.10+ | With pip |
| **PostgreSQL** | 14+ | Local or remote |
| **SQL Server** | 2019+ | SCADA database |
| **Network** | VPN to SAP | Required for online mode |
| **Ports** | 5000 (app), 5432 (PostgreSQL) | Firewall rules |

---

# 2. Phase 1: Environment Setup

## 2.1 Install Python Dependencies

```powershell
cd C:\Hercules\backend
pip install -r requirements.txt
pip install waitress  # Production WSGI server
pip install python-dotenv  # Environment variable support
```

## 2.2 Create Environment Configuration

Create file: `C:\Hercules\backend\.env`

```ini
# === SECURITY (REQUIRED - CHANGE THESE) ===
JWT_SECRET=<generate-64-char-random-string>
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"

# === DATABASE ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sap
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-secure-password>

MSSQL_HOST=localhost
MSSQL_DB=HerculesV2
MSSQL_USER=Hercules
MSSQL_PASSWORD=<your-secure-password>

# === SAP ===
SAP_USERNAME=99999
SAP_PASSWORD=<your-sap-password>
SAP_BASE_URL=https://vhmioqs4ci.sap.mc3.com.sa:44300
SAP_CLIENT=250

# === MODE ===
MOCK_SAP_MODE=false
USE_SCADA_EMULATOR=false

# === LOGGING ===
LOG_LEVEL=INFO
LOG_FILE=C:\Hercules\logs\hercules.log
```

## 2.3 Create Required Directories

```powershell
mkdir C:\Hercules\logs
mkdir C:\Hercules\backups
```

---

# 3. Phase 2: Application Security

## 3.1 Security Fixes Required

### Fix 1: Move JWT Secret to Environment Variable

**File**: `backend/services/auth_service.py`

```python
# BEFORE (Line 20) - INSECURE:
JWT_SECRET = "hercules_sfms_secret_key_2024"

# AFTER:
import os
from dotenv import load_dotenv
load_dotenv()

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is required")
```

### Fix 2: Move Database Passwords to Environment Variables

**File**: `backend/database.py`

```python
# BEFORE - INSECURE:
mssql_connection_string = "mssql+pyodbc://Hercules:nl6oUpr@localhost/HerculesV2..."
postgres_engine = create_engine("postgresql+psycopg2://postgres:Hercules@localhost:5432/sap")

# AFTER:
import os
from dotenv import load_dotenv
load_dotenv()

mssql_connection_string = (
    f"mssql+pyodbc://{os.environ['MSSQL_USER']}:{os.environ['MSSQL_PASSWORD']}"
    f"@{os.environ['MSSQL_HOST']}/{os.environ['MSSQL_DB']}"
    "?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
)

postgres_engine = create_engine(
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
)
```

### Fix 3: Enable SSL Verification (when certs available)

**File**: `backend/utils/vpn_check.py` and `backend/services/sap_confirmation.py`

```python
# BEFORE - INSECURE:
response = requests.get(url, verify=False, ...)

# AFTER (when SAP CA cert is available):
SAP_CA_CERT = os.environ.get("SAP_CA_CERT_PATH", False)
response = requests.get(url, verify=SAP_CA_CERT, ...)
```

### Fix 4: Add Security Headers

**File**: `backend/app.py` (add after `create_app()`)

```python
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

### Fix 5: Add Rate Limiting

**Install**: `pip install flask-limiter`

**File**: `backend/app.py`

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri="memory://"
)

def create_app():
    app = Flask(__name__)
    limiter.init_app(app)
    # ... rest of setup
```

**File**: `backend/routes/auth_routes.py`

```python
from app import limiter

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")  # Prevent brute force
def login():
    # ... existing code
```

## 3.2 Security Checklist

| Item | Status | Priority |
|------|--------|----------|
| JWT secret in environment variable | ⬜ | Critical |
| Database passwords in environment variable | ⬜ | Critical |
| Security headers added | ⬜ | High |
| Rate limiting on login | ⬜ | High |
| CORS restricted to production domain | ⬜ | High |
| SSL verification enabled | ⬜ | Medium (when certs ready) |
| Audit logging enabled | ⬜ | Medium |

---

# 4. Phase 3: Production Server Setup

## 4.1 Stop Using Flask Development Server

**NEVER run in production:**
```python
# DO NOT USE IN PRODUCTION:
app.run(debug=True)
```

## 4.2 Use Waitress (Windows Production Server)

### Option A: Run Directly

```powershell
cd C:\Hercules\backend
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 app:app
```

### Option B: Create Windows Service (Recommended)

**Step 1**: Install NSSM (Non-Sucking Service Manager)
```powershell
# Download from https://nssm.cc/download
# Extract to C:\nssm\
```

**Step 2**: Create the service
```powershell
C:\nssm\nssm.exe install HerculesBackend

# Configure in GUI:
# Path: C:\Python310\python.exe
# Startup directory: C:\Hercules\backend
# Arguments: -m waitress --host=0.0.0.0 --port=5000 --threads=4 app:app
```

**Step 3**: Configure service properties
```powershell
C:\nssm\nssm.exe set HerculesBackend AppDirectory C:\Hercules\backend
C:\nssm\nssm.exe set HerculesBackend AppEnvironmentExtra "PATH=C:\Python310;C:\Python310\Scripts"
C:\nssm\nssm.exe set HerculesBackend DisplayName "Hercules SFMS Backend"
C:\nssm\nssm.exe set HerculesBackend Description "Hercules Shop Floor Management System"
C:\nssm\nssm.exe set HerculesBackend Start SERVICE_AUTO_START
```

**Step 4**: Start the service
```powershell
net start HerculesBackend
```

## 4.3 Create Startup Script

Create file: `C:\Hercules\start_hercules.bat`

```batch
@echo off
echo Starting Hercules SFMS...

cd /d C:\Hercules\backend

REM Load environment variables
for /f "tokens=*" %%a in (.env) do set %%a

REM Start with Waitress
python -m waitress --host=0.0.0.0 --port=5000 --threads=4 app:app

pause
```

## 4.4 Build Frontend for Production

```powershell
cd C:\Hercules\Frontend\client

# Install dependencies if not already
npm install

# Build production bundle
npm run build

# Output automatically goes to backend/public/
```

---

# 5. Phase 4: Cybersecurity Hardening

## 5.1 Network Security

| Layer | Configuration |
|-------|---------------|
| **Windows Firewall** | Allow inbound: 5000 (HTTP), block 5432 (PostgreSQL external) |
| **VPN** | Required for SAP communication |
| **Internal Network** | Restrict access to authorized IPs only |

### Firewall Rules (PowerShell)

```powershell
# Allow Hercules app
New-NetFirewallRule -DisplayName "Hercules SFMS" -Direction Inbound -Port 5000 -Protocol TCP -Action Allow

# Block external PostgreSQL access
New-NetFirewallRule -DisplayName "Block PostgreSQL External" -Direction Inbound -Port 5432 -Protocol TCP -Action Block -RemoteAddress Any
```

## 5.2 HTTPS Setup (Recommended)

### Option A: Use IIS as Reverse Proxy

1. Install IIS with URL Rewrite and ARR modules
2. Create SSL certificate (or use internal CA)
3. Configure reverse proxy to localhost:5000

### Option B: Use nginx for Windows

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name hercules.company.local;
    
    ssl_certificate     C:/Hercules/certs/hercules.crt;
    ssl_certificate_key C:/Hercules/certs/hercules.key;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 5.3 Database Security

### PostgreSQL

```sql
-- Change default passwords
ALTER USER postgres WITH PASSWORD 'new-strong-password';

-- Create application-specific user with limited privileges
CREATE USER hercules_app WITH PASSWORD 'app-password';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hercules_app;
```

### SQL Server

```sql
-- Ensure Hercules user has minimal required permissions
USE HerculesV2;
GRANT SELECT ON [dbo].[ASMArchive_DB5] TO Hercules;
-- Deny write access to SCADA tables (read-only)
DENY INSERT, UPDATE, DELETE ON [dbo].[ASMArchive_DB5] TO Hercules;
```

## 5.4 Audit Logging

Add to `backend/app.py`:

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler(
        'logs/hercules.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Hercules SFMS startup')
```

---

# 6. Phase 5: Turning Into a Production App

## 6.1 Production Readiness Checklist

| Category | Item | Status |
|----------|------|--------|
| **Deployment** | Using WSGI server (Waitress) | ⬜ |
| **Deployment** | Windows Service configured | ⬜ |
| **Deployment** | Auto-start on boot | ⬜ |
| **Security** | Secrets in environment variables | ⬜ |
| **Security** | Security headers enabled | ⬜ |
| **Security** | Rate limiting enabled | ⬜ |
| **Security** | HTTPS enabled | ⬜ |
| **Reliability** | Health check endpoint | ✅ `/api/health` |
| **Reliability** | Logging to file with rotation | ⬜ |
| **Reliability** | Database backups scheduled | ⬜ |
| **Monitoring** | Error alerting (email/SMS) | ⬜ |

## 6.2 Creating Windows Executable

### Option A: Use Existing Build

An `.exe` already exists at:
```
backend/dist/app/app.exe
backend/dist/app.exe
```

To run:
```powershell
cd C:\Hercules\backend\dist\app
.\app.exe
```

### Option B: Rebuild After Code Changes

```powershell
cd C:\Hercules\backend

# Install PyInstaller
pip install pyinstaller

# Create executable (folder with dependencies)
pyinstaller --onedir --add-data "public;public" --add-data "config;config" --name HerculesSFMS app.py

# OR single file executable (slower startup)
pyinstaller --onefile --add-data "public;public" --add-data "config;config" --name HerculesSFMS app.py

# Output in dist/HerculesSFMS/
```

### Important: .exe Still Requires

| Requirement | Notes |
|-------------|-------|
| `.env` file | Must be in same directory as .exe |
| PostgreSQL | Must be running and accessible |
| SQL Server | SCADA database must be accessible |
| Network/VPN | For SAP communication (unless demo mode) |

### .exe vs Windows Service

| Feature | .exe (PyInstaller) | Windows Service |
|---------|-------------------|-----------------|
| Auto-start on boot | ❌ No | ✅ Yes |
| Runs in background | ❌ No (console window) | ✅ Yes |
| Easy updates | ❌ Rebuild required | ✅ Restart service |
| No Python needed | ✅ Yes | ❌ Requires Python |
| Distribution | ✅ Copy folder | ⚠️ Requires setup |

**Recommendation**: 
- **Production server** → Windows Service
- **Portable/demo use** → .exe

## 6.3 Protection Summary

### What's Protected Automatically (After Deployment Plan)

| Protection | How It Works |
|------------|--------------|
| **User Authentication** | JWT tokens required for API access |
| **Password Security** | bcrypt hashing (cannot be reversed) |
| **Secrets Hidden** | In `.env` file, not in source code |
| **Network Security** | Firewall rules, HTTPS via proxy |
| **Database Security** | Credentials in environment variables |

### What Requires Code Implementation (Section 7)

| Protection | Current Status | Action Required |
|------------|----------------|-----------------|
| **RBAC Route Protection** | ❌ Only 2/15 routes | Add `@require_permission` decorators |
| **Rate Limiting** | ❌ Not implemented | Add Flask-Limiter |
| **Operator Restrictions** | ❌ Can access admin API | Protect critical routes |

### Final Security State After Full Implementation

| User Role | Can Access |
|-----------|------------|
| **Admin** | Everything |
| **Manager** | Orders, confirmations, mappings, logs |
| **Operator** | Orders, confirmations only |
| **Guest** | View only (no actions) |

**⚠️ The system is NOT fully protected until Section 7 (RBAC) is implemented.**

## 6.4 Final Folder Structure

```
C:\Hercules\
├── backend\
│   ├── app.py
│   ├── .env                 # Environment variables (NOT in git)
│   ├── public\              # Built React frontend
│   └── logs\                # Application logs
├── certs\                   # SSL certificates
├── backups\                 # Database backups
├── start_hercules.bat       # Manual start script
└── README.md                # Operations documentation
```

---

# 7. Post-Deployment Tasks

## 7.1 Verify Deployment

| Check | Command/Action | Expected Result |
|-------|----------------|-----------------|
| Service running | `sc query HerculesBackend` | RUNNING |
| App accessible | Browse `http://localhost:5000` | Login page |
| Health check | `curl http://localhost:5000/api/health` | `{"status": "ok"}` |
| SAP connection | Test order pull | Orders retrieved |
| SCADA connection | Check live monitor | Data updating |
| Login works | Test admin login | JWT token issued |

## 7.2 Initial Configuration

1. **Change default admin password** immediately
2. **Configure shift times** in Admin page
3. **Verify mappings** (material, palletizer, milling versions)
4. **Test offline mode** by disconnecting VPN

## 7.3 User Training

- Train operators on order validation workflow
- Train supervisors on reports and logs
- Document emergency procedures (offline mode, manual confirmation)

---

# 8. Maintenance Schedule

## 8.1 Daily Tasks

| Task | Action |
|------|--------|
| Log review | Check `logs/hercules.log` for errors |
| Offline queue | Process any pending offline confirmations |

## 8.2 Weekly Tasks

| Task | Action |
|------|--------|
| Backup verification | Verify PostgreSQL backups are running |
| Performance check | Review response times, worker performance |
| Security review | Check for failed login attempts |

## 8.3 Monthly Tasks

| Task | Action |
|------|--------|
| Dependency updates | `pip list --outdated` and update |
| Log cleanup | Archive old logs (>30 days) |
| Database maintenance | `VACUUM ANALYZE` on PostgreSQL |

## 8.4 Backup Script

Create file: `C:\Hercules\backup_db.bat`

```batch
@echo off
set BACKUP_DIR=C:\Hercules\backups
set DATE=%date:~-4%%date:~3,2%%date:~0,2%

echo Backing up PostgreSQL...
"C:\Program Files\PostgreSQL\14\bin\pg_dump" -U postgres -F c sap > "%BACKUP_DIR%\sap_%DATE%.backup"

echo Backup complete: %BACKUP_DIR%\sap_%DATE%.backup

REM Delete backups older than 30 days
forfiles /p "%BACKUP_DIR%" /s /m *.backup /d -30 /c "cmd /c del @path" 2>nul
```

Schedule with Task Scheduler to run daily at 2:00 AM.

---

# 9. Quick Reference Commands

```powershell
# Start service
net start HerculesBackend

# Stop service
net stop HerculesBackend

# Restart service
net stop HerculesBackend && net start HerculesBackend

# View logs
Get-Content C:\Hercules\logs\hercules.log -Tail 100

# Check service status
sc query HerculesBackend

# Test health
Invoke-RestMethod http://localhost:5000/api/health
```

---

# 7. Phase 6: Multi-User & Role-Based Access Control

## 7.1 Current RBAC Status

### What's Already Implemented ✅

| Component | Status | Details |
|-----------|--------|---------|
| **User/Role Tables** | ✅ Complete | `users`, `roles`, `user_roles` in PostgreSQL |
| **4 Role Levels** | ✅ Defined | admin, manager, operator, guest |
| **JWT Authentication** | ✅ Working | Token-based auth with bcrypt password hashing |
| **Auth Decorators** | ✅ Available | `@require_auth`, `@require_role`, `@require_permission` |
| **Frontend AuthContext** | ✅ Implemented | `hasPermission()`, `hasRole()` in components |

### Current Permission Matrix

| Permission | Admin | Manager | Operator | Guest |
|------------|-------|---------|----------|-------|
| `view_sync_interval` | ✅ | ✅ | ✅ | ❌ |
| `change_sync_interval` | ✅ | ✅ | ❌ | ❌ |
| `view_all_data` | ✅ | ✅ | ❌ | ❌ |
| `manage_users` | ✅ | ❌ | ❌ | ❌ |
| `system_admin` | ✅ | ❌ | ❌ | ❌ |

## 7.2 Critical Gap: Unprotected Routes ❌

| Route Category | Currently Protected? | Risk Level |
|----------------|---------------------|------------|
| `/api/sync-interval/*` | ✅ Yes | Low |
| `/api/auth/*` (user management) | ✅ Yes | Low |
| **`/api/orders/*`** (confirmations) | ❌ **NO** | 🔴 Critical |
| **`/scada/reset`** (zero scales) | ❌ **NO** | 🔴 Critical |
| **`/api/mappings/*`** (material/version) | ❌ **NO** | 🔴 Critical |
| **`/api/offline/*`** (re-push orders) | ❌ **NO** | 🔴 Critical |
| `/api/kpi/*` (KPI data) | ❌ NO | ⚠️ Medium |
| `/api/reports/*` (reports) | ❌ NO | ⚠️ Medium |

**⚠️ WARNING**: Only 2 out of 15+ blueprints are protected! Operators can currently access admin features via direct API calls.

## 7.3 Required Fixes

### Step 1: Add New Permissions

**File**: `backend/models/user_roles.py`

```python
PERMISSIONS = {
    'admin': {
        'view_sync_interval': True,
        'change_sync_interval': True,
        'view_all_data': True,
        'manage_users': True,
        'system_admin': True,
        # NEW PERMISSIONS:
        'confirm_orders': True,
        'reset_scada': True,
        'manage_mappings': True,
        'push_offline': True,
        'delete_orders': True,
        'view_logs': True,
    },
    'manager': {
        'view_sync_interval': True,
        'change_sync_interval': True,
        'view_all_data': True,
        'manage_users': False,
        'system_admin': False,
        # NEW:
        'confirm_orders': True,
        'reset_scada': True,
        'manage_mappings': True,
        'push_offline': True,
        'delete_orders': False,
        'view_logs': True,
    },
    'operator': {
        'view_sync_interval': True,
        'change_sync_interval': False,
        'view_all_data': False,
        'manage_users': False,
        'system_admin': False,
        # NEW - Limited access:
        'confirm_orders': True,   # Can confirm orders
        'reset_scada': False,     # Cannot reset scales
        'manage_mappings': False, # Cannot change mappings
        'push_offline': False,    # Cannot re-push offline
        'delete_orders': False,
        'view_logs': False,
    },
    'guest': {
        'view_sync_interval': False,
        'change_sync_interval': False,
        'view_all_data': False,
        'manage_users': False,
        'system_admin': False,
        # NEW - View only:
        'confirm_orders': False,
        'reset_scada': False,
        'manage_mappings': False,
        'push_offline': False,
        'delete_orders': False,
        'view_logs': False,
    }
}
```

### Step 2: Protect Critical Routes

**File**: `backend/routes/scada_routes.py`
```python
from services.auth_service import require_permission

@scada_bp.route("/scada/reset", methods=["POST"])
@require_permission('reset_scada')  # ADD THIS LINE
def reset_scada_to_zero():
    # ... existing code
```

**File**: `backend/routes/process_orders.py`
```python
from services.auth_service import require_permission

@process_orders_bp.route("/orders/<order_id>/confirm", methods=["POST"])
@require_permission('confirm_orders')  # ADD THIS LINE
def confirm_order(order_id):
    # ... existing code
```

**File**: `backend/routes/offline_confirmations.py`
```python
from services.auth_service import require_permission

@offline_bp.route("/send", methods=["POST"])
@require_permission('push_offline')  # ADD THIS LINE
def send_offline_confirmations():
    # ... existing code
```

**File**: `backend/routes/milling_routes.py`
```python
from services.auth_service import require_permission

@milling_bp.route("/mappings", methods=["POST"])
@require_permission('manage_mappings')  # ADD THIS LINE
def create_mapping():
    # ...

@milling_bp.route("/mappings/<id>", methods=["DELETE"])
@require_permission('manage_mappings')  # ADD THIS LINE
def delete_mapping(id):
    # ...
```

### Step 3: Add Auth Decorators to All Routes

Add `@require_auth` to all routes that should require login:

```python
from services.auth_service import require_auth

@kpi_bp.route("/kpi/latest", methods=["GET"])
@require_auth  # Requires login but no specific permission
def get_latest_kpi():
    # ...
```

## 7.4 Role-Based UI Features

### What Operators Should See
- ✅ Dashboard (view only)
- ✅ Order list and details
- ✅ Order confirmation (their assigned orders)
- ❌ SCADA reset button (hidden)
- ❌ Mapping management (hidden)
- ❌ User management (hidden)
- ❌ Sync interval settings (view only, no edit)

### What Admins Should See
- ✅ Everything operators see
- ✅ SCADA reset functionality
- ✅ Mapping management (material, version, palletizer)
- ✅ User management
- ✅ Sync interval settings (full control)
- ✅ System logs
- ✅ Offline order re-push

## 7.5 Default Users

| Username | Password | Role | Purpose |
|----------|----------|------|---------|
| `admin` | `admin123` | admin | System administrator |
| (create) | (set) | operator | Floor operators |
| (create) | (set) | manager | Shift supervisors |

**⚠️ IMPORTANT**: Change default admin password immediately after deployment!

## 7.6 RBAC Implementation Checklist

| Task | File | Status |
|------|------|--------|
| Add new permissions to PERMISSIONS dict | `models/user_roles.py` | ⬜ Pending |
| Protect `/scada/reset` | `routes/scada_routes.py` | ⬜ Pending |
| Protect order confirmation routes | `routes/process_orders.py` | ⬜ Pending |
| Protect offline push routes | `routes/offline_confirmations.py` | ⬜ Pending |
| Protect mapping routes | `routes/milling_routes.py` | ⬜ Pending |
| Protect palletizer mapping | `routes/palletizer_routes.py` | ⬜ Pending |
| Add `@require_auth` to KPI routes | `routes/kpi_routes.py` | ⬜ Pending |
| Add `@require_auth` to report routes | `routes/reports.py` | ⬜ Pending |
| Test all roles via API | - | ⬜ Pending |
| Create operator test user | - | ⬜ Pending |
| Change default admin password | - | ⬜ Pending |

---

# 11. Troubleshooting

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Service won't start | Missing .env file | Create .env with required variables |
| Database connection failed | Wrong password in .env | Verify credentials |
| SAP orders not pulling | VPN disconnected | Check VPN connection |
| Login fails | JWT_SECRET not set | Check .env file |
| SCADA data not updating | SQL Server connection | Verify MSSQL credentials |
| Slow performance | Worker running every 1s | Increase to 5-10s |
| Permission denied (403) | User lacks required role | Check user roles in database |
| Token expired | JWT token > 24 hours old | Re-login to get new token |

---

**Document Version**: 1.1  
**Last Updated**: January 16, 2026  
**Author**: Hercules Development Team
