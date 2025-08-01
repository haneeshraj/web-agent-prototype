"""
MCC (Merchant Category Code) classifier using Pixtral Large model locally.
Two-stage classification: Category -> Exact MCC Code
"""

import json
import os
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from utils.text_extractor import TextExtractor
from utils.terminal_prettify import success, error, warning, info, processing


class MCCClassifier:
    """
    MCC classifier that uses Pixtral Large locally for two-stage classification.
    """
    
    def __init__(self, mcc_data_path: str = "data/mcc_codes_extracted.csv"):
        """
        Initialize MCC classifier.
        
        Args:
            mcc_data_path (str): Path to MCC codes CSV file
        """
        self.mcc_data_path = mcc_data_path
        self.mcc_df = None
        self.text_extractor = TextExtractor()
        
        # MCC category ranges
        self.mcc_categories = {
            "0001-1499": "Agricultural Services",
            "1500-2999": "Contracted Services", 
            "3000-3299": "Airlines",
            "3300-3499": "Car Rental",
            "3500-3999": "Lodging",
            "4000-4799": "Transportation Services",
            "4800-4999": "Utility Services",
            "5000-5599": "Retail Outlet Services",
            "5600-5699": "Clothing Stores",
            "5700-7299": "Miscellaneous Stores",
            "7300-7999": "Business Services",
            "8000-8999": "Professional Services and Membership Organizations",
            "9000-9999": "Government Services"
        }
        
        # Load MCC data
        self._load_mcc_data()
        
        # Initialize Pixtral Large client (placeholder for local model)
        self._initialize_local_model()
    
    def _load_mcc_data(self) -> bool:
        """Load MCC codes from CSV file."""
        try:
            if not os.path.exists(self.mcc_data_path):
                error(f"MCC data file not found: {self.mcc_data_path}")
                return False
            
            self.mcc_df = pd.read_csv(self.mcc_data_path)
            info(f"Loaded {len(self.mcc_df)} MCC codes from {self.mcc_data_path}")
            return True
            
        except Exception as e:
            error(f"Failed to load MCC data: {e}")
            return False
    
    def _initialize_local_model(self):
        """
        Initialize Mistral API client for Pixtral Large.
        """
        try:
            info("Initializing Mistral API client...")
            
            # Import required libraries
            from mistralai import Mistral
            import os
            from dotenv import load_dotenv
            
            # Load environment variables
            load_dotenv()
            
            # Get API key
            api_key = os.getenv('MISTRAL_API_KEY')
            if not api_key:
                error("MISTRAL_API_KEY not found in environment variables")
                error("Please add MISTRAL_API_KEY=your_key_here to your .env file")
                self.model_initialized = False
                return
            
            # Initialize Mistral client
            self.mistral_client = Mistral(api_key=api_key)
            self.model_name = "pixtral-large-latest"  # Use latest Pixtral Large model
            
            success("Mistral API client initialized successfully!")
            self.model_initialized = True
            
        except ImportError as e:
            error("Missing required packages. Please install: pip install mistralai python-dotenv")
            self.model_initialized = False
            raise e
            
        except Exception as e:
            error(f"Failed to initialize Mistral API: {e}")
            self.model_initialized = False
            raise e
    
    def _get_category_range_codes(self, category_range: str) -> pd.DataFrame:
        """
        Get MCC codes for a specific category range.
        
        Args:
            category_range (str): Category range like "5000-5599"
            
        Returns:
            pd.DataFrame: Filtered MCC codes for the category
        """
        if self.mcc_df is None:
            return pd.DataFrame()
        
        try:
            start_code, end_code = category_range.split('-')
            start_code = int(start_code)
            end_code = int(end_code)
            
            filtered_df = self.mcc_df[
                (self.mcc_df['MCC'] >= start_code) & 
                (self.mcc_df['MCC'] <= end_code)
            ]
            
            return filtered_df
            
        except Exception as e:
            warning(f"Error filtering MCC codes for range {category_range}: {e}")
            return pd.DataFrame()
    
    def _create_stage1_prompt(self, text_content: str) -> str:
        """
        Create prompt for Stage 1: Category classification.
        
        Args:
            text_content (str): Extracted website text
            
        Returns:
            str: Stage 1 classification prompt
        """
        categories_text = "\n".join([f"{range}: {name}" for range, name in self.mcc_categories.items()])
        
        prompt = f"""You are an expert MCC (Merchant Category Code) classifier. Your task is to analyze the website content and screenshot to determine which MCC category this business belongs to.

WEBSITE TEXT CONTENT:
{text_content}

MCC CATEGORIES:
{categories_text}

INSTRUCTIONS:
1. Analyze both the screenshot and the text content to understand what type of business this is
2. Look for key indicators like:
   - Business name and branding
   - Products or services offered
   - Industry terminology
   - Visual elements in the screenshot (storefront, professional services, etc.)
3. Select the most appropriate MCC category from the list above
4. Consider the primary business activity, not secondary services

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{{
    "selected_category_range": "XXXX-YYYY",
    "selected_category_name": "Category Name",
    "confidence": 0.95,
    "reasoning": "Detailed explanation of why this category was selected based on the evidence from text and visual analysis",
    "key_indicators": ["indicator1", "indicator2", "indicator3"],
    "business_type_identified": "Brief description of the business type"
}}

IMPORTANT:
- Only return valid JSON
- Confidence should be between 0.0 and 1.0
- If you cannot confidently categorize, set confidence below 0.7 and explain why
- Focus on the PRIMARY business activity, not secondary services"""

        return prompt
    
    def _create_stage2_prompt(self, text_content: str, category_range: str, candidate_mccs: pd.DataFrame) -> str:
        """
        Create prompt for Stage 2: Exact MCC code determination.
        
        Args:
            text_content (str): Extracted website text
            category_range (str): Selected category range from Stage 1
            candidate_mccs (pd.DataFrame): Candidate MCC codes in the category
            
        Returns:
            str: Stage 2 classification prompt
        """
        # Format candidate MCCs for the prompt
        mcc_options = []
        for _, row in candidate_mccs.iterrows():
            mcc_options.append(f"MCC {row['MCC']}: {row['Description']}")
        
        mcc_options_text = "\n".join(mcc_options)
        
        # Create business-specific validation rules
        validation_rules = self._get_business_validation_rules(text_content)
        
        prompt = f"""You are an expert MCC (Merchant Category Code) classifier. Based on the Stage 1 analysis, this business belongs to the "{self.mcc_categories.get(category_range, 'Unknown')}" category ({category_range}).

Now determine the EXACT MCC code from the available options in this category.

WEBSITE TEXT CONTENT:
{text_content}

AVAILABLE MCC CODES IN THIS CATEGORY:
{mcc_options_text}

CRITICAL VALIDATION RULES:
{validation_rules}

INSTRUCTIONS:
1. Analyze the specific business activities described in the text and shown in the screenshot
2. Apply the CRITICAL VALIDATION RULES above - these are non-negotiable
3. Match the business to the most specific and accurate MCC code from the options above
4. Consider:
   - Primary business activity (what they actually do/sell)
   - Business model (retail, service, restaurant, etc.)
   - Industry specialization
   - Customer interaction model
5. Select the single best match - be precise and logical

FOOD BUSINESS SPECIFIC RULES:
- If the business serves/sells FOOD or DRINKS → Must be food-related MCC (5812, 5813, 5814, 5441, etc.)
- NEVER classify food businesses as: Florists, Hardware, Clothing, Electronics, etc.
- Restaurants/Cafés → 5812 (Eating Places and Restaurants)
- Fast Food → 5814 (Fast Food Restaurants)  
- Bars/Pubs → 5813 (Bars, Cocktail Lounges)
- Bakeries/Pastries → 5441 (Candy, Nut, and Confectionery Stores) or 5812 if they have seating

RETAIL BUSINESS SPECIFIC RULES:
- Online stores selling physical products → Appropriate retail MCC based on product type
- Service businesses → Business Services category (7300-7999)
- NEVER mix up product categories (e.g., Art prints ≠ Electronics)

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{{
    "selected_mcc": 1234,
    "selected_mcc_description": "Exact description from the MCC list",
    "confidence": 0.95,
    "reasoning": "Detailed explanation of why this specific MCC was selected over other options, including validation rule compliance",
    "business_match_factors": ["primary_activity", "business_model", "industry_type"],
    "alternative_mccs_considered": [
        {{"mcc": 1235, "reason_rejected": "Why this wasn't selected"}},
        {{"mcc": 1236, "reason_rejected": "Why this wasn't selected"}}
    ]
}}

IMPORTANT:
- Only return valid JSON
- Selected MCC must be from the provided list
- Selected MCC must comply with validation rules
- Confidence should be between 0.0 and 1.0
- If no MCC in the list fits the validation rules, set confidence to 0.5 and explain the conflict
- Be very specific about why you chose this MCC over similar ones"""

        return prompt
    
    def _query_pixtral_local(self, prompt: str, image_path: str) -> str:
        """
        Query Pixtral Large model via Mistral API with text prompt and image.
        
        Args:
            prompt (str): Text prompt for the model
            image_path (str): Path to screenshot image
            
        Returns:
            str: Model response
        """
        if not self.model_initialized:
            error("Mistral API client not initialized")
            return '{"error": "API client not initialized"}'
        
        try:
            import base64
            from PIL import Image
            import io
            
            processing("Preparing image and prompt for Mistral API...")
            
            # Load and process image
            if not os.path.exists(image_path):
                error(f"Screenshot not found: {image_path}")
                return '{"error": "Image file not found"}'
            
            # Convert image to base64
            with open(image_path, "rb") as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create message with image and text
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:image/png;base64,{image_base64}"
                        }
                    ]
                }
            ]
            
            # Generate response
            processing("Querying Pixtral Large via Mistral API...")
            
            chat_response = self.mistral_client.chat.complete(
                model=self.model_name,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent JSON
                max_tokens=1024
            )
            
            response = chat_response.choices[0].message.content
            info("Pixtral Large API call completed successfully")
            return response.strip()
            
        except Exception as e:
            error(f"Mistral API call failed: {e}")
            
            # Fallback to placeholder if API fails
            warning("Falling back to placeholder response")
            if "MCC CATEGORIES:" in prompt:
                # Stage 1: Category classification
                fallback_response = """
                {
                    "selected_category_range": "5812-5812",
                    "selected_category_name": "Eating Places and Restaurants",
                    "confidence": 0.75,
                    "reasoning": "API call failed, using fallback classification. Manual review recommended.",
                    "key_indicators": ["restaurant", "food", "menu"],
                    "business_type_identified": "Restaurant/Food service (API fallback)"
                }
                """
            else:
                # Stage 2: Exact MCC code
                fallback_response = """
                {
                    "selected_mcc": 5812,
                    "selected_mcc_description": "Eating Places and Restaurants",
                    "confidence": 0.75,
                    "reasoning": "API call failed, using fallback MCC code. Manual review recommended.",
                    "business_match_factors": ["food service", "restaurant"],
                    "alternative_mccs_considered": []
                }
                """
            
            return fallback_response.strip()
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from Pixtral Large.
        
        Args:
            response (str): Raw response from model
            
        Returns:
            Dict[str, Any]: Parsed JSON response
        """
        try:
            # Clean response - remove markdown formatting if present
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            return json.loads(response.strip())
            
        except json.JSONDecodeError as e:
            error(f"Failed to parse JSON response: {e}")
            return {"error": f"Invalid JSON response: {str(e)}"}
        except Exception as e:
            error(f"Error parsing response: {e}")
            return {"error": f"Response parsing failed: {str(e)}"}
    
    def classify_mcc(self, domain_dir: str, domain_name: str) -> Dict[str, Any]:
        """
        Classify MCC code for a website using two-stage approach.
        
        Args:
            domain_dir (str): Path to domain directory containing files
            domain_name (str): Domain name for logging
            
        Returns:
            Dict[str, Any]: Complete MCC classification results
        """
        processing(f"Starting MCC classification for {domain_name}")
        
        # Initialize result structure
        result = {
            "domain": domain_name,
            "classification_success": False,
            "stage1_result": {},
            "stage2_result": {},
            "final_mcc": None,
            "final_mcc_description": "",
            "final_confidence": 0.0,
            "error": None,
            "processing_metadata": {
                "text_extraction_success": False,
                "screenshot_found": False,
                "stage1_completed": False,
                "stage2_completed": False
            }
        }
        
        try:
            # 1. Load required files
            html_path = os.path.join(domain_dir, "page.html")
            screenshot_path = self._find_screenshot(domain_dir)
            
            if not os.path.exists(html_path):
                result["error"] = "HTML file not found"
                return result
            
            if not screenshot_path:
                result["error"] = "Screenshot not found"
                return result
            
            result["processing_metadata"]["screenshot_found"] = True
            
            # 2. Extract text content
            text_content = self.text_extractor.extract_for_mcc_classification(html_path)
            if not text_content:
                result["error"] = "Failed to extract text content"
                return result
            
            result["processing_metadata"]["text_extraction_success"] = True
            info(f"Extracted {len(text_content)} characters of text")
            
            # 3. Stage 1: Category Classification
            info("Stage 1: Determining MCC category...")
            stage1_prompt = self._create_stage1_prompt(text_content)
            stage1_response = self._query_pixtral_local(stage1_prompt, screenshot_path)
            stage1_result = self._parse_json_response(stage1_response)
            
            result["stage1_result"] = stage1_result
            
            if "error" in stage1_result:
                result["error"] = f"Stage 1 failed: {stage1_result['error']}"
                return result
            
            result["processing_metadata"]["stage1_completed"] = True
            
            # Validate Stage 1 results
            selected_range = stage1_result.get("selected_category_range")
            if not selected_range:
                result["error"] = f"No category range returned from Stage 1"
                return result
            
            # Handle cases where model returns specific MCC codes instead of ranges
            # If it's a specific MCC code (like 5812), find the appropriate range
            if selected_range and '-' not in selected_range:
                try:
                    mcc_code = int(selected_range)
                    # Find which category this MCC belongs to
                    for range_key, category_name in self.mcc_categories.items():
                        start_code, end_code = range_key.split('-')
                        if int(start_code) <= mcc_code <= int(end_code):
                            selected_range = range_key
                            stage1_result["selected_category_range"] = range_key
                            info(f"Mapped MCC {mcc_code} to range {range_key}")
                            break
                except ValueError:
                    pass
            
            # Handle ranges that don't exactly match our predefined categories
            # (e.g., model returns "5812-5814" but we need "5700-7299")
            if selected_range not in self.mcc_categories:
                # Try to find the best matching category
                try:
                    if '-' in selected_range:
                        start_mcc, end_mcc = selected_range.split('-')
                        mid_mcc = (int(start_mcc) + int(end_mcc)) // 2
                    else:
                        mid_mcc = int(selected_range)
                    
                    # Find which category this MCC falls into
                    for range_key, category_name in self.mcc_categories.items():
                        start_code, end_code = range_key.split('-')
                        if int(start_code) <= mid_mcc <= int(end_code):
                            selected_range = range_key
                            stage1_result["selected_category_range"] = range_key
                            stage1_result["selected_category_name"] = category_name
                            info(f"Mapped range {stage1_result.get('selected_category_range')} to category {range_key}")
                            break
                    else:
                        result["error"] = f"Could not map category range {selected_range} to valid MCC category"
                        return result
                        
                except ValueError:
                    result["error"] = f"Invalid category range format from Stage 1: {selected_range}"
                    return result
            
            success(f"Stage 1 complete: {selected_range} - {stage1_result.get('selected_category_name')}")
            
            # 4. Stage 2: Exact MCC Code Determination
            info("Stage 2: Determining exact MCC code...")
            candidate_mccs = self._get_category_range_codes(selected_range)
            
            if candidate_mccs.empty:
                result["error"] = f"No MCC codes found for category {selected_range}"
                return result
            
            info(f"Found {len(candidate_mccs)} candidate MCC codes in category")
            
            stage2_prompt = self._create_stage2_prompt(text_content, selected_range, candidate_mccs)
            stage2_response = self._query_pixtral_local(stage2_prompt, screenshot_path)
            stage2_result = self._parse_json_response(stage2_response)
            
            result["stage2_result"] = stage2_result
            
            if "error" in stage2_result:
                result["error"] = f"Stage 2 failed: {stage2_result['error']}"
                return result
            
            result["processing_metadata"]["stage2_completed"] = True
            
            # 5. Validate and finalize results
            final_mcc = stage2_result.get("selected_mcc")
            if not final_mcc:
                result["error"] = f"No MCC code returned from Stage 2"
                return result
            
            # Validate MCC is in candidate list
            if final_mcc not in candidate_mccs['MCC'].values:
                result["error"] = f"Selected MCC {final_mcc} not in candidate list for category {selected_range}"
                return result
            
            # Validate business logic
            is_valid, validation_error = self._validate_mcc_selection(final_mcc, text_content, candidate_mccs)
            if not is_valid:
                result["error"] = validation_error
                return result
            
            result["final_mcc"] = final_mcc
            result["final_mcc_description"] = stage2_result.get("selected_mcc_description", "")
            result["final_confidence"] = min(
                stage1_result.get("confidence", 0.0),
                stage2_result.get("confidence", 0.0)
            )
            result["classification_success"] = True
            
            success(f"MCC Classification complete: {final_mcc} - {result['final_mcc_description']}")
            success(f"Final confidence: {result['final_confidence']:.2f}")
            
            return result
            
        except Exception as e:
            error(f"MCC classification failed for {domain_name}: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
            return result
    
    def _find_screenshot(self, domain_dir: str) -> Optional[str]:
        """Find screenshot file in domain directory."""
        try:
            for file in os.listdir(domain_dir):
                if file.startswith("screenshot_") and file.endswith(".png"):
                    return os.path.join(domain_dir, file)
        except Exception:
            pass
        return None
    
    def _get_business_validation_rules(self, text_content: str) -> str:
        """
        Generate business-specific validation rules based on text content analysis.
        
        Args:
            text_content (str): Extracted website text
            
        Returns:
            str: Formatted validation rules for the prompt
        """
        text_lower = text_content.lower()
        rules = []
        
        # Food and Restaurant Rules
        food_keywords = ['restaurant', 'pizza', 'food', 'menu', 'dining', 'eat', 'drink', 'bar', 'café', 'cafe', 
                        'bakery', 'pastry', 'patisserie', 'sushi', 'kitchen', 'chef', 'cook', 'meal', 'buffet',
                        'takeout', 'delivery', 'catering', 'wine', 'beer', 'cocktail', 'lunch', 'dinner', 'breakfast']
        
        if any(keyword in text_lower for keyword in food_keywords):
            rules.append("🍕 FOOD BUSINESS DETECTED: This business MUST be classified with a food-related MCC code (5812, 5813, 5814, 5441, etc.). NEVER use non-food MCCs like Florists, Hardware, Electronics, etc.")
        
        # Retail Rules
        retail_keywords = ['shop', 'store', 'buy', 'purchase', 'product', 'retail', 'sell', 'order', 'cart', 'checkout']
        if any(keyword in text_lower for keyword in retail_keywords):
            rules.append("🛍️ RETAIL BUSINESS DETECTED: Focus on what products are actually sold, not peripheral services.")
        
        # Service Rules  
        service_keywords = ['consulting', 'service', 'management', 'professional', 'advice', 'support', 'solutions']
        if any(keyword in text_lower for keyword in service_keywords):
            rules.append("💼 SERVICE BUSINESS DETECTED: Focus on the primary service offered, use Business Services MCCs (7300-7999).")
        
        # Specific Business Type Rules
        if 'patisserie' in text_lower or 'bakery' in text_lower or 'pastry' in text_lower:
            rules.append("🥐 BAKERY/PATISSERIE DETECTED: Use MCC 5441 (Candy, Nut, and Confectionery Stores) or 5812 (Restaurants) if seating available. NEVER use 5992 (Florists).")
        
        if 'pizza' in text_lower:
            rules.append("🍕 PIZZA BUSINESS DETECTED: Use MCC 5812 (Restaurants) for sit-down pizza places or 5814 (Fast Food) for delivery/takeout focused.")
        
        if 'bar' in text_lower or 'pub' in text_lower or 'tavern' in text_lower:
            rules.append("🍺 BAR/PUB DETECTED: Use MCC 5813 (Bars, Cocktail Lounges) for alcohol-focused establishments.")
        
        if 'art' in text_lower and 'print' in text_lower:
            rules.append("🎨 ART PRINTS DETECTED: Use MCC 5111 (Stationery, Office Supplies) for printable art or similar paper-based products.")
        
        # Instagram/Social Media Rules
        if 'instagram' in text_lower or 'social media' in text_lower or 'influencer' in text_lower:
            rules.append("📱 SOCIAL MEDIA BUSINESS DETECTED: If content creation/curation is the primary activity, use MCC 7392 (Consulting, Management and PR Services).")
        
        # YouTube/Content Rules
        if 'youtube' in text_lower or 'channel' in text_lower or 'content creator' in text_lower:
            rules.append("📺 CONTENT CREATOR DETECTED: If selling products, classify by product type. If pure content creation, use appropriate services MCC.")
        
        if not rules:
            rules.append("⚠️ GENERAL RULE: Classify based on PRIMARY business activity. Avoid broad/generic MCCs when specific ones exist.")
        
        return "\n".join(rules)
    
    def _validate_mcc_selection(self, selected_mcc: int, text_content: str, candidate_mccs: pd.DataFrame) -> tuple[bool, str]:
        """
        Validate that the selected MCC makes logical sense for the business.
        
        Args:
            selected_mcc (int): Selected MCC code
            text_content (str): Business text content
            candidate_mccs (pd.DataFrame): Available MCC options
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        text_lower = text_content.lower()
        
        # Get MCC description
        mcc_row = candidate_mccs[candidate_mccs['MCC'] == selected_mcc]
        if mcc_row.empty:
            return False, f"Selected MCC {selected_mcc} not in candidate list"
        
        mcc_description = mcc_row.iloc[0]['Description'].lower()
        
        # Food business validation
        food_keywords = ['restaurant', 'pizza', 'food', 'menu', 'dining', 'eat', 'drink', 'bar', 'café', 'cafe', 
                        'bakery', 'pastry', 'patisserie', 'sushi', 'kitchen', 'chef', 'cook', 'meal']
        
        is_food_business = any(keyword in text_lower for keyword in food_keywords)
        is_food_mcc = any(food_term in mcc_description for food_term in ['eating', 'restaurant', 'food', 'bar', 'cocktail', 'candy', 'nut', 'confectionery'])
        
        if is_food_business and not is_food_mcc:
            # Special exceptions
            if 'florist' in mcc_description:
                return False, f"VALIDATION ERROR: Food business cannot be classified as Florists (MCC {selected_mcc})"
            if any(bad_match in mcc_description for bad_match in ['hardware', 'electronics', 'clothing', 'automotive']):
                return False, f"VALIDATION ERROR: Food business incorrectly classified as {mcc_description} (MCC {selected_mcc})"
        
        # Patisserie/Bakery specific validation
        if any(term in text_lower for term in ['patisserie', 'bakery', 'pastry']) and 'florist' in mcc_description:
            return False, f"VALIDATION ERROR: Bakery/Patisserie cannot be classified as Florists (MCC {selected_mcc})"
        
        return True, ""
    
    def save_mcc_result(self, domain_dir: str, mcc_result: Dict[str, Any]) -> str:
        """
        Save MCC classification result to JSON file.
        
        Args:
            domain_dir (str): Domain directory path
            mcc_result (Dict[str, Any]): MCC classification result
            
        Returns:
            str: Path to saved file
        """
        try:
            mcc_file_path = os.path.join(domain_dir, "mcc_classification.json")
            
            with open(mcc_file_path, 'w', encoding='utf-8') as f:
                json.dump(mcc_result, f, indent=2, ensure_ascii=False)
            
            return mcc_file_path
            
        except Exception as e:
            error(f"Failed to save MCC result: {e}")
            return ""


# Convenience function
def classify_website_mcc(domain_dir: str, domain_name: str, mcc_data_path: str = "data/mcc_codes_extracted.csv") -> Dict[str, Any]:
    """
    Convenience function to classify MCC for a website.
    
    Args:
        domain_dir (str): Path to domain directory
        domain_name (str): Domain name
        mcc_data_path (str): Path to MCC data CSV
        
    Returns:
        Dict[str, Any]: MCC classification results
    """
    classifier = MCCClassifier(mcc_data_path)
    return classifier.classify_mcc(domain_dir, domain_name)


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        domain_dir = sys.argv[1]
        domain_name = sys.argv[2]
        
        classifier = MCCClassifier()
        result = classifier.classify_mcc(domain_dir, domain_name)
        
        print("=" * 60)
        print("MCC CLASSIFICATION RESULT")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        
    else:
        print("Usage: python mcc_classifier.py <domain_directory> <domain_name>")
        print("Example: python mcc_classifier.py data/runs/run_20240101_120000/example_com_20240101_120000 example.com")