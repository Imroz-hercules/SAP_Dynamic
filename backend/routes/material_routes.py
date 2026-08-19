from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import SessionLocal

material_bp = Blueprint("material_bp", __name__)

@material_bp.route("/api/materials/health", methods=["GET"])
def health_check():
    """Health check endpoint for material routes"""
    try:
        session = SessionLocal()
        # Test database connection
        session.execute(text("SELECT 1"))
        session.close()
        return jsonify({"status": "healthy", "message": "Material routes are working"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@material_bp.route("/api/materials", methods=["GET"])
def get_materials():
    session = SessionLocal()
    try:
        result = session.execute(text("SELECT * FROM material_mappings ORDER BY id DESC"))
        materials = [dict(row._mapping) for row in result]
        return jsonify(materials)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@material_bp.route("/api/materials", methods=["POST"])
def add_material():
    data = request.get_json()
    session = SessionLocal()
    try:
        # Validate required fields
        required_fields = ['material', 'version', 'scale', 'packingLine']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Set default recipe if not provided
        if not data.get('recipe'):
            # Determine recipe based on material code
            material_code = data.get('material', '')
            if '13' in material_code:
                data['recipe'] = 'Milling Recipe'
            elif '14' in material_code:
                data['recipe'] = 'Packing Recipe'
            else:
                data['recipe'] = 'Default Recipe'
        
        # Set default packing line for milling materials if not provided or is N/A
        if not data.get('packingLine') or data.get('packingLine') == 'N/A':
            material_code = data.get('material', '')
            if '13' in material_code:
                data['packingLine'] = 'N/A'  # Milling materials don't need packing lines
            elif '14' in material_code and not data.get('packingLine'):
                data['packingLine'] = 'PL601'  # Default packing line for packing materials
        
        # Note: Ensure the keys in `data` match the column names exactly.
        insert_query = text("""
            INSERT INTO material_mappings (material, version, scale, recipe, packingLine)
            VALUES (:material, :version, :scale, :recipe, :packingLine)
        """)
        session.execute(insert_query, data)
        session.commit()
        return jsonify({"message": "Material added successfully"}), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
