# Backend/create_reports_tables.py
"""
Script to create the reports tables in PostgreSQL database.
Run this script to set up the shift_reports and daily_summaries tables.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.shift_report import ShiftReport, DailySummary, Base
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create the reports tables in PostgreSQL"""
    try:
        # Use PostgreSQL engine
        postgres_engine = create_engine("postgresql+psycopg2://postgres:Hercules2@localhost:5432/sap")
        
        # Create all tables
        Base.metadata.create_all(bind=postgres_engine)
        
        logger.info("✅ Reports tables created successfully!")
        
        # Verify tables were created
        with postgres_engine.connect() as conn:
            # Check if tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('shift_reports', 'daily_summaries')
            """))
            
            tables = [row[0] for row in result]
            logger.info(f"📋 Created tables: {tables}")
            
            if 'shift_reports' in tables:
                # Get table structure
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'shift_reports'
                    ORDER BY ordinal_position
                """))
                
                logger.info("📊 Shift Reports table structure:")
                for row in result:
                    logger.info(f"  - {row[0]}: {row[1]} ({'NULL' if row[2] == 'YES' else 'NOT NULL'})")
            
            if 'daily_summaries' in tables:
                # Get table structure
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'daily_summaries'
                    ORDER BY ordinal_position
                """))
                
                logger.info("📊 Daily Summaries table structure:")
                for row in result:
                    logger.info(f"  - {row[0]}: {row[1]} ({'NULL' if row[2] == 'YES' else 'NOT NULL'})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        return False

def seed_sample_data():
    """Seed the tables with sample data"""
    try:
        postgres_engine = create_engine("postgresql+psycopg2://postgres:Hercules2@localhost:5432/sap")
        SessionLocal = sessionmaker(bind=postgres_engine)
        db = SessionLocal()
        
        # Sample shift reports
        sample_reports = [
            {
                'po_number': 'P012345',
                'material': 'Bakery Flour',
                'version': 'BKF1',
                'planned_quantity': 500.0,
                'actual_quantity': 480.0,
                'unit': 'T',
                'flour_extraction_percent': 79.0,
                'utilization_percent': 92.0,
                'loss_percent': 0.5,
                'status': 'Accepted'
            },
            {
                'po_number': 'P012346',
                'material': 'Cake Flour',
                'version': 'CKF1',
                'planned_quantity': 300.0,
                'actual_quantity': 295.0,
                'unit': 'T',
                'flour_extraction_percent': 81.0,
                'utilization_percent': 90.0,
                'loss_percent': 0.4,
                'status': 'Accepted'
            },
            {
                'po_number': 'P012347',
                'material': 'Brawny Flour',
                'version': 'BRF2',
                'planned_quantity': 250.0,
                'actual_quantity': 240.0,
                'unit': 'T',
                'flour_extraction_percent': 77.0,
                'utilization_percent': 85.0,
                'loss_percent': 0.7,
                'status': 'Rejected'
            },
            {
                'po_number': 'P012348',
                'material': 'IWW Flour',
                'version': 'IWF2',
                'planned_quantity': 200.0,
                'actual_quantity': 190.0,
                'unit': 'T',
                'flour_extraction_percent': 75.0,
                'utilization_percent': 88.0,
                'loss_percent': 0.6,
                'status': 'Accepted'
            }
        ]
        
        # Insert sample shift reports
        for report_data in sample_reports:
            # Check if report already exists
            existing = db.query(ShiftReport).filter(
                ShiftReport.po_number == report_data['po_number']
            ).first()
            
            if not existing:
                report = ShiftReport(**report_data)
                db.add(report)
                logger.info(f"📝 Added sample report: {report_data['po_number']}")
        
        # Sample daily summary
        from datetime import datetime, date
        
        today = date.today()
        existing_summary = db.query(DailySummary).filter(
            DailySummary.report_date == datetime.combine(today, datetime.min.time())
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
            logger.info(f"📊 Added daily summary for {today}")
        
        db.commit()
        db.close()
        
        logger.info("✅ Sample data seeded successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error seeding sample data: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Creating reports tables...")
    
    if create_tables():
        print("\n🌱 Seeding sample data...")
        seed_sample_data()
        print("\n✅ Setup completed successfully!")
    else:
        print("\n❌ Setup failed!")
