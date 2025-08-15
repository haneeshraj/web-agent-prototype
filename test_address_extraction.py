#!/usr/bin/env python3
"""
Test script to validate the address extraction functionality.
This script tests the AddressExtractor independently without running the full scraper.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from agent.address_extractor import AddressExtractor
from utils.terminal_prettify import header, info, success, error


def test_address_extraction():
    """Test the address extraction functionality"""
    header("Testing Address Extraction Feature")
    
    # Initialize the address extractor
    info("Initializing AddressExtractor...")
    address_extractor = AddressExtractor()
    success("AddressExtractor initialized successfully")
    
    # Test HTML content with sample business address
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Acme Pizza Restaurant</title>
    </head>
    <body>
        <header>
            <h1>Acme Pizza</h1>
            <nav>Home | Menu | Contact</nav>
        </header>
        <main>
            <section id="contact">
                <h2>Contact Us</h2>
                <div class="address">
                    <p>Main Location:</p>
                    <p>123 Main Street<br>
                    New York, NY 10001<br>
                    United States</p>
                </div>
                <p>Phone: (555) 123-4567</p>
            </section>
        </main>
        <footer>
            <p>&copy; 2025 Acme Pizza Restaurant. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """
    
    # Create a temporary test directory and HTML file
    test_dir = Path("test_address_extraction")
    test_dir.mkdir(exist_ok=True)
    
    html_file = test_dir / "page.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(test_html)
    
    info("Created test HTML file with sample address")
    
    try:
        # Test address extraction
        info("Testing address extraction...")
        result = address_extractor.extract_address(
            str(test_dir), 
            "test_domain", 
            "Acme Pizza", 
            "restaurant"
        )
        
        # Display results
        header("Address Extraction Results:")
        info(f"Final Address: {result.get('final_address', 'None')}")
        info(f"Confidence: {result.get('final_confidence', 0.0):.2f}")
        info(f"Source: {result.get('final_source', 'None')}")
        info(f"Method: {result.get('address_extraction_method', 'None')}")
        info(f"Reasoning: {result.get('reasoning', 'None')}")
        
        # Check if address was found
        if result.get('final_address'):
            success("✅ Address extraction test PASSED")
            success(f"Found address: {result['final_address']}")
        else:
            error("❌ Address extraction test FAILED")
            error("No address was extracted from test HTML")
        
        # Display detailed analysis
        header("Detailed Analysis:")
        website_analysis = result.get('website_analysis', {})
        info(f"Website Analysis - Found: {website_analysis.get('address_found_in_website', False)}")
        info(f"Website Analysis - Confidence: {website_analysis.get('address_confidence', 0.0):.2f}")
        info(f"Website Analysis - Reasoning: {website_analysis.get('reasoning', 'None')}")
        
        # Test search functionality (if SerpAPI is available)
        if address_extractor.serpapi_client.is_available():
            info("SerpAPI is available - search functionality can be tested")
        else:
            info("SerpAPI not available (SERPAPI_KEY not set) - search functionality will be skipped in real runs")
        
    except Exception as e:
        error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            if html_file.exists():
                html_file.unlink()
            if test_dir.exists():
                test_dir.rmdir()
            info("Cleaned up test files")
        except Exception as e:
            error(f"Cleanup failed: {e}")


def test_serpapi_availability():
    """Test if SerpAPI is properly configured"""
    header("Testing SerpAPI Configuration")
    
    from utils.web_search import create_serpapi_client
    
    serpapi_client = create_serpapi_client()
    
    if serpapi_client.is_available():
        success("✅ SerpAPI is available (SERPAPI_KEY found)")
        
        # Test a simple search
        try:
            info("Testing SerpAPI search...")
            result = serpapi_client.search("pizza restaurant main office address", num_results=2)
            
            if result:
                success("✅ SerpAPI search test PASSED")
                business_info = serpapi_client.extract_business_info(result)
                info(f"Extracted {len(business_info)} business info items from search results")
            else:
                error("❌ SerpAPI search test FAILED - no results returned")
                
        except Exception as e:
            error(f"❌ SerpAPI search test FAILED with error: {e}")
    else:
        error("❌ SerpAPI not available")
        error("To enable SerpAPI functionality, set the SERPAPI_KEY environment variable")
        error("Get your API key from: https://serpapi.com/")


if __name__ == "__main__":
    test_address_extraction()
    print()
    test_serpapi_availability()
