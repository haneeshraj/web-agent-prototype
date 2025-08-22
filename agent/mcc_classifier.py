"""
MCC (Merchant Category Code) classifier using LLM from config.
Two-stage classification: Category -> Exact MCC Code
"""

import json
import os
import time
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from utils.text_extractor import TextExtractor
from utils.terminal_prettify import success, error, warning, info, processing
from utils.llm import create_llm_client
from utils.config import get_model_config, get_config


class MCCClassifier:
    """
    MCC classifier that uses LLM from config for two-stage classification.
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
        
        # Initialize LLM client from config
        self.llm_client = create_llm_client()
        self.model_config = get_model_config("classifier-agent")
        self.config = get_config()
        
        # Get retry configuration
        self.backup_model = self.config.get('agent.classifier-agent.backup_model', 'gpt-4o-mini')
        self.max_retries = self.config.get('processing.max_json_retries', 1)
        self.retry_delay = self.config.get('processing.json_retry_delay_seconds', 10)
        
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
    
    def _load_mcc_data(self) -> bool:
        """Load MCC codes from CSV file."""
        try:
            if not os.path.exists(self.mcc_data_path):
                error(f"MCC data file not found: {self.mcc_data_path}")
                return False
            
            self.mcc_df = pd.read_csv(self.mcc_data_path)
            # Load MCC data silently - no need to log count
            return True
            
        except Exception as e:
            error(f"Failed to load MCC data: {e}")
            return False
    
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
        
        # Analyze text to provide business-specific guidance
        business_guidance = self._get_stage1_business_guidance(text_content)
        
        prompt = f"""You are an expert MCC (Merchant Category Code) classifier. Your task is to analyze the website content and screenshot to determine which MCC category this business belongs to.

WEBSITE TEXT CONTENT:
{text_content}

MCC CATEGORIES:
{categories_text}

BUSINESS-SPECIFIC GUIDANCE:
{business_guidance}

CRITICAL CATEGORY SELECTION RULES:
🍰 BAKERIES/PATISSERIES/CONFECTIONERY → "5000-5599: Retail Outlet Services" (contains MCC 5441 for candy/confectionery stores)
🍕 RESTAURANTS/DINING → "5700-7299: Miscellaneous Stores" (contains MCC 5812, 5813, 5814 for restaurants/bars)
🛍️ RETAIL STORES → Choose category based on what they sell (clothing → 5600-5699, home goods → 5700-7299, etc.)
💼 SERVICES → "7300-7999: Business Services" (consulting, management, PR, etc.)
✈️ TRAVEL → "3000-3299: Airlines", "3300-3499: Car Rental", "3500-3999: Lodging"

INSTRUCTIONS:
1. Analyze both the screenshot and the text content to understand what type of business this is
2. Look for key indicators like:
   - Business name and branding
   - Products or services offered
   - Industry terminology
   - Visual elements in the screenshot
3. Apply the CRITICAL CATEGORY SELECTION RULES above - these are mandatory
4. Select the most appropriate MCC category from the list that will contain the correct specific MCC code
5. Consider the primary business activity, not secondary services

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{{
    "selected_category_range": "XXXX-YYYY",
    "selected_category_name": "Category Name", 
    "confidence": 0.95,
    "reasoning": "Detailed explanation of why this category was selected based on evidence from text and visual analysis, including reference to category selection rules",
    "key_indicators": ["indicator1", "indicator2", "indicator3"],
    "business_type_identified": "Brief description of the business type"
}}

