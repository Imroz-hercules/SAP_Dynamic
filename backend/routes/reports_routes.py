# backend/routes/reports_routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta
import logging

from database import PostgresSessionLocal
from models.shift_report import ShiftReport, DailySummary

# Create blueprint
reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db():
    """Get database session"""
    db = PostgresSessionLocal()
    try:
        yield db
    finally:
        db.close()

@reports_bp.route('/shift-reports', methods=['GET'])
def get_shift_reports():
    """Get shift reports with optional filtering"""
    try:
        db = PostgresSessionLocal()
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        material = request.args.get('material')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build query
        query = db.query(ShiftReport)
        
        # Apply filters
        if status:
            query = query.filter(ShiftReport.status == status)
        if material:
            query = query.filter(ShiftReport.material.ilike(f'%{material}%'))
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(ShiftReport.timestamp >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format'}), 400
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.filter(ShiftReport.timestamp <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format'}), 400
        
        # Order by timestamp descending (newest first)
        query = query.order_by(desc(ShiftReport.timestamp))
        
        # Apply pagination
        total_count = query.count()
        reports = query.offset(offset).limit(limit).all()
        
        # Debug logging
        logger.info(f"Found {total_count} total reports, returning {len(reports)} reports")
        if reports:
            logger.info(f"First report: {reports[0].to_dict()}")
        
        # Convert to dict format
        reports_data = [report.to_dict() for report in reports]
        
        db.close()
        
        return jsonify({
            'reports': reports_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Error fetching shift reports: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500

@reports_bp.route('/shift-reports', methods=['POST'])
def create_shift_report():
    """Create a new shift report"""
    try:
        db = PostgresSessionLocal()
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['po_number', 'material', 'version', 'planned_quantity', 'actual_quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create new shift report
        shift_report = ShiftReport(
            po_number=data['po_number'],
            material=data['material'],
            version=data.get('version', 'v1.0'),
            planned_quantity=data['planned_quantity'],
            actual_quantity=data['actual_quantity'],
            unit=data.get('unit', 'T'),
            flour_extraction_percent=data.get('flour_extraction_percent', 0),
            utilization_percent=data.get('utilization_percent', 0),
            loss_percent=data.get('loss_percent', 0),
            status=data.get('status', 'Pending'),
            timestamp=data.get('timestamp', datetime.now())
        )
        
        db.add(shift_report)
        db.commit()
        db.refresh(shift_report)
        
        db.close()
        
        return jsonify({
            'message': 'Shift report created successfully',
            'report': shift_report.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating shift report: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@reports_bp.route('/daily-summary', methods=['GET'])
def get_daily_summary():
    """Get daily summary data"""
    try:
        db = PostgresSessionLocal()
        
        # Get query parameters
        date = request.args.get('date')
        if not date:
            # Default to today
            date = datetime.now().date()
        else:
            try:
                date = datetime.fromisoformat(date).date()
            except ValueError:
                return jsonify({'error': 'Invalid date format'}), 400
        
        logger.info(f"Looking for daily summary for date: {date}")
        
        # Get summary for the specified date
        summary = db.query(DailySummary).filter(
            func.date(DailySummary.report_date) == date
        ).first()
        
        if not summary:
            logger.info("No summary found for the date, returning default values")
            # If no summary exists, create a default one
            summary_data = {
                'report_date': datetime.combine(date, datetime.min.time()).isoformat(),
                'total_wheat': 0,
                'total_flour': 0,
                'total_bran': 0,
                'total_water': 0,
                'total_packing': 0,
                'efficiency_percent': 0,
                'wheat_unit': 'T',
                'flour_unit': 'T',
                'bran_unit': 'T',
                'water_unit': 'm³',
                'packing_unit': 'Bags'
            }
        else:
            logger.info(f"Found summary: {summary.to_dict()}")
            summary_data = summary.to_dict()
        
        db.close()
        
        return jsonify(summary_data)
        
    except Exception as e:
        logger.error(f"Error fetching daily summary: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500

@reports_bp.route('/daily-summary', methods=['POST'])
def create_daily_summary():
    """Create or update daily summary"""
    try:
        db = PostgresSessionLocal()
        
        data = request.get_json()
        
        # Validate required fields
        if 'report_date' not in data:
            return jsonify({'error': 'Missing required field: report_date'}), 400
        
        # Parse date
        try:
            report_date = datetime.fromisoformat(data['report_date'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid report_date format'}), 400
        
        # Check if summary already exists for this date
        existing_summary = db.query(DailySummary).filter(
            func.date(DailySummary.report_date) == report_date.date()
        ).first()
        
        if existing_summary:
            # Update existing summary
            for key, value in data.items():
                if hasattr(existing_summary, key) and key != 'id':
                    setattr(existing_summary, key, value)
            summary = existing_summary
        else:
            # Create new summary
            summary = DailySummary(
                report_date=report_date,
                total_wheat=data.get('total_wheat', 0),
                total_flour=data.get('total_flour', 0),
                total_bran=data.get('total_bran', 0),
                total_water=data.get('total_water', 0),
                total_packing=data.get('total_packing', 0),
                efficiency_percent=data.get('efficiency_percent', 0),
                wheat_unit=data.get('wheat_unit', 'T'),
                flour_unit=data.get('flour_unit', 'T'),
                bran_unit=data.get('bran_unit', 'T'),
                water_unit=data.get('water_unit', 'm³'),
                packing_unit=data.get('packing_unit', 'Bags')
            )
            db.add(summary)
        
        db.commit()
        db.refresh(summary)
        
        db.close()
        
        return jsonify({
            'message': 'Daily summary saved successfully',
            'summary': summary.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating daily summary: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@reports_bp.route('/export-pdf', methods=['POST'])
def export_pdf():
    """Export reports to PDF"""
    try:
        data = request.get_json()
        
        # This would integrate with your existing PDF export logic
        # For now, return success
        return jsonify({
            'message': 'PDF export initiated successfully',
            'download_url': '/api/reports/download/pdf/export.pdf'
        })
        
    except Exception as e:
        logger.error(f"Error exporting PDF: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@reports_bp.route('/send-to-sap', methods=['POST'])
def send_to_sap():
    """Send reports to SAP"""
    try:
        data = request.get_json()
        
        # This would integrate with your existing SAP integration
        # For now, return success
        return jsonify({
            'message': 'Reports sent to SAP successfully',
            'sap_reference': f'SAP_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        })
        
    except Exception as e:
        logger.error(f"Error sending to SAP: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@reports_bp.route('/test-db', methods=['GET'])
def test_database():
    """Test database connection and table existence"""
    try:
        db = PostgresSessionLocal()
        
        from sqlalchemy import text
        
        # Test basic connection
        result = db.execute(text("SELECT 1 as test")).fetchone()
        logger.info(f"Database connection test: {result}")
        
        # Check if tables exist
        tables_result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('shift_reports', 'daily_summaries')
        """)).fetchall()
        
        table_names = [row[0] for row in tables_result]
        logger.info(f"Found tables: {table_names}")
        
        # If shift_reports exists, check row count
        row_count = 0
        if 'shift_reports' in table_names:
            count_result = db.execute(text("SELECT COUNT(*) FROM shift_reports")).fetchone()
            row_count = count_result[0] if count_result else 0
            logger.info(f"shift_reports table has {row_count} rows")
            
            # Get sample data
            if row_count > 0:
                sample_result = db.execute(text("SELECT * FROM shift_reports LIMIT 1")).fetchone()
                logger.info(f"Sample row: {sample_result}")
        
        db.close()
        
        return jsonify({
            'connection_test': 'success',
            'tables_found': table_names,
            'shift_reports_count': row_count if 'shift_reports' in table_names else 0
        })
        
    except Exception as e:
        logger.error(f"Error testing database: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Database test failed', 'details': str(e)}), 500

@reports_bp.route('/seed-data', methods=['POST'])
def seed_sample_data():
    """Insert sample data for testing"""
    try:
        db = PostgresSessionLocal()
        
        # Check if data already exists
        existing_count = db.query(ShiftReport).count()
        if existing_count > 0:
            return jsonify({'message': f'Data already exists ({existing_count} records)'})
        
        # Insert sample shift reports
        sample_reports = [
            ShiftReport(
                po_number='P012345',
                material='Bakery Flour',
                version='BKF1',
                planned_quantity=500.0,
                actual_quantity=480.0,
                unit='T',
                flour_extraction_percent=79.0,
                utilization_percent=92.0,
                loss_percent=0.5,
                status='Accepted'
            ),
            ShiftReport(
                po_number='P012346',
                material='Cake Flour',
                version='CKF1',
                planned_quantity=300.0,
                actual_quantity=295.0,
                unit='T',
                flour_extraction_percent=81.0,
                utilization_percent=90.0,
                loss_percent=0.4,
                status='Accepted'
            ),
            ShiftReport(
                po_number='P012347',
                material='Brawny Flour',
                version='BRF2',
                planned_quantity=250.0,
                actual_quantity=240.0,
                unit='T',
                flour_extraction_percent=77.0,
                utilization_percent=85.0,
                loss_percent=0.7,
                status='Rejected'
            ),
            ShiftReport(
                po_number='P012348',
                material='IWW Flour',
                version='IWF2',
                planned_quantity=200.0,
                actual_quantity=190.0,
                unit='T',
                flour_extraction_percent=75.0,
                utilization_percent=88.0,
                loss_percent=0.6,
                status='Accepted'
            )
        ]
        
        for report in sample_reports:
            db.add(report)
        
        # Insert sample daily summary
        today = datetime.now().date()
        existing_summary = db.query(DailySummary).filter(
            func.date(DailySummary.report_date) == today
        ).first()
        
        if not existing_summary:
            summary = DailySummary(
                report_date=datetime.combine(today, datetime.min.time()),
                total_wheat=1580.0,
                total_flour=136.0,
                total_bran=35.0,
                total_water=280.0,
                total_packing=11200.0,
                efficiency_percent=88.0
            )
            db.add(summary)
        
        db.commit()
        db.close()
        
        return jsonify({
            'message': 'Sample data inserted successfully',
            'shift_reports_added': len(sample_reports),
            'daily_summary_added': 1 if not existing_summary else 0
        })
        
    except Exception as e:
        logger.error(f"Error seeding data: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to seed data', 'details': str(e)}), 500

@reports_bp.route('/stats', methods=['GET'])
def get_reports_stats():
    """Get reports statistics"""
    try:
        db = PostgresSessionLocal()
        
        # Get basic statistics
        total_reports = db.query(ShiftReport).count()
        accepted_reports = db.query(ShiftReport).filter(ShiftReport.status == 'Accepted').count()
        rejected_reports = db.query(ShiftReport).filter(ShiftReport.status == 'Rejected').count()
        
        # Get recent reports count (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_reports = db.query(ShiftReport).filter(
            ShiftReport.timestamp >= week_ago
        ).count()
        
        db.close()
        
        return jsonify({
            'total_reports': total_reports,
            'accepted_reports': accepted_reports,
            'rejected_reports': rejected_reports,
            'recent_reports': recent_reports,
            'acceptance_rate': round((accepted_reports / total_reports * 100) if total_reports > 0 else 0, 2)
        })
        
    except Exception as e:
        logger.error(f"Error fetching reports stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# ORDERS SUMMARY API - C31-T13 (Task 16)
# Get orders summary with date/shift filtering for Reports page
# =============================================================================

@reports_bp.route('/summary', methods=['GET'])
def get_report_summary():
    """
    Get orders summary with date and shift filtering.
    
    Query params:
    - start_date: YYYY-MM-DD (required)
    - end_date: YYYY-MM-DD (required)
    - shifts: comma-separated (A,B,C) - optional, defaults to all shifts
    - status: filter by status - optional
    - order_type: MILLING or PACKING - optional
    - limit: max orders to return (default 1000)
    - offset: pagination offset (default 0)
    
    Returns:
    {
        "success": true,
        "orders": [...],
        "summary": {
            "total_orders": 100,
            "by_status": {"Pending": 50, "InProgress": 20, ...},
            "by_type": {"MILLING": 60, "PACKING": 40},
            "production_totals": {...}
        }
    }
    """
    from sqlalchemy import text
    from database import postgres_engine
    
    # Parse query parameters
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    shifts_str = request.args.get("shifts")  # e.g., "A,B,C"
    status_filter = request.args.get("status")
    order_type_filter = request.args.get("order_type")
    
    try:
        limit = min(int(request.args.get("limit", 1000)), 10000)
        offset = int(request.args.get("offset", 0))
    except ValueError:
        limit, offset = 1000, 0
    
    # Validate required parameters
    if not start_date_str or not end_date_str:
        return jsonify({
            "success": False,
            "error": "Missing required parameters: start_date and end_date (format: YYYY-MM-DD)"
        }), 400
    
    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        # Set end_date to end of day
        end_date = end_date + timedelta(days=1)
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        }), 400
    
    # Validate date range
    if start_date >= end_date:
        return jsonify({
            "success": False,
            "error": "start_date must be before end_date"
        }), 400
    
    # Parse shifts
    shifts = None
    if shifts_str:
        shifts = [s.strip().upper() for s in shifts_str.split(",") if s.strip()]
    
    try:
        # Build SQL query with filters
        base_sql = """
            SELECT 
                id,
                order_id,
                material,
                version,
                batch,
                quantity,
                unit,
                status,
                priority,
                plant,
                confirmed_qty,
                material_desc,
                expected_weight,
                created_at,
                updated_at,
                order_type,
                current_shift,
                weight_shift_a,
                weight_shift_b,
                weight_shift_c,
                confirmed_shift_a,
                confirmed_shift_b,
                confirmed_shift_c,
                overflow_weight,
                validation_method
            FROM process_orders
            WHERE created_at >= :start_date AND created_at < :end_date
        """
        
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset
        }
        
        # Add shift filter
        if shifts:
            base_sql += " AND current_shift IN :shifts"
            params["shifts"] = tuple(shifts)
        
        # Add status filter
        if status_filter and status_filter != "All":
            base_sql += " AND status = :status"
            params["status"] = status_filter
        
        # Add order type filter
        if order_type_filter:
            base_sql += " AND order_type = :order_type"
            params["order_type"] = order_type_filter
        
        # Add ordering and pagination
        orders_sql = base_sql + " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        
        # Count query (without pagination)
        count_sql = f"SELECT COUNT(*) FROM ({base_sql}) AS filtered_orders"
        
        # Summary queries
        status_count_sql = f"""
            SELECT status, COUNT(*) as count 
            FROM ({base_sql}) AS filtered_orders 
            GROUP BY status
        """
        
        type_count_sql = f"""
            SELECT order_type, COUNT(*) as count 
            FROM ({base_sql}) AS filtered_orders 
            GROUP BY order_type
        """
        
        production_sql = f"""
            SELECT 
                order_type,
                SUM(COALESCE(confirmed_qty, 0)) as total_confirmed,
                SUM(COALESCE(weight_shift_a, 0)) as total_shift_a,
                SUM(COALESCE(weight_shift_b, 0)) as total_shift_b,
                SUM(COALESCE(weight_shift_c, 0)) as total_shift_c,
                SUM(COALESCE(overflow_weight, 0)) as total_overflow
            FROM ({base_sql}) AS filtered_orders
            GROUP BY order_type
        """
        
        logger.info(f"Report summary query: start={start_date}, end={end_date}, shifts={shifts}, status={status_filter}")
        
        with postgres_engine.connect() as conn:
            # Execute main query
            rows = conn.execute(text(orders_sql), params).mappings().all()
            
            # Execute count query
            total_count = conn.execute(text(count_sql), params).scalar() or 0
            
            # Execute summary queries
            status_counts = {}
            status_rows = conn.execute(text(status_count_sql), params).mappings().all()
            for row in status_rows:
                status_counts[row["status"] or "Unknown"] = row["count"]
            
            type_counts = {}
            type_rows = conn.execute(text(type_count_sql), params).mappings().all()
            for row in type_rows:
                type_counts[row["order_type"] or "Unknown"] = row["count"]
            
            production_totals = {}
            prod_rows = conn.execute(text(production_sql), params).mappings().all()
            for row in prod_rows:
                order_type = row["order_type"] or "Unknown"
                production_totals[order_type] = {
                    "total_confirmed": float(row["total_confirmed"] or 0),
                    "total_shift_a": float(row["total_shift_a"] or 0),
                    "total_shift_b": float(row["total_shift_b"] or 0),
                    "total_shift_c": float(row["total_shift_c"] or 0),
                    "total_overflow": float(row["total_overflow"] or 0),
                }
            
            # Format orders for response
            orders_data = []
            for row in rows:
                order = {
                    "id": row["id"],
                    "po_number": row["order_id"],
                    "material": row["material"],
                    "version": row["version"],
                    "batch": row["batch"],
                    "quantity": float(row["quantity"]) if row["quantity"] else None,
                    "unit": row["unit"],
                    "status": row["status"],
                    "priority": row["priority"],
                    "plant": row["plant"],
                    "confirmed_qty": float(row["confirmed_qty"]) if row["confirmed_qty"] else None,
                    "material_desc": row["material_desc"],
                    "expected_weight": float(row["expected_weight"]) if row["expected_weight"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    "order_type": row["order_type"],
                    "current_shift": row["current_shift"],
                    "weight_shift_a": float(row["weight_shift_a"]) if row["weight_shift_a"] else 0,
                    "weight_shift_b": float(row["weight_shift_b"]) if row["weight_shift_b"] else 0,
                    "weight_shift_c": float(row["weight_shift_c"]) if row["weight_shift_c"] else 0,
                    "validation_method": row["validation_method"],
                }
                orders_data.append(order)
            
            return jsonify({
                "success": True,
                "orders": orders_data,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "summary": {
                    "total_orders": total_count,
                    "by_status": status_counts,
                    "by_type": type_counts,
                    "production_totals": production_totals,
                    "filters_applied": {
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                        "shifts": shifts if shifts else "ALL",
                        "status": status_filter if status_filter else "ALL",
                        "order_type": order_type_filter if order_type_filter else "ALL"
                    }
                }
            })
            
    except Exception as e:
        logger.error(f"Error in get_report_summary: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Error fetching report summary: {str(e)}"
        }), 500


# =============================================================================
# KPI TRACKING API - Get KPI data from kpi_send_tracking table
# Returns only kpi_payload_sent (JSON) and shift_code columns
# =============================================================================

@reports_bp.route('/kpi-tracking', methods=['GET'])
def get_kpi_tracking():
    """
    Get KPI tracking data from kpi_send_tracking table.
    Only returns kpi_payload_sent (JSON) and shift_code columns, not baseline columns.
    
    Query params:
    - start_date: YYYY-MM-DD or YYYY-MM-DD HH:mm:ss (required)
    - end_date: YYYY-MM-DD or YYYY-MM-DD HH:mm:ss (required)
    - shifts: comma-separated (A,B,C) - optional, defaults to all shifts
    - department: MILLING or PACKING - optional, defaults to both
    - limit: max records to return (default 1000)
    - offset: pagination offset (default 0)
    
    Returns:
    {
        "success": true,
        "data": [
            {
                "id": 34,
                "department": "MILLING",
                "shift_code": "A",
                "last_sent_at": "2026-01-22T21:02:11.040671-08:00",
                "send_type": "manual",
                "kpi_payload": {
                    "NET_HOURS": "8.0",
                    "TOTAL_WATER": "13.01",
                    "MILLING_GAIN": "36.42",
                    ...
                }
            },
            ...
        ],
        "total_count": 10,
        "limit": 1000,
        "offset": 0
    }
    """
    from models.kpi_send_tracking import KpiSendTracking
    
    # Parse query parameters
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    shifts_str = request.args.get("shifts")  # e.g., "A,B,C"
    department_filter = request.args.get("department")  # MILLING or PACKING
    
    try:
        limit = min(int(request.args.get("limit", 1000)), 10000)
        offset = int(request.args.get("offset", 0))
    except ValueError:
        limit, offset = 1000, 0
    
    # Validate required parameters
    if not start_date_str or not end_date_str:
        return jsonify({
            "success": False,
            "error": "Missing required parameters: start_date and end_date (format: YYYY-MM-DD or YYYY-MM-DD HH:mm:ss)"
        }), 400
    
    # Parse dates
    try:
        # Try parsing with time first
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            # Set to end of day if only date provided
            end_date = end_date + timedelta(days=1)
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": f"Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:mm:ss. Error: {str(e)}"
        }), 400
    
    # Validate date range
    if start_date >= end_date:
        return jsonify({
            "success": False,
            "error": "start_date must be before end_date"
        }), 400
    
    # Parse shifts
    shifts = None
    if shifts_str:
        shifts = [s.strip().upper() for s in shifts_str.split(",") if s.strip()]
        # If all shifts selected, don't filter
        if set(shifts) == {'A', 'B', 'C'}:
            shifts = None
    
    try:
        db = PostgresSessionLocal()
        
        # Build query - only select kpi_payload_sent and shift_code (plus metadata)
        query = db.query(
            KpiSendTracking.id,
            KpiSendTracking.department,
            KpiSendTracking.shift_code,
            KpiSendTracking.last_sent_at,
            KpiSendTracking.kpi_payload_sent,
            KpiSendTracking.send_type
        ).filter(
            and_(
                KpiSendTracking.last_sent_at >= start_date,
                KpiSendTracking.last_sent_at < end_date
            )
        )
        
        # Filter by department
        if department_filter:
            query = query.filter(KpiSendTracking.department == department_filter.upper())
        
        # Filter by shift code
        if shifts:
            query = query.filter(KpiSendTracking.shift_code.in_(shifts))
        else:
            # If no shift filter, include all shifts (A, B, C) and NULL
            query = query.filter(
                or_(
                    KpiSendTracking.shift_code.in_(['A', 'B', 'C']),
                    KpiSendTracking.shift_code.is_(None)
                )
            )
        
        # Only return records that have kpi_payload_sent (not NULL)
        query = query.filter(KpiSendTracking.kpi_payload_sent.isnot(None))
        
        # Get total count
        total_count = query.count()
        
        # Order by last_sent_at descending (newest first)
        query = query.order_by(desc(KpiSendTracking.last_sent_at))
        
        # Apply pagination
        records = query.offset(offset).limit(limit).all()
        
        # Format response
        data = []
        for record in records:
            data.append({
                "id": record.id,
                "department": record.department,
                "shift_code": record.shift_code,
                "last_sent_at": record.last_sent_at.isoformat() if record.last_sent_at else None,
                "send_type": record.send_type,
                "kpi_payload": record.kpi_payload_sent  # This is the JSON payload
            })
        
        db.close()
        
        logger.info(f"KPI tracking query: start={start_date}, end={end_date}, shifts={shifts}, department={department_filter}, found={total_count} records")
        
        return jsonify({
            "success": True,
            "data": data,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        })
        
    except Exception as e:
        logger.error(f"Error in get_kpi_tracking: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Error fetching KPI tracking data: {str(e)}"
        }), 500
