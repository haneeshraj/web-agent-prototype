"""
Business Insights API Startup Script
Handles environment setup and starts the API server
"""

import sys
import os
import subprocess
from pathlib import Path


def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'selenium',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print("   pip install -r requirements.txt")
        return False
    
    return True


def check_environment():
    """Check if environment is properly configured"""
    issues = []
    
    # Check for .env file or required environment variables
    env_file = Path(".env")
    if not env_file.exists():
        # Check if API keys are set in environment
        required_env_vars = []
        if not os.getenv('OPENAI_API_KEY') and not os.getenv('ANTHROPIC_API_KEY') and not os.getenv('GOOGLE_API_KEY'):
            required_env_vars.append("At least one AI provider API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY)")
        
        if required_env_vars:
            issues.append("Missing .env file and required environment variables:")
            issues.extend([f"   - {var}" for var in required_env_vars])
    
    # Check if Chrome is installed (basic check)
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]
    
    chrome_found = any(os.path.exists(path) for path in chrome_paths)
    if not chrome_found:
        issues.append("Google Chrome not found - required for web scraping")
    
    if issues:
        print("⚠️  Environment Issues:")
        for issue in issues:
            print(issue)
        print("\n💡 Please resolve these issues before starting the API")
        return False
    
    return True


def start_api_server():
    """Start the FastAPI server"""
    try:
        print("🚀 Starting Business Insights API Server...")
        print("📚 API Documentation will be available at: http://127.0.0.1:8000/docs")
        print("🔍 Health check available at: http://127.0.0.1:8000/health")
        print("⭐ Interactive API testing at: http://127.0.0.1:8000/docs")
        print("\n🛑 Press Ctrl+C to stop the server\n")
        
        # Start the server
        result = subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "api:app", 
            "--host", "127.0.0.1", 
            "--port", "8000",
            "--reload"
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Main startup function"""
    print("🔧 Business Insights API - Startup Check")
    print("=" * 50)
    
    # Check requirements
    print("1. Checking required packages...")
    if not check_requirements():
        return
    print("✅ All required packages are installed")
    
    # Check environment
    print("\n2. Checking environment configuration...")
    if not check_environment():
        return
    print("✅ Environment configuration looks good")
    
    # Start server
    print("\n3. Starting API server...")
    start_api_server()


if __name__ == "__main__":
    main()