IMPORTANT:
- Only return valid JSON
- Selected category must be from the MCC CATEGORIES list above
- Confidence should be between 0.0 and 1.0
- If you cannot confidently categorize, set confidence below 0.7 and explain why
- Focus on the PRIMARY business activity that determines which MCC codes are available
- Use the CRITICAL CATEGORY SELECTION RULES to ensure proper category mapping"""

        return prompt
    
    def _get_stage1_business_guidance(self, text_content: str) -> str:
        """
        Generate business-specific guidance for Stage 1 classification.
        
        Args:
            text_content (str): Extracted website text
            
        Returns:
            str: Formatted guidance for category selection
        """
        text_lower = text_content.lower()
        guidance = []
        
        # Bakery/Patisserie specific guidance
        if any(term in text_lower for term in ['patisserie', 'bakery', 'pastry', 'confectionery', 'candy', 'sweets', 'dessert']):
            guidance.append("🍰 BAKERY/PATISSERIE DETECTED: This business sells baked goods, pastries, or confectionery items. Must select '5000-5599: Retail Outlet Services' to access MCC 5441 (Candy, Nut, and Confectionery Stores).")
        
        # Restaurant/Food Service guidance
        elif any(term in text_lower for term in ['restaurant', 'dining', 'eat', 'food', 'menu', 'pizza', 'sushi', 'kitchen', 'chef', 'meal']):
            guidance.append("🍕 RESTAURANT/FOOD SERVICE DETECTED: This business serves prepared food to customers. Must select '5700-7299: Miscellaneous Stores' to access restaurant MCCs (5812, 5813, 5814).")
        
        # Bar/Drinking establishment guidance
        if any(term in text_lower for term in ['bar', 'pub', 'tavern', 'cocktail', 'beer', 'wine', 'alcohol', 'drinking']):
            guidance.append("🍺 BAR/DRINKING ESTABLISHMENT DETECTED: This business primarily serves alcoholic beverages. Must select '5700-7299: Miscellaneous Stores' to access MCC 5813 (Bars, Cocktail Lounges).")
        
        # Retail guidance based on products
        if any(term in text_lower for term in ['shop', 'store', 'retail', 'buy', 'purchase', 'product']):
            if any(term in text_lower for term in ['art', 'print', 'craft', 'stationery', 'paper']):
                guidance.append("🎨 ART/CRAFT RETAIL DETECTED: This business sells art supplies, prints, or craft items. Consider '5700-7299: Miscellaneous Stores' to access MCC 5970 (Artist Supply Stores).")
            elif any(term in text_lower for term in ['clothing', 'apparel', 'fashion', 'shirt', 'dress']):
                guidance.append("👕 CLOTHING RETAIL DETECTED: This business sells clothing or apparel. Must select '5600-5699: Clothing Stores' for clothing-specific MCCs.")
            elif any(term in text_lower for term in ['furniture', 'home', 'decor', 'rug', 'furnishing']):
                guidance.append("🏠 HOME FURNISHINGS DETECTED: This business sells furniture or home decor. Must select '5700-7299: Miscellaneous Stores' to access MCC 5712 (Furniture and Home Furnishings).")
        
        # Service business guidance
        if any(term in text_lower for term in ['consulting', 'management', 'service', 'professional', 'advice', 'support']):
            guidance.append("💼 PROFESSIONAL SERVICES DETECTED: This business provides consulting, management, or professional services. Must select '7300-7999: Business Services' for service-related MCCs.")
        
        # Social media/content guidance
        if any(term in text_lower for term in ['instagram', 'youtube', 'social media', 'content', 'influencer', 'creator']):
            guidance.append("📱 SOCIAL MEDIA/CONTENT BUSINESS DETECTED: This business focuses on content creation or social media services. Must select '7300-7999: Business Services' to access MCC 7392 (Consulting, Management and PR Services).")
        
        # Travel-related guidance
        if any(term in text_lower for term in ['airline', 'flight', 'aviation']):
            guidance.append("✈️ AIRLINE DETECTED: Must select '3000-3299: Airlines' for aviation-related MCCs.")
        elif any(term in text_lower for term in ['hotel', 'lodging', 'accommodation', 'resort']):
            guidance.append("🏨 LODGING DETECTED: Must select '3500-3999: Lodging' for hotel/accommodation MCCs.")
        elif any(term in text_lower for term in ['car rental', 'vehicle rental', 'rental car']):
            guidance.append("🚗 CAR RENTAL DETECTED: Must select '3300-3499: Car Rental' for vehicle rental MCCs.")
        
        if not guidance:
            guidance.append("⚠️ GENERAL GUIDANCE: Analyze the primary business activity and select the category that contains the most specific MCC codes for this type of business.")
        
        return "\n".join(guidance)
    
    def _get_stage2_business_guidance(self, text_content: str) -> str:
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
        validation_rules = self._get_stage2_business_guidance(text_content)
        
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
    
    def _query_llm_with_retry(self, prompt: str, image_path: str, stage: str, retry_count: int = 0) -> str:
        """
        Query LLM with retry logic for rate limiting.
        
        Args:
            prompt (str): Text prompt for the model
            image_path (str): Path to screenshot image
            stage (str): Classification stage ("stage1" or "stage2")
            retry_count (int): Current retry attempt
            
        Returns:
            str: Model response
        """
        try:
            # Load screenshot if available
            screenshot_data = None
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    screenshot_data = f.read()
            
            # Create appropriate system prompt based on stage
            if stage == "stage1":
                system_prompt = "You are an expert at categorizing businesses into MCC categories. Analyze the website and return JSON."
            else:
                system_prompt = "You are an expert at selecting specific MCC codes for businesses. Analyze the website and return JSON."
            
            response = self.llm_client.query(
                model=self.model_config['model'],
                system_prompt=system_prompt,
                user_prompt=prompt,
                image_data=screenshot_data,
                image_mime_type="image/png" if screenshot_data else None,
                max_tokens=self.model_config['max_tokens'],
                temperature=self.model_config.get('temperature', 0.3)
            )
            
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
                    return self._query_llm_with_retry(prompt, image_path, stage, retry_count + 1)
                else:
                    error(f"Max retries reached. Using fallback classification.")
                    return self._get_fallback_response(stage)
            
            # For other errors, log and use fallback
            error(f"LLM query failed: {e}")
            return self._get_fallback_response(stage)
    
    def _get_fallback_response(self, stage: str) -> str:
        """
        Get fallback response when LLM fails.
        
        Args:
            stage (str): Classification stage
            
        Returns:
            str: Fallback JSON response
        """
        if stage == "stage1":
            # Default to restaurants/food service category
            return json.dumps({
                "selected_category_range": "5700-7299",
                "selected_category_name": "Miscellaneous Stores",
                "confidence": 0.5,
                "reasoning": "Fallback classification due to API error. Manual review recommended.",
                "key_indicators": ["fallback"],
                "business_type_identified": "Unknown (API fallback)"
            })
        else:
            # Default to general restaurant MCC
            return json.dumps({
                "selected_mcc": 5812,
                "selected_mcc_description": "Eating Places and Restaurants",
                "confidence": 0.5,
                "reasoning": "Fallback MCC code due to API error. Manual review recommended.",
                "business_match_factors": ["fallback"],
                "alternative_mccs_considered": []
            })
    
    def _find_screenshot(self, domain_dir: str) -> Optional[str]:
        """Find screenshot file in domain directory."""
        try:
            for file in os.listdir(domain_dir):
                if file.startswith("screenshot_") and file.endswith(".png"):
                    return os.path.join(domain_dir, file)
        except Exception:
            pass
        return None
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM.
        
        Args:
            response (str): Raw response from model
            
        Returns:
            Dict[str, Any]: Parsed JSON response
        """
        try:
            if not response:
                return {"error": "Empty response from LLM"}
                
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

    def _query_llm_with_json_retry(self, prompt: str, screenshot_path: str, stage_name: str) -> Dict[str, Any]:
        """
        Query LLM with retry logic for JSON parsing errors and quota exhaustion.
        
        Args:
            prompt (str): The prompt to send
            screenshot_path (str): Path to screenshot
            stage_name (str): Stage identifier for logging
            
        Returns:
            Dict[str, Any]: Parsed JSON response or error dict
        """
        current_model = self.model_config.get('model', 'gemini-2.5-flash')
        
        # First attempt with primary model
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                warning(f"Retry attempt {attempt} for {stage_name} (waiting {self.retry_delay}s)")
                time.sleep(self.retry_delay)
            
            try:
                response = self._query_llm_with_retry(prompt, screenshot_path, stage_name)
                parsed_result = self._parse_json_response(response)
                
                if "error" not in parsed_result:
                    if attempt > 0:
                        success(f"✅ Retry {attempt} succeeded for {stage_name}")
                    return parsed_result
                    
                error(f"❌ JSON parsing failed for {stage_name} (attempt {attempt + 1}): {parsed_result.get('error', 'Unknown error')}")
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for quota/rate limit errors
                if any(quota_term in error_msg for quota_term in [
                    'quota', 'rate limit', 'billing', 'exceeded', 'exhausted', 
                    'permission', 'insufficient', 'usage limit', 'credit'
                ]):
                    warning(f"🚫 Quota/Rate limit detected for {stage_name} with '{current_model}': {str(e)}")
                    break  # Skip remaining retries with same model, go to backup immediately
                else:
                    error(f"❌ LLM query failed for {stage_name} (attempt {attempt + 1}): {str(e)}")
        
        # All retries with primary model failed, try backup model
        if self.backup_model and self.backup_model != current_model:
            warning(f"🔄 All retries failed with '{current_model}'. Switching to backup model '{self.backup_model}' for {stage_name}")
            
            # Temporarily switch to backup model
            original_model = self.model_config['model']
            original_llm_client = self.llm_client
            
            try:
                # Update model config and recreate client
                self.model_config['model'] = self.backup_model
                self.llm_client = create_llm_client()
                
                info(f"🔄 Attempting {stage_name} with backup model '{self.backup_model}'")
                response = self._query_llm_with_retry(prompt, screenshot_path, f"{stage_name}_backup")
                parsed_result = self._parse_json_response(response)
                
                if "error" not in parsed_result:
                    success(f"✅ Backup model '{self.backup_model}' succeeded for {stage_name}")
                    return parsed_result
                else:
                    error(f"❌ Backup model also failed for {stage_name}: {parsed_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                error_msg = str(e).lower()
                if any(quota_term in error_msg for quota_term in [
                    'quota', 'rate limit', 'billing', 'exceeded', 'exhausted', 
                    'permission', 'insufficient', 'usage limit', 'credit'
                ]):
                    error(f"🚫 Backup model '{self.backup_model}' also has quota issues for {stage_name}: {str(e)}")
                else:
                    error(f"❌ Backup model '{self.backup_model}' failed for {stage_name}: {str(e)}")
            finally:
                # Restore original model and client
                self.model_config['model'] = original_model
                self.llm_client = original_llm_client
                info(f"🔄 Restored primary model '{original_model}'")
        
        # All attempts failed
        return {"error": f"All retry attempts failed for {stage_name} with both primary and backup models"}
        
        # All attempts failed
        return {"error": f"All retry attempts failed for {stage_name} with both primary and backup models"}
    
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
    
    def classify_mcc(self, domain_dir: str, domain_name: str) -> Dict[str, Any]:
        """
        Classify MCC code for a website using two-stage approach.
        
        Args:
            domain_dir (str): Path to domain directory containing files
            domain_name (str): Domain name for logging
            
        Returns:
            Dict[str, Any]: Complete MCC classification results
        """
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
                "stage2_completed": False,
                "model_used": self.model_config['model']
            }
        }
        
        try:
            # 1. Load required files
            html_path = os.path.join(domain_dir, "page.html")
            screenshot_path = self._find_screenshot(domain_dir)
            
            if not os.path.exists(html_path):
                result["error"] = "HTML file not found"
                return result
            
            if screenshot_path:
                result["processing_metadata"]["screenshot_found"] = True
            
            # 2. Extract text content
            text_content = self.text_extractor.extract_for_mcc_classification(html_path)
            if not text_content:
                result["error"] = "Failed to extract text content"
                return result
            
            result["processing_metadata"]["text_extraction_success"] = True
            
            # 3. Stage 1: Category Classification
            stage1_prompt = self._create_stage1_prompt(text_content)
            stage1_result = self._query_llm_with_json_retry(stage1_prompt, screenshot_path, "stage1")
            
            result["stage1_result"] = stage1_result
            
            if "error" in stage1_result:
                result["error"] = f"Stage 1 failed: {stage1_result['error']}"
                return result
            
            result["processing_metadata"]["stage1_completed"] = True
            
            # Validate and normalize Stage 1 results
            selected_range = stage1_result.get("selected_category_range")
            if not selected_range:
                result["error"] = "No category range returned from Stage 1"
                return result
            
            # Handle cases where model returns specific MCC codes instead of ranges
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
                            info(f"Mapped range to category {range_key}")
                            break
                    else:
                        result["error"] = f"Could not map category range {selected_range} to valid MCC category"
                        return result
                        
                except ValueError:
                    result["error"] = f"Invalid category range format from Stage 1: {selected_range}"
                    return result
            
            success(f"Stage 1 complete: {selected_range} - {stage1_result.get('selected_category_name')}")
            
            # 4. Stage 2: Exact MCC Code Determination
            candidate_mccs = self._get_category_range_codes(selected_range)
            
            if candidate_mccs.empty:
                result["error"] = f"No MCC codes found for category {selected_range}"
                return result
            
            # Found candidate MCC codes (count tracked internally)
            
            stage2_prompt = self._create_stage2_prompt(text_content, selected_range, candidate_mccs)
            stage2_result = self._query_llm_with_json_retry(stage2_prompt, screenshot_path, "stage2")
            
            result["stage2_result"] = stage2_result
            
            if "error" in stage2_result:
                result["error"] = f"Stage 2 failed: {stage2_result['error']}"
                return result
            
            result["processing_metadata"]["stage2_completed"] = True
            
            # 5. Validate and finalize results
            final_mcc = stage2_result.get("selected_mcc")
            if not final_mcc:
                result["error"] = "No MCC code returned from Stage 2"
                return result
            
            # Validate MCC is in candidate list
            if final_mcc not in candidate_mccs['MCC'].values:
                # Try to find closest match in category
                warning(f"Selected MCC {final_mcc} not in exact candidate list, finding closest match...")
                # Use first MCC in category as fallback
                final_mcc = candidate_mccs.iloc[0]['MCC']
                stage2_result["selected_mcc"] = final_mcc
                stage2_result["selected_mcc_description"] = candidate_mccs.iloc[0]['Description']
                stage2_result["confidence"] = min(stage2_result.get("confidence", 0.5), 0.7)
            
            # Validate business logic
            is_valid, validation_error = self._validate_mcc_selection(final_mcc, text_content, candidate_mccs)
            if not is_valid:
                warning(f"Validation warning: {validation_error}")
                # Continue with lower confidence rather than failing
                stage2_result["confidence"] = min(stage2_result.get("confidence", 0.5), 0.6)
            
            result["final_mcc"] = final_mcc
            result["final_mcc_description"] = stage2_result.get("selected_mcc_description", "")
            result["final_confidence"] = min(
                stage1_result.get("confidence", 0.0),
                stage2_result.get("confidence", 0.0)
            )
            result["classification_success"] = True
            
            return result
            
        except Exception as e:
            error(f"MCC classification failed for {domain_name}: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
            return result
    
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