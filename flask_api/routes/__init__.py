# Routes package
from .auth import auth_bp
from .assets import assets_bp
from .inventory import inventory_bp
from .references import references_bp
from .reports import reports_bp

__all__ = ['auth_bp', 'assets_bp', 'inventory_bp', 'references_bp', 'reports_bp']
