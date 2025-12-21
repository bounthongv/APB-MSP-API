from flask import Blueprint, request, jsonify
from database import get_db
from models import Asset, Section, Department, Property, AssetType, Place
from routes.auth import require_auth
from sqlalchemy import and_, or_, desc, asc
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
assets_bp = Blueprint('assets', __name__)


@assets_bp.route('/', methods=['GET'])
@require_auth
def get_assets(user):
    """Get paginated list of assets with filtering and search"""
    try:
        db = next(get_db())
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        sec_id = request.args.get('sec_id')
        dep_id = request.args.get('dep_id')
        type_id = request.args.get('type_id')
        search = request.args.get('search')
        barcode = request.args.get('barcode')
        status = request.args.get('status')  # Add status filter
        price_min = request.args.get('price_min', type=Decimal)
        price_max = request.args.get('price_max', type=Decimal)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build query with joins for related data
        query = db.query(
            Asset,
            Section.sec_name.label('section_name'),
            Department.dep_name.label('department_name'),
            Property.pro_name.label('property_name'),
            AssetType.type_name.label('type_name'),
            Place.p_name.label('place_name')
        ).outerjoin(Section, Asset.sec_id == Section.sec_id)\
         .outerjoin(Department, Asset.dep_id == Department.dep_id)\
         .outerjoin(Property, Asset.pro_id == Property.pro_id)\
         .outerjoin(AssetType, Asset.type_id == AssetType.type_id)\
         .outerjoin(Place, Asset.p_id == Place.p_id)
        
        # Apply filters
        if sec_id:
            query = query.filter(Asset.sec_id == sec_id)
        if dep_id:
            query = query.filter(Asset.dep_id == dep_id)
        if type_id:
            query = query.filter(Asset.type_id == type_id)
        if search:
            search_filter = or_(
                Asset.tre_name.ilike(f"%{search}%"),
                Asset.tre_name_eng.ilike(f"%{search}%"),
                Asset.tre_num.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        if barcode:
            query = query.filter(Asset.tre_barcode == barcode)
        if status:
            if status == "active":
                # Filter for active assets (tre_sts_box is null, '1', or 'active')
                query = query.filter(or_(
                    Asset.tre_sts_box.is_(None), 
                    Asset.tre_sts_box == "1",
                    Asset.tre_sts_box == "active"
                ))
            elif status == "inactive":
                # Filter for inactive assets (tre_sts_box is '0', 'inactive', or other inactive values)
                query = query.filter(or_(
                    Asset.tre_sts_box == "0",
                    Asset.tre_sts_box == "inactive"
                ))
            else:
                # Filter for specific status
                query = query.filter(Asset.tre_sts_box == status)
        if price_min is not None:
            query = query.filter(Asset.tre_price >= price_min)
        if price_max is not None:
            query = query.filter(Asset.tre_price <= price_max)
        if date_from:
            query = query.filter(Asset.tre_sale_date >= date_from)
        if date_to:
            query = query.filter(Asset.tre_sale_date <= date_to)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        assets = query.offset(offset).limit(limit).all()
        
        # Convert to response format
        asset_list = []
        for asset_data in assets:
            asset, section_name, department_name, property_name, type_name, place_name = asset_data
            
            asset_response = {
                "tre_id": asset.tre_id,
                "tre_num": asset.tre_num,
                "tre_name": asset.tre_name,
                "tre_name_eng": asset.tre_name_eng,
                "tre_barcode": asset.tre_barcode,
                "tre_price": float(asset.tre_price) if asset.tre_price else None,
                "tre_cur": asset.tre_cur,
                "tre_qty": asset.tre_qty,
                "tre_unit": asset.tre_unit,
                "tre_sale_date": asset.tre_sale_date.isoformat() if asset.tre_sale_date else None,
                "tre_use_date": asset.tre_use_date.isoformat() if asset.tre_use_date else None,
                "tre_finit_date": asset.tre_finit_date.isoformat() if asset.tre_finit_date else None,
                "tre_qty_year": float(asset.tre_qty_year) if asset.tre_qty_year else None,
                "tre_qty_month": float(asset.tre_qty_month) if asset.tre_qty_month else None,
                "tre_qty_day": float(asset.tre_qty_day) if asset.tre_qty_day else None,
                "tre_remark": asset.tre_remark,
                "tre_status": "active" if (asset.tre_sts_box == "1" or asset.tre_sts_box is None) else "inactive",  # Convert numeric to text status
                "sec_id": asset.sec_id,
                "dep_id": asset.dep_id,
                "pro_id": asset.pro_id,
                "type_id": asset.type_id,
                "p_id": asset.p_id,
                "section_name": section_name,
                "department_name": department_name,
                "property_name": property_name,
                "type_name": type_name,
                "place_name": place_name
            }
            asset_list.append(asset_response)
        
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
            "data": asset_list,
            "pagination": pagination
        })
        
    except Exception as e:
        logger.error(f"Error fetching assets: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to fetch assets"
            }
        }), 500

