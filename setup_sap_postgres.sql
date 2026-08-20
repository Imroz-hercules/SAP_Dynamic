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

-- =============================================================================
-- DYNAMIC CONFIGURATION TABLES (added in commit 0)
--
-- Table ownership is exclusive - see backend/CONTRACTS.md:
--   classification_rules -> Workstream A
--   scada_tags           -> Workstream B
--   kpi_config           -> Workstream B
--
-- Schemas are fixed here so neither branch has to edit this file again.
-- Further changes to YOUR table go in your own backend/migrate_*.py;
-- this file is reconciled once, at the end, in a single cleanup PR.
-- =============================================================================

-- ---------------------------------------------------------------- Workstream A
CREATE TABLE IF NOT EXISTS classification_rules (
    id           SERIAL PRIMARY KEY,
    rule_type    VARCHAR(32)  NOT NULL,           -- 'material_prefix' | 'plant_department'
    match_value  VARCHAR(32)  NOT NULL,           -- '13', '14', '3130', or '*'
    result_value VARCHAR(32)  NOT NULL,           -- 'MILLING' | 'PACKING'
    priority     INTEGER      NOT NULL DEFAULT 100,
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    description  VARCHAR(255),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_classification_rule UNIQUE (rule_type, match_value)
);
CREATE INDEX IF NOT EXISTS idx_classification_rule_lookup
    ON classification_rules (rule_type, is_active, priority);

-- Seeded from the current hardcoded behaviour, so a fresh DB matches production.
INSERT INTO classification_rules (rule_type, match_value, result_value, priority, description)
VALUES
  ('material_prefix',   '13',   'MILLING', 10, 'order_validation.py:6247'),
  ('material_prefix',   '14',   'PACKING', 10, 'order_validation.py:6249'),
  ('plant_department',  '3130', 'MILLING', 10, 'plant 3130 is the mill'),
  ('plant_department',  '*',    'PACKING', 99, 'catch-all: any other plant is packing')
ON CONFLICT (rule_type, match_value) DO NOTHING;

