import os
from typing import List

class Settings:
    def __init__(self):
        # Database Configuration - These will be overridden by .env
        self.oracle_host = os.getenv("ORACLE_HOST", "localhost")
        self.oracle_port = int(os.getenv("ORACLE_PORT", "1521"))
        self.oracle_service_name = os.getenv("ORACLE_SERVICE_NAME", "XEPDB1")
        self.oracle_username = os.getenv("ORACLE_USERNAME", "apasset_schema")
        self.oracle_password = os.getenv("ORACLE_PASSWORD", "ApAsset25!")
        
        # API Configuration
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.api_debug = os.getenv("API_DEBUG", "True").lower() == "true"
        
        # Security Configuration - These will be overridden by .env
        self.secret_key = os.getenv("SECRET_KEY", "")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        
        # Application Settings - These are fixed, no need to change
        self.app_name = "JDB Asset Management API"
        self.app_version = "1.0.0"
        
        # CORS Settings - These will be overridden by .env
        # Note: Mobile apps don't have domains, so CORS doesn't apply to them
        # These are only for web applications that might access your API
        self.allowed_origins = [
            "http://localhost:3000",  # For web development
            "http://127.0.0.1:3000",  # Alternative localhost
            "http://localhost:*",     # Flutter development server
            "http://127.0.0.1:*",    # Flutter development server
            "*",                     # Allow all origins for development
            # Add your web app domains here if you create a web interface
        ]
        
        # File Upload Settings - These are fixed, no need to change
        self.max_file_size = 5242880  # 5MB in bytes
        self.upload_dir = "./uploads"
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "./logs/api.log")

# Global settings instance
settings = Settings()
