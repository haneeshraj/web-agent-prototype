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
    Logo detection agent that analyzes screenshots and HTML to identify website logos.
    """
    
    def __init__(self):
        """Initialize the logo detector with LLM client and configuration."""
        self.llm_client = create_llm_client()
        self.model_config = get_model_config("classifier-agent")
        
        # System prompt for logo detection
        self.system_prompt = """You are a website logo detection expert. Your task is to identify the main logo/brand image from a website using the provided screenshot and HTML structure.

INSTRUCTIONS:
1. Analyze the screenshot to visually identify the website's main logo/brand image
2. Use the HTML structure to understand the page layout and context
3. If there are cookie overlays, popups, or modals, ignore them and focus on the main website content behind them
4. Look for logos typically positioned in:
   - Header/navigation area (most common)
   - Top-left corner
   - Center of header
   - Footer area (secondary logos)

5. From the provided images list, identify which image corresponds to the logo you see in the screenshot
6. Consider these logo characteristics:
   - Usually contains company/brand name or distinctive visual identity
   - Often positioned prominently in navigation
   - May have alt text with brand/company names
   - Typically appears in header sections
7. PLATFORM vs MERCHANT DISTINCTION:
   - If the page is a social media platform's login page, signup page, or generic platform page (showing Instagram, Facebook, Twitter, LinkedIn branding), return logo_found as false
   - Only return logo_found as true if you can identify a MERCHANT/BUSINESS logo, not the platform's own branding
   - Platform logos (Instagram wordmark, Facebook logo, etc.) should NOT be considered the "main brand logo" you're looking for
8. VALID LOGO CRITERIA:
   - A valid logo must be a designed brand identity element (text-based logo, symbol, or combination)
   - DO NOT select profile pictures that are photos of people, even if they appear in profile/avatar positions
   - DO NOT select generic photos, lifestyle images, or personal photographs
   - Only select images that clearly represent a business/brand identity (company name, brand symbol, designed logo mark)
   - If a profile picture is just a photo of a person rather than a designed logo, return logo_found as false

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
    "logo_found": true/false,
    "confidence": "range - [0.0, 1.0]",
    "selected_image": {
        // If logo found, include the exact image object from the images array
        // If not found, use empty object {}
    },
    "reasoning": "Detailed explanation of why this image was selected as the logo, or why no logo was found",
    "visual_description": "Description of what the logo looks like in the screenshot"
}

IMPORTANT:
- Only return valid JSON
- If you cannot confidently identify a logo, set logo_found to false and explain why
- If multiple logos exist, choose the primary/main brand logo
- Ignore decorative images, icons that aren't logos, and background images"""

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
        
        prompt = f"""Please analyze this website to identify the main logo/brand image.

WEBSITE HTML STRUCTURE:
```html
{html_content}
```

AVAILABLE IMAGES ON THE PAGE:
```json
{json.dumps(images_data, indent=2)}
```

TASK:
1. Look at the provided screenshot to visually identify the main logo
2. Use the HTML structure to understand the page layout
3. Match the logo you see in the screenshot with one of the images from the available images list
4. Return your analysis in the specified JSON format

Remember to ignore any cookie overlays, popups, or modal dialogs - focus on the main website content behind them."""

        return prompt
    
    def detect_logo(self, domain_dir: str, domain_name: str) -> Dict[str, Any]:
        """
        Detect logo from website files in the domain directory.
        
        Args:
            domain_dir (str): Path to domain directory containing the files
            domain_name (str): Domain name for logging
            
        Returns:
            Dict[str, Any]: Logo detection results
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
                
                # Validate required keys
                required_keys = ['logo_found', 'confidence', 'selected_image', 'reasoning']
                for key in required_keys:
                    if key not in result:
                        result[key] = None
                
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