import json
import os
import time
import requests
import urllib.parse
from typing import Dict, Any, Optional, List
from pathlib import Path

from utils.llm import create_llm_client
from utils.config import get_model_config
from utils.web_search import create_serpapi_client
from utils.terminal_prettify import success, error, warning, info


class AddressExtractor:
    """
    Address extraction agent that analyzes websites and search results to extract business addresses.
    """
    
    def __init__(self):
        """Initialize the address extractor with LLM client and SerpAPI client."""
        self.llm_client = create_llm_client()
        self.model_config = get_model_config("classifier-agent")
        self.serpapi_client = create_serpapi_client()
        
        # System prompt for location context extraction
        self.location_context_prompt = """You are an expert at analyzing website content to identify geographic location context for a business.

INSTRUCTIONS:
1. Analyze the provided website content to identify location indicators
2. Look for mentions of:
   - Countries, states/provinces, cities where the business operates
   - "Founded in", "Based in", "Established in" statements
   - Geographic indicators in the business description
   - Regional mentions that suggest the original/primary location

3. Focus on finding the ORIGINAL or PRIMARY business location, not just any location where they operate
4. Prioritize information that suggests headquarters, founding location, or main base of operations

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
    "primary_country": "Country where business was founded/is primarily based",
    "primary_state_province": "State/province of primary location (if applicable)",
    "primary_city": "City of primary location (if mentioned)",
    "additional_locations": ["other countries/regions mentioned", "if any"],
    "location_confidence": 0.85,
    "reasoning": "Explanation of why this location was identified as primary"
}

IMPORTANT:
- Only return valid JSON
- If no clear location context is found, use empty strings for location fields
- Confidence should be between 0.0 and 1.0
- Focus on ORIGINAL/FOUNDING location, not expansion markets"""

        # System prompt for address detection in website content
        self.address_detection_prompt = """You are an expert at analyzing website content to determine if a business address is present and extracting it.

INSTRUCTIONS:
1. Analyze the provided website HTML content to determine if it contains a business address
2. Look for addresses in common locations:
   - Contact page sections
   - Footer areas
   - Header information
   - About sections
   - Store/location pages
   - Business information sections

3. IMPORTANT: Look for MAIN business addresses such as:
   - Headquarters address
   - Main office address
   - Primary store location
   - Business registration address
   - Corporate office

4. DO NOT extract:
   - Shipping/warehouse addresses (unless that's the main business location)
   - Customer service addresses
   - PO Box addresses (unless it's the only address available)
   - Multiple store locations (focus on main/headquarters)

5. If multiple addresses are found, prioritize:
   - Headquarters/main office
   - Primary business location
   - The address labeled as "main" or "corporate"

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
    "address_found_in_website": true/false,
    "extracted_address": "Full formatted address if found, empty string if not",
    "address_components": {
        "house_number_street": "House number and street name (e.g., '225 Delaware Avenue')",
        "city": "City name in full form (e.g., 'New York' not 'NYC')",
        "county": "County/District if applicable",
        "state": "State/Province in full form (e.g., 'New York' not 'NY')",
        "country": "Country in full form (e.g., 'United States' not 'USA')",
        "postal_code": "Postal/ZIP code if applicable"
    },
    "clean_address": "Address without suite numbers or secondary identifiers",
    "address_confidence": 0.95,
    "address_source": "Where the address was found (e.g., 'contact page', 'footer', 'about section')",
    "address_type": "Type of address (e.g., 'headquarters', 'main office', 'primary store')",
    "reasoning": "Detailed explanation of why this address was selected or why no address was found"
}

IMPORTANT ADDRESS FORMATTING RULES:
- Expand all abbreviations: NY → New York, USA → United States, CA → California
- Remove suite numbers, unit numbers, floor numbers from main address
- Store suite/unit info separately but prioritize the main street address
- Use full official names for countries and states
- If city has common abbreviations (NYC, LA, etc.), use full names

IMPORTANT:
- Only return valid JSON
- If no address is found, set address_found_in_website to false
- Address confidence should be between 0.0 and 1.0
- Be specific about the source and type of address found"""

        # System prompt for address extraction from search results
        self.search_address_extraction_prompt = """You are an expert at analyzing search results to extract the PRIMARY headquarters address for a business, especially when multiple locations exist.

INSTRUCTIONS:
1. Analyze the provided search results to find the most accurate PRIMARY business headquarters
2. When multiple addresses are found, prioritize in this order:
   - Original founding location/headquarters
   - Corporate headquarters or main office
   - Administrative headquarters
   - Primary business registration address
   - First established location (if business has expanded)

3. Look for key indicators:
   - "Headquarters", "Head Office", "Corporate Office", "Founded in"
   - "Main Office", "Primary Location", "Original Location"
   - Business registration addresses
   - Official company contact addresses

4. Handle multi-location businesses carefully:
   - If a business has expanded to multiple countries/states, prioritize the ORIGINAL location
   - Distinguish between franchise locations and corporate headquarters
   - Consider historical context (e.g., if founded in one city but later expanded)
   - Prefer addresses associated with corporate/administrative functions

5. Validate consistency across sources:
   - Official business listings take priority over third-party directories
   - Company website information is most authoritative
   - Government/business registration data is highly reliable

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
    "address_found": true/false,
    "extracted_address": "Full formatted address if found, empty string if not",
    "address_components": {
        "house_number_street": "House number and street name (e.g., '225 Delaware Avenue')",
        "city": "City name in full form (e.g., 'New York' not 'NYC')",
        "county": "County/District if applicable",
        "state": "State/Province in full form (e.g., 'New York' not 'NY')",
        "country": "Country in full form (e.g., 'United States' not 'USA')",
        "postal_code": "Postal/ZIP code if applicable"
    },
    "clean_address": "Address without suite numbers or secondary identifiers",
    "address_confidence": 0.95,
    "address_source": "Which search result source provided the address",
    "address_type": "Type of address (e.g., 'corporate headquarters', 'founding location', 'main office')",
    "reasoning": "Detailed explanation of why this address was selected as the PRIMARY headquarters",
    "supporting_sources": ["list of sources that confirm this address"],
    "alternative_addresses": [
        {
            "address": "Other significant addresses found",
            "type": "Type (e.g., 'regional office', 'franchise location')",
            "reason_not_selected": "Why this wasn't chosen as primary"
        }
    ]
}

IMPORTANT ADDRESS FORMATTING RULES:
- Expand all abbreviations: NY → New York, USA → United States, CA → California  
- Remove suite numbers, unit numbers, floor numbers from main address
- Store suite/unit info separately but prioritize the main street address
- Use full official names for countries and states
- If city has common abbreviations (NYC, LA, etc.), use full names

IMPORTANT:
- Only return valid JSON
- If no reliable PRIMARY headquarters is found, set address_found to false
- Address confidence should be between 0.0 and 1.0
- When multiple legitimate headquarters exist (e.g., dual headquarters), choose the ORIGINAL/FOUNDING location
- Always explain your reasoning, especially when multiple addresses were considered"""

    def _load_html_content(self, html_path: str) -> Optional[str]:
        """Load HTML content from file."""
        try:
            if not os.path.exists(html_path):
                return None
                
            with open(html_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    def _query_llm_with_retry(self, prompt: str, system_prompt: str, context: str, retry_count: int = 0) -> str:
        """
        Query LLM with retry logic for rate limiting.
        
        Args:
            prompt (str): User prompt for the model
            system_prompt (str): System prompt for the model
            context (str): Context for error messages ("website_analysis" or "search_analysis")
            retry_count (int): Current retry attempt
            
        Returns:
            str: Model response or fallback response
        """
        try:
            
            response = self.llm_client.query(
                model=self.model_config['model'],
                system_prompt=system_prompt,
                user_prompt=prompt,
                max_tokens=self.model_config['max_tokens'],
                temperature=self.model_config.get('temperature', 0.3)
            )
            
            # Query completed successfully
            content = response.get('content') if response else None
            return content.strip() if content else ""
            
        except Exception as e:
            error_str = str(e)
            
            # Check for rate limiting
            if any(indicator in error_str.lower() for indicator in ['429', 'rate', 'limit', 'quota', 'capacity']):
                if retry_count < 3:
                    wait_time = (2 ** retry_count) * 10  # 10, 20, 40 seconds
                    warning(f"Rate limited. Waiting {wait_time} seconds before retry {retry_count + 1}/3...")
                    time.sleep(wait_time)
                    return self._query_llm_with_retry(prompt, system_prompt, context, retry_count + 1)
                else:
                    error(f"Max retries reached for {context}. Using fallback.")
                    return self._get_fallback_response(context)
            
            # For other errors, log and use fallback
            error(f"LLM query failed for {context}: {e}")
            return self._get_fallback_response(context)

    def _get_fallback_response(self, context: str) -> str:
        """Get fallback JSON response when LLM fails."""
        if context == "website_analysis":
            return json.dumps({
                "address_found_in_website": False,
                "extracted_address": "",
                "address_components": {
                    "house_number_street": "",
                    "city": "",
                    "county": "",
                    "state": "",
                    "country": "",
                    "postal_code": ""
                },
                "clean_address": "",
                "address_confidence": 0.0,
                "address_source": "",
                "address_type": "",
                "reasoning": "LLM query failed - fallback response used"
            })
        elif context == "location_context":
            return json.dumps({
                "primary_country": "",
                "primary_state_province": "",
                "primary_city": "",
                "additional_locations": [],
                "location_confidence": 0.0,
                "reasoning": "LLM query failed - fallback response used"
            })
        else:  # search_analysis
            return json.dumps({
                "address_found": False,
                "extracted_address": "",
                "address_components": {
                    "house_number_street": "",
                    "city": "",
                    "county": "",
                    "state": "",
                    "country": "",
                    "postal_code": ""
                },
                "clean_address": "",
                "address_confidence": 0.0,
                "address_source": "",
                "address_type": "",
                "reasoning": "LLM query failed - fallback response used",
                "supporting_sources": [],
                "alternative_addresses": []
            })

    def _geocode_address(self, address: str) -> Dict[str, Any]:
        """
        Simple geocoding method that validates an address string and returns coordinates.
        
        Args:
            address (str): Full address string to geocode
            
        Returns:
            Dict[str, Any]: Geocoding result with success status, coordinates, and formatted address
        """
        try:
            if not address or not address.strip():
                return {
                    "success": False,
                    "error": "Empty address provided",
                    "lat": None,
                    "lon": None,
                    "formatted_address": ""
                }
            
            # Make request to Nominatim API
            params = {
                'q': address.strip(),
                'format': 'json',
                'limit': '1',
                'addressdetails': '1'
            }
            
            headers = {
                'User-Agent': 'LLMAgentPrototype/1.0 (business-address-extraction)',
                'Accept': 'application/json'
            }
            
            # Rate limiting - Nominatim allows 1 request per second
            time.sleep(1)
            
            response = requests.get(
                "https://nominatim.openstreetmap.org/search", 
                params=params, 
                headers=headers, 
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json()
            
            if results and len(results) > 0:
                result = results[0]
                return {
                    "success": True,
                    "lat": float(result.get('lat', 0)),
                    "lon": float(result.get('lon', 0)),
                    "formatted_address": result.get('display_name', address),
                    "place_id": result.get('place_id'),
                    "address_type": result.get('addresstype'),
                    "boundingbox": result.get('boundingbox'),
                    "confidence": float(result.get('importance', 0.5))
                }
            else:
                return {
                    "success": False,
                    "error": "No geocoding results found",
                    "lat": None,
                    "lon": None,
                    "formatted_address": address
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Geocoding API request failed: {str(e)}",
                "lat": None,
                "lon": None,
                "formatted_address": address
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Geocoding failed: {str(e)}",
                "lat": None,
                "lon": None,
                "formatted_address": address
            }

    def _geocode_address_detailed(self, address_components: Dict[str, str], full_address: str) -> Optional[Dict[str, Any]]:
        """
        Geocode address using OpenStreetMap Nominatim API with detailed components.
        
        Args:
            address_components (Dict[str, str]): Structured address components
            full_address (str): Full address string as fallback
            
        Returns:
            Optional[Dict[str, Any]]: Geocoding result with lat, lon, and validated address
        """
        try:
            # First attempt: Use structured query with components
            if address_components:
                params = {}
                if address_components.get('house_number_street'):
                    params['street'] = address_components['house_number_street']
                if address_components.get('city'):
                    params['city'] = address_components['city']
                if address_components.get('county'):
                    params['county'] = address_components['county']
                if address_components.get('state'):
                    params['state'] = address_components['state']
                if address_components.get('country'):
                    params['country'] = address_components['country']
                if address_components.get('postal_code'):
                    params['postalcode'] = address_components['postal_code']
                
                params['format'] = 'json'
                params['limit'] = '5'
                
                if params:
                    response = self._make_nominatim_request(params)
                    if response and len(response) > 0:
                        result = response[0]  # Take first result
                        return {
                            'lat': result.get('lat'),
                            'lon': result.get('lon'),
                            'display_name': result.get('display_name'),
                            'address_type': result.get('addresstype'),
                            'place_id': result.get('place_id'),
                            'boundingbox': result.get('boundingbox'),
                            'source': 'structured_query'
                        }
            
            # Fallback: Try with full address string
            if full_address:
                fallback_params = {
                    'q': full_address,
                    'format': 'json',
                    'limit': '5'
                }
                response = self._make_nominatim_request(fallback_params)
                if response and len(response) > 0:
                    result = response[0]  # Take first result
                    return {
                        'lat': result.get('lat'),
                        'lon': result.get('lon'),
                        'display_name': result.get('display_name'),
                        'address_type': result.get('addresstype'),
                        'place_id': result.get('place_id'),
                        'boundingbox': result.get('boundingbox'),
                        'source': 'full_address_query'
                    }
            
            warning("No geocoding results found")
            return None
            
        except Exception as e:
            error(f"Geocoding failed: {e}")
            return None

    def _make_nominatim_request(self, params: Dict[str, str]) -> Optional[List[Dict]]:
        """
        Make request to Nominatim API with proper rate limiting.
        
        Args:
            params (Dict[str, str]): Query parameters
            
        Returns:
            Optional[List[Dict]]: API response or None if failed
        """
        try:
            base_url = "https://nominatim.openstreetmap.org/search"
            
            # Add required headers
            headers = {
                'User-Agent': 'LLMAgentPrototype/1.0 (business-address-extraction)',
                'Accept': 'application/json'
            }
            
            # Rate limiting - Nominatim allows 1 request per second
            time.sleep(1)
            
            response = requests.get(base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except requests.exceptions.RequestException as e:
            error(f"Nominatim API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            error(f"Failed to parse Nominatim response: {e}")
            return None

    def _create_clean_address_fallback(self, full_address: str) -> str:
        """
        Create a clean address by removing suite numbers and expanding abbreviations.
        Used as fallback when LLM doesn't provide clean_address.
        
        Args:
            full_address (str): Original address
            
        Returns:
            str: Cleaned address
        """
        if not full_address:
            return ""
        
        # Remove common suite/unit identifiers
        import re
        clean_addr = re.sub(r'\b(Suite|Ste|Unit|Apt|Apartment|Floor|Fl|Room|Rm)\s+[A-Za-z0-9#-]+\b,?\s*', '', full_address, flags=re.IGNORECASE)
        
        # Basic abbreviation expansions
        expansions = {
            r'\bNY\b': 'New York',
            r'\bCA\b': 'California', 
            r'\bTX\b': 'Texas',
            r'\bFL\b': 'Florida',
            r'\bUSA\b': 'United States',
            r'\bNYC\b': 'New York',
            r'\bLA\b': 'Los Angeles'
        }
        
        for abbrev, full_form in expansions.items():
            clean_addr = re.sub(abbrev, full_form, clean_addr, flags=re.IGNORECASE)
        
        return clean_addr.strip()

    def _extract_location_context(self, html_content: str) -> Dict[str, Any]:
        """
        Extract location context from website content to improve search queries.
        
        Args:
            html_content (str): Website HTML content
            
        Returns:
            Dict[str, Any]: Location context information
        """
        try:
            # Don't truncate HTML - location context might be anywhere on the page
            # Let the LLM analyze the complete content for geographic indicators
            
            user_prompt = f"""Please analyze this website content to identify the geographic location context for this business.

WEBSITE HTML CONTENT:
```html
{html_content}
```

TASK:
1. Identify the primary/original location where this business was founded or is primarily based
2. Look for geographic indicators in the content
3. Focus on finding the main business location, not just any location where they operate
4. Return your analysis in the specified JSON format

Focus on finding the ORIGINAL or PRIMARY business location that would help identify the main headquarters."""

            # Use retry logic for LLM query
            raw_response = self._query_llm_with_retry(
                user_prompt, 
                self.location_context_prompt, 
                "location_context"
            )
            
            if not raw_response:
                return {
                    "primary_country": "",
                    "primary_state_province": "",
                    "primary_city": "",
                    "additional_locations": [],
                    "location_confidence": 0.0,
                    "reasoning": "No location context could be extracted"
                }
            
            # Ensure raw_response is a string
            if not isinstance(raw_response, str):
                raw_response = str(raw_response) if raw_response else ""
            
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = raw_response
            
            # Parse JSON response
            result = json.loads(json_str)
            # Location context extraction complete
            return result
            
        except Exception as e:
            error(f"Location context extraction failed: {e}")
            return {
                "primary_country": "",
                "primary_state_province": "",
                "primary_city": "",
                "additional_locations": [],
                "location_confidence": 0.0,
                "reasoning": f"Location context extraction error: {e}"
            }

    def _analyze_website_for_address(self, html_content: str) -> Dict[str, Any]:
        """
        Analyze website HTML content for business address.
        
        Args:
            html_content (str): Website HTML content
            
        Returns:
            Dict[str, Any]: Address analysis results
        """
        try:
            # Don't truncate HTML - addresses are often in footers/contact sections at the end
            # Let the LLM see the complete page content to find addresses anywhere
            
            user_prompt = f"""Please analyze this website HTML content to detect if a business address is present and extract it.

WEBSITE HTML CONTENT:
```html
{html_content}
```

TASK:
1. Scan through the HTML content for business address information
2. Look for complete addresses including street, city, state/province, postal code
3. Identify the type and source of the address found
4. Return your analysis in the specified JSON format

Remember to focus on main business addresses (headquarters, main office, primary location) and avoid secondary addresses like warehouses or customer service centers unless that's the primary business location."""

            # Use retry logic for LLM query
            raw_response = self._query_llm_with_retry(
                user_prompt, 
                self.address_detection_prompt, 
                "website_analysis"
            )
            
            if not raw_response:
                error("LLM returned empty response")
                return {
                    "address_found_in_website": False,
                    "extracted_address": "",
                    "address_confidence": 0.0,
                    "address_source": "",
                    "address_type": "",
                    "reasoning": "LLM returned empty response"
                }
            
            # Ensure raw_response is a string
            if not isinstance(raw_response, str):
                raw_response = str(raw_response) if raw_response else ""
            
            # Try to extract JSON from the response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = raw_response
                
            # Check if JSON appears to be truncated
            if not json_str.strip().endswith('}') and len(raw_response) >= 1900:
                warning("JSON response appears to be truncated. Attempting to fix...")
                # Try to close any open objects/arrays
                open_braces = json_str.count('{') - json_str.count('}')
                if open_braces > 0:
                    json_str += '}' * open_braces
                    info(f"Added {open_braces} closing braces to fix truncated JSON")
            
            # Parse JSON response
            result = json.loads(json_str)
            
            # Add geocoding if address was found
            if result.get("address_found_in_website", False) and result.get("extracted_address"):
                # Get address components for structured geocoding
                address_components = result.get("address_components", {})
                full_address = result.get("extracted_address", "")
                clean_address = result.get("clean_address", "")
                
                # Create clean address fallback if not provided by LLM
                if not clean_address:
                    clean_address = self._create_clean_address_fallback(full_address)
                    result["clean_address"] = clean_address
                
                # Try geocoding with clean address first, then full address
                geocoding_result = None
                if clean_address:
                    # Create clean address components for geocoding
                    clean_components = address_components.copy() if address_components else {}
                    if clean_components.get('house_number_street'):
                        # Remove suite numbers from street component
                        import re
                        clean_street = re.sub(r'\b(Suite|Ste|Unit|Apt|Apartment|Floor|Fl|Room|Rm)\s+[A-Za-z0-9#-]+\b,?\s*', 
                                            '', clean_components['house_number_street'], flags=re.IGNORECASE).strip()
                        clean_components['house_number_street'] = clean_street
                    
                    geocoding_result = self._geocode_address_detailed(clean_components, clean_address)
                
                # Fallback to full address if clean address geocoding failed
                if not geocoding_result and full_address != clean_address:
                    warning("Clean address geocoding failed, trying full address...")
                    geocoding_result = self._geocode_address_detailed(address_components, full_address)
                
                # Add geocoding results to response
                if geocoding_result:
                    result["geocoding"] = geocoding_result
                    # Address geocoded successfully (displayed in main script)
                else:
                    result["geocoding"] = None
                    warning("Address geocoding failed - no coordinates available")
            
            # Website address analysis complete
            return result
            
        except json.JSONDecodeError as e:
            error(f"Failed to parse LLM response as JSON: {e}")
            error(f"Raw response: {raw_response[:200]}...")
            
            # Check if response appears to be truncated
            if len(raw_response) >= 1900 and not raw_response.strip().endswith('}'):
                warning("Response appears to be truncated due to token limit. Consider increasing max_tokens in config.yaml")
                
                # Try to extract partial information from truncated response
                if "extracted_address" in raw_response:
                    import re
                    # Try to extract the address from the partial JSON
                    address_match = re.search(r'"extracted_address":\s*"([^"]*)"', raw_response)
                    if address_match:
                        extracted_address = address_match.group(1)
                        warning(f"Extracted partial address from truncated response: {extracted_address}")
                        return {
                            "address_found_in_website": True,
                            "extracted_address": extracted_address,
                            "address_confidence": 0.5,  # Lower confidence due to truncation
                            "address_source": "Partial extraction from truncated response",
                            "address_type": "unknown",
                            "reasoning": f"JSON parsing error due to truncated response: {e}"
                        }
            
            return {
                "address_found_in_website": False,
                "extracted_address": "",
                "address_confidence": 0.0,
                "address_source": "",
                "address_type": "",
                "reasoning": f"JSON parsing error: {e}"
            }
        except Exception as e:
            error(f"Website address analysis failed: {e}")
            return {
                "address_found_in_website": False,
                "extracted_address": "",
                "address_confidence": 0.0,
                "address_source": "",
                "address_type": "",
                "reasoning": f"Analysis error: {e}"
            }

    def _search_for_address(self, company_name: str, business_type: str = "", location_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Search for business address using SerpAPI with location context.
        
        Args:
            company_name (str): Name of the business/company
            business_type (str): Type of business for better search context
            location_context (Dict[str, Any]): Geographic context from website analysis
            
        Returns:
            Dict[str, Any]: Search-based address extraction results
        """
        if not self.serpapi_client.is_available():
            return {
                "address_found": False,
                "extracted_address": "",
                "address_confidence": 0.0,
                "address_source": "",
                "address_type": "",
                "reasoning": "SerpAPI not available - missing API key",
                "supporting_sources": [],
                "alternative_addresses": []
            }
        
        try:
            # Build location-aware search queries
            base_queries = [
                f"{company_name} headquarters address",
                f"{company_name} corporate office address",
                f"{company_name} main office location",
                f"{company_name} head office address"
            ]
            
            # Add location context to search queries if available
            if location_context and location_context.get("location_confidence", 0.0) > 0.3:
                location_parts = []
                
                if location_context.get("primary_city"):
                    location_parts.append(location_context["primary_city"])
                if location_context.get("primary_state_province"):
                    location_parts.append(location_context["primary_state_province"])
                if location_context.get("primary_country"):
                    location_parts.append(location_context["primary_country"])
                
                if location_parts:
                    location_str = " ".join(location_parts)
                    # Add location-specific queries at the beginning (higher priority)
                    location_queries = [
                        f"{company_name} headquarters address {location_str}",
                        f"{company_name} main office {location_str}",
                        f"{company_name} corporate office {location_str}",
                        f"{company_name} founded in {location_str} headquarters"
                    ]
                    base_queries = location_queries + base_queries
                    # Using location context for search
            
            # Add business type specific queries if available
            if business_type:
                base_queries.extend([
                    f"{company_name} {business_type} headquarters address",
                    f"{company_name} {business_type} main location"
                ])
            
            all_business_info = []
            
            # Perform search with the first (most location-specific) query
            primary_query = base_queries[0]
            search_results = self.serpapi_client.search(primary_query, num_results=8)  # Increased for better coverage
            
            if search_results:
                # Send raw SerpAPI results directly to LLM instead of processing them first
                # This bypasses potential errors in extract_business_info()
                # Ensure search_results is a dictionary before sending to LLM
                if isinstance(search_results, dict):
                    all_business_info = search_results
                else:
                    # If search_results is not a dict, wrap it for safety
                    all_business_info = {"raw_response": search_results}
                # Found search results (count tracked internally)
            else:
                return {
                    "address_found": False,
                    "extracted_address": "",
                    "address_confidence": 0.0,
                    "address_source": "",
                    "address_type": "",
                    "reasoning": "No search results returned from SerpAPI",
                    "supporting_sources": [],
                    "alternative_addresses": []
                }
            
            # Analyze search results using LLM
            location_info = ""
            if location_context and location_context.get("location_confidence", 0.0) > 0.3:
                location_info = f"""
LOCATION CONTEXT (from website analysis):
- Primary Country: {location_context.get('primary_country', 'Unknown')}
- Primary State/Province: {location_context.get('primary_state_province', 'Unknown')}
- Primary City: {location_context.get('primary_city', 'Unknown')}
- Location Confidence: {location_context.get('location_confidence', 0.0):.2f}
- Reasoning: {location_context.get('reasoning', 'None')}

IMPORTANT: Use this location context to prioritize addresses in the primary location over expansion locations."""

            user_prompt = f"""Please analyze these RAW SerpAPI search results to extract the PRIMARY headquarters address for: {company_name}

COMPANY/BUSINESS NAME: {company_name}
BUSINESS TYPE: {business_type if business_type else "Unknown"}
{location_info}

RAW SERPAPI SEARCH RESULTS:
```json
{json.dumps(all_business_info, indent=2)}
```

INSTRUCTIONS FOR PARSING SERPAPI DATA:
1. Look in "knowledge_graph" section for direct business info (title, description, address, phone, website)
2. Look in "local_results" array for Google My Business listings (each has title, address, phone, etc.)
3. Look in "organic_results" array for regular search results (title, link, snippet)
4. Look in "answer_box" section for featured snippet information
5. Prioritize addresses from knowledge_graph and local_results as they are most reliable

TASK:
1. Parse the SerpAPI structure above to find address information
2. Find the PRIMARY headquarters address (original/founding location if multiple exist)
3. If location context is provided above, prioritize addresses in that primary location
4. For multi-location businesses, prefer the ORIGINAL headquarters over expansion offices
5. Return your analysis in the specified JSON format

Focus on finding the PRIMARY business headquarters for {company_name}, especially considering any location context provided above."""

            # Use retry logic for LLM query
            raw_response = self._query_llm_with_retry(
                user_prompt, 
                self.search_address_extraction_prompt, 
                "search_analysis"
            )
            
            if not raw_response:
                error("LLM returned empty response for search analysis")
                return {
                    "address_found": False,
                    "extracted_address": "",
                    "address_confidence": 0.0,
                    "address_source": "",
                    "address_type": "",
                    "reasoning": "LLM returned empty response for search analysis",
                    "supporting_sources": [],
                    "alternative_addresses": []
                }
            
            # Ensure raw_response is a string
            if not isinstance(raw_response, str):
                raw_response = str(raw_response) if raw_response else ""
            
            # Try to extract JSON from the response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = raw_response
            
            # Parse JSON response
            result = json.loads(json_str)
            
            # Add geocoding if address was found
            if result.get("address_found", False) and result.get("extracted_address"):
                # Get address components for structured geocoding
                address_components = result.get("address_components", {})
                full_address = result.get("extracted_address", "")
                clean_address = result.get("clean_address", "")
                
                # Create clean address fallback if not provided by LLM
                if not clean_address:
                    clean_address = self._create_clean_address_fallback(full_address)
                    result["clean_address"] = clean_address
                
                # Try geocoding with clean address first, then full address
                geocoding_result = None
                if clean_address:
                    # Create clean address components for geocoding
                    clean_components = address_components.copy() if address_components else {}
                    if clean_components.get('house_number_street'):
                        # Remove suite numbers from street component
                        import re
                        clean_street = re.sub(r'\b(Suite|Ste|Unit|Apt|Apartment|Floor|Fl|Room|Rm)\s+[A-Za-z0-9#-]+\b,?\s*', 
                                            '', clean_components['house_number_street'], flags=re.IGNORECASE).strip()
                        clean_components['house_number_street'] = clean_street
                    
                    geocoding_result = self._geocode_address_detailed(clean_components, clean_address)
                
                # Fallback to full address if clean address geocoding failed
                if not geocoding_result and full_address != clean_address:
                    warning("Clean address geocoding failed, trying full address...")
                    geocoding_result = self._geocode_address_detailed(address_components, full_address)
                
                # Add geocoding results to response
                if geocoding_result:
                    result["geocoding"] = geocoding_result
                    # Search address geocoded successfully (displayed in main script)
                else:
                    result["geocoding"] = None
                    warning("Search address geocoding failed - no coordinates available")
            
            # Search-based address extraction complete
            return result
            
        except json.JSONDecodeError as e:
            error(f"Failed to parse LLM response as JSON: {e}")
            error(f"Raw response: {raw_response[:200]}...")
            return {
                "address_found": False,
                "extracted_address": "",
                "address_confidence": 0.0,
                "address_source": "",
                "address_type": "",
                "reasoning": f"JSON parsing error: {e}",
                "supporting_sources": [],
                "alternative_addresses": []
            }
        except Exception as e:
            error(f"Search-based address extraction failed: {e}")
            return {
                "address_found": False,
                "extracted_address": "",
                "address_confidence": 0.0,
                "address_source": "",
                "address_type": "",
                "reasoning": f"Search error: {e}",
                "supporting_sources": [],
                "alternative_addresses": []
            }

    def extract_address(self, domain_dir: str, domain_name: str, company_name: str = "", business_type: str = "", 
                       brand_image_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract business address using an optimized approach:
        - If brand image detection found complete address: Skip website analysis, only geocode
        - If brand image detection found location context only: Use for intelligent external search
        - If brand image detection found nothing: Proceed directly to external search
        
        Args:
            domain_dir (str): Directory containing website data
            domain_name (str): Domain name of the website
            company_name (str): Company/business name for search queries
            business_type (str): Type of business for search context
            brand_image_result (Dict[str, Any], optional): Complete brand image detection results
            
        Returns:
            Dict[str, Any]: Complete address extraction results
        """
        
        result = {
            "domain": domain_name,
            "company_name_used": company_name,
            "business_type_used": business_type,
            "location_context": {},
            "website_analysis": {},
            "search_analysis": {},
            "final_address": "",
            "final_confidence": 0.0,
            "final_source": "",
            "address_extraction_method": "",
            "reasoning": "",
            "error": None,
            "geocoding": {}
        }
        
        try:
            # ================================================================
            # OPTIMIZATION: CHECK IF BRAND IMAGE DETECTION FOUND COMPLETE ADDRESS
            # ================================================================
            
            if (brand_image_result and 
                brand_image_result.get("address_found_in_branding", False) and
                brand_image_result.get("address_analysis", {}).get("primary_address")):
                
                # Extract address information from brand analysis
                address_analysis = brand_image_result.get("address_analysis", {})
                extracted_address = address_analysis.get("primary_address", "")
                
                info(f"🚀 OPTIMIZATION: Address found in brand step, skipping website analysis, proceeding to geocoding")
                
                # Only perform geocoding validation
                geocoded_result = self._geocode_address(extracted_address)
                
                # Populate website_analysis with brand results for consistency
                result["website_analysis"] = {
                    "address_found_in_website": True,
                    "extracted_address": extracted_address,
                    "address_components": address_analysis.get("address_components", {}),
                    "clean_address": address_analysis.get("clean_address", extracted_address),
                    "address_confidence": address_analysis.get("confidence", 0.0),
                    "address_source": address_analysis.get("source", "brand_analysis"),
                    "address_type": "primary store",
                    "reasoning": f"Address extracted during brand image detection: {address_analysis.get('reasoning', '')}",
                    "geocoding": geocoded_result
                }
                
                # Use location context from brand analysis
                result["location_context"] = brand_image_result.get("location_context", {})
                
                if geocoded_result.get("success", False):
                    result["final_address"] = geocoded_result.get("formatted_address", extracted_address)
                    result["final_confidence"] = min(address_analysis.get("confidence", 0.0), 0.95)
                    result["final_source"] = f"brand_analysis_{address_analysis.get('source', '')}"
                    result["address_extraction_method"] = "optimized_brand_geocoding_only"
                    result["reasoning"] = f"Address found in brand step and validated via geocoding: {address_analysis.get('reasoning', '')}"
                    result["geocoding"] = geocoded_result
                    
                    success(f"🚀 OPTIMIZED: {result['final_address']} (confidence: {result['final_confidence']:.2f})")
                    return result
                else:
                    # Address found but geocoding failed - still use it with lower confidence
                    result["final_address"] = extracted_address
                    result["final_confidence"] = address_analysis.get("confidence", 0.0) * 0.8  # Slight reduction for unvalidated
                    result["final_source"] = f"brand_analysis_{address_analysis.get('source', '')}"
                    result["address_extraction_method"] = "optimized_brand_unvalidated"
                    result["reasoning"] = f"Address found in brand step but geocoding validation failed: {address_analysis.get('reasoning', '')}"
                    result["geocoding"] = geocoded_result
                    
                    warning(f"🚀 OPTIMIZED (unvalidated): {result['final_address']} (confidence: {result['final_confidence']:.2f})")
                    return result
            
            # ================================================================
            # WEBSITE ANALYSIS: USE EXISTING HTML ANALYSIS FROM BRAND STEP
            # ================================================================
            
            info(f"📍 Using existing HTML analysis from brand step, proceeding to external search")
            
            # Use website analysis results from brand step if available
            if brand_image_result and brand_image_result.get("html_analysis_performed", False):
                # Populate website_analysis with indication that HTML was already analyzed
                result["website_analysis"] = {
                    "address_found_in_website": False,
                    "extracted_address": "",
                    "address_components": {},
                    "clean_address": "",
                    "address_confidence": 0.0,
                    "address_source": "brand_step_analysis",
                    "address_type": "",
                    "reasoning": "HTML content already analyzed in brand detection step - no complete address found"
                }
            else:
                # Fallback: minimal analysis indication
                result["website_analysis"] = {
                    "address_found_in_website": False,
                    "extracted_address": "",
                    "address_confidence": 0.0,
                    "reasoning": "Website analysis performed in brand step"
                }
            
            # Use location context from brand analysis as intelligent hints (if available)
            location_context_hints = {}
            if brand_image_result and brand_image_result.get("location_context"):
                location_context_hints = brand_image_result.get("location_context", {})
                info(f"📍 Using location context from brand analysis as search hints")
            
            # ================================================================
            # EXTERNAL SEARCH: FIND ADDRESS VIA SEARCH ENGINES
            # ================================================================
            
            # Use location context from brand analysis or set empty context
            if location_context_hints:
                location_context = location_context_hints
            else:
                # No location context available - use empty context
                location_context = {
                    "primary_country": "",
                    "primary_state_province": "",
                    "primary_city": "",
                    "additional_locations": [],
                    "location_confidence": 0.0,
                    "reasoning": "No location context available from brand analysis"
                }
            
            result["location_context"] = location_context
            
            # Only proceed to external search if we have company name
            if company_name:
                # Display location context being used
                if location_context.get('city') or location_context.get('state') or location_context.get('country'):
                    location_info = []
                    if location_context.get('city'): location_info.append(location_context['city'])
                    if location_context.get('state'): location_info.append(location_context['state'])
                    if location_context.get('country'): location_info.append(location_context['country'])
                    info(f"Using location context: {', '.join(location_info)}")
                
                try:
                    # Perform external search
                    search_result = self._search_for_address(company_name, business_type, location_context)
                    
                    # Defensive programming: ensure search_result is a dictionary
                    if not isinstance(search_result, dict):
                        error(f"Unexpected search result type: {type(search_result)} - {search_result}")
                        search_result = {
                            "address_found": False,
                            "extracted_address": "",
                            "address_confidence": 0.0,
                            "address_source": "",
                            "address_type": "",
                            "reasoning": f"Invalid search result format: {type(search_result)}",
                            "supporting_sources": [],
                            "alternative_addresses": []
                        }
                    
                    result["search_analysis"] = search_result
                except Exception as e:
                    error(f"External search failed with error: {e}")
                    result["search_analysis"] = {
                        "address_found": False,
                        "reasoning": f"External search error: {str(e)}"
                    }
                    search_result = result["search_analysis"]
                
                if (search_result.get("address_found", False) and 
                    search_result.get("address_confidence", 0.0) > 0.5):
                    
                    extracted_address = search_result.get("extracted_address", "")
                    
                    # Geocode the search result address
                    geocoded_result = self._geocode_address(extracted_address)
                    
                    # Defensive programming: ensure geocoded_result is a dictionary
                    if not isinstance(geocoded_result, dict):
                        error(f"Unexpected geocoded result type: {type(geocoded_result)} - {geocoded_result}")
                        geocoded_result = {"success": False, "error": f"Invalid geocoding result format: {type(geocoded_result)}"}
                    
                    if geocoded_result.get("success", False):
                        result["final_address"] = geocoded_result.get("formatted_address", extracted_address)
                        result["final_confidence"] = min(search_result.get("address_confidence", 0.0), 0.95)
                        result["final_source"] = f"search_{search_result.get('address_source', '')}"
                        result["address_extraction_method"] = "external_search_optimized"
                        result["reasoning"] = f"Address found via external search and validated: {search_result.get('reasoning', '')}"
                        result["geocoding"] = geocoded_result
                        
                        success(f"Address found via search: {result['final_address']} (confidence: {result['final_confidence']:.2f})")
                        return result
                    else:
                        # Search found address but geocoding failed
                        result["final_address"] = extracted_address
                        result["final_confidence"] = search_result.get("address_confidence", 0.0) * 0.7
                        result["final_source"] = f"search_{search_result.get('address_source', '')}"
                        result["address_extraction_method"] = "external_search_unvalidated_optimized"
                        result["reasoning"] = f"Address found via search but geocoding failed: {search_result.get('reasoning', '')}"
                        result["geocoding"] = geocoded_result
                        
                        warning(f"Search address unvalidated: {result['final_address']} (confidence: {result['final_confidence']:.2f})")
                        return result
            else:
                result["search_analysis"] = {
                    "address_found": False,
                    "reasoning": "No company name provided for external search"
                }
            
            # ================================================================
            # NO ADDRESS FOUND
            # ================================================================
            
            result["final_address"] = ""
            result["final_confidence"] = 0.0
            result["final_source"] = ""
            result["address_extraction_method"] = "none_optimized"
            result["reasoning"] = "No complete address found via brand analysis or external search (HTML analysis skipped for optimization)"
            
            warning("No address found in website or external search")
            return result
            
        except Exception as e:
            error(f"Address extraction failed: {e}")
            result["error"] = str(e)
            result["reasoning"] = f"Address extraction failed due to error: {e}"
            return result

    def save_address_result(self, domain_dir: str, address_result: Dict[str, Any]) -> str:
        """
        Save address extraction results to JSON file.
        
        Args:
            domain_dir (str): Directory to save the result
            address_result (Dict[str, Any]): Address extraction results
            
        Returns:
            str: Path to saved file
        """
        try:
            output_path = os.path.join(domain_dir, "address_extraction.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(address_result, f, indent=2, ensure_ascii=False)
            
            # Address extraction results saved silently
            return output_path
            
        except Exception as e:
            error(f"Failed to save address extraction results: {e}")
            return ""
