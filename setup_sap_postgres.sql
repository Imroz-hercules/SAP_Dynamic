-- =============================================================================
-- SAP_Dynamic PostgreSQL setup
-- Database: sap   User: postgres   Password: Hercules   Port: 5432
-- (matches backend/database.py)
--
-- Usage (psql as superuser):
--   psql -U postgres -f setup_sap_postgres.sql
-- Or, if database sap already exists:
--   psql -U postgres -d sap -f setup_sap_postgres.sql
--
-- Default login after seed: admin / admin123
-- Demo mode is enabled so the app can run without SQL Server.
-- =============================================================================

-- Create database if missing (must not be connected to sap yet)
SELECT 'CREATE DATABASE sap WITH OWNER = postgres ENCODING = ''UTF8'' TEMPLATE = template0'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sap')\gexec

\c sap

CREATE EXTENSION IF NOT EXISTS pgcrypto;

BEGIN;

-- =============================================================================
-- AUTH / RBAC
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(255),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMP,
    updated_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    permissions TEXT,
    created_at  TIMESTAMP,
    updated_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_roles (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    role_id     INTEGER NOT NULL REFERENCES roles(id),
    assigned_at TIMESTAMP,
    assigned_by INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sync_interval_settings (
    id                     SERIAL PRIMARY KEY,
    sync_type              VARCHAR(50) NOT NULL UNIQUE,
    sync_time              VARCHAR(5) NOT NULL DEFAULT '09:00',
    sync_interval_minutes  INTEGER,
    sync_date              VARCHAR(10),
    is_enabled             BOOLEAN DEFAULT TRUE,
    last_sync              TIMESTAMPTZ,
    next_sync              TIMESTAMPTZ,
    created_at             TIMESTAMPTZ,
    updated_at             TIMESTAMPTZ,
    created_by             INTEGER REFERENCES users(id),
    updated_by             INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS system_logs (
    id           SERIAL PRIMARY KEY,
    timestamp    TIMESTAMP,
    source       VARCHAR(100),
    action       VARCHAR(100),
    status       VARCHAR(50),
    details      TEXT,
    log_metadata TEXT,
    operator     VARCHAR(100),
    duration_ms  INTEGER,
    error_code   VARCHAR(100),
    created_at   TIMESTAMP,
    shift        VARCHAR(50),
    level        VARCHAR(20),
    message      TEXT,
    category     VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS sync_status (
    id                 SERIAL PRIMARY KEY,
    sync_type          VARCHAR(50) NOT NULL,
    status             VARCHAR(20) NOT NULL,
    start_time         TIMESTAMP NOT NULL,
    end_time           TIMESTAMP,
    duration_ms        INTEGER,
    records_processed  INTEGER,
    records_successful INTEGER,
    records_failed     INTEGER,
    error_message      TEXT,
    error_details      TEXT,
    sync_result        TEXT,
    triggered_by       VARCHAR(50),
    created_at         TIMESTAMP,
    updated_at         TIMESTAMP
);

-- =============================================================================
-- SYSTEM SETTINGS (demo / mock SAP / emulator)
-- =============================================================================
CREATE TABLE IF NOT EXISTS system_settings (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(100) NOT NULL UNIQUE,
    value       TEXT,
    value_type  VARCHAR(20) DEFAULT 'string',
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_system_settings_key ON system_settings(key);

-- =============================================================================
-- SHIFTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS shift_master (
    id          SERIAL PRIMARY KEY,
    plant       VARCHAR(20) NOT NULL,
    department  VARCHAR(20) NOT NULL,
    shift_code  VARCHAR(10) NOT NULL,
    start_time  TIME NOT NULL,
    end_time    TIME NOT NULL,
    sort_order  INTEGER NOT NULL
);

-- =============================================================================
-- PROCESS ORDERS (main queue / validation table)
-- =============================================================================
CREATE TABLE IF NOT EXISTS process_orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    material VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    batch VARCHAR(50),
    quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit VARCHAR(10) NOT NULL DEFAULT 'KG',
    status VARCHAR(20) NOT NULL DEFAULT 'Open',
    priority INTEGER NOT NULL DEFAULT 0,
    date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    plant VARCHAR(50),
    confirmed_qty DOUBLE PRECISION DEFAULT 0,
    material_desc VARCHAR(200),
    sap_created_on TIMESTAMPTZ,
    uom VARCHAR(10),
    sap_order_id VARCHAR(50),
    total_qty DOUBLE PRECISION,
    priority_id INTEGER,
    hercules_priority INTEGER DEFAULT 0,

    expected_weight DOUBLE PRECISION DEFAULT 0,
    validation_method VARCHAR(20),
    confirmed_text VARCHAR(500),
    scrap DOUBLE PRECISION DEFAULT 0,
    last_confirmed_qty DOUBLE PRECISION DEFAULT 0,
    is_final_sent BOOLEAN DEFAULT FALSE,

    order_type VARCHAR(50),
    packing_line VARCHAR(10),
    bag_size VARCHAR(10),

    scale1 VARCHAR(50),
    scale1_qty DOUBLE PRECISION DEFAULT 0,
    scale2 VARCHAR(50),
    scale2_qty DOUBLE PRECISION DEFAULT 0,
    scale3 VARCHAR(50),
    scale3_qty DOUBLE PRECISION DEFAULT 0,

    baseline_sl601_counter DOUBLE PRECISION DEFAULT 0,
    baseline_sl602_counter DOUBLE PRECISION DEFAULT 0,
    baseline_sl603_counter DOUBLE PRECISION DEFAULT 0,
    baseline_sl606_counter DOUBLE PRECISION DEFAULT 0,
    baseline_sl607_counter DOUBLE PRECISION DEFAULT 0,

    baseline_wg101 DOUBLE PRECISION DEFAULT 0,
    baseline_wg201 DOUBLE PRECISION DEFAULT 0,
    baseline_wg202 DOUBLE PRECISION DEFAULT 0,
    baseline_wg301 DOUBLE PRECISION DEFAULT 0,
    baseline_wg302 DOUBLE PRECISION DEFAULT 0,
    baseline_wg501 DOUBLE PRECISION DEFAULT 0,
    baseline_wg502 DOUBLE PRECISION DEFAULT 0,
    baseline_wg503 DOUBLE PRECISION DEFAULT 0,

    baseline_dm101 DOUBLE PRECISION DEFAULT 0,
    baseline_dm102 DOUBLE PRECISION DEFAULT 0,
    baseline_dm201 DOUBLE PRECISION DEFAULT 0,
    baseline_dm202 DOUBLE PRECISION DEFAULT 0,
    baseline_dm203 DOUBLE PRECISION DEFAULT 0,
    baseline_fixed_flags JSON DEFAULT '{}'::json,

    current_shift VARCHAR(1),
    shift_start_time TIMESTAMPTZ,
    shift_end_time TIMESTAMPTZ,
    weight_shift_a DOUBLE PRECISION DEFAULT 0,
    weight_shift_b DOUBLE PRECISION DEFAULT 0,
    weight_shift_c DOUBLE PRECISION DEFAULT 0,
    confirmed_shift_a DOUBLE PRECISION DEFAULT 0,
    confirmed_shift_b DOUBLE PRECISION DEFAULT 0,
    confirmed_shift_c DOUBLE PRECISION DEFAULT 0,
    shift_a_confirmed BOOLEAN DEFAULT FALSE,
    shift_b_confirmed BOOLEAN DEFAULT FALSE,
    shift_c_confirmed BOOLEAN DEFAULT FALSE,
    overflow_weight DOUBLE PRECISION DEFAULT 0,
    is_target_reached BOOLEAN DEFAULT FALSE,
    total_shifts_used INTEGER DEFAULT 0,
    last_shift_completed VARCHAR(1),
    baseline_shift_a_start JSON,
    baseline_shift_b_start JSON,
    baseline_shift_c_start JSON,
    last_scada_values JSON
);

CREATE INDEX IF NOT EXISTS idx_process_order_order_id ON process_orders(order_id);
CREATE INDEX IF NOT EXISTS idx_process_order_status ON process_orders(status);
CREATE INDEX IF NOT EXISTS idx_process_order_date ON process_orders(date);
CREATE INDEX IF NOT EXISTS idx_process_order_priority ON process_orders(priority);
CREATE INDEX IF NOT EXISTS idx_process_order_type ON process_orders(order_type);
CREATE INDEX IF NOT EXISTS idx_current_shift ON process_orders(current_shift);
CREATE INDEX IF NOT EXISTS idx_shift_confirmed ON process_orders(shift_a_confirmed, shift_b_confirmed, shift_c_confirmed);
CREATE INDEX IF NOT EXISTS idx_target_reached ON process_orders(is_target_reached);

-- =============================================================================
-- CONFIRMATIONS / ERRORS / OVERFLOW
-- =============================================================================
CREATE TABLE IF NOT EXISTS offline_confirmations (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    process_order_id INTEGER,
    material VARCHAR(200),
    version VARCHAR(50),
    confirmed_weight DOUBLE PRECISION NOT NULL,
    total_qty DOUBLE PRECISION NOT NULL,
    uom VARCHAR(10),
    plant VARCHAR(50),
    batch VARCHAR(50),
    shift VARCHAR(10),
    scrap DOUBLE PRECISION DEFAULT 0,
    confirmed_text VARCHAR(500),
    sap_payload JSON,
    validation_method VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    retry_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS ix_offline_confirmations_order_id ON offline_confirmations(order_id);
CREATE INDEX IF NOT EXISTS ix_offline_confirmations_status ON offline_confirmations(status);

CREATE TABLE IF NOT EXISTS manual_confirmations (
    id SERIAL PRIMARY KEY,
    process_order_id INTEGER NOT NULL REFERENCES process_orders(id) ON DELETE CASCADE,
    shift_code VARCHAR(1) NOT NULL,
    confirmed_weight DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    synced_to_sap BOOLEAN NOT NULL DEFAULT FALSE,
    sap_response JSON,
    created_by VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS error_log (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(50),
    error_type VARCHAR(50) NOT NULL,
    error_message TEXT,
    source VARCHAR(50),
    payload JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'Open',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_error_log_po_number ON error_log(po_number);

CREATE TABLE IF NOT EXISTS scale_overflows (
    scale_tag VARCHAR(50) PRIMARY KEY,
    overflow_qty DOUBLE PRECISION DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sap_logs (
    id SERIAL PRIMARY KEY,
    direction VARCHAR(10) NOT NULL,
    endpoint VARCHAR(200),
    method VARCHAR(10),
    request_payload JSONB,
    response_payload JSONB,
    status_code INTEGER,
    error_message TEXT,
    duration_ms INTEGER,
    po_number VARCHAR(50),
    log_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sap_logs_po_number ON sap_logs(po_number);
CREATE INDEX IF NOT EXISTS ix_sap_logs_created_at ON sap_logs(created_at);

-- =============================================================================
-- MAPPINGS
-- =============================================================================
CREATE TABLE IF NOT EXISTS milling_version_mappings (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,
    scales JSON NOT NULL,
    formula VARCHAR(200) NOT NULL,
    scale1 VARCHAR(50),
    scale2 VARCHAR(50),
    scale3 VARCHAR(50),
    description VARCHAR(255),
    scada_recipe_name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS palletizer_mapping (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    palletizer VARCHAR(50) NOT NULL,
    bag_size_kg DOUBLE PRECISION NOT NULL,
    bags_per_pallet DOUBLE PRECISION NOT NULL,
    kg_per_pallet DOUBLE PRECISION NOT NULL,
    description VARCHAR(255)
);

-- =============================================================================
-- KPI / SCADA HISTORY
-- Mixed-case names MUST stay quoted — kpi_incremental.py uses "baseline_WG101"
-- =============================================================================
CREATE TABLE IF NOT EXISTS kpi_send_tracking (
    id SERIAL PRIMARY KEY,
    department VARCHAR(20) NOT NULL,
    shift_code VARCHAR(10),
    last_sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "baseline_WG101" DOUBLE PRECISION DEFAULT 0,
    "baseline_WG201" DOUBLE PRECISION DEFAULT 0,
    "baseline_WG202" DOUBLE PRECISION DEFAULT 0,
    "baseline_WG301" DOUBLE PRECISION DEFAULT 0,
    "baseline_WG302" DOUBLE PRECISION DEFAULT 0,
    "baseline_WG501" DOUBLE PRECISION DEFAULT 0,
    "baseline_WG502" DOUBLE PRECISION DEFAULT 0,
    "baseline_WG503" DOUBLE PRECISION DEFAULT 0,
    "baseline_DM101" DOUBLE PRECISION DEFAULT 0,
    "baseline_DM102" DOUBLE PRECISION DEFAULT 0,
    "baseline_DM201" DOUBLE PRECISION DEFAULT 0,
    "baseline_DM202" DOUBLE PRECISION DEFAULT 0,
    "baseline_DM203" DOUBLE PRECISION DEFAULT 0,
    "baseline_PL601_TOT" DOUBLE PRECISION DEFAULT 0,
    "baseline_PL602_TOT" DOUBLE PRECISION DEFAULT 0,
    "baseline_PL603_TOT" DOUBLE PRECISION DEFAULT 0,
    send_type VARCHAR(20) NOT NULL,
    notes TEXT,
    kpi_payload_sent JSON
);

CREATE TABLE IF NOT EXISTS scada_aggregate_values (
    id SERIAL PRIMARY KEY,
    mode VARCHAR(50) NOT NULL,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    VALUE_WG101 DOUBLE PRECISION,
    VALUE_WG201 DOUBLE PRECISION,
    VALUE_WG202 DOUBLE PRECISION,
    VALUE_WG301 DOUBLE PRECISION,
    VALUE_WG302 DOUBLE PRECISION,
    VALUE_WG501 DOUBLE PRECISION,
    VALUE_WG502 DOUBLE PRECISION,
    VALUE_WG503 DOUBLE PRECISION,
    VALUE_DM101 DOUBLE PRECISION,
    VALUE_DM102 DOUBLE PRECISION,
    VALUE_DM201 DOUBLE PRECISION,
    VALUE_DM202 DOUBLE PRECISION,
    VALUE_DM203 DOUBLE PRECISION,
    VALUE_PL601_TOT DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS milling_kpi_snapshots (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mode VARCHAR(16) NOT NULL DEFAULT 'latest',
    mill_throughput_pct DOUBLE PRECISION,
    mill_time_efficiency_pct DOUBLE PRECISION,
    total_utilization_pct DOUBLE PRECISION,
    milling_gain_pct DOUBLE PRECISION,
    milling_screening_pct DOUBLE PRECISION,
    water_consumption_m3 DOUBLE PRECISION,
    flour_extraction_pct DOUBLE PRECISION,
    bran_extraction_pct DOUBLE PRECISION,
    milling_loss_pct DOUBLE PRECISION,
    net_hours_hrs DOUBLE PRECISION,
    downtime_hrs DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_milling_kpi_created_at ON milling_kpi_snapshots(created_at);
CREATE INDEX IF NOT EXISTS idx_milling_kpi_mode ON milling_kpi_snapshots(mode);

CREATE TABLE IF NOT EXISTS packing_kpi_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    daily_packing_output_bags DOUBLE PRECISION,
    downtime_hrs DOUBLE PRECISION,
    machine_utilization_pct DOUBLE PRECISION,
    net_hours_hrs DOUBLE PRECISION,
    packing_line_capacity_bags_hr DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_packing_kpi_timestamp ON packing_kpi_snapshots(timestamp);

CREATE TABLE IF NOT EXISTS shift_reports (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(64) NOT NULL,
    material VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL DEFAULT 'v1.0',
    planned_quantity NUMERIC(18,3) NOT NULL DEFAULT 0,
    actual_quantity NUMERIC(18,3) NOT NULL DEFAULT 0,
    unit VARCHAR(16) NOT NULL DEFAULT 'T',
    flour_extraction_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    utilization_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    loss_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'Pending',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_shift_reports_po_number ON shift_reports(po_number);
CREATE INDEX IF NOT EXISTS idx_shift_reports_timestamp ON shift_reports(timestamp);
CREATE INDEX IF NOT EXISTS idx_shift_reports_status ON shift_reports(status);
CREATE INDEX IF NOT EXISTS idx_shift_reports_material ON shift_reports(material);

CREATE TABLE IF NOT EXISTS daily_summaries (
    id SERIAL PRIMARY KEY,
    report_date TIMESTAMPTZ NOT NULL,
    total_wheat NUMERIC(18,3) NOT NULL DEFAULT 0,
    total_flour NUMERIC(18,3) NOT NULL DEFAULT 0,
    total_bran NUMERIC(18,3) NOT NULL DEFAULT 0,
    total_water NUMERIC(18,3) NOT NULL DEFAULT 0,
    total_packing NUMERIC(18,3) NOT NULL DEFAULT 0,
    efficiency_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
    wheat_unit VARCHAR(16) NOT NULL DEFAULT 'T',
    flour_unit VARCHAR(16) NOT NULL DEFAULT 'T',
    bran_unit VARCHAR(16) NOT NULL DEFAULT 'T',
    water_unit VARCHAR(16) NOT NULL DEFAULT 'm³',
    packing_unit VARCHAR(16) NOT NULL DEFAULT 'Bags',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON daily_summaries(report_date);

-- =============================================================================
-- SEED: roles, admin user, settings, shifts, sync times
-- =============================================================================
INSERT INTO roles (name, description, permissions, created_at, updated_at)
VALUES
  ('admin', 'System Administrator - Full access',
   '{"view_sync_interval": true, "change_sync_interval": true, "view_all_data": true, "manage_users": true, "system_admin": true, "order_access_milling": true, "order_access_packing": true}',
   NOW(), NOW()),
  ('manager', 'Manager',
   '{"view_sync_interval": true, "change_sync_interval": true, "view_all_data": true, "manage_users": false, "system_admin": false, "order_access_milling": true, "order_access_packing": true}',
   NOW(), NOW()),
  ('operator', 'Operator',
   '{"view_sync_interval": true, "change_sync_interval": false, "view_all_data": false, "manage_users": false, "system_admin": false, "order_access_milling": true, "order_access_packing": true}',
   NOW(), NOW()),
  ('milling_operator', 'Milling Operator',
   '{"view_sync_interval": true, "change_sync_interval": false, "view_all_data": false, "manage_users": false, "system_admin": false, "order_access_milling": true, "order_access_packing": false}',
   NOW(), NOW()),
  ('packing_operator', 'Packing Operator',
   '{"view_sync_interval": true, "change_sync_interval": false, "view_all_data": false, "manage_users": false, "system_admin": false, "order_access_milling": false, "order_access_packing": true}',
   NOW(), NOW()),
  ('guest', 'Guest',
   '{"view_sync_interval": false, "change_sync_interval": false, "view_all_data": false, "manage_users": false, "system_admin": false, "order_access_milling": false, "order_access_packing": false}',
   NOW(), NOW())
ON CONFLICT (name) DO NOTHING;

INSERT INTO users (username, email, password_hash, full_name, is_active, created_at, updated_at)
VALUES (
    'admin',
    'admin@hercules.com',
    crypt('admin123', gen_salt('bf')),
    'System Administrator',
    TRUE,
    NOW(),
    NOW()
)
ON CONFLICT (username) DO NOTHING;

INSERT INTO user_roles (user_id, role_id, assigned_at)
SELECT u.id, r.id, NOW()
FROM users u
JOIN roles r ON r.name = 'admin'
WHERE u.username = 'admin'
  AND NOT EXISTS (
      SELECT 1 FROM user_roles ur
      WHERE ur.user_id = u.id AND ur.role_id = r.id
  );

INSERT INTO system_settings (key, value, value_type, description)
VALUES
  ('demo_mode_enabled', 'true', 'boolean', 'Use embedded SCADA emulator instead of MSSQL'),
  ('mock_sap_enabled', 'true', 'boolean', 'Send SAP calls to mock server instead of real SAP'),
  ('emulator_auto_start', 'true', 'boolean', 'Auto-start emulator in demo mode'),
  ('emulator_interval', '10', 'float', 'Seconds between emulator updates'),
  ('emulator_step_min', '1', 'float', 'Minimum increment per emulator tick'),
  ('emulator_step_max', '10', 'float', 'Maximum increment per emulator tick'),
  ('emulator_active_scales', '[]', 'json', 'Active SCADA tags in emulator')
ON CONFLICT (key) DO NOTHING;

INSERT INTO sync_interval_settings (sync_type, sync_time, sync_interval_minutes, is_enabled, created_at, updated_at)
VALUES
  ('raw_data', '09:00', NULL, TRUE, NOW(), NOW()),
  ('kpi', '09:30', NULL, TRUE, NOW(), NOW()),
  ('process_orders', '10:00', 60, TRUE, NOW(), NOW())
ON CONFLICT (sync_type) DO NOTHING;

INSERT INTO shift_master (plant, department, shift_code, start_time, end_time, sort_order)
SELECT * FROM (VALUES
  ('3130', 'MILLING', 'A', TIME '07:00', TIME '15:00', 1),
  ('3130', 'MILLING', 'B', TIME '15:00', TIME '23:00', 2),
  ('3130', 'MILLING', 'C', TIME '23:00', TIME '07:00', 3),
  ('3130', 'PACKING', 'A', TIME '07:00', TIME '19:00', 1),
  ('3130', 'PACKING', 'B', TIME '19:00', TIME '07:00', 2)
) AS v(plant, department, shift_code, start_time, end_time, sort_order)
WHERE NOT EXISTS (
    SELECT 1 FROM shift_master s
    WHERE s.plant = v.plant AND s.department = v.department AND s.shift_code = v.shift_code
);

COMMIT;