@assets_bp.route('/update/<tre_id>', methods=['PUT'])
@require_auth
def update_asset(user, tre_id):
    """Update an existing asset"""
    try:
        db = next(get_db())
        
        # Get the asset to update
        asset = db.query(Asset).filter(Asset.tre_id == tre_id).first()
        if not asset:
            return jsonify({
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Asset not found"
                }
            }), 404
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "No data provided"
                }
            }), 400
        
        # Update asset fields
        if 'tre_name' in data:
            asset.tre_name = data['tre_name']
        if 'tre_name_eng' in data:
            asset.tre_name_eng = data['tre_name_eng']
        if 'tre_price' in data:
            asset.tre_price = Decimal(str(data['tre_price']))
        if 'tre_qty' in data:
            asset.tre_qty = int(data['tre_qty'])
        if 'tre_unit' in data:
            asset.tre_unit = data['tre_unit']
        if 'tre_remark' in data:
            asset.tre_remark = data['tre_remark']
        if 'tre_barcode' in data:
            asset.tre_barcode = data['tre_barcode']
        if 'sec_id' in data:
            asset.sec_id = data['sec_id']
        if 'dep_id' in data:
            asset.dep_id = data['dep_id']
        if 'pro_id' in data:
            asset.pro_id = data['pro_id']
        if 'type_id' in data:
            asset.type_id = data['type_id']
        if 'tre_sts_box' in data:
            asset.tre_sts_box = data['tre_sts_box']
        
        # Commit changes
        db.commit()
        
        logger.info(f"Asset {tre_id} updated successfully by user {user.username}")
        
        return jsonify({
            "success": True,
            "message": "Asset updated successfully",
            "data": {
                "tre_id": asset.tre_id,
                "tre_name": asset.tre_name,
                "tre_name_eng": asset.tre_name_eng,
                "tre_price": float(asset.tre_price) if asset.tre_price else None,
                "tre_qty": asset.tre_qty,
                "tre_unit": asset.tre_unit,
                "tre_remark": asset.tre_remark,
                "tre_barcode": asset.tre_barcode,
                "sec_id": asset.sec_id,
                "dep_id": asset.dep_id,
                "pro_id": asset.pro_id,
                "type_id": asset.type_id,
                "tre_sts_box": asset.tre_sts_box
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating asset {tre_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to update asset"
            }
        }), 500

@assets_bp.route('/<asset_id>', methods=['GET'])
@require_auth
def get_asset(user, asset_id):
    """Get specific asset by ID"""
    try:
        db = next(get_db())
        
        asset_data = db.query(
            Asset,
            Section.sec_name.label('section_name'),
            Department.dep_name.label('department_name'),
            Property.pro_name.label('property_name'),
            AssetType.type_name.label('type_name'),
            Place.p_name.label('place_name')
        ).outerjoin(Section, Asset.sec_id == Section.sec_id)\
         .outerjoin(Department, Asset.dep_id == Department.dep_id)\
         .outerjoin(Property, Asset.pro_id == Property.pro_id)\
         .outerjoin(AssetType, Asset.type_id == AssetType.type_id)\
         .outerjoin(Place, Asset.p_id == Place.p_id)\
         .filter(Asset.tre_id == asset_id).first()
        
        if not asset_data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Asset not found"
                }
            }), 404
        
        asset, section_name, department_name, property_name, type_name, place_name = asset_data
        
        return jsonify({
            "success": True,
            "data": {
                "tre_id": asset.tre_id,
                "tre_num": asset.tre_num,
                "tre_name": asset.tre_name,
                "tre_name_eng": asset.tre_name_eng,
                "tre_barcode": asset.tre_barcode,
                "tre_price": float(asset.tre_price) if asset.tre_price else None,
                "tre_cur": asset.tre_cur,
                "tre_qty": asset.tre_qty,
                "tre_unit": asset.tre_unit,
                "tre_sale_date": asset.tre_sale_date.isoformat() if asset.tre_sale_date else None,
                "tre_use_date": asset.tre_use_date.isoformat() if asset.tre_use_date else None,
                "tre_finit_date": asset.tre_finit_date.isoformat() if asset.tre_finit_date else None,
                "tre_qty_year": float(asset.tre_qty_year) if asset.tre_qty_year else None,
                "tre_qty_month": float(asset.tre_qty_month) if asset.tre_qty_month else None,
                "tre_qty_day": float(asset.tre_qty_day) if asset.tre_qty_day else None,
                "tre_remark": asset.tre_remark,
                "sec_id": asset.sec_id,
                "dep_id": asset.dep_id,
                "pro_id": asset.pro_id,
                "type_id": asset.type_id,
                "p_id": asset.p_id,
                "section_name": section_name,
                "department_name": department_name,
                "property_name": property_name,
                "type_name": type_name,
                "place_name": place_name
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching asset {asset_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to fetch asset"
            }
        }), 500

@assets_bp.route('/create', methods=['POST'])
@require_auth
def create_asset(user):
    """Create a new asset"""
    try:
        db = next(get_db())
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "No data provided"
                }
            }), 400
        
        # Validate required fields
        required_fields = ['tre_name', 'tre_price', 'tre_qty', 'sec_id', 'dep_id', 'pro_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": f"Missing required field: {field}"
                    }
                }), 400
        
        # Generate next asset ID
        # Find the highest existing ID with FA25 prefix
        latest_asset = db.query(Asset).filter(
            Asset.tre_id.like('FA25%')
        ).order_by(Asset.tre_id.desc()).first()
        
        if latest_asset:
            # Extract the numeric part and increment
            latest_num = int(latest_asset.tre_id[4:])  # Remove 'FA25' prefix
            next_num = latest_num + 1
        else:
            # Start from 00001 if no assets exist
            next_num = 1
        
        # Format the new ID
        new_tre_id = f"FA25{next_num:05d}"
        
        # Create new asset
        new_asset = Asset(
            tre_id=new_tre_id,
            tre_name=data['tre_name'],
            tre_name_eng=data.get('tre_name_eng'),
            tre_price=Decimal(str(data['tre_price'])),
            tre_qty=int(data['tre_qty']),
            tre_unit=data.get('tre_unit'),
            tre_remark=data.get('tre_remark'),
            tre_barcode=data.get('tre_barcode'),
            sec_id=data['sec_id'],
            dep_id=data['dep_id'],
            pro_id=data['pro_id'],
            type_id=data.get('type_id'),
            tre_sts_box=data.get('tre_sts_box', '1')  # Default to active
        )
        
        # Add to database
        db.add(new_asset)
        db.commit()
        db.refresh(new_asset)
        
        logger.info(f"Asset created successfully by user {user.username}: {new_asset.tre_id}")
        
        return jsonify({
            "success": True,
            "message": "Asset created successfully",
            "data": {
                "tre_id": new_asset.tre_id,
                "tre_name": new_asset.tre_name,
                "tre_name_eng": new_asset.tre_name_eng,
                "tre_price": float(new_asset.tre_price) if new_asset.tre_price else None,
                "tre_qty": new_asset.tre_qty,
                "tre_unit": new_asset.tre_unit,
                "tre_remark": new_asset.tre_remark,
                "tre_barcode": new_asset.tre_barcode,
                "sec_id": new_asset.sec_id,
                "dep_id": new_asset.dep_id,
                "pro_id": new_asset.pro_id,
                "type_id": new_asset.type_id,
                "tre_sts_box": new_asset.tre_sts_box
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating asset: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to create asset"
            }
        }), 500

