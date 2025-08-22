"""
FastAPI server for Business Insights - AI-Powered Business Intelligence Extraction
Provides REST API endpoints for processing single websites
"""

import sys
import os
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import uvicorn

# Add the current directory to Python path to import modules
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from agent.information_extractor import WebsiteInformationExtractor
from utils.config import get_config
from api.config import APIConfig, API_METADATA, RESPONSE_TEMPLATES


# Global extractor instance
extractor_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown"""
    global extractor_instance
    
    # Startup
    print("🚀 Starting Business Insights API...")
    try:
        extractor_instance = WebsiteInformationExtractor()
        if extractor_instance.setup_driver():
            print("✅ WebDriver initialized successfully")
        else:
            print("❌ Failed to initialize WebDriver")
            extractor_instance = None
    except Exception as e:
        print(f"❌ Error during startup: {e}")
        extractor_instance = None
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Business Insights API...")
    if extractor_instance and extractor_instance.driver:
        try:
            extractor_instance.driver.quit()
            print("✅ WebDriver closed successfully")
        except Exception as e:
            print(f"⚠️  Error closing WebDriver: {e}")


# Initialize FastAPI app with lifespan management
app = FastAPI(
    title=API_METADATA["title"],
    description=API_METADATA["description"],
    version=API_METADATA["version"],
    contact=API_METADATA["contact"],
    license_info=API_METADATA["license"],
    lifespan=lifespan
)

# Get API configuration
api_config = APIConfig.get_config()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_config["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class WebsiteAnalysisRequest(BaseModel):
    url: HttpUrl
    include_screenshot: bool = True
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.spotcoffee.com",
                "include_screenshot": True
            }
        }


class WebsiteAnalysisResponse(BaseModel):
    success: bool
    url: str
    processing_time_seconds: float
    timestamp: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "url": "https://www.spotcoffee.com",
                "processing_time_seconds": 45.2,
                "timestamp": "2024-08-22T10:30:45Z",
                "data": {
                    "original_url": "https://www.spotcoffee.com/wp-content/uploads/spot-coffee-logo.png",
                    "company_name": "SPoT Coffee",
                    "company_name_confidence": 0.95,
                    "company_name_reasoning": "Page title, header logo, footer copyright",
                    "mcc_code": 5812,
                    "mcc_name": "Eating Places and Restaurants",
                    "mcc_confidence": 0.95,
                    "mcc_reasoning": "Restaurant business model with food service",
                    "brand_image_found": True,
                    "brand_image_confidence": 0.95,
                    "brand_image_reasoning": "Main logo in header with company name",
                    "address": "225, Delaware Avenue, Buffalo, NY",
                    "address_latitude": None,
                    "address_longitude": None,
                    "address_confidence": 0.95,
                    "address_reasoning": "search_spotcoffee.com",
                    "total_tokens_used": 21220,
                    "processing_time_seconds": 45.2,
                    "status": "success",
                    "success": True
                },
                "error": None
            }
        }


class HealthResponse(BaseModel):
    status: str
    webdriver_ready: bool
    timestamp: str


# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with basic API information"""
    return {
        "message": "Business Insights API",
        "description": "AI-Powered Business Intelligence Extraction",
        "version": "1.0.0",
        "endpoints": {
            "/analyze": "POST - Analyze a single website",
            "/health": "GET - Check API health status",
            "/docs": "GET - API documentation"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    global extractor_instance
    
    webdriver_ready = False
    if extractor_instance and extractor_instance.driver:
        try:
            # Simple test to check if driver is responsive
            extractor_instance.driver.current_url
            webdriver_ready = True
        except:
            webdriver_ready = False
    
    return HealthResponse(
        status="healthy" if webdriver_ready else "degraded",
        webdriver_ready=webdriver_ready,
        timestamp=datetime.now().isoformat()
    )


@app.post("/analyze", response_model=WebsiteAnalysisResponse)
async def analyze_website(request: WebsiteAnalysisRequest):
    """
    Analyze a single website and extract business intelligence
    
    - **url**: The website URL to analyze
    - **include_screenshot**: Whether to take a screenshot (default: True)
    
    Returns comprehensive business intelligence including:
    - Company name and confidence
    - MCC (Merchant Category Code) classification
    - Business address extraction
    - Brand image detection
    """
    global extractor_instance
    
    if not extractor_instance:
        raise HTTPException(
            status_code=503, 
            detail="Service unavailable: WebDriver not initialized"
        )
    
    start_time = time.time()
    url_str = str(request.url)
    
    try:
        # Setup run directory for this request
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join("data", "api_runs", f"run_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)
        
        # Set the base data directory for this request
        extractor_instance.base_data_dir = run_dir
        extractor_instance.run_timestamp = timestamp
        
        # Process the website
        result = extractor_instance.extract_website_information(url_str)
        
        processing_time = time.time() - start_time
        
        # Calculate total tokens used
        total_tokens = 0
        
        # Brand detection tokens
        brand_metadata = result.get("brand_image_detection", {}).get("analysis_metadata", {})
        if brand_metadata.get("tokens_used"):
            total_tokens += brand_metadata["tokens_used"]
        
        # MCC classification tokens
        mcc_metadata = result.get("mcc_metadata", {})
        if mcc_metadata.get("tokens_used"):
            total_tokens += mcc_metadata["tokens_used"]
        
        # Address extraction tokens
        address_metadata = result.get("address_metadata", {})
        if address_metadata.get("tokens_used"):
            total_tokens += address_metadata["tokens_used"]
        
        # Extract only the essential business intelligence data you requested
        response_data = {
            # Original URL
            "original_url": result.get("brand_image_detection", {}).get("selected_image", {}).get("src", ""),
            
            # Company name with confidence and reasoning
            "company_name": result.get("company_name", ""),
            "company_name_confidence": result.get("company_name_confidence", 0.0),
            "company_name_reasoning": result.get("company_name_source", ""),
            
            # MCC code with confidence and reasoning
            "mcc_code": result.get("final_mcc_code"),
            "mcc_name": result.get("mcc_classification", {}).get("description", ""),
            "mcc_confidence": result.get("mcc_confidence", 0.0),
            "mcc_reasoning": result.get("mcc_classification", {}).get("reasoning", ""),
            
            # Brand image with confidence and reasoning
            "brand_image_found": result.get("brand_image_detection", {}).get("brand_image_found", False),
            "brand_image_confidence": result.get("brand_image_detection", {}).get("confidence", 0.0),
            "brand_image_reasoning": result.get("brand_image_detection", {}).get("reasoning", ""),
            
            # Address with coordinates, confidence and reasoning
            "address": result.get("final_address", ""),
            "address_latitude": None,  # Will be added when geocoding is available
            "address_longitude": None,  # Will be added when geocoding is available
            "address_confidence": result.get("address_confidence", 0.0),
            "address_reasoning": result.get("address_source", ""),
            
            # Performance metrics
            "total_tokens_used": total_tokens,
            "processing_time_seconds": round(processing_time, 2),
            "status": result.get("status", "failed"),
            "success": result.get("status") == "success"
        }
        
        return WebsiteAnalysisResponse(
            success=result.get("status") == "success",
            url=url_str,
            processing_time_seconds=round(processing_time, 2),
            timestamp=datetime.now().isoformat(),
            data=response_data,
            error=result.get("error") if result.get("status") != "success" else None
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        return WebsiteAnalysisResponse(
            success=False,
            url=url_str,
            processing_time_seconds=round(processing_time, 2),
            timestamp=datetime.now().isoformat(),
            data=None,
            error=str(e)
        )


@app.get("/config")
async def get_configuration():
    """Get current API configuration"""
    try:
        config = get_config()
        
        # Get model configuration
        try:
            from utils.config import get_model_config
            model_config = get_model_config("classifier-agent")
            model_name = model_config.get('model', 'Unknown')
        except:
            model_name = "Configuration not available"
        
        return {
            "ai_model": model_name,
            "processing": {
                "website_delay_seconds": config.get('processing.website_delay_seconds', 60),
                "rate_limit_delay_seconds": config.get('processing.rate_limit_delay_seconds', 10)
            },
            "webdriver_status": "ready" if extractor_instance and extractor_instance.driver else "not_ready"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving configuration: {str(e)}")


if __name__ == "__main__":
    # Get configuration for server
    config = APIConfig.get_config()
    server_info = APIConfig.get_server_info()
    
    print(f"🚀 Starting Business Insights API on {server_info['server_url']}")
    print(f"📚 API Documentation: {server_info['docs_url']}")
    print(f"🔍 Health check: {server_info['health_url']}")
    print(f"⚙️  Configuration: {server_info['config_url']}")
    
    uvicorn.run(
        "api:app",
        host=config["host"],
        port=config["port"],
        reload=False,  # Set to True for development
        log_level=config["log_level"]
    )
