"""
Main script to orchestrate logo extraction from small business websites.
Loads websites from file_utils and processes them with the web_agent.
"""

import os
import sys
from typing import List, Dict
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'agent'))

from utils.file_utils import load_website_data
from utils.terminal_prettify import (
    success, error, warning, info, processing, completed,
    header, subheader, separator, progress_bar, status_message
)
from agent.web_agent import WebAgent, extract_logos_from_website


def process_single_website(website_data: Dict, agent: WebAgent, base_output_dir: str) -> Dict:
    """
    Process a single website to extract logo images.
    
    Args:
        website_data (Dict): Website data with id and url
        agent (WebAgent): Web agent instance
        base_output_dir (str): Base directory for saving results
        
    Returns:
        Dict: Processing results with status and details
    """
    website_id = website_data['id']
    url = website_data['url']
    
    try:
        processing(f"Extracting logos from {url}")
        
        # Extract logos using the web agent
        results = agent.extract_logo_images(url)
        
        # Save results to structured directory
        results_file = agent.save_results(website_data, results, base_output_dir)
        
        # Determine result status
        if results['status'] == 'success':
            logo_count = len(results['logo_candidates'])
            if logo_count > 0:
                success(f"Found {logo_count} potential logo(s) for {url}")
                return {
                    'status': 'success',
                    'website_id': website_id,
                    'url': url,
                    'logo_count': logo_count,
                    'results_file': results_file,
                    'top_logo_score': results['logo_candidates'][0]['logo_score'] if logo_count > 0 else 0
                }
            else:
                warning(f"No potential logos found for {url}")
                return {
                    'status': 'no_logos',
                    'website_id': website_id,
                    'url': url,
                    'logo_count': 0,
                    'results_file': results_file,
                    'top_logo_score': 0
                }
        else:
            error(f"Failed to process {url}: {results.get('error', 'Unknown error')}")
            return {
                'status': 'error',
                'website_id': website_id,
                'url': url,
                'error': results.get('error', 'Unknown error'),
                'results_file': results_file if 'results_file' in locals() else None
            }
            
    except Exception as e:
        error(f"Exception processing {url}: {str(e)}")
        return {
            'status': 'exception',
            'website_id': website_id,
            'url': url,
            'error': str(e)
        }


def main():
    """Main function to orchestrate the logo extraction process."""
    
    # Print banner
    header("Small Business Logo Extractor")
    info("Loading websites and extracting potential logo images...")
    separator()
    
    try:
        # Step 1: Load website data
        status_message("Loading website data from file...", "loading")
        json_file_path, workspace_path = load_website_data()
        
        if not json_file_path or not os.path.exists(json_file_path):
            error("Failed to load website data. Make sure 'data/load_websites.txt' exists.")
            return
        
        # Load the processed website data
        import json
        with open(json_file_path, 'r') as f:
            websites_data = json.load(f)
        
        success(f"Loaded {len(websites_data)} websites for processing")
        info(f"Results will be saved to: {workspace_path}")
        separator()
        
        # Step 2: Initialize web agent
        status_message("Initializing web agent...", "loading")
        agent = WebAgent(timeout=15, max_retries=3)
        success("Web agent initialized successfully")
        
        # Step 3: Process websites
        subheader(f"Processing {len(websites_data)} websites")
        
        results_summary = {
            'total_websites': len(websites_data),
            'successful': 0,
            'no_logos': 0,
            'errors': 0,
            'total_logos_found': 0,
            'processing_results': []
        }
        
        # Process websites (you can enable concurrent processing by changing max_workers)
        max_workers = 3  # Sequential processing to be respectful to websites
        
        if max_workers == 1:
            # Sequential processing
            for i, website_data in enumerate(websites_data, 1):
                progress_bar(i - 1, len(websites_data), label_text="Progress")
                
                result = process_single_website(website_data, agent, workspace_path)
                results_summary['processing_results'].append(result)
                
                # Update summary stats
                if result['status'] == 'success':
                    results_summary['successful'] += 1
                    results_summary['total_logos_found'] += result['logo_count']
                elif result['status'] == 'no_logos':
                    results_summary['no_logos'] += 1
                else:
                    results_summary['errors'] += 1
                
                # Small delay to be respectful to websites
                time.sleep(1)
            
            # Complete progress bar
            progress_bar(len(websites_data), len(websites_data), label_text="Progress")
        
        else:
            # Concurrent processing (use with caution)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_website = {
                    executor.submit(process_single_website, website_data, agent, workspace_path): website_data
                    for website_data in websites_data
                }
                
                completed_count = 0
                for future in as_completed(future_to_website):
                    result = future.result()
                    results_summary['processing_results'].append(result)
                    
                    # Update summary stats
                    if result['status'] == 'success':
                        results_summary['successful'] += 1
                        results_summary['total_logos_found'] += result['logo_count']
                    elif result['status'] == 'no_logos':
                        results_summary['no_logos'] += 1
                    else:
                        results_summary['errors'] += 1
                    
                    completed_count += 1
                    progress_bar(completed_count, len(websites_data), label_text="Progress")
        
        # Step 4: Save processing summary
        separator()
        status_message("Saving processing summary...", "loading")
        
        summary_file = os.path.join(workspace_path, 'processing_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(results_summary, f, indent=2)
        
        # Step 5: Display final results
        separator()
        header("Processing Complete!")
        
        success(f"Successfully processed: {results_summary['successful']} websites")
        warning(f"No logos found: {results_summary['no_logos']} websites")
        error(f"Errors encountered: {results_summary['errors']} websites")
        info(f"Total logos found: {results_summary['total_logos_found']}")
        info(f"Results saved to: {workspace_path}")
        info(f"Summary saved to: {summary_file}")
        
        # Show top results
        if results_summary['successful'] > 0:
            separator()
            subheader("Top Logo Extraction Results")
            
            successful_results = [r for r in results_summary['processing_results'] if r['status'] == 'success']
            top_results = sorted(successful_results, key=lambda x: x['top_logo_score'], reverse=True)[:5]
            
            for i, result in enumerate(top_results, 1):
                info(f"{i}. {result['url']} - {result['logo_count']} logo(s) (top score: {result['top_logo_score']})")
        
        completed("Logo extraction process completed successfully!")
        
    except Exception as e:
        error(f"An error occurred during processing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()