@assets_bp.route('/search/barcode/<barcode>', methods=['GET'])
@require_auth
def get_asset_by_barcode(user, barcode):
    """Get asset by barcode (for QR code scanning)"""
    try:
        db = next(get_db())
        
        asset_data = db.query(
            Asset,
            Section.sec_name.label('section_name'),
            Department.dep_name.label('department_name'),
            Property.pro_name.label('property_name'),
            AssetType.type_name.label('type_name'),
            Place.p_name.label('place_name')
        ).outerjoin(Section, Asset.sec_id == Section.sec_id)\
         .outerjoin(Department, Asset.dep_id == Department.dep_id)\
         .outerjoin(Property, Asset.pro_id == Property.pro_id)\
         .outerjoin(AssetType, Asset.type_id == AssetType.type_id)\
         .outerjoin(Place, Asset.p_id == Place.p_id)\
         .filter(Asset.tre_barcode == barcode).first()
        
        if not asset_data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Asset with barcode not found"
                }
            }), 404
        
        asset, section_name, department_name, property_name, type_name, place_name = asset_data
        
        return jsonify({
            "success": True,
            "data": {
                "tre_id": asset.tre_id,
                "tre_num": asset.tre_num,
                "tre_name": asset.tre_name,
                "tre_name_eng": asset.tre_name_eng,
                "tre_barcode": asset.tre_barcode,
                "tre_price": float(asset.tre_price) if asset.tre_price else None,
                "tre_cur": asset.tre_cur,
                "tre_qty": asset.tre_qty,
                "tre_unit": asset.tre_unit,
                "tre_sale_date": asset.tre_sale_date.isoformat() if asset.tre_sale_date else None,
                "tre_use_date": asset.tre_use_date.isoformat() if asset.tre_use_date else None,
                "tre_finit_date": asset.tre_finit_date.isoformat() if asset.tre_finit_date else None,
                "tre_qty_year": float(asset.tre_qty_year) if asset.tre_qty_year else None,
                "tre_qty_month": float(asset.tre_qty_month) if asset.tre_qty_month else None,
                "tre_qty_day": float(asset.tre_qty_day) if asset.tre_qty_day else None,
                "tre_remark": asset.tre_remark,
                "sec_id": asset.sec_id,
                "dep_id": asset.dep_id,
                "pro_id": asset.pro_id,
                "type_id": asset.type_id,
                "p_id": asset.p_id,
                "section_name": section_name,
                "department_name": department_name,
                "property_name": property_name,
                "type_name": type_name,
                "place_name": place_name
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching asset by barcode {barcode}: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to fetch asset by barcode"
            }
        }), 500

@assets_bp.route('/delete/<tre_id>', methods=['DELETE'])
@require_auth
def delete_asset(user, tre_id):
    """Delete an asset"""
    try:
        db = next(get_db())
        
        # Get the asset to delete
        asset = db.query(Asset).filter(Asset.tre_id == tre_id).first()
        if not asset:
            return jsonify({
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Asset not found"
                }
            }), 404
        
        # Delete the asset
        db.delete(asset)
        db.commit()
        
        logger.info(f"Asset {tre_id} deleted successfully by user {user.username}")
        
        return jsonify({
            "success": True,
            "message": "Asset deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting asset {tre_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to delete asset"
            }
        }), 500

