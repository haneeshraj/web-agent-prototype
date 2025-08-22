import json
import os
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.llm import create_llm_client
from utils.config import get_model_config
from utils.terminal_prettify import success, error, warning, info


class BrandImageDetector:
    """
    Brand image detection agent that analyzes screenshots and HTML to identify website brand images and extract company names.
    """
    
    def __init__(self):
        """Initialize the brand image detector with LLM client and configuration."""
        self.llm_client = create_llm_client()
        self.model_config = get_model_config("classifier-agent")
        
        # System prompt for brand image detection and company name extraction
        self.system_prompt = """You are a website brand image detection, company name extraction, and business address analysis expert. Your task is to identify the main brand image/visual identity element from a website, extract the company/business name, AND analyze for business address information using the provided screenshot and HTML structure.

INSTRUCTIONS:
1. Analyze the screenshot to visually identify the website's main brand image/visual identity element
2. Use the HTML structure to understand the page layout and context
3. Extract the company/business name from various sources (brand image text, page title, headings, etc.)
4. ADDITIONALLY: Analyze the HTML content for business address information and location context
5. If there are cookie overlays, popups, or modals, ignore them and focus on the main website content behind them

BRAND IMAGE DETECTION:
6. Look for brand images typically positioned in:
   - Header/navigation area (most common)
   - Top-left corner
   - Center of header
   - Footer area (secondary brand images)

7. From the provided images list, identify which image corresponds to the brand image you see in the screenshot
8. Consider these brand image characteristics:
   - Usually contains company/brand name or distinctive visual identity
   - Often positioned prominently in navigation
   - May have alt text with brand/company names
   - Typically appears in header sections

COMPANY NAME EXTRACTION:
9. Look for the business/company name in multiple sources:
   - Brand image text (text within or next to the brand image)
   - Page title (HTML <title> tag)
   - Main headings (H1, H2 tags)
   - Navigation menu items
   - "About" or "Company" sections
   - Meta tags (business name, site name)
   - Footer copyright information
10. Prioritize names that appear in prominent locations (header, brand image area, main title)
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
16. PLATFORM vs COMPANY DISTINCTION:
    - If the page is a social media platform's login/signup page, return brand_image_found as false
    - Only return brand_image_found as true for actual COMPANY/BUSINESS brand images
    - Platform brand images should NOT be considered the "main brand image"

17. VALID BRAND IMAGE CRITERIA:
    - Must be a designed brand identity element (text-based brand image, symbol, or combination)
    - DO NOT select profile pictures of people or generic photos
    - Only select images representing business/brand identity

RESPONSE FORMAT:
Return ONLY a valid JSON object with this exact structure - no other text before or after:
{
    "brand_image_found": true,
    "confidence": 0.95,
    "selected_image": {
        "src": "image_url_here",
        "alt": "alt_text_here",
        "class": "class_name_here"
    },
    "reasoning": "Detailed explanation of brand image selection or why no brand image found",
    "visual_description": "Description of what the brand image looks like in the screenshot",
    "company_name": "Extracted business/company name",
    "company_name_source": "Where the company name was found",
    "company_name_confidence": 0.95,
    "alternative_names": ["other possible business names found"],
    "address_analysis": {
        "addresses_found": ["list of addresses found on the website"],
        "confidence": 0.85,
        "primary_address": "Main business address if found",
        "address_components": {
            "house_number_street": "House number and street name",
            "city": "City name in full form",
            "county": "County/District if applicable",
            "state": "State/Province in full form",
            "country": "Country in full form",
            "postal_code": "Postal/ZIP code if applicable"
        },
        "clean_address": "Address without suite numbers",
        "source": "Where address was found",
        "reasoning": "Explanation of address selection"
    },
    "location_context": {
        "city": "Primary city",
        "state": "Primary state/province",
        "country": "Primary country",
        "region": "Regional context",
        "local_references": ["local landmarks or references"],
        "confidence": 0.80
    }
}

CRITICAL JSON REQUIREMENTS:
- Return ONLY valid JSON - no markdown code blocks, no explanatory text
- Use double quotes for all strings
- No trailing commas
- All fields must be present with appropriate default values
- String values cannot be null - use empty string "" if no value
- Confidence values: use decimal numbers between 0.0 and 1.0 (not strings)
- If no brand image found, set selected_image to {}
- All address components must be strings, not null

IMPORTANT:
- Return ONLY valid JSON - no markdown, no explanations, no code blocks
- Use proper JSON syntax with double quotes and no trailing commas
- All fields must be present - use empty strings "" instead of null
- If no brand image found, set brand_image_found to false and selected_image to {}
- If no address found, use empty strings for address fields
- If no location context found, use empty strings for location fields
- Always attempt to extract company name even if no brand image found
- Focus on ORIGINAL/PRIMARY business locations, not expansion markets
- Use decimal confidence values between 0.0 and 1.0 (e.g., 0.95, 0.75, 0.50)
"""

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
        
        prompt = f"""Please analyze this website to: 1) identify the main brand image/visual identity element, 2) extract the company/business name, and 3) analyze address/location information.

WEBSITE HTML STRUCTURE:
```html
{html_content}
```

AVAILABLE IMAGES ON THE PAGE:
```json
{json.dumps(images_data, indent=2)}
```

COMBINED ANALYSIS TASKS:

**BRAND IMAGE DETECTION:**
1. Look at the provided screenshot to visually identify the main brand image
2. Use the HTML structure to understand the page layout and extract business information
3. Match the brand image you see in the screenshot with one of the images from the available images list

**COMPANY NAME EXTRACTION PRIORITY:**
- Text within or immediately next to the brand image
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
    
    def detect_brand_image(self, domain_dir: str, domain_name: str) -> Dict[str, Any]:
        """
        Detect brand image from website files, extract company name, and analyze address/location information.
        This is an optimized method that combines brand image detection with address extraction stages 0-1
        to reduce LLM API calls.
        
        Args:
            domain_dir (str): Path to domain directory containing the files
            domain_name (str): Domain name for logging
            
        Returns:
            Dict[str, Any]: Combined analysis results including:
                - Brand image detection results and company name
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
            error(f"Brand image detection failed for {domain_name}: {e}")
            return self._create_error_result(f"Analysis failed: {str(e)}")
    
    def _parse_llm_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse LLM response with robust JSON handling and comprehensive defaults.
        
        Args:
            response_content (str): Raw LLM response
            
        Returns:
            Dict[str, Any]: Parsed brand image detection result
        """
        try:
            # Save raw response for debugging
            debug_response = response_content[:1000] + "..." if len(response_content) > 1000 else response_content
            
            # Try multiple JSON extraction strategies
            result = None
            
            # Strategy 1: Look for complete JSON block
            import re
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    # Strategy 2: Try to fix common JSON issues
                    json_str = self._fix_json_format(json_str)
                    try:
                        result = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Strategy 3: Extract partial valid JSON
                        result = self._extract_partial_json(json_str)
            
            if result is None:
                # Strategy 4: Try to extract key information manually
                result = self._extract_manual_parsing(response_content)
            
            # Validate and populate with defaults
            if result:
                result = self._ensure_complete_structure(result)
                return result
            else:
                return self._create_error_result(f"Failed to parse JSON response. Debug: {debug_response}")
                
        except Exception as e:
            return self._create_error_result(f"Response parsing failed: {str(e)}")
    
    def _fix_json_format(self, json_str: str) -> str:
        """Fix common JSON formatting issues."""
        import re
        # Remove trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        # Fix unescaped quotes in strings
        json_str = re.sub(r'(?<!\\)"(?=[^:,}\]]*")', '\\"', json_str)
        # Ensure proper quote consistency
        json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
        return json_str
    
    def _extract_partial_json(self, json_str: str) -> Dict[str, Any]:
        """Extract valid JSON from a potentially corrupted response."""
        try:
            # Try to find valid JSON blocks within the string
            brace_count = 0
            for i, char in enumerate(json_str):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found a complete JSON block
                        partial_json = json_str[:i+1]
                        try:
                            return json.loads(partial_json)
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass
        return None
    
    def _extract_manual_parsing(self, response_content: str) -> Dict[str, Any]:
        """Manually extract key information when JSON parsing fails."""
        import re
        result = {}
        
        # Extract company name manually
        company_patterns = [
            r'"company_name":\s*"([^"]+)"',
            r"'company_name':\s*'([^']+)'",
            r'company name.*?[:\-]\s*([A-Za-z0-9\s&.-]+)',
            r'business name.*?[:\-]\s*([A-Za-z0-9\s&.-]+)'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, response_content, re.IGNORECASE)
            if match:
                result['company_name'] = match.group(1).strip()
                result['company_name_source'] = 'manual_extraction'
                result['company_name_confidence'] = 0.7
                break
        
        # Extract brand detection result
        if re.search(r'brand.*found|logo.*detected|brand.*present', response_content, re.IGNORECASE):
            result['brand_image_found'] = True
            result['confidence'] = 0.6
        else:
            result['brand_image_found'] = False
            result['confidence'] = 0.2
        
        return result if result else None
    
    def _ensure_complete_structure(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the result has all required fields with proper defaults."""
        # Validate required keys and add defaults for new fields
        required_keys = ['brand_image_found', 'confidence', 'selected_image', 'reasoning']
        
        for key in required_keys:
            if key not in result:
                result[key] = None
        
        # Add default values for company name fields if missing
        if 'company_name' not in result:
            result['company_name'] = ""
        if 'company_name_source' not in result:
            result['company_name_source'] = ""
        if 'company_name_confidence' not in result:
            result['company_name_confidence'] = 0.0
        if 'alternative_names' not in result:
            result['alternative_names'] = []
        
        # Add default values for address analysis fields if missing
        if 'address_analysis' not in result:
            result['address_analysis'] = {
                'addresses_found': [],
                'confidence': 0.0,
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
                'confidence': 0.0
            }
        
        return result
    
    def _create_error_result(self, reason: str) -> Dict[str, Any]:
        """
        Create a standard error result.
        
        Args:
            reason (str): Reason for the error
            
        Returns:
            Dict[str, Any]: Error result
        """
        return {
            'brand_image_found': False,
            'confidence': 0.0,
            'selected_image': {},
            'reasoning': reason,
            'visual_description': 'Analysis failed',
            'company_name': '',
            'company_name_source': '',
            'company_name_confidence': 0.0,
            'alternative_names': [],
            'address_analysis': {
                'addresses_found': [],
                'confidence': 0.0,
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
                'confidence': 0.0
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
    
    def save_brand_image_result(self, domain_dir: str, brand_image_result: Dict[str, Any]) -> str:
        """
        Save brand image detection result to JSON file.
        
        Args:
            domain_dir (str): Domain directory path
            brand_image_result (Dict[str, Any]): Brand image detection result
            
        Returns:
            str: Path to saved file
        """
        try:
            brand_image_file_path = os.path.join(domain_dir, "brand_image_detection.json")
            
            with open(brand_image_file_path, 'w', encoding='utf-8') as f:
                json.dump(brand_image_result, f, indent=2, ensure_ascii=False)
            
            return brand_image_file_path
        except Exception:
            return ""


# Convenience functions
def detect_website_brand_image(domain_dir: str, domain_name: str) -> Dict[str, Any]:
    """
    Convenience function to detect brand image from a website directory.
    
    Args:
        domain_dir (str): Path to domain directory
        domain_name (str): Domain name
        
    Returns:
        Dict[str, Any]: Brand image detection results
    """
    detector = BrandImageDetector()
    return detector.detect_brand_image(domain_dir, domain_name)