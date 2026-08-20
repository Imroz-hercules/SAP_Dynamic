from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import SessionLocal
from services.classification_service import resolve_order_type  # A1: rules-driven routing

material_bp = Blueprint("material_bp", __name__)

# A6: the fallback used when a caller adds a packing material without naming a
# line. "PL601" was hardcoded here; a line that has no palletizer_mapping row
# produces an order that classifies but never tracks, so the default has to
# come from the data.
DEFAULT_PACKING_LINE_FALLBACK = "PL601"


def _default_packing_line() -> str:
    """
    Lowest-numbered packing line that actually has a mapping.

    Falls back to the historical literal if the table cannot be read — this is
    a convenience default on a create path, not something worth failing over.
    """
    try:
        from database import PostgresSessionLocal
        from models.palletizer_mapping import PalletizerMapping

        with PostgresSessionLocal() as db:
            row = (
                db.query(PalletizerMapping.palletizer)
                  .filter(PalletizerMapping.palletizer.isnot(None))
                  .order_by(PalletizerMapping.palletizer.asc())
                  .first()
            )
        if row and row[0]:
            return row[0]
    except Exception as exc:
        print(f"⚠️ [materials] Could not read a default packing line ({exc}) — "
              f"using {DEFAULT_PACKING_LINE_FALLBACK}")
    return DEFAULT_PACKING_LINE_FALLBACK

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
        
        # ✅ A1: was `if '13' in material_code` — a SUBSTRING match, so any code
        # containing "13" anywhere matched, including inside the zero padding or
        # mid-code. Everywhere else in the system classifies on the prefix of the
        # zero-stripped code. Both now go through the same classification_rules
        # lookup, so they cannot drift apart again.
        material_code = data.get('material', '')
        order_type = resolve_order_type(material_code)

        # Set default recipe if not provided
        if not data.get('recipe'):
            if order_type == 'MILLING':
                data['recipe'] = 'Milling Recipe'
            elif order_type == 'PACKING':
                data['recipe'] = 'Packing Recipe'
            else:
                data['recipe'] = 'Default Recipe'

        # Set default packing line for milling materials if not provided or is N/A
        if not data.get('packingLine') or data.get('packingLine') == 'N/A':
            if order_type == 'MILLING':
                data['packingLine'] = 'N/A'  # Milling materials don't need packing lines
            elif order_type == 'PACKING' and not data.get('packingLine'):
                # ✅ A6: was a hardcoded 'PL601'. Now the lowest-numbered line
                # that actually has a mapping, so this cannot name a line that
                # does not exist. The screen sends an explicit value anyway —
                # this only fires when the caller omits one.
                data['packingLine'] = _default_packing_line()
        
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
