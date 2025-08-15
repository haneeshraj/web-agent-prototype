import json
import os
import time
from typing import Dict, Any, Optional
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
    "address_confidence": 0.95,
    "address_source": "Where the address was found (e.g., 'contact page', 'footer', 'about section')",
    "address_type": "Type of address (e.g., 'headquarters', 'main office', 'primary store')",
    "reasoning": "Detailed explanation of why this address was selected or why no address was found"
}

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
    "address_confidence": 0.95,
    "address_source": "Which search result source provided the address",
    "address_type": "Type of address (e.g., 'corporate headquarters', 'founding location', 'main office')",
    "reasoning": "Detailed explanation of why this address was selected as the PRIMARY headquarters, especially if multiple locations were considered",
    "supporting_sources": ["list of sources that confirm this address"],
    "alternative_addresses": [
        {
            "address": "Other significant addresses found",
            "type": "Type (e.g., 'regional office', 'franchise location')",
            "reason_not_selected": "Why this wasn't chosen as primary"
        }
    ]
}

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
            info(f"Querying {self.model_config['model']} for {context}...")
            
            response = self.llm_client.query(
                model=self.model_config['model'],
                system_prompt=system_prompt,
                user_prompt=prompt,
                max_tokens=self.model_config['max_tokens'],
                temperature=self.model_config.get('temperature', 0.3)
            )
            
            info(f"{self.model_config['model']} query completed successfully")
            return response['content'].strip()
            
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
                "address_confidence": 0.0,
                "address_source": "",
                "address_type": "",
                "reasoning": "LLM query failed - fallback response used",
                "supporting_sources": [],
                "alternative_addresses": []
            })

    def _extract_location_context(self, html_content: str) -> Dict[str, Any]:
        """
        Extract location context from website content to improve search queries.
        
        Args:
            html_content (str): Website HTML content
            
        Returns:
            Dict[str, Any]: Location context information
        """
        try:
            # Truncate HTML if too long to avoid token limits
            max_html_length = 15000
            if len(html_content) > max_html_length:
                html_content = html_content[:max_html_length] + "\n... [HTML truncated for length]"
            
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
            
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = raw_response
            
            # Parse JSON response
            result = json.loads(json_str)
            info(f"Location context extraction completed")
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
            # Truncate HTML if too long to avoid token limits
            max_html_length = 20000
            if len(html_content) > max_html_length:
                html_content = html_content[:max_html_length] + "\n... [HTML truncated for length]"
            
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
            
            # Debug: Log the raw response
            info(f"LLM response length: {len(raw_response)} characters")
            
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
            
            # Try to extract JSON from the response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = raw_response
            
            # Parse JSON response
            result = json.loads(json_str)
            info(f"Website address analysis completed")
            return result
            
        except json.JSONDecodeError as e:
            error(f"Failed to parse LLM response as JSON: {e}")
            error(f"Raw response: {raw_response[:200]}...")
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

    def _search_for_address(self, merchant_name: str, business_type: str = "", location_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Search for business address using SerpAPI with location context.
        
        Args:
            merchant_name (str): Name of the business/merchant
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
                f"{merchant_name} headquarters address",
                f"{merchant_name} corporate office address",
                f"{merchant_name} main office location",
                f"{merchant_name} head office address"
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
                        f"{merchant_name} headquarters address {location_str}",
                        f"{merchant_name} main office {location_str}",
                        f"{merchant_name} corporate office {location_str}",
                        f"{merchant_name} founded in {location_str} headquarters"
                    ]
                    base_queries = location_queries + base_queries
                    info(f"Using location context: {location_str}")
            
            # Add business type specific queries if available
            if business_type:
                base_queries.extend([
                    f"{merchant_name} {business_type} headquarters address",
                    f"{merchant_name} {business_type} main location"
                ])
            
            all_business_info = []
            
            # Perform search with the first (most location-specific) query
            primary_query = base_queries[0]
            search_results = self.serpapi_client.search(primary_query, num_results=8)  # Increased for better coverage
            
            if search_results:
                business_info = self.serpapi_client.extract_business_info(search_results)
                all_business_info.extend(business_info)
                info(f"Found {len(business_info)} search results for address extraction")
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

            user_prompt = f"""Please analyze these search results to extract the PRIMARY headquarters address for: {merchant_name}

MERCHANT/BUSINESS NAME: {merchant_name}
BUSINESS TYPE: {business_type if business_type else "Unknown"}
{location_info}

SEARCH RESULTS:
```json
{json.dumps(all_business_info, indent=2)}
```

TASK:
1. Look through all the search results for address information
2. Find the PRIMARY headquarters address (original/founding location if multiple exist)
3. If location context is provided above, prioritize addresses in that primary location
4. For multi-location businesses, prefer the ORIGINAL headquarters over expansion offices
5. Return your analysis in the specified JSON format

Focus on finding the PRIMARY business headquarters for {merchant_name}, especially considering any location context provided above."""

            # Use retry logic for LLM query
            raw_response = self._query_llm_with_retry(
                user_prompt, 
                self.search_address_extraction_prompt, 
                "search_analysis"
            )
            
            # Debug: Log the raw response
            info(f"LLM response length: {len(raw_response)} characters")
            
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
            
            # Try to extract JSON from the response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = raw_response
            
            # Parse JSON response
            result = json.loads(json_str)
            info(f"Search-based address extraction completed")
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

    def extract_address(self, domain_dir: str, domain_name: str, merchant_name: str = "", business_type: str = "") -> Dict[str, Any]:
        """
        Extract business address using a two-stage approach: website analysis + search fallback.
        
        Args:
            domain_dir (str): Directory containing website data
            domain_name (str): Domain name of the website
            merchant_name (str): Merchant/business name for search queries
            business_type (str): Type of business for search context
            
        Returns:
            Dict[str, Any]: Complete address extraction results
        """
        info(f"Starting address extraction for {domain_name}")
        
        result = {
            "domain": domain_name,
            "merchant_name_used": merchant_name,
            "business_type_used": business_type,
            "location_context": {},
            "website_analysis": {},
            "search_analysis": {},
            "final_address": "",
            "final_confidence": 0.0,
            "final_source": "",
            "address_extraction_method": "",
            "reasoning": "",
            "error": None
        }
        
        try:
            # Stage 0: Extract location context from website
            html_path = os.path.join(domain_dir, "page.html")
            html_content = self._load_html_content(html_path)
            
            if not html_content:
                result["error"] = "HTML file not found or could not be loaded"
                return result
            
            info("Stage 0: Extracting location context...")
            location_context = self._extract_location_context(html_content)
            result["location_context"] = location_context
            
            if location_context.get("location_confidence", 0.0) > 0.3:
                primary_location = []
                if location_context.get("primary_city"):
                    primary_location.append(location_context["primary_city"])
                if location_context.get("primary_state_province"):
                    primary_location.append(location_context["primary_state_province"])
                if location_context.get("primary_country"):
                    primary_location.append(location_context["primary_country"])
                if primary_location:
                    info(f"Identified primary location context: {', '.join(primary_location)}")
            
            # Stage 1: Analyze website HTML for address
            info("Stage 1: Analyzing website content for address...")
            website_result = self._analyze_website_for_address(html_content)
            result["website_analysis"] = website_result
            
            # If address found in website with high confidence, use it
            if (website_result.get("address_found_in_website", False) and 
                website_result.get("address_confidence", 0.0) >= 0.7):
                
                result["final_address"] = website_result.get("extracted_address", "")
                result["final_confidence"] = website_result.get("address_confidence", 0.0)
                result["final_source"] = f"website_{website_result.get('address_source', '')}"
                result["address_extraction_method"] = "website_direct"
                result["reasoning"] = f"Address found directly on website with high confidence: {website_result.get('reasoning', '')}"
                
                success(f"Address found on website: {result['final_address']}")
                return result
            
            # Stage 2: Search for address using SerpAPI (if address not found on website or low confidence)
            if merchant_name:
                info("Stage 2: Searching for address using SerpAPI...")
                search_result = self._search_for_address(merchant_name, business_type, location_context)
                result["search_analysis"] = search_result
                
                if (search_result.get("address_found", False) and 
                    search_result.get("address_confidence", 0.0) > 0.0):
                    
                    result["final_address"] = search_result.get("extracted_address", "")
                    result["final_confidence"] = search_result.get("address_confidence", 0.0)
                    result["final_source"] = f"search_{search_result.get('address_source', '')}"
                    result["address_extraction_method"] = "search_based"
                    result["reasoning"] = f"Address found via search after website analysis: {search_result.get('reasoning', '')}"
                    
                    success(f"Address found via search: {result['final_address']}")
                    return result
            else:
                info("Stage 2 skipped: No merchant name provided for search")
                result["search_analysis"] = {
                    "address_found": False,
                    "reasoning": "No merchant name provided for search"
                }
            
            # No address found
            if website_result.get("address_found_in_website", False):
                # Found on website but low confidence
                result["final_address"] = website_result.get("extracted_address", "")
                result["final_confidence"] = website_result.get("address_confidence", 0.0)
                result["final_source"] = f"website_{website_result.get('address_source', '')}"
                result["address_extraction_method"] = "website_low_confidence"
                result["reasoning"] = f"Address found on website but with low confidence: {website_result.get('reasoning', '')}"
                warning(f"Address found but with low confidence: {result['final_address']}")
            else:
                # No address found anywhere
                result["final_address"] = ""
                result["final_confidence"] = 0.0
                result["final_source"] = ""
                result["address_extraction_method"] = "none"
                result["reasoning"] = "No address found on website or through search"
                warning("No business address could be found")
            
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
            
            success(f"Address extraction results saved: {os.path.basename(output_path)}")
            return output_path
            
        except Exception as e:
            error(f"Failed to save address extraction results: {e}")
            return ""
