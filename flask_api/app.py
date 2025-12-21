from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from config import settings

# Create necessary directories
os.makedirs("logs", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# Configure logging
log_handlers = [logging.StreamHandler()]
if settings.log_file:
    try:
        log_dir = os.path.dirname(settings.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        log_handlers.append(logging.FileHandler(settings.log_file))
    except Exception as e:
        print(f"Warning: Could not create log file {settings.log_file}: {e}")

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.secret_key

# Add CORS support
CORS(app, origins=settings.allowed_origins)

# Import and register blueprints
from routes import auth_bp, assets_bp, inventory_bp, references_bp, reports_bp

app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
app.register_blueprint(references_bp, url_prefix='/api/v1/references')
app.register_blueprint(assets_bp, url_prefix='/api/v1/assets')
app.register_blueprint(inventory_bp, url_prefix='/api/v1/inventory')
app.register_blueprint(reports_bp, url_prefix='/api/v1/reports')


# Initialize database
from database import init_database

def initialize_database():
    """Initialize database on startup"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    if init_database():
        logger.info("✅ Database connection established")
    else:
        logger.error("❌ Database connection failed")
        raise Exception("Database initialization failed")

@app.route('/')
def root():
    """Root endpoint - API health check"""
    return jsonify({
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs"
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        from database import db_manager
        
        # Test database connection
        db_status = db_manager.test_connection()
        
        return jsonify({
            "status": "healthy" if db_status else "unhealthy",
            "database": "connected" if db_status else "disconnected",
            "version": settings.app_version,
            "timestamp": "2025-09-22T00:00:00Z"
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "version": settings.app_version
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "success": False,
        "error": {
            "code": "NOT_FOUND",
            "message": "Endpoint not found"
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        "success": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An internal server error occurred"
        }
    }), 500

if __name__ == '__main__':
    # Initialize database
    initialize_database()
    
    # Run the application
    app.run(
        host=settings.api_host,
        port=settings.api_port,
        debug=settings.api_debug
    )
