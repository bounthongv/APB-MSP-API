from flask import Blueprint, request, jsonify
from functools import wraps
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import logging

from database import get_db
from models import User
from config import settings

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def get_current_user():
    """Get current authenticated user from JWT token"""
    auth_header = request.headers.get('Authorization')
    logger.debug(f"Auth header: {auth_header}")
    
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning("No valid Authorization header found")
        return None
    
    token = auth_header.split(' ')[1]
    logger.debug(f"Token: {token[:20]}...")  # Log first 20 chars of token
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub", "")
        token_type: str = payload.get("type", "")
        
        logger.debug(f"Token payload - username: {username}, type: {token_type}")
        
        if not username or token_type != "access":
            logger.warning(f"Invalid token payload - username: {username}, type: {token_type}")
            return None
        
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if user:
            logger.debug(f"User found: {user.username}")
        else:
            logger.warning(f"User not found in database: {username}")
            
        return user
        
    except JWTError as e:
        logger.warning(f"JWT error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Could not validate credentials"
                }
            }), 401
        return f(user, *args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT tokens"""
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
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                "success": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Username and password required"
                }
            }), 400
        
        # DEBUG: Log input data
        logger.debug(f"DEBUG LOGIN: Username={username}, Password length={len(password) if password else 0}")
        
        # Get database session
        db = next(get_db())
        logger.debug("DEBUG LOGIN: Database session obtained")
        
        # Find user by username
        user = db.query(User).filter(User.username == username).first()
        logger.debug(f"DEBUG LOGIN: User query result - {user is not None}")
        
        if not user:
            logger.warning(f"Login attempt with non-existent username: {username}")
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Incorrect username or password"
                }
            }), 401
        
        # DEBUG: Log password verification
        logger.debug("DEBUG LOGIN: Verifying password")
        
        # Verify password
        if not verify_password(password, user.password):
            logger.warning(f"Failed login attempt for user: {username}")
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Incorrect username or password"
                }
            }), 401
        
        # DEBUG: Log token creation
        logger.debug("DEBUG LOGIN: Creating access token")
        
        # Create access token (short-lived)
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username, "type": "access"}, 
            expires_delta=access_token_expires
        )
        
        # DEBUG: Log refresh token creation
        logger.debug("DEBUG LOGIN: Creating refresh token")
        
        # Create refresh token (long-lived)
        refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
        refresh_token = create_access_token(
            data={"sub": user.username, "type": "refresh"}, 
            expires_delta=refresh_token_expires
        )
        
        logger.info(f"Successful login for user: {username}")
        
        # DEBUG: Log response creation
        logger.debug("DEBUG LOGIN: Creating response")
        
        # Return tokens and user info
        return jsonify({
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": settings.access_token_expire_minutes * 60,  # seconds
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "fname": user.fname,
                "status": user.status,
                "off_id": user.off_id
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error during login"
            }
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
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
        
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({
                "success": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Refresh token required"
                }
            }), 400
        
        # Verify refresh token
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub", "")
        token_type: str = payload.get("type", "")
        
        if not username or token_type != "refresh":
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid refresh token"
                }
            }), 401
        
        # Get user
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "User not found"
                }
            }), 401
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username, "type": "access"}, 
            expires_delta=access_token_expires
        )
        
        return jsonify({
            "success": True,
            "access_token": access_token,
            "expires_in": settings.access_token_expire_minutes * 60  # seconds
        })
        
    except JWTError:
        return jsonify({
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Invalid refresh token"
            }
        }), 401
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to refresh token"
            }
        }), 500

@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user_info(user):
    """Get current user information"""
    return jsonify({
        "user_id": user.user_id,
        "username": user.username,
        "fname": user.fname,
        "status": user.status,
        "off_id": user.off_id
    })

@auth_bp.route('/change-password', methods=['PUT'])
@require_auth
def change_password(user):
    """Change user password"""
    try:
        logger.info(f"Password change attempt for user: {user.username}")
        
        data = request.get_json()
        if not data:
            logger.warning("Password change failed: No JSON data provided")
            return jsonify({
                "success": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "JSON data required"
                }
            }), 400
        
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        logger.debug(f"Password change data - old_password length: {len(old_password) if old_password else 0}, new_password length: {len(new_password) if new_password else 0}")
        
        if not old_password or not new_password:
            logger.warning("Password change failed: Missing old or new password")
            return jsonify({
                "success": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Old password and new password required"
                }
            }), 400
        
        # Verify old password
        logger.debug("Verifying old password")
        if not verify_password(old_password, user.password):
            logger.warning(f"Password change failed: Incorrect old password for user {user.username}")
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Current password is incorrect"
                }
            }), 401
        
        # Validate new password
        if len(new_password) < 6:
            return jsonify({
                "success": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "New password must be at least 6 characters long"
                }
            }), 400
        
        # Hash new password
        logger.debug("Hashing new password")
        hashed_new_password = pwd_context.hash(new_password)
        
        # Update password in database
        logger.debug("Updating password in database")
        db = next(get_db())
        
        # Get the user from the database session
        db_user = db.query(User).filter(User.username == user.username).first()
        if not db_user:
            logger.error(f"User not found in database: {user.username}")
            return jsonify({
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "User not found in database"
                }
            }), 500
        
        # Update the password
        db_user.password = hashed_new_password
        db.commit()
        
        logger.info(f"Password updated in database for user: {user.username}")
        
        logger.info(f"Password changed successfully for user: {user.username}")
        
        return jsonify({
            "success": True,
            "message": "Password changed successfully"
        })
        
    except Exception as e:
        logger.error(f"Password change error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to change password"
            }
        }), 500


@auth_bp.route('/update-profile', methods=['PUT'])
def update_profile():
    """Update user profile information"""
    try:
        # Get current user from JWT token
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Not authenticated"}}), 401

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": {"code": "INVALID_REQUEST", "message": "No data provided"}}), 400

        # Extract fields to update
        new_name = data.get('name')
        new_email = data.get('email')
        new_department = data.get('department')

        # Validate required fields
        if not new_name or not new_email:
            return jsonify({"success": False, "error": {"code": "INVALID_REQUEST", "message": "Name and email are required"}}), 400

        # Get database session
        db = next(get_db())
        
        # Find user in database
        db_user = db.query(User).filter(User.username == user.username).first()
        if not db_user:
            logger.error(f"User not found in database: {user.username}")
            return jsonify({"success": False, "error": {"code": "INTERNAL_ERROR", "message": "User not found in database"}}), 500

        # Update user fields
        db_user.name = new_name
        db_user.email = new_email
        if new_department:
            db_user.department = new_department

        # Commit changes
        db.commit()
        db.close()

        logger.info(f"Profile updated for user: {user.username}")
        return jsonify({
            "success": True, 
            "message": "Profile updated successfully",
            "data": {
                "name": new_name,
                "email": new_email,
                "department": new_department
            }
        })

    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        return jsonify({"success": False, "error": {"code": "INTERNAL_ERROR", "message": "Failed to update profile"}}), 500
