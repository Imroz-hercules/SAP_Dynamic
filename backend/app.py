# # backend/app.py
# import sys
# import os
# from flask import Flask, send_from_directory
# from flask_cors import CORS
# from sqlalchemy import text

# # Ensure backend/ is in sys.path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# # --- Blueprints (API routes) ---
# from routes.kpi_routes import kpi_bp
# from routes.material_routes import material_bp
# from routes.order_validation import orders_bp
# from routes.dev_seed import dev_bp
# from routes.process_orders import process_orders_bp
# from routes.scada_routes import scada_bp
# from routes.reports_routes import reports_bp
# from routes.sap_sync import sap_sync_bp
# from routes.system_logs import system_logs_bp
# from routes.auth_routes import auth_bp
# from routes.sync_interval_routes import sync_interval_bp
# from routes.shifts import shifts_bp
# from routes.milling_mapping_routes import milling_bp
# from services.sync_scheduler import start_sync_scheduler

# # --- DB engines / Base ---
# from database import engine as mssql_engine, postgres_engine, PostgresBase
# from models.kpi_model import Base as KpiBase
# from models.material_model import Base as MaterialBase
# from models.order_validation import Base as OrderValidation
# from models.order_model import Base as OrderBase
# from models.shift_report import ShiftReport, DailySummary
# from models.shift_master import ShiftMaster

# # --- New KPI Snapshot tables ---
# from models.milling_kpi_snapshot import create_milling_kpi_schema
# from models.packing_kpi_snapshot import create_packing_kpi_schema
# from models.process_order import create_process_order_schema
# from models.process_order_pg import create_process_order_pg_schema

# # --- KPI Send Tracking (for incremental sends) ---
# from models.kpi_send_tracking import KpiSendTracking  # Import to ensure table is created

# # --- SCADA / SAP services ---
# from services.create_scada_table import create_scada_schema
# from services.process_order_sync import sync_process_orders

# # --- Scheduler ---
# from app_scheduler import start_scheduler

# # --- Auto Validator background worker ---
# from services.auto_validator import auto_validator

# # --- Database initialization ---
# from init_sync_settings import init_default_sync_settings


# def check_table_exists(engine, table_name):
#     """Check if a table exists in the database"""
#     try:
#         with engine.connect() as conn:
#             result = conn.execute(text(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table_name}'"))
#             return result.scalar() > 0
#     except:
#         return False

# def check_postgres_table_exists(engine, table_name):
#     """Check if a table exists in PostgreSQL database"""
#     try:
#         with engine.connect() as conn:
#             result = conn.execute(text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"))
#             return result.scalar() > 0
#     except:
#         return False

# def check_any_tables_exist(engine, table_names, is_postgres=False):
#     """Check if any of the specified tables exist in the database"""
#     try:
#         with engine.connect() as conn:
#             if is_postgres:
#                 # PostgreSQL query
#                 table_list = "', '".join(table_names)
#                 result = conn.execute(text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('{table_list}')"))
#             else:
#                 # MSSQL query
#                 table_list = "', '".join(table_names)
#                 result = conn.execute(text(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME IN ('{table_list}')"))
#             return result.scalar() > 0
#     except:
#         return False

# def initialize_database_tables():
#     """Initialize database tables on application startup - only create if they don't exist"""
#     try:
#         print("🔧 Initializing database connections...")
        
#         # Test MSSQL connection and create tables only if they don't exist
#         try:
#             with mssql_engine.connect() as conn:
#                 conn.execute(text("SELECT 1"))
            
#             # Check if any key tables exist
#             key_tables = ['kpi_data', 'materials', 'order_validations', 'orders', 'process_orders', 'sync_interval_settings']
#             tables_exist = check_any_tables_exist(mssql_engine, key_tables, is_postgres=False)
            
#             if not tables_exist:
#                 print("📝 Creating MSSQL tables...")
#                 KpiBase.metadata.create_all(mssql_engine)
#                 MaterialBase.metadata.create_all(mssql_engine)
#                 OrderValidation.metadata.create_all(mssql_engine)
#                 OrderBase.metadata.create_all(mssql_engine)
#                 create_process_order_schema()
#                 print("✅ MSSQL tables created")
                
