from flask import Blueprint, request, jsonify
from database import get_db
from models import Inventory, Asset
from routes.auth import require_auth
import logging

logger = logging.getLogger(__name__)
inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/', methods=['GET'])
@require_auth
def get_inventory(user):
    """Get inventory records"""
    try:
        db = next(get_db())
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        tre_id = request.args.get('tre_id')
        
        # Build query
        query = db.query(Inventory, Asset.tre_name.label('asset_name'), Asset.tre_barcode.label('asset_barcode'))\
                  .outerjoin(Asset, Inventory.tre_id == Asset.tre_id)
        
        if tre_id:
            query = query.filter(Inventory.tre_id == tre_id)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        inventory_records = query.offset(offset).limit(limit).all()
        
        # Convert to response format
        inventory_list = []
        for record in inventory_records:
            inventory, asset_name, asset_barcode = record
            inventory_list.append({
                "iv_id": inventory.iv_id,
                "tre_id": inventory.tre_id,
                "iv_price1": float(inventory.iv_price1) if inventory.iv_price1 else None,
                "iv_price2": float(inventory.iv_price2) if inventory.iv_price2 else None,
                "iv_price3": float(inventory.iv_price3) if inventory.iv_price3 else None,
                "iv_name": inventory.iv_name,
                "iv_remark": inventory.iv_remark,
                "iv_date": inventory.iv_date.isoformat() if inventory.iv_date else None,
                "asset_name": asset_name,
                "asset_barcode": asset_barcode
            })
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        pagination = {
            "current_page": page,
            "total_pages": total_pages,
            "total_records": total_count,
            "per_page": limit
        }
        
        return jsonify({
            "success": True,
            "data": inventory_list,
            "pagination": pagination
        })
        
    except Exception as e:
        logger.error(f"Error fetching inventory: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to fetch inventory"
            }
        }), 500

@inventory_bp.route('/', methods=['POST'])
@require_auth
def create_inventory_record(user):
    """Create inventory record"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "JSON data required"
                }
            }), 400
        
        # Validate required fields
        required_fields = ['tre_id', 'iv_price1']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": f"Missing required field: {field}"
                    }
                }), 400
        
        db = next(get_db())
        
        # Create inventory record
        inventory = Inventory(
            iv_id=f"BK25.{str(len(db.query(Inventory).all()) + 1).zfill(5)}",  # Simple ID generation
            tre_id=data['tre_id'],
            iv_price1=data['iv_price1'],
            iv_price2=data.get('iv_price2', data['iv_price1']),
            iv_price3=data.get('iv_price3', data['iv_price1']),
            iv_name=data.get('iv_name'),
            iv_remark=data.get('iv_remark')
        )
        
        db.add(inventory)
        db.commit()
        db.refresh(inventory)
        
        return jsonify({
            "success": True,
            "message": "Inventory record created",
            "data": {
                "iv_id": inventory.iv_id
            }
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating inventory record: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to create inventory record"
            }
        }), 500
