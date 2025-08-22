"""
API Configuration Module
Centralized configuration for the Business Insights API
"""

import os
from typing import Dict, Any


class APIConfig:
    """Configuration class for the API server"""
    
    # Default configuration
    DEFAULT_CONFIG = {
        "host": "127.0.0.1",
        "port": 8000,
        "cors_origins": ["*"],
        "timeout_seconds": 600,  # 10 minutes for analysis
        "max_concurrent_requests": 5,
        "enable_docs": True,
        "log_level": "info"
    }
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        Get API configuration from environment variables or defaults
        
        Returns:
            Dict[str, Any]: API configuration
        """
        config = cls.DEFAULT_CONFIG.copy()
        
        # Override with environment variables if available
        config["host"] = os.getenv("API_HOST", config["host"])
        config["port"] = int(os.getenv("API_PORT", config["port"]))
        config["timeout_seconds"] = int(os.getenv("API_TIMEOUT", config["timeout_seconds"]))
        config["max_concurrent_requests"] = int(os.getenv("API_MAX_REQUESTS", config["max_concurrent_requests"]))
        config["log_level"] = os.getenv("API_LOG_LEVEL", config["log_level"])
        
        # Parse CORS origins from environment
        cors_origins = os.getenv("API_CORS_ORIGINS")
        if cors_origins:
            config["cors_origins"] = [origin.strip() for origin in cors_origins.split(",")]
        
        return config
    
    @classmethod
    def get_server_info(cls) -> Dict[str, str]:
        """
        Get server information for display
        
        Returns:
            Dict[str, str]: Server information
        """
        config = cls.get_config()
        
        return {
            "server_url": f"http://{config['host']}:{config['port']}",
            "docs_url": f"http://{config['host']}:{config['port']}/docs",
            "health_url": f"http://{config['host']}:{config['port']}/health",
            "config_url": f"http://{config['host']}:{config['port']}/config"
        }


# Response templates for consistent API responses
RESPONSE_TEMPLATES = {
    "success": {
        "success": True,
        "data": {},
        "error": None
    },
    "error": {
        "success": False,
        "data": None,
        "error": "An error occurred"
    },
    "service_unavailable": {
        "success": False,
        "data": None,
        "error": "Service unavailable: WebDriver not initialized"
    }
}


# API Documentation metadata
API_METADATA = {
    "title": "Business Insights API",
    "description": """
    🧠 **AI-Powered Business Intelligence Extraction**
    
    Extract comprehensive business intelligence from any website URL including:
    
    - **Company Information**: Name, confidence, reasoning
    - **Business Classification**: MCC code, description, confidence, reasoning
    - **Brand Analysis**: Logo detection, confidence, reasoning
    - **Address Data**: Complete address, coordinates, confidence, reasoning
    - **Performance Metrics**: Token usage, processing time, status
    
    ### ✨ **Key Features:**
    - Clean, focused response structure
    - Comprehensive confidence scoring
    - Detailed reasoning for all extractions
    - Real-time processing status
    - Token usage tracking
    
    ### 🚀 **Quick Start:**
    1. Check `/health` endpoint to ensure service is ready
    2. Use `/analyze` endpoint with website URL
    3. Get structured business intelligence data
    
    ### 🎯 **Perfect For:**
    - Lead generation and prospecting
    - Business directory building
    - Market research and analysis
    - Competitive intelligence
    - Data enrichment workflows
    """,
    "version": "1.0.0",
    "contact": {
        "name": "Business Insights API",
        "url": "https://github.com/your-repo/business-insights"
    },
    "license": {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
}