#         except Exception as e:
#             print(f"⚠️ MSSQL connection issue: {e}")
        
#         # Test PostgreSQL connection and create tables only if they don't exist
#         try:
#             with postgres_engine.connect() as conn:
#                 conn.execute(text("SELECT 1"))
            
#             # Check if any key tables exist
#             key_pg_tables = ['scada_data', 'milling_kpi_snapshots', 'packing_kpi_snapshots', 'process_orders_pg', 'sync_interval_settings', 'shift_master']
#             pg_tables_exist = check_any_tables_exist(postgres_engine, key_pg_tables, is_postgres=True)
            
#             if not pg_tables_exist:
#                 print("📝 Creating PostgreSQL tables...")
#                 create_scada_schema()
#                 create_milling_kpi_schema()
#                 create_packing_kpi_schema()
#                 create_process_order_pg_schema()
#                 PostgresBase.metadata.create_all(bind=postgres_engine)
#                 print("✅ PostgreSQL tables created")
                
#         except Exception as e:
#             print(f"⚠️ PostgreSQL connection issue: {e}")
        
#         # Initialize default sync settings (this is safe to run multiple times)
#         try:
#             init_default_sync_settings()
#         except Exception as e:
#             print(f"⚠️ Sync settings issue: {e}")
            
#         print("✅ Database initialization completed")
            
#     except Exception as e:
#         print(f"❌ Database initialization error: {e}")


# def create_app():
#     """Application factory for Hercules KPI API + React Frontend."""
#     app = Flask(__name__)
#     CORS(app, 
#          supports_credentials=True, 
#          origins=['*'],  # Allow all origins for development
#          methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
#          allow_headers=['Content-Type', 'Authorization'])

#     # ----------------- Ensure MSSQL tables exist -----------------
#     KpiBase.metadata.create_all(mssql_engine)
#     MaterialBase.metadata.create_all(mssql_engine)
#     OrderValidation.metadata.create_all(mssql_engine)
#     OrderBase.metadata.create_all(mssql_engine)
#     create_process_order_schema()
    
#     # ✅ CRITICAL: Ensure milling_version_mappings table exists
#     from models.milling_version_mapping import MillingVersionMapping
#     from database import Base
#     Base.metadata.create_all(mssql_engine, tables=[MillingVersionMapping.__table__])
#     print("✅ Verified milling_version_mappings table exists")

#     # ----------------- Ensure Postgres tables exist --------------
#     create_scada_schema()
#     create_milling_kpi_schema()
#     create_packing_kpi_schema()
#     create_process_order_pg_schema()
#     PostgresBase.metadata.create_all(bind=postgres_engine)

#     # ----------------- Register Blueprints ------------------------
#     app.register_blueprint(kpi_bp)
#     app.register_blueprint(material_bp)
#     app.register_blueprint(orders_bp)
#     app.register_blueprint(dev_bp)
#     app.register_blueprint(process_orders_bp)
#     app.register_blueprint(scada_bp)
#     app.register_blueprint(reports_bp)
#     app.register_blueprint(sap_sync_bp)
#     app.register_blueprint(system_logs_bp)
#     app.register_blueprint(auth_bp)
#     app.register_blueprint(sync_interval_bp)
#     app.register_blueprint(shifts_bp)
#     app.register_blueprint(milling_bp)
    
#     from init_sync_settings import init_default_sync_settings
#     init_default_sync_settings()
#     start_sync_scheduler()

#     # ----------------- Start Scheduler & AutoValidator ------------
#     is_main = os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug
#     if is_main:
#         start_scheduler()

#     # ----------------- Serve React Frontend ------------------------
#     if getattr(sys, 'frozen', False):
#         # Running as frozen .exe
#         # Exe location: backend/dist/app/app.exe
#         exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        
#         # Go up ONE level to reach backend folder (where public folder is)
#         base_path = os.path.dirname(exe_dir)
        
