from flask import Blueprint, request, jsonify
from database import postgres_engine, PostgresSessionLocal
from models.milling_version_mapping import MillingVersionMapping
from services.classification_service import invalidate_cache  # A3: drop cached classifications on write

milling_bp = Blueprint("milling_mapping", __name__)

# ------------------------------
# GET ALL MAPPINGS
# ------------------------------
@milling_bp.route("/api/milling-mapping", methods=["GET"])
def get_milling_mappings():
    session = PostgresSessionLocal()
    try:
        mappings = session.query(MillingVersionMapping).order_by(
            MillingVersionMapping.version.asc()
        ).all()

        result = []
        for m in mappings:
            result.append({
                "id": m.id,
                "version": m.version,
                "scales": m.scales,
                "formula": m.formula,
                "scale1": m.scale1,
                "scale2": m.scale2,
                "description": m.description,
                "scada_recipe_name": m.scada_recipe_name
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()


# ------------------------------
# ADD NEW MAPPING
# ------------------------------
@milling_bp.route("/api/milling-mapping", methods=["POST"])
def add_milling_mapping():
    data = request.get_json()
    session = PostgresSessionLocal()

    try:
        # Required fields
        required = ["version", "scales", "formula"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        # ✅ CRITICAL: Ensure table exists before inserting
        from sqlalchemy import inspect
        inspector = inspect(postgres_engine)
        if "milling_version_mappings" not in inspector.get_table_names():
            print("⚠️ Table 'milling_version_mappings' does not exist. Creating it...")
            from database import PostgresBase
            PostgresBase.metadata.create_all(postgres_engine, tables=[MillingVersionMapping.__table__])
            print("✅ Table 'milling_version_mappings' created")

        # ✅ CRITICAL: Ensure scales is properly formatted (should be a list/array)
        scales_data = data["scales"]
        if isinstance(scales_data, str):
            # If it's a string, try to parse it as JSON
            import json
            try:
                scales_data = json.loads(scales_data)
            except:
                return jsonify({"error": "Invalid scales format. Expected JSON array."}), 400

        new_mapping = MillingVersionMapping(
            version=data["version"].upper().strip(),
            scales=scales_data,  # Use processed scales_data
            formula=data["formula"].strip(),
            scale1=data.get("scale1") if data.get("scale1") else None,
            scale2=data.get("scale2") if data.get("scale2") else None,
            description=data.get("description") if data.get("description") else None,
            scada_recipe_name=(data.get("scada_recipe_name") or "").strip() or None
        )

        session.add(new_mapping)
        session.flush()  # Flush to get the ID
        
        # ✅ CRITICAL: Verify the record was added
        mapping_id = new_mapping.id
        print(f"✅ Added milling mapping: id={mapping_id}, version={new_mapping.version}, scales={new_mapping.scales}")
        
        session.commit()
        # ✅ A3: a mapping change must reach running orders now, not
        #    when the classification TTL happens to expire.
        invalidate_cache()
        
        # ✅ CRITICAL: Verify it was actually saved by querying it back
        verify_mapping = session.query(MillingVersionMapping).filter(
            MillingVersionMapping.id == mapping_id
        ).first()
        
        if not verify_mapping:
            print(f"❌ ERROR: Mapping was not saved! id={mapping_id}")
            return jsonify({"error": "Mapping was not saved to database"}), 500
        
        print(f"✅ Verified mapping saved: id={verify_mapping.id}, version={verify_mapping.version}")

        return jsonify({
            "message": "Milling mapping added successfully",
            "id": mapping_id,
            "version": verify_mapping.version
        }), 201

    except Exception as e:
        session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error adding milling mapping: {e}")
        print(f"❌ Traceback: {error_trace}")
        return jsonify({"error": str(e), "traceback": error_trace}), 500

    finally:
        session.close()


# ------------------------------
# UPDATE EXISTING MAPPING
# ------------------------------
@milling_bp.route("/api/milling-mapping/<int:id>", methods=["PATCH"])
def update_milling_mapping(id):
    data = request.get_json()
    session = PostgresSessionLocal()

    try:
        mapping = session.query(MillingVersionMapping).get(id)
        if not mapping:
            return jsonify({"error": "Mapping not found"}), 404

        # ✅ CRITICAL: Handle scales field properly (should be a list/array)
        scales_data = data.get("scales", mapping.scales)
        if isinstance(scales_data, str):
            # If it's a string, try to parse it as JSON
            import json
            try:
                scales_data = json.loads(scales_data)
            except:
                return jsonify({"error": "Invalid scales format. Expected JSON array."}), 400
        
        if data.get("version"):
            mapping.version = data.get("version").upper().strip()
        mapping.scales = scales_data
        if data.get("formula"):
            mapping.formula = data.get("formula").strip()
        mapping.scale1 = data.get("scale1", mapping.scale1) if data.get("scale1") else None
        mapping.scale2 = data.get("scale2", mapping.scale2) if data.get("scale2") else None
        
        # Update description if provided (allow empty string to clear it)
        if "description" in data:
            mapping.description = data.get("description") if data.get("description") else None
        # Update SCADA recipe name if provided
        if "scada_recipe_name" in data:
            mapping.scada_recipe_name = (data.get("scada_recipe_name") or "").strip() or None

        session.commit()
        # ✅ A3: a mapping change must reach running orders now, not
        #    when the classification TTL happens to expire.
        invalidate_cache()

        return jsonify({"message": "Mapping updated successfully"}), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()


# ------------------------------
# DELETE MAPPING
# ------------------------------
@milling_bp.route("/api/milling-mapping/<int:id>", methods=["DELETE"])
def delete_milling_mapping(id):
    session = PostgresSessionLocal()

    try:
        mapping = session.query(MillingVersionMapping).get(id)
        if not mapping:
            return jsonify({"error": "Mapping not found"}), 404

        session.delete(mapping)
        session.commit()
        # ✅ A3: a mapping change must reach running orders now, not
        #    when the classification TTL happens to expire.
        invalidate_cache()

        return jsonify({"message": "Mapping deleted"}), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()

