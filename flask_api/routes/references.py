from flask import Blueprint, request, jsonify
from database import get_db
from models import Section, Department, Place, Property, AssetType
from routes.auth import require_auth

references_bp = Blueprint('references', __name__)

@references_bp.route('/sections', methods=['GET'])
@require_auth
def get_sections(user):
    """Get all sections"""
    try:
        db = next(get_db())
        sections = db.query(Section).all()
        
        result = []
        for section in sections:
            result.append({
                "sec_id": section.sec_id,
                "sec_name": section.sec_name,
                "sec_name_eng": section.sec_name_eng,
                "sec_remark": section.sec_remark
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to fetch sections"
            }
        }), 500

@references_bp.route('/departments', methods=['GET'])
@require_auth
def get_departments(user):
    """Get departments, optionally filtered by section"""
    try:
        db = next(get_db())
        sec_id = request.args.get('sec_id')
        
        query = db.query(Department)
        if sec_id:
            query = query.filter(Department.sec_id == sec_id)
        departments = query.all()
        
        result = []
        for dept in departments:
            result.append({
                "dep_id": dept.dep_id,
                "dep_name": dept.dep_name,
                "dep_name_eng": dept.dep_name_eng,
                "dep_remark": dept.dep_remark,
                "sec_id": dept.sec_id
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to fetch departments"
            }
        }), 500

@references_bp.route('/places', methods=['GET'])
@require_auth
def get_places(user):
    """Get all places/locations"""
    try:
        db = next(get_db())
        places = db.query(Place).all()
        
        result = []
        for place in places:
            result.append({
                "p_id": place.p_id,
                "p_name": place.p_name,
                "p_name_eng": place.p_name_eng,
                "p_remark": place.p_remark
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to fetch places"
            }
        }), 500

@references_bp.route('/properties', methods=['GET'])
@require_auth
def get_properties(user):
    """Get all property types"""
    try:
        db = next(get_db())
        properties = db.query(Property).all()
        
        result = []
        for prop in properties:
            result.append({
                "pro_id": prop.pro_id,
                "pro_name": prop.pro_name,
                "pro_name_eng": prop.pro_name_eng
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to fetch properties"
            }
        }), 500

@references_bp.route('/types', methods=['GET'])
@require_auth
def get_asset_types(user):
    """Get all asset types"""
    try:
        db = next(get_db())
        types = db.query(AssetType).all()
        
        result = []
        for asset_type in types:
            result.append({
                "type_id": asset_type.type_id,
                "type_name": asset_type.type_name,
                "type_name_eng": asset_type.type_name_eng,
                "type_remark": asset_type.type_remark
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to fetch asset types"
            }
        }), 500