-- ---------------------------------------------------------------- Workstream B
CREATE TABLE IF NOT EXISTS scada_tags (
    id            SERIAL PRIMARY KEY,
    tag           VARCHAR(50)  NOT NULL UNIQUE,   -- 'WG501', 'PL601_TOT'
    category      VARCHAR(20)  NOT NULL,          -- INPUT|MILLING|WATER|PACKING|DAMAGED
    reading_type  VARCHAR(20)  NOT NULL,          -- hi_lo | single | average
    source_column VARCHAR(64),                    -- exact ASMArchive_DB5 column
    rollover_max  NUMERIC(18,3),                  -- counter wrap point, NULL = none
    unit          VARCHAR(16),
    is_pollable   BOOLEAN      NOT NULL DEFAULT TRUE,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    emulator_seed NUMERIC(18,3) DEFAULT 0,
    display_name  VARCHAR(100),
    sort_order    INTEGER      NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_scada_tag_category ON scada_tags (category, is_active);
CREATE INDEX IF NOT EXISTS idx_scada_tag_pollable ON scada_tags (is_pollable, is_active);

-- Seeded from ALLOWED_SCADA_FIELDS in services/scale_service.py:768.
-- emulator_seed is left at 0; populate from REALISTIC_STARTING_VALUES in B1.
INSERT INTO scada_tags (tag, category, reading_type, source_column, rollover_max, unit, is_active, sort_order, display_name)
VALUES
  ('WG101','INPUT','hi_lo','WG101',1000000,'TON',TRUE,10,'Wheat input - Silo 1'),
  ('WG201','INPUT','hi_lo','WG201',1000000,'TON',TRUE,11,'Wheat input - Silo 2'),
  ('WG202','INPUT','hi_lo','WG202',1000000,'TON',TRUE,12,'Clean wheat - active scale'),
  ('WG301','INPUT','hi_lo','WG301',1000000,'TON',TRUE,13,'Milling screenings'),
  ('WG302','INPUT','hi_lo','WG302',1000000,'TON',TRUE,14,'Pre-clean screenings'),
  ('WG501','MILLING','hi_lo','WG501',1000000,'TON',TRUE,20,'Bakery flour stream'),
  ('WG502','MILLING','hi_lo','WG502',1000000,'TON',TRUE,21,'Cake / IWW flour stream'),
  ('WG503','MILLING','hi_lo','WG503',1000000,'TON',TRUE,22,'Bran stream'),
  ('DM101','WATER','average','DM101',NULL,'m3',TRUE,30,'Water meter 1'),
  ('DM102','WATER','average','DM102',NULL,'m3',TRUE,31,'Water meter 2'),
  ('DM201','WATER','average','DM201',NULL,'m3',TRUE,32,'Water meter 3'),
  ('DM202','WATER','average','DM202',NULL,'m3',TRUE,33,'Water meter 4'),
  ('DM203','WATER','average','DM203',NULL,'m3',TRUE,34,'Water meter 5'),
  ('PL601_TOT','PACKING','single','PL601_TOT',100000,'PALLET',TRUE,40,'Palletizer 1'),
  ('PL602_TOT','PACKING','single','PL602_TOT',100000,'PALLET',TRUE,41,'Palletizer 2'),
  ('PL603_TOT','PACKING','single','PL603_TOT',100000,'PALLET',TRUE,42,'Palletizer 3 - bran'),
  ('SL606_TOT','PACKING','single','SL606_TOT',100000,'PALLET',TRUE,43,'Line 6 - 1 KG'),
  ('SL607_TOT','PACKING','single','SL607_TOT',100000,'PALLET',TRUE,44,'Line 7 - 10 KG'),
  ('SL601_DAMAGED','DAMAGED','single','SL601_DAMAGED',NULL,'BAG',TRUE,50,'Line 1 damaged bags'),
  ('SL602_DAMAGED','DAMAGED','single','SL602_DAMAGED',NULL,'BAG',TRUE,51,'Line 2 damaged bags'),
  ('SL603_DAMAGED','DAMAGED','single','SL603_DAMAGED',NULL,'BAG',TRUE,52,'Line 3 damaged bags'),
  ('SL606_DAMAGED','DAMAGED','single','SL606_DAMAGED',NULL,'BAG',TRUE,53,'Line 6 damaged bags'),
  ('SL607_DAMAGED','DAMAGED','single','SL607_DAMAGED',NULL,'BAG',TRUE,54,'Line 7 damaged bags'),
  ('SL601_COUNTER','PACKING','single','SL601_COUNTER',100000,'BAG',FALSE,60,'Line 1 bag counter'),
  ('SL602_COUNTER','PACKING','single','SL602_COUNTER',100000,'BAG',FALSE,61,'Line 2 bag counter'),
  ('SL603_COUNTER','PACKING','single','SL603_COUNTER',100000,'BAG',FALSE,62,'Line 3 bag counter'),
  ('SL606_COUNTER','PACKING','single','SL606_COUNTER',100000,'BAG',FALSE,63,'Line 6 bag counter'),
  ('SL607_COUNTER','PACKING','single','SL607_COUNTER',100000,'BAG',FALSE,64,'Line 7 bag counter')
ON CONFLICT (tag) DO NOTHING;
-- The five *_COUNTER rows above are seeded INACTIVE on purpose. They exist in
-- ASMArchive_DB5 (see Book1.xlsx) and process_orders has matching
-- baseline_sl60x_counter columns, but they are absent from ALLOWED_SCADA_FIELDS
-- today, so reads return NULL. Verify against real data in B3, then flip
-- is_active rather than assuming they work.

-- ---------------------------------------------------------------- Workstream B
CREATE TABLE IF NOT EXISTS kpi_config (
    id            SERIAL PRIMARY KEY,
    kpi_key       VARCHAR(64)  NOT NULL UNIQUE,
    display_name  VARCHAR(128) NOT NULL,
    department    VARCHAR(20)  NOT NULL,          -- MILLING | PACKING
    target_column VARCHAR(64),                    -- column in *_kpi_snapshots
    max_value     NUMERIC(18,3),                  -- result ceiling, NULL = uncapped
    unit          VARCHAR(16),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    sort_order    INTEGER      NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_kpi_config_dept ON kpi_config (department, is_active);

-- Seeded with the ceilings currently applied in routes/kpi_routes.py:272-383.
-- NOTE: generate_kpi_doc.py documents 150 for mill_throughput and
-- max_utilization_milling_capacity. Code says 100. Resolve in B4 before
-- relying on these values.
INSERT INTO kpi_config (kpi_key, display_name, department, target_column, max_value, unit, sort_order)
VALUES
  ('mill_throughput_pct','Mill Throughput (%)','MILLING','mill_throughput_pct',100,'%',10),
  ('mill_time_efficiency_pct','Mill Time Efficiency (%)','MILLING','mill_time_efficiency_pct',100,'%',11),
  ('total_utilization_pct','Total Utilization (%)','MILLING','total_utilization_pct',100,'%',12),
  ('milling_gain_pct','Milling Gain (%)','MILLING','milling_gain_pct',120,'%',13),
  ('milling_screening_pct','Milling Screening (%)','MILLING','milling_screening_pct',20,'%',14),
  ('flour_extraction_pct','Flour Extraction (%)','MILLING','flour_extraction_pct',85,'%',15),
  ('bran_extraction_pct','Bran Extraction (%)','MILLING','bran_extraction_pct',25,'%',16),
  ('milling_loss_pct','Milling Loss (%)','MILLING','milling_loss_pct',NULL,'%',17),
  ('water_consumption_m3','Water Consumption (m3)','MILLING','water_consumption_m3',NULL,'m3',18),
  ('milling_net_hours_hrs','Net Hours (hrs)','MILLING','net_hours_hrs',NULL,'hrs',19),
  ('milling_downtime_hrs','Downtime (hrs)','MILLING','downtime_hrs',NULL,'hrs',20),
  ('max_utilization_milling_capacity_pct','Max Utilization of Milling Capacity (%)','MILLING',NULL,100,'%',21),
  ('pre_cleaning_screening_pct','Pre Cleaning Screening (%)','MILLING',NULL,20,'%',22),
  ('first_break_capacity_tph','1st Break Capacity per Hour (t/h)','MILLING',NULL,30,'t/h',23),
  ('packing_line_capacity_bags_hr','Packing Line Capacity (bags/hr)','PACKING','packing_line_capacity_bags_hr',2000,'bags/hr',30),
  ('daily_packing_output_bags','Daily Packing Output (bags)','PACKING','daily_packing_output_bags',100000,'bags',31),
  ('machine_utilization_pct','Machine Utilization (%)','PACKING','machine_utilization_pct',100,'%',32),
  ('packing_net_hours_hrs','Net Hours (hrs)','PACKING','net_hours_hrs',NULL,'hrs',33),
  ('packing_downtime_hrs','Downtime (hrs)','PACKING','downtime_hrs',NULL,'hrs',34)
ON CONFLICT (kpi_key) DO NOTHING;

-- Plant constant, not a per-KPI value: routes/kpi_routes.py:262 and :328.
INSERT INTO system_settings (key, value, value_type, description)
VALUES ('mill_nameplate_tph', '25', 'float', 'Mill nameplate capacity in tons/hour')
ON CONFLICT (key) DO NOTHING;

COMMIT;
