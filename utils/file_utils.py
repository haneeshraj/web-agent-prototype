from datetime import datetime
import json
import uuid
import os
import re

def load_website_data() -> tuple:
    """
    Load website data from a file, remove duplicates, and return processed data.

    Returns:
        tuple: (json_file_path, workspace_path) for the processed website data
    """
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "..", 'data', 'load_websites.txt')
    
    try:
        websites = []
        
        with open(file_path, 'r') as file:
            # Read all websites and strip whitespace
            raw_websites = [website.strip() for website in file if website.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        for website in raw_websites:
            # Normalize URL for duplicate checking (convert to lowercase, remove trailing slash)
            normalized_url = website.lower().rstrip('/')
            if normalized_url not in seen:
                seen.add(normalized_url)
                websites.append(website)  # Keep original case
        
        if len(raw_websites) > len(websites):
            print(f"Removed {len(raw_websites) - len(websites)} duplicate URLs")
        
        processed_data = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for website in websites:
            ws_uuid = str(uuid.uuid4())
            
            processed_data.append({
                "id": ws_uuid,
                "url": website,
            })
        
        # Create comprehensive directory structure under data/runs/
        # This matches the scraper's run directory structure
        run_data_dir = os.path.join(script_dir, "..", 'data', 'runs', f"run_{timestamp}")
        os.makedirs(run_data_dir, exist_ok=True)
        
        # Save the processed website data in the same run directory
        json_file_path = os.path.join(run_data_dir, f"websites_data_{timestamp}.json")
        
        with open(json_file_path, 'w') as json_file:
            json.dump(processed_data, json_file, indent=2)
        
        print(f"Loaded {len(websites)} unique websites for processing")
        return (json_file_path, run_data_dir)
        
    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
        return ("", "")
    except Exception as e:
        print(f"Error loading website data: {e}")
        return ("", "")


def parse_json_from_markdown(response_content: str) -> dict:
    """
    Parse JSON from LLM response that might be wrapped in markdown code blocks.
    
    Args:
        response_content (str): The raw response content from LLM
        
    Returns:
        dict: Parsed JSON object
        
    Raises:
        json.JSONDecodeError: If JSON cannot be parsed
        ValueError: If no JSON content found
    """
    try:
        # First, try to parse as direct JSON
        return json.loads(response_content.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    # Pattern 1: ```json ... ```
    json_pattern = r'```json\s*\n(.*?)\n```'
    match = re.search(json_pattern, response_content, re.DOTALL | re.IGNORECASE)
    
    if match:
        json_content = match.group(1).strip()
        try:
            return json.loads(json_content)
        except json.JSONDecodeError:
            pass
    
    # Pattern 2: ``` ... ``` (without json specifier)
    code_block_pattern = r'```\s*\n(.*?)\n```'
    match = re.search(code_block_pattern, response_content, re.DOTALL)
    
    if match:
        json_content = match.group(1).strip()
        try:
            return json.loads(json_content)
        except json.JSONDecodeError:
            pass
    
    # Pattern 3: Look for JSON-like content between { and }
    json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_object_pattern, response_content, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue
    
    # If all patterns fail, raise an error
    raise ValueError(f"Could not extract valid JSON from response: {response_content[:200]}...")