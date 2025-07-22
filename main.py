"""
Main execution file for the website content extraction system.
"""

import os
from agent.reader_agent import ReaderAgent
from utils.file_utils import load_website_data
from utils.terminal_prettify import success, error, warning, info


def main():
    """
    Main function - get all websites and run them with the reader agent.
    """
    try:
        # Load websites from file
        info("Loading websites from file...")
        json_path, workspace_path = load_website_data()
        
        if not json_path or not os.path.exists(json_path):
            error("No website data file found. Please add URLs to load_websites.txt")
            return
        
        # Read the website data
        import json
        with open(json_path, 'r') as f:
            website_data = json.load(f)
        
        # Extract URLs
        websites = [item['url'] for item in website_data]
        info(f"Loaded {len(websites)} websites from file")
        
        if not websites:
            warning("No websites found in the file")
            return
        
        # Initialize Reader Agent with 5 second wait time and config file
        info("Initializing Reader Agent...")
        agent = ReaderAgent(wait_time=5, config_path="config.yaml")
        
        # Process all websites using the workspace path
        info("Starting website processing...")
        final_workspace_path, results = agent.process_websites(websites, workspace_path)
        
        if results:
            success(f"Processing completed! Results saved in: {final_workspace_path}")
        else:
            warning("No results generated")
            
    except Exception as e:
        error(f"Error in main execution: {e}")
        raise


if __name__ == "__main__":
    main()