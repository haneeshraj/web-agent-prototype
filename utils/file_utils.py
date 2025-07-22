from datetime import datetime
import json
import uuid
import os
import re

def load_website_data() -> str:
    """
    Load website data from a file.

    Args:
        file_path (str): The path to the file containing website data.

    Returns:
        str: The file path of the processed website data
    """
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "..", 'data', 'load_websites.txt')
    
    try:
        
        websites = []
        
        with open(file_path, 'r') as file:
            websites = [website.strip() for website in file if website.strip()]
            
        processed_data = []

        for website in websites:
            ws_uuid = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            
            processed_data.append({
                "id": ws_uuid,
                "url": website,
            })
            
            # create a directory called 'websites_timestamp' and inside that dirr create a file with the name website_data_timestamp.json which contains the website id and URL as a list of jsons

            json_file_path = os.path.join(script_dir, "..", 'data', 'websites', f"websites_{timestamp}", f"websites_data_{timestamp}.json")
            workspace_path =  os.path.join(script_dir, "..", 'data', 'websites', f"websites_{timestamp}")
            os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
            
            with open(json_file_path, 'w') as json_file:
                json.dump(processed_data, json_file, indent=2)

        return (json_file_path, workspace_path)
    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
        return ""


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

