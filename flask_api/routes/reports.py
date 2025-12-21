from flask import Blueprint, request, jsonify
from database import get_db
from models import Asset, Section, Property
from routes.auth import require_auth
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)
reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/assets/summary', methods=['GET'])
@require_auth
def get_asset_summary(user):
    """Get asset summary report"""
    try:
        db = next(get_db())
        
        # Get query parameters
        sec_id = request.args.get('sec_id')
        dep_id = request.args.get('dep_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build base query
        query = db.query(Asset)
        
        # Apply filters
        if sec_id:
            query = query.filter(Asset.sec_id == sec_id)
        if dep_id:
            query = query.filter(Asset.dep_id == dep_id)
        if date_from:
            query = query.filter(Asset.tre_sale_date >= date_from)
        if date_to:
            query = query.filter(Asset.tre_sale_date <= date_to)
        
        # Get total assets and value
        total_assets = query.count()
        total_value_result = query.with_entities(func.sum(Asset.tre_price)).scalar()
        total_value = float(total_value_result) if total_value_result else 0.0
        
        # Get summary by section
        section_query = db.query(
            Section.sec_id,
            Section.sec_name,
            func.count(Asset.tre_id).label('asset_count'),
            func.sum(Asset.tre_price).label('total_value')
        ).outerjoin(Asset, Section.sec_id == Asset.sec_id)
        
        if sec_id:
            section_query = section_query.filter(Asset.sec_id == sec_id)
        if dep_id:
            section_query = section_query.filter(Asset.dep_id == dep_id)
        if date_from:
            section_query = section_query.filter(Asset.tre_sale_date >= date_from)
        if date_to:
            section_query = section_query.filter(Asset.tre_sale_date <= date_to)
        
        section_summary = section_query.group_by(Section.sec_id, Section.sec_name).all()
        
        by_section = []
        for section in section_summary:
            by_section.append({
                "sec_id": section.sec_id,
                "sec_name": section.sec_name,
                "asset_count": section.asset_count or 0,
                "total_value": float(section.total_value) if section.total_value else 0.0
            })
        
        # Get summary by property type
        property_query = db.query(
            Property.pro_id,
            Property.pro_name,
            func.count(Asset.tre_id).label('asset_count'),
            func.sum(Asset.tre_price).label('total_value')
        ).outerjoin(Asset, Property.pro_id == Asset.pro_id)
        
        if sec_id:
            property_query = property_query.filter(Asset.sec_id == sec_id)
        if dep_id:
            property_query = property_query.filter(Asset.dep_id == dep_id)
        if date_from:
            property_query = property_query.filter(Asset.tre_sale_date >= date_from)
        if date_to:
            property_query = property_query.filter(Asset.tre_sale_date <= date_to)
        
        property_summary = property_query.group_by(Property.pro_id, Property.pro_name).all()
        
        by_property_type = []
        for prop in property_summary:
            by_property_type.append({
                "pro_id": prop.pro_id,
                "pro_name": prop.pro_name,
                "asset_count": prop.asset_count or 0,
                "total_value": float(prop.total_value) if prop.total_value else 0.0
            })
        
        # Calculate depreciation summary using database fields
        # Get total original value from tre_price
        original_value_result = query.with_entities(func.sum(Asset.tre_price)).scalar()
        total_original_value = float(original_value_result) if original_value_result else 0.0
        
        # Get total depreciation from tre_qty_year (annual depreciation)
        depreciation_result = query.with_entities(func.sum(Asset.tre_qty_year)).scalar()
        total_depreciation = float(depreciation_result) if depreciation_result else 0.0
        
        # Calculate current value (original - depreciation)
        current_value = total_original_value - total_depreciation
        
        # Get additional financial metrics
        total_monthly_depreciation = query.with_entities(func.sum(Asset.tre_qty_month)).scalar()
        total_daily_depreciation = query.with_entities(func.sum(Asset.tre_qty_day)).scalar()
        total_kip_value = query.with_entities(func.sum(Asset.tre_price_kip)).scalar()
        total_exchange = query.with_entities(func.sum(Asset.tre_ex)).scalar()
        
        # Get asset lifecycle information
        assets_in_use = query.filter(Asset.tre_use_date.isnot(None)).count()
        assets_completed = query.filter(Asset.tre_date_succ.isnot(None)).count()
        assets_with_suppliers = query.filter(Asset.tre_sup_name.isnot(None)).count()
        
        # Get status breakdown
        active_assets = query.filter(or_(Asset.tre_sts_box.is_(None), Asset.tre_sts_box == "1", Asset.tre_sts_box == "active")).count()
        inactive_assets = query.filter(or_(Asset.tre_sts_box == "0", Asset.tre_sts_box == "inactive")).count()
        
        depreciation_summary = {
            "total_original_value": total_original_value,
            "total_depreciation": total_depreciation,
            "current_value": current_value,
            "monthly_depreciation": float(total_monthly_depreciation) if total_monthly_depreciation else 0.0,
            "daily_depreciation": float(total_daily_depreciation) if total_daily_depreciation else 0.0,
            "total_kip_value": float(total_kip_value) if total_kip_value else 0.0,
            "total_exchange": float(total_exchange) if total_exchange else 0.0
        }
        
        # Asset lifecycle summary
        lifecycle_summary = {
            "assets_in_use": assets_in_use,
            "assets_completed": assets_completed,
            "assets_with_suppliers": assets_with_suppliers,
            "active_assets": active_assets,
            "inactive_assets": inactive_assets
        }
        
        return jsonify({
            "success": True,
            "data": {
                "total_assets": total_assets,
                "total_value": total_value,
                "by_section": by_section,
                "by_property_type": by_property_type,
                "depreciation_summary": depreciation_summary,
                "lifecycle_summary": lifecycle_summary
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating asset summary: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to generate asset summary"
            }
        }), 500

@reports_bp.route('/assets/by-location', methods=['GET'])
@require_auth
def get_assets_by_location(user):
    """Get assets by location report"""
    try:
        db = next(get_db())
        
        # This would require a Place model and proper joins
        # For now, return a simple response
        return jsonify({
            "success": True,
            "data": [],
            "message": "Location report not yet implemented"
        })
        
    except Exception as e:
        logger.error(f"Error generating location report: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to generate location report"
            }
        }), 500