#         print(f"🔍 Running as .exe from: {exe_dir}")
#         print(f"🔍 Going up 1 level to: {base_path}")
#     else:
#         # Running as normal Python script
#         base_path = os.path.dirname(os.path.abspath(__file__))
#         print(f"🔍 Running as Python script from: {base_path}")

#     # public folder is in backend root
#     react_build_path = os.path.join(base_path, 'public')

#     # Debug logging
#     print(f"🔍 Frozen: {getattr(sys, 'frozen', False)}")
#     print(f"🔍 Base path: {base_path}")
#     print(f"🔍 React build path: {react_build_path}")
#     print(f"🔍 Path exists: {os.path.exists(react_build_path)}")

#     if os.path.exists(react_build_path):
#         files = os.listdir(react_build_path)
#         print(f"✅ Files in public: {files[:5]}")
#     else:
#         print(f"❌ public folder not found!")
#         if os.path.exists(base_path):
#             print(f"📁 Files in base_path: {os.listdir(base_path)[:10]}")

#     app.static_folder = react_build_path

#     # ----------------- API Health Check -----------------------
#     @app.route("/api/health")
#     def health():
#         return {"status": "✅ Hercules KPI API is running"}
    
#     # ----------------- Server Time Endpoint -----------------------
#     @app.route("/api/time")
#     def get_server_time():
#         """Get server time and timezone information."""
#         from datetime import datetime, timezone
#         import time
        
#         server_now = datetime.now()
#         server_utc = datetime.now(timezone.utc)
#         server_timestamp = time.time()
        
#         return {
#             "server_time": server_now.isoformat(),
#             "server_time_utc": server_utc.isoformat(),
#             "server_timestamp": server_timestamp,
#             "server_timezone": str(server_now.astimezone().tzinfo),
#             "server_time_formatted": server_now.strftime("%Y-%m-%d %H:%M:%S"),
#             "server_date": server_now.strftime("%Y-%m-%d"),
#             "server_time_only": server_now.strftime("%H:%M:%S")
#         }

#     # ----------------- Serve React SPA ------------------------
#     @app.route("/", defaults={'path': ''})
#     @app.route("/<path:path>")
#     def serve_react(path):
#         """Serve the React frontend for non-API routes."""
#         if path.startswith('api/'):
#             return {"error": "API endpoint not found"}, 404
        
#         full_path = os.path.join(react_build_path, path)
#         if path and os.path.isfile(full_path):
#             return send_from_directory(react_build_path, path)
        
#         index_path = os.path.join(react_build_path, "index.html")
#         if os.path.exists(index_path):
#             return send_from_directory(react_build_path, "index.html")
        
#         return {
#             "error": "❌ React build not found",
#             "expected_path": react_build_path,
#             "base_path": base_path,
#             "frozen": getattr(sys, 'frozen', False),
#             "available_files": os.listdir(base_path) if os.path.exists(base_path) else [],
#             "help": "Run 'npm run build' in Frontend folder"
#         }, 500

#     return app


# app = create_app()

# # Initialize database tables on startup
# initialize_database_tables()

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
# backend/app.py
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import text

# Ensure backend/ is in sys.path and load .env before any DB/SAP imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(Path(__file__).resolve().parent / ".env")

# --- Blueprints (API routes) ---
from routes.kpi_routes import kpi_bp
from routes.material_routes import material_bp
from routes.order_validation import orders_bp
from routes.dev_seed import dev_bp
from routes.process_orders import process_orders_bp
from routes.scada_routes import scada_bp
from routes.reports_routes import reports_bp
from routes.sap_sync import sap_sync_bp
from routes.system_logs import system_logs_bp
from routes.auth_routes import auth_bp
from routes.sync_interval_routes import sync_interval_bp
from routes.shifts import shifts_bp
from routes.milling_mapping_routes import milling_bp
from routes.error_log_routes import error_log_bp
from routes.offline_confirmations import offline_bp
from routes.sap_log_routes import sap_log_bp
from routes.emulator_routes import emulator_bp
from routes.system_mode_routes import system_mode_bp
from routes.admin_routes import admin_bp
# --- Dynamic configuration blueprints (added in commit 0; see backend/CONTRACTS.md) ---
from routes.classification_routes import classification_bp   # Workstream A
from routes.engineering_routes import engineering_bp         # Workstream A (A8)
from routes.scada_config_routes import scada_config_bp       # Workstream B
from routes.kpi_config_routes import kpi_config_bp           # Workstream B
from services.sync_scheduler import start_sync_scheduler

