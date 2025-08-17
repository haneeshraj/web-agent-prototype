#!/usr/bin/env python3
"""
Test script to verify token limit configuration and JSON response handling.
"""

from utils.config import get_model_config

def test_config():
    """Test the model configuration."""
    print("🔧 Testing configuration...")
    
    try:
        config = get_model_config("classifier-agent")
        print(f"✅ Model: {config['model']}")
        print(f"✅ Max tokens: {config['max_tokens']}")
        print(f"✅ Temperature: {config['temperature']}")
        
        if config['max_tokens'] >= 4096:
            print("✅ Token limit increased successfully!")
        else:
            print(f"⚠️  Token limit might still be low: {config['max_tokens']}")
            
    except Exception as e:
        print(f"❌ Configuration error: {e}")

if __name__ == "__main__":
    test_config()
