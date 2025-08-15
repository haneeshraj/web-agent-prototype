import json
import os
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.llm import create_llm_client
from utils.config import get_model_config
from utils.terminal_prettify import success, error, warning, info


class LogoDetector:
    """
    Logo detection agent that analyzes screenshots and HTML to identify website logos and extract merchant names.
    """
    
    def __init__(self):
        """Initialize the logo detector with LLM client and configuration."""
        self.llm_client = create_llm_client()
        self.model_config = get_model_config("classifier-agent")
        
        # System prompt for logo detection and merchant name extraction
        self.system_prompt = """You are a website logo detection, merchant name extraction, and business address analysis expert. Your task is to identify the main logo/brand image from a website, extract the merchant/business name, AND analyze for business address information using the provided screenshot and HTML structure.

INSTRUCTIONS:
1. Analyze the screenshot to visually identify the website's main logo/brand image
2. Use the HTML structure to understand the page layout and context
3. Extract the merchant/business name from various sources (logo text, page title, headings, etc.)
4. ADDITIONALLY: Analyze the HTML content for business address information and location context
5. If there are cookie overlays, popups, or modals, ignore them and focus on the main website content behind them

LOGO DETECTION:
6. Look for logos typically positioned in:
   - Header/navigation area (most common)
   - Top-left corner
   - Center of header
   - Footer area (secondary logos)

7. From the provided images list, identify which image corresponds to the logo you see in the screenshot
8. Consider these logo characteristics:
   - Usually contains company/brand name or distinctive visual identity
   - Often positioned prominently in navigation
   - May have alt text with brand/company names
   - Typically appears in header sections

MERCHANT NAME EXTRACTION:
9. Look for the business/merchant name in multiple sources:
   - Logo text (text within or next to the logo)
   - Page title (HTML <title> tag)
   - Main headings (H1, H2 tags)
   - Navigation menu items
   - "About" or "Company" sections
   - Meta tags (business name, site name)
   - Footer copyright information
10. Prioritize names that appear in prominent locations (header, logo area, main title)
11. Extract the BUSINESS name, not generic terms like "Home" or "Welcome"
12. If multiple business names found, choose the most prominent/consistent one

ADDRESS & LOCATION ANALYSIS:
13. SIMULTANEOUSLY analyze the HTML content for business address information:
    - Look for complete addresses in Contact pages, About sections, Footer areas
    - Identify headquarters, main office, or primary store addresses
    - Focus on MAIN business addresses (not shipping/warehouse/customer service addresses)
    - Look for street addresses with city, state/province, postal code

14. ALSO extract location context from the website content:
    - Countries, states/provinces, cities where the business operates
    - "Founded in", "Based in", "Established in" statements
    - Geographic indicators that suggest the original/primary location
    - Regional mentions in business descriptions

15. PRIORITIZATION for addresses:
    - If a complete address is found, extract it directly
    - If no complete address but location context exists, note the context
    - Focus on ORIGINAL/FOUNDING location, not expansion markets

VALIDATION RULES:
16. PLATFORM vs MERCHANT DISTINCTION:
    - If the page is a social media platform's login/signup page, return logo_found as false
    - Only return logo_found as true for actual MERCHANT/BUSINESS logos
    - Platform logos should NOT be considered the "main brand logo"

17. VALID LOGO CRITERIA:
    - Must be a designed brand identity element (text-based logo, symbol, or combination)
    - DO NOT select profile pictures of people or generic photos
    - Only select images representing business/brand identity

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
    "logo_found": true/false,
    "confidence": 0.95,
    "selected_image": {
        // If logo found, include the exact image object from images array
        // If not found, use empty object {}
    },
    "reasoning": "Detailed explanation of logo selection or why no logo found",
    "visual_description": "Description of what the logo looks like in the screenshot",
    "merchant_name": "Extracted business/merchant name",
    "merchant_name_source": "Where the merchant name was found",
    "merchant_name_confidence": 0.95,
    "alternative_names": ["other possible business names found"],
    
    // NEW: Address Analysis Results
    "address_analysis": {
        "addresses_found": ["list of addresses found on the website"],
        "confidence": "high|medium|low|none",
        "primary_address": "Main business address if found",
        "address_components": {
            "house_number_street": "House number and street name (e.g., '225 Delaware Avenue')",
            "city": "City name in full form (e.g., 'New York' not 'NYC')",
            "county": "County/District if applicable",
            "state": "State/Province in full form (e.g., 'New York' not 'NY')",
            "country": "Country in full form (e.g., 'United States' not 'USA')",
            "postal_code": "Postal/ZIP code if applicable"
        },
        "clean_address": "Address without suite numbers or secondary identifiers",
        "source": "Where address was found (e.g., 'contact page', 'footer', 'about section')",
        "reasoning": "Explanation of why this address was selected or why none found"
    },
    
    // NEW: Location Context Results
    "location_context": {
        "primary_country": "Country where business was founded/primarily based",
        "primary_state_province": "State/province of primary location",
        "primary_city": "City of primary location",
        "additional_locations": ["other countries/regions mentioned"],
        "location_confidence": 0.85,
        "location_reasoning": "Explanation of why this location was identified as primary"
    }
}

IMPORTANT:
- Only return valid JSON
- If no logo found, set logo_found to false and explain why
- If no address found, set address_found_on_website to false
- If no location context found, use empty strings for location fields
- Always attempt to extract merchant name even if no logo found
- Focus on ORIGINAL/PRIMARY business locations, not expansion markets
- Confidence scores should be between 0.0 and 1.0"""

    def _load_screenshot(self, screenshot_path: str) -> Optional[bytes]:
        """
        Load screenshot image as bytes.
        
        Args:
            screenshot_path (str): Path to screenshot file
            
        Returns:
            Optional[bytes]: Screenshot data or None if failed
        """
        try:
            if not os.path.exists(screenshot_path):
                return None
                
            with open(screenshot_path, 'rb') as f:
                return f.read()
        except Exception:
            return None
    
    def _load_html_content(self, html_path: str) -> Optional[str]:
        """
        Load HTML content.
        
        Args:
            html_path (str): Path to HTML file
            
        Returns:
            Optional[str]: HTML content or None if failed
        """
        try:
            if not os.path.exists(html_path):
                return None
                
            with open(html_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None
    
    def _load_images_data(self, images_path: str) -> Optional[List[Dict]]:
        """
        Load images JSON data.
        
        Args:
            images_path (str): Path to images JSON file
            
        Returns:
            Optional[List[Dict]]: Images data or None if failed
        """
        try:
            if not os.path.exists(images_path):
                return None
                
            with open(images_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _create_user_prompt(self, html_content: str, images_data: List[Dict]) -> str:
        """
        Create the user prompt with HTML and images data.
        
        Args:
            html_content (str): Website HTML content
            images_data (List[Dict]): List of image objects
            
        Returns:
            str: Formatted user prompt
        """
        # Truncate HTML if too long (to avoid token limits)
        max_html_length = 15000  # Adjust based on your needs
        if len(html_content) > max_html_length:
            html_content = html_content[:max_html_length] + "\n... [HTML truncated for length]"
        
        prompt = f"""Please analyze this website to: 1) identify the main logo/brand image, 2) extract the merchant/business name, and 3) analyze address/location information.

WEBSITE HTML STRUCTURE:
```html
{html_content}
```

AVAILABLE IMAGES ON THE PAGE:
```json
{json.dumps(images_data, indent=2)}
```

COMBINED ANALYSIS TASKS:

**LOGO DETECTION:**
1. Look at the provided screenshot to visually identify the main logo
2. Use the HTML structure to understand the page layout and extract business information
3. Match the logo you see in the screenshot with one of the images from the available images list

**MERCHANT NAME EXTRACTION PRIORITY:**
- Text within or immediately next to the logo
- Main page title (HTML <title> tag)
- Primary headings (H1, H2) that contain business names
- Navigation menu items that indicate business name
- Header/footer text with business identification
- Meta tags with site/business names

**ADDRESS & LOCATION ANALYSIS:**
4. Extract complete business address information from the website content
5. Identify location context clues (city, state, country, region mentions)
6. Look for contact information, store locations, "about us" sections
7. Analyze any address-related structured data or schema markup

**ADDRESS EXTRACTION PRIORITY:**
- Contact/About pages with full addresses
- Footer sections with business address
- Store location pages or "Find Us" sections
- Structured data (JSON-LD, microdata) with address info
- Headers with location information
- Maps or location widgets with address details

**LOCATION CONTEXT CLUES:**
- City/state mentions in text content
- Phone numbers with area codes
- Local references or landmarks
- Service area descriptions
- "Serving [Location]" or "Located in [City]" text

**IMPORTANT ADDRESS FORMATTING RULES:**
- Expand all abbreviations: NY → New York, USA → United States, CA → California
- Remove suite numbers, unit numbers, floor numbers from main address
- Store suite/unit info separately but prioritize the main street address  
- Use full official names for countries and states
- If city has common abbreviations (NYC, LA, etc.), use full names

Remember to ignore any cookie overlays, popups, or modal dialogs - focus on the main website content behind them."""

        return prompt
    
    def detect_logo(self, domain_dir: str, domain_name: str) -> Dict[str, Any]:
        """
        Detect logo from website files, extract merchant name, and analyze address/location information.
        This is an optimized method that combines logo detection with address extraction stages 0-1
        to reduce LLM API calls.
        
        Args:
            domain_dir (str): Path to domain directory containing the files
            domain_name (str): Domain name for logging
            
        Returns:
            Dict[str, Any]: Combined analysis results including:
                - Logo detection results and merchant name
                - Address analysis (equivalent to address extraction stage 0-1)
                - Location context information
        """
        # Define file paths
        screenshot_path = None
        html_path = os.path.join(domain_dir, "page.html")
        images_path = os.path.join(domain_dir, "images.json")
        
        # Find screenshot file (it has timestamp in name)
        try:
            for file in os.listdir(domain_dir):
                if file.startswith("screenshot_") and file.endswith(".png"):
                    screenshot_path = os.path.join(domain_dir, file)
                    break
        except Exception as e:
            error(f"Error finding screenshot: {e}")
        
        # Load all required files
        screenshot_data = self._load_screenshot(screenshot_path) if screenshot_path else None
        html_content = self._load_html_content(html_path)
        images_data = self._load_images_data(images_path)
        
        # Check if we have the minimum required data
        if not screenshot_data:
            return self._create_error_result("No screenshot available for analysis")
        
        if not html_content:
            return self._create_error_result("No HTML content available for analysis")
        
        if not images_data:
            return self._create_error_result("No images data available for analysis")
        
        try:
            # Create user prompt
            user_prompt = self._create_user_prompt(html_content, images_data)
            
            # Query the LLM (silently)
            response = self.llm_client.query(
                model=self.model_config['model'],
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                image_data=screenshot_data,
                image_mime_type="image/png",
                max_tokens=self.model_config['max_tokens'],
                temperature=self.model_config['temperature']
            )
            
            # Parse the response
            result = self._parse_llm_response(response['content'])
            
            # Add metadata
            result['analysis_metadata'] = {
                'model_used': self.model_config['model'],
                'total_images_analyzed': len(images_data),
                'html_length': len(html_content),
                'screenshot_available': True,
                'tokens_used': response.get('usage', {}).get('total_tokens', 0)
            }
            
            return result
            
        except Exception as e:
            error(f"Logo detection failed for {domain_name}: {e}")
            return self._create_error_result(f"Analysis failed: {str(e)}")
    
    def _parse_llm_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse LLM response and extract JSON.
        
        Args:
            response_content (str): Raw LLM response
            
        Returns:
            Dict[str, Any]: Parsed logo detection result
        """
        try:
            # Try to find JSON in the response
            import re
            
            # Look for JSON block
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # Validate required keys and add defaults for new fields
                required_keys = ['logo_found', 'confidence', 'selected_image', 'reasoning']
                new_keys = ['merchant_name', 'merchant_name_source', 'merchant_name_confidence', 'alternative_names']
                address_keys = ['address_analysis', 'location_context']
                
                for key in required_keys:
                    if key not in result:
                        result[key] = None
                
                # Add default values for merchant name fields if missing
                if 'merchant_name' not in result:
                    result['merchant_name'] = ""
                if 'merchant_name_source' not in result:
                    result['merchant_name_source'] = ""
                if 'merchant_name_confidence' not in result:
                    result['merchant_name_confidence'] = 0.0
                if 'alternative_names' not in result:
                    result['alternative_names'] = []
                
                # Add default values for address analysis fields if missing
                if 'address_analysis' not in result:
                    result['address_analysis'] = {
                        'addresses_found': [],
                        'confidence': 'none',
                        'primary_address': '',
                        'address_components': {
                            'house_number_street': '',
                            'city': '',
                            'county': '',
                            'state': '',
                            'country': '',
                            'postal_code': ''
                        },
                        'clean_address': '',
                        'source': '',
                        'reasoning': 'No address information found'
                    }
                elif 'address_components' not in result['address_analysis']:
                    # Ensure address_components exists in existing address_analysis
                    result['address_analysis']['address_components'] = {
                        'house_number_street': '',
                        'city': '',
                        'county': '',
                        'state': '',
                        'country': '',
                        'postal_code': ''
                    }
                if 'clean_address' not in result.get('address_analysis', {}):
                    result['address_analysis']['clean_address'] = ''
                if 'location_context' not in result:
                    result['location_context'] = {
                        'city': '',
                        'state': '',
                        'country': '',
                        'region': '',
                        'local_references': [],
                        'confidence': 'none'
                    }
                
                return result
            else:
                # No JSON found, create error result
                return self._create_error_result("LLM response did not contain valid JSON")
                
        except json.JSONDecodeError as e:
            return self._create_error_result(f"Invalid JSON in response: {str(e)}")
        except Exception as e:
            return self._create_error_result(f"Response parsing failed: {str(e)}")
    
    def _create_error_result(self, reason: str) -> Dict[str, Any]:
        """
        Create a standard error result.
        
        Args:
            reason (str): Reason for the error
            
        Returns:
            Dict[str, Any]: Error result
        """
        return {
            'logo_found': False,
            'confidence': 'none',
            'selected_image': {},
            'reasoning': reason,
            'visual_description': 'Analysis failed',
            'merchant_name': '',
            'merchant_name_source': '',
            'merchant_name_confidence': 0.0,
            'alternative_names': [],
            'address_analysis': {
                'addresses_found': [],
                'confidence': 'none',
                'primary_address': '',
                'address_components': {
                    'house_number_street': '',
                    'city': '',
                    'county': '',
                    'state': '',
                    'country': '',
                    'postal_code': ''
                },
                'clean_address': '',
                'source': '',
                'reasoning': 'Analysis failed'
            },
            'location_context': {
                'city': '',
                'state': '',
                'country': '',
                'region': '',
                'local_references': [],
                'confidence': 'none'
            },
            'analysis_metadata': {
                'error': True,
                'model_used': self.model_config.get('model', 'unknown'),
                'total_images_analyzed': 0,
                'html_length': 0,
                'screenshot_available': False,
                'tokens_used': 0
            }
        }
    
    def save_logo_result(self, domain_dir: str, logo_result: Dict[str, Any]) -> str:
        """
        Save logo detection result to JSON file.
        
        Args:
            domain_dir (str): Domain directory path
            logo_result (Dict[str, Any]): Logo detection result
            
        Returns:
            str: Path to saved file
        """
        try:
            logo_file_path = os.path.join(domain_dir, "logo_detection.json")
            
            with open(logo_file_path, 'w', encoding='utf-8') as f:
                json.dump(logo_result, f, indent=2, ensure_ascii=False)
            
            return logo_file_path
            
        except Exception as e:
            return ""


# Convenience function
def detect_website_logo(domain_dir: str, domain_name: str) -> Dict[str, Any]:
    """
    Convenience function to detect logo from a website directory.
    
    Args:
        domain_dir (str): Path to domain directory
        domain_name (str): Domain name
        
    Returns:
        Dict[str, Any]: Logo detection results
    """
    detector = LogoDetector()
    return detector.detect_logo(domain_dir, domain_name)