# --- DB engines / Base ---
from database import engine as mssql_engine, postgres_engine, PostgresBase
from models.kpi_model import Base as KpiBase
from models.material_model import Base as MaterialBase
from models.order_validation import Base as OrderValidation
from models.order_model import Base as OrderBase
from models.shift_report import ShiftReport, DailySummary
from models.shift_master import ShiftMaster
from models.offline_confirmation import OfflineConfirmation  # Ensure table creation
from models.scale_overflow import ScaleOverflow  # Ensure table creation
from models.sap_log import SapLog  # Ensure table creation
from models.classification_rule import ClassificationRule  # Workstream A - ensure table creation
from models.scada_tag import ScadaTag                      # Workstream B - ensure table creation
from models.kpi_config import KpiConfig                    # Workstream B - ensure table creation

# --- New KPI Snapshot tables ---
from models.milling_kpi_snapshot import create_milling_kpi_schema
from models.packing_kpi_snapshot import create_packing_kpi_schema
from models.process_order import create_process_order_schema
from models.process_order_pg import create_process_order_pg_schema

# --- KPI Send Tracking (for incremental sends) ---
from models.kpi_send_tracking import KpiSendTracking  # Import to ensure table is created

# --- SCADA / SAP services ---
from services.create_scada_table import create_scada_schema
from services.process_order_sync import sync_process_orders

# --- Scheduler ---
from app_scheduler import start_scheduler

# --- Auto Validator background worker ---
from services.auto_validator import auto_validator

# --- Database initialization ---
from init_sync_settings import init_default_sync_settings


def check_table_exists(engine, table_name):
    """Check if a table exists in the database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table_name}'"))
            return result.scalar() > 0
    except:
        return False

def check_postgres_table_exists(engine, table_name):
    """Check if a table exists in PostgreSQL database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"))
            return result.scalar() > 0
    except:
        return False

