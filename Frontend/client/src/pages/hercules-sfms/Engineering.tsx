/**
 * Engineering hub — plant configuration.
 *
 * All former Admin tabs (System, Shifts, Demo Mode, Email, Branding, SAP Logs,
 * etc.) plus Connection / SCADA Tags / KPI Limits live here. The page body is
 * still implemented in Admin.tsx so we do not duplicate ~3k lines; this file
 * is the route entry for /engineering.
 */
export { Admin as default } from './Admin';