def check_any_tables_exist(engine, table_names, is_postgres=False):
    """Check if any of the specified tables exist in the database"""
    try:
        with engine.connect() as conn:
            if is_postgres:
                # PostgreSQL query
                table_list = "', '".join(table_names)
                result = conn.execute(text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('{table_list}')"))
            else:
                # MSSQL query
                table_list = "', '".join(table_names)
                result = conn.execute(text(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME IN ('{table_list}')"))
            return result.scalar() > 0
    except:
        return False

def initialize_database_tables():
    """Initialize database tables on application startup - only create if they don't exist"""
    try:
        print("🔧 Initializing database connections...")
        
        # Test MSSQL connection and create tables only if they don't exist
        from database import is_mssql_enabled
        if not is_mssql_enabled():
            print("⚠️ MSSQL disabled (MSSQL_ENABLED=false) — skipping MSSQL init")
        else:
            try:
                with mssql_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                # Check if any key tables exist
                key_tables = ['kpi_data', 'materials', 'order_validations', 'orders', 'process_orders', 'sync_interval_settings']
                tables_exist = check_any_tables_exist(mssql_engine, key_tables, is_postgres=False)
                
                if not tables_exist:
                    print("📝 Creating MSSQL tables...")
                    KpiBase.metadata.create_all(mssql_engine)
                    MaterialBase.metadata.create_all(mssql_engine)
                    OrderValidation.metadata.create_all(mssql_engine)
                    OrderBase.metadata.create_all(mssql_engine)
                    create_process_order_schema()
                    print("✅ MSSQL tables created")
                    
            except Exception as e:
                print(f"⚠️ MSSQL connection issue (demo/mock mode OK): {e}")
        
        # Test PostgreSQL connection and create tables only if they don't exist
        try:
            with postgres_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Check if any key tables exist
            key_pg_tables = ['scada_data', 'milling_kpi_snapshots', 'packing_kpi_snapshots', 'process_orders_pg', 'sync_interval_settings', 'shift_master']
            pg_tables_exist = check_any_tables_exist(postgres_engine, key_pg_tables, is_postgres=True)
            
            if not pg_tables_exist:
                print("📝 Creating PostgreSQL tables...")
                create_scada_schema()
                create_milling_kpi_schema()
                create_packing_kpi_schema()
                create_process_order_pg_schema()
                PostgresBase.metadata.create_all(bind=postgres_engine)
                print("✅ PostgreSQL tables created")
                
        except Exception as e:
            print(f"⚠️ PostgreSQL connection issue: {e}")
        
        # Initialize default sync settings (this is safe to run multiple times)
        try:
            init_default_sync_settings()
        except Exception as e:
            print(f"⚠️ Sync settings issue: {e}")
            
        print("✅ Database initialization completed")
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")


# CORS allowed origins - from CORS_ALLOWED_ORIGINS env (comma-separated), else localhost defaults.
_cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
if _cors_env:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

def create_app():
    """Application factory for Hercules KPI API + React Frontend."""
    # B5: fail fast on missing required SAP config instead of silent production connect
    try:
        from services.runtime_config import missing_required
        missing = missing_required()
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(
                f"Missing required configuration: {names}. "
                f"Set them in backend/.env or system_settings before starting."
            )
    except RuntimeError:
        raise
    except Exception as exc:
        print(f"⚠️ startup config check deferred: {exc}")

    app = Flask(__name__)
    CORS(app, 
         supports_credentials=True, 
         origins=CORS_ALLOWED_ORIGINS,
         methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'ngrok-skip-browser-warning'],
         expose_headers=['Content-Type', 'Authorization'])

    @app.after_request
    def add_cors_headers_if_allowed(response):
        """Ensure CORS headers on every response when origin is allowed (fixes preflight/ngrok)."""
        origin = request.headers.get('Origin')
        if origin and origin in CORS_ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, ngrok-skip-browser-warning'
        return response

    # ----------------- Ensure MSSQL tables exist (optional) -----------------
    # Skip when MSSQL_ENABLED=false, or when ODBC/SQL Server is missing (demo machines).
    from database import is_mssql_enabled
    if not is_mssql_enabled():
        print("⚠️ MSSQL disabled (MSSQL_ENABLED=false) — using Postgres + demo/mock only")
    else:
        try:
            with mssql_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            KpiBase.metadata.create_all(mssql_engine)
            MaterialBase.metadata.create_all(mssql_engine)
            OrderValidation.metadata.create_all(mssql_engine)
            OrderBase.metadata.create_all(mssql_engine)
            create_process_order_schema()
            print("✅ MSSQL tables verified")
        except Exception as e:
            print(f"⚠️ MSSQL unavailable (demo/mock mode OK): {e}")
    
    # ✅ CRITICAL: Ensure milling_version_mappings table exists in PostgreSQL
    from models.milling_version_mapping import MillingVersionMapping
    from database import PostgresBase, postgres_engine
    PostgresBase.metadata.create_all(postgres_engine, tables=[MillingVersionMapping.__table__])
    print("✅ Verified milling_version_mappings table exists in PostgreSQL")

    # ----------------- Ensure Postgres tables exist --------------
    create_scada_schema()
    create_milling_kpi_schema()
    create_packing_kpi_schema()
    create_process_order_pg_schema()
    
    # Ensure SystemSettings table exists (for demo mode configuration)
    from models.system_settings import SystemSettings
    
    PostgresBase.metadata.create_all(bind=postgres_engine)
    
    # ✅ Migration: Add error_message column to offline_confirmations if missing (Jan 30, 2026)
    try:
        with postgres_engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE offline_confirmations 
                ADD COLUMN IF NOT EXISTS error_message TEXT
            """))
            conn.commit()
            print("✅ Verified offline_confirmations.error_message column exists")
    except Exception as e:
        print(f"⚠️ Migration warning (error_message column): {e}")

    # ✅ Migration: Add scada_recipe_name to milling_version_mappings if missing
    try:
        with postgres_engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE milling_version_mappings
                ADD COLUMN IF NOT EXISTS scada_recipe_name VARCHAR(255)
            """))
            conn.commit()
            print("✅ Verified milling_version_mappings.scada_recipe_name column exists")
    except Exception as e:
        print(f"⚠️ Migration warning (scada_recipe_name column): {e}")

    # ✅ Migration: Add hercules_priority to process_orders (queue order; SAP does not change it)
    try:
        with postgres_engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE process_orders
                ADD COLUMN IF NOT EXISTS hercules_priority INTEGER DEFAULT 0
            """))
            conn.commit()
            conn.execute(text("""
                UPDATE process_orders SET hercules_priority = COALESCE(priority, 0) WHERE hercules_priority IS NULL
            """))
            conn.commit()
            print("✅ Verified process_orders.hercules_priority column exists")
    except Exception as e:
        print(f"⚠️ Migration warning (hercules_priority column): {e}")

    # ----------------- Register Blueprints ------------------------
    app.register_blueprint(kpi_bp)
    app.register_blueprint(material_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(dev_bp)
    app.register_blueprint(process_orders_bp)
    app.register_blueprint(scada_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(sap_sync_bp)
    app.register_blueprint(system_logs_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(sync_interval_bp)
    app.register_blueprint(shifts_bp)
    app.register_blueprint(milling_bp)
    app.register_blueprint(error_log_bp)
    app.register_blueprint(offline_bp)
    app.register_blueprint(sap_log_bp)
    app.register_blueprint(emulator_bp)
    app.register_blueprint(system_mode_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(classification_bp)   # Workstream A
    app.register_blueprint(engineering_bp)      # Workstream A (A8)
    app.register_blueprint(scada_config_bp)     # Workstream B
    app.register_blueprint(kpi_config_bp)       # Workstream B
    
    from init_sync_settings import init_default_sync_settings
    init_default_sync_settings()
    start_sync_scheduler()
    
    # ----------------- Initialize System Settings & Emulator ----------------
    try:
        from models.system_settings import init_default_settings, is_demo_mode_enabled, is_emulator_auto_start
        init_default_settings()
        
        # Auto-start emulator if demo mode and auto-start enabled
        if is_demo_mode_enabled() and is_emulator_auto_start():
            from services.embedded_emulator import get_emulator
            emulator = get_emulator()
            emulator.start()
            print("🚀 Embedded SCADA Emulator auto-started (demo mode)")
    except Exception as e:
        print(f"⚠️ System settings/emulator init: {e}")

    # ----------------- Start Scheduler & AutoValidator ------------
    # ✅ FIX (Jan 30, 2026): Always start scheduler, with diagnostic logging
    is_main = os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug
    print(f"🔧 Scheduler check: is_main={is_main}, WERKZEUG_RUN_MAIN={os.environ.get('WERKZEUG_RUN_MAIN')}, app.debug={app.debug}")
    
    # ✅ CRITICAL FIX: Always start scheduler for auto shift confirmation
    # Previously scheduler wasn't starting in some configurations
    try:
        print("🚀🚀🚀 STARTING APP_SCHEDULER (auto shift confirmation every 1 min) 🚀🚀🚀")
        start_scheduler()
        print("✅ APP_SCHEDULER STARTED SUCCESSFULLY")
    except Exception as sched_err:
        print(f"❌ FAILED TO START APP_SCHEDULER: {sched_err}")
        import traceback
        traceback.print_exc()

    # ----------------- Serve React Frontend ------------------------
    if getattr(sys, 'frozen', False):
        # Running as frozen .exe
        # Exe location: backend/dist/app/app.exe
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        
        # Go up ONE level to reach backend folder (where public folder is)
        base_path = os.path.dirname(exe_dir)
        
        print(f"🔍 Running as .exe from: {exe_dir}")
        print(f"🔍 Going up 1 level to: {base_path}")
    else:
        # Running as normal Python script
        base_path = os.path.dirname(os.path.abspath(__file__))
        print(f"🔍 Running as Python script from: {base_path}")

    # public folder is in backend root
    react_build_path = os.path.join(base_path, 'public')

    # Debug logging
    print(f"🔍 Frozen: {getattr(sys, 'frozen', False)}")
    print(f"🔍 Base path: {base_path}")
    print(f"🔍 React build path: {react_build_path}")
    print(f"🔍 Path exists: {os.path.exists(react_build_path)}")

    if os.path.exists(react_build_path):
        files = os.listdir(react_build_path)
        print(f"✅ Files in public: {files[:5]}")
    else:
        print(f"❌ public folder not found!")
        if os.path.exists(base_path):
            print(f"📁 Files in base_path: {os.listdir(base_path)[:10]}")

    app.static_folder = react_build_path

    # ----------------- API Health Check -----------------------
    @app.route("/api/health")
    def health():
        return {"status": "✅ Hercules KPI API is running"}
    
    # ----------------- Server Time Endpoint -----------------------
    @app.route("/api/time")
    def get_server_time():
        """Get server time and timezone information."""
        from datetime import datetime, timezone
        import time
        
        server_now = datetime.now()
        server_utc = datetime.now(timezone.utc)
        server_timestamp = time.time()
        
        return {
            "server_time": server_now.isoformat(),
            "server_time_utc": server_utc.isoformat(),
            "server_timestamp": server_timestamp,
            "server_timezone": str(server_now.astimezone().tzinfo),
            "server_time_formatted": server_now.strftime("%Y-%m-%d %H:%M:%S"),
            "server_date": server_now.strftime("%Y-%m-%d"),
            "server_time_only": server_now.strftime("%H:%M:%S")
        }

    # ----------------- Serve React SPA ------------------------
    @app.route("/", defaults={'path': ''})
    @app.route("/<path:path>")
    def serve_react(path):
        """Serve the React frontend for non-API routes."""
        if path.startswith('api/'):
            # Debug: Print which API path wasn't found
            print(f"⚠️ [404] API endpoint not found: /{path}")
            print(f"⚠️ [404] Registered routes: {[rule.rule for rule in app.url_map.iter_rules() if 'process_orders' in rule.rule][:10]}")
            return {"error": "API endpoint not found", "path": path}, 404
        
        full_path = os.path.join(react_build_path, path)
        if path and os.path.isfile(full_path):
            return send_from_directory(react_build_path, path)
        
        index_path = os.path.join(react_build_path, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(react_build_path, "index.html")
        
        return {
            "error": "❌ React build not found",
            "expected_path": react_build_path,
            "base_path": base_path,
            "frozen": getattr(sys, 'frozen', False),
            "available_files": os.listdir(base_path) if os.path.exists(base_path) else [],
            "help": "Run 'npm run build' in Frontend folder"
        }, 500

    return app


app = create_app()

# Initialize database tables on startup
initialize_database_tables()

# ✅ CRITICAL FIX (Jan 27, 2026): Clean up stale InProgress orders from previous sessions
# This prevents orphaned InProgress orders from showing as "Running" in UI when they have no workers
try:
    from database import PostgresSessionLocal
    from models.process_order import ProcessOrder
    
    db = PostgresSessionLocal()
    try:
        stale_inprogress = db.query(ProcessOrder).filter(ProcessOrder.status == "InProgress").all()
        if stale_inprogress:
            print(f"🧹 [STARTUP] Found {len(stale_inprogress)} stale InProgress orders - resetting to Pending...")
            for order in stale_inprogress:
                order.status = "Pending"
                db.add(order)
                print(f"   🔄 [{order.order_id}]: InProgress → Pending (stale from previous session)")
            db.commit()
            print(f"✅ [STARTUP] Reset {len(stale_inprogress)} stale InProgress orders to Pending")
        else:
            print("✅ [STARTUP] No stale InProgress orders found - database is clean")
    finally:
        db.close()
except Exception as e:
    print(f"⚠️ [STARTUP] Failed to clean stale InProgress orders: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    # Default 5000 matches Frontend/vite.config.ts proxy (/api → localhost:5000) and backend/README.md
    port = int(os.environ.get("PORT", os.environ.get("FLASK_RUN_PORT", "5000")))
    print("🚀 Starting server with Flask development server (threaded mode)")
    print(f"📡 Server running on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
