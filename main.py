"""
Main script for processing multiple websites and extracting their images.
Loads websites from file_utils and processes them using the web_agent.
"""

import os
import sys
from multiprocessing import Pool, cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

# Add utils directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'agent'))

from utils.file_utils import load_website_data
from utils.terminal_prettify import success, error, warning, info, processing, header, separator
from agent.web_agent import process_single_website


def process_website_wrapper(args):
    """
    Wrapper function for multiprocessing.
    
    Args:
        args (tuple): (website_url, base_save_dir)
        
    Returns:
        Dict: Processing results
    """
    website_url, base_save_dir = args
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # Add delay between retries
            if attempt > 0:
                time.sleep(attempt * 2)
            
            return process_single_website(website_url, base_save_dir)
            
        except Exception as e:
            error_msg = str(e)
            if "WinError 193" in error_msg or "not a valid Win32 application" in error_msg:
                warning(f"ChromeDriver issue for {website_url}, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    continue
            
            error(f"Error processing {website_url}: {error_msg}")
            return {
                'url': website_url,
                'domain': 'error',
                'total_images': 0,
                'downloaded_images': 0,
                'failed_downloads': 0,
                'image_types': {},
                'error': error_msg
            }


def process_websites_batch(websites, base_save_dir="downloaded_images", max_workers=None):
    """
    Process multiple websites concurrently.
    
    Args:
        websites (list): List of website URLs
        base_save_dir (str): Base directory for saving images
        max_workers (int): Maximum number of worker processes
        
    Returns:
        list: List of processing results
    """
    if max_workers is None:
        # Reduce workers to avoid ChromeDriver conflicts on Windows
        max_workers = min(2, len(websites))  # Max 2 workers for Windows compatibility
    
    info(f"Processing {len(websites)} websites with {max_workers} workers")
    
    # Prepare arguments for workers
    args_list = [(url, base_save_dir) for url in websites]
    
    results = []
    completed = 0
    
    # For small batches, process sequentially to avoid driver conflicts
    if len(websites) <= 3:
        info("Processing websites sequentially for better stability")
        for args in args_list:
            result = process_website_wrapper(args)
            results.append(result)
            completed += 1
            
            if 'error' not in result:
                success(f"[{completed}/{len(websites)}] Completed: {result['domain']} "
                       f"({result['downloaded_images']} images)")
            else:
                error(f"[{completed}/{len(websites)}] Failed: {args[0]}")
    else:
        # Use ProcessPoolExecutor for larger batches
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_url = {executor.submit(process_website_wrapper, args): args[0] 
                            for args in args_list}
            
            # Process completed jobs
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    if 'error' not in result:
                        success(f"[{completed}/{len(websites)}] Completed: {result['domain']} "
                               f"({result['downloaded_images']} images)")
                    else:
                        error(f"[{completed}/{len(websites)}] Failed: {url}")
                        
                except Exception as e:
                    error(f"[{completed}/{len(websites)}] Exception for {url}: {str(e)}")
                    completed += 1
    
    return results


def print_summary(results):
    """
    Print a summary of processing results.
    
    Args:
        results (list): List of processing results
    """
    separator()
    header("PROCESSING SUMMARY")
    
    total_websites = len(results)
    successful = sum(1 for r in results if 'error' not in r)
    failed = total_websites - successful
    
    total_images = sum(r.get('total_images', 0) for r in results if 'error' not in r)
    downloaded_images = sum(r.get('downloaded_images', 0) for r in results if 'error' not in r)
    
    # Aggregate image types
    all_image_types = {}
    for r in results:
        if 'error' not in r:
            for img_type, count in r.get('image_types', {}).items():
                all_image_types[img_type] = all_image_types.get(img_type, 0) + count
    
    info(f"Websites processed: {total_websites}")
    success(f"Successful: {successful}")
    if failed > 0:
        error(f"Failed: {failed}")
    
    info(f"Total images found: {total_images}")
    success(f"Images downloaded: {downloaded_images}")
    
    # Show breakdown by image type
    info("Image types found:")
    for img_type, count in sorted(all_image_types.items()):
        info(f"  {img_type}: {count}")
    
    if successful > 0:
        avg_images = downloaded_images / successful
        info(f"Average images per site: {avg_images:.1f}")
    
    separator()
    
    # Print details for each website
    header("DETAILED RESULTS")
    for result in results:
        if 'error' not in result:
            type_summary = ', '.join([f"{k}:{v}" for k, v in result.get('image_types', {}).items()])
            print(f"✓ {result['domain']:20} | "
                  f"Images: {result['downloaded_images']:3d} | "
                  f"Types: [{type_summary}] | "
                  f"Dir: {result['save_directory']}")
        else:
            print(f"✗ {result['url']:30} | Error: {result.get('error', 'Unknown')}")


def main():
    """Main function to process all websites."""
    start_time = time.time()
    
    header("WEBSITE IMAGE EXTRACTOR")
    info("Loading websites from data file...")
    
    try:
        # Load websites from file_utils
        json_file_path, workspace_path = load_website_data()
        
        if not json_file_path:
            error("Failed to load website data")
            return
        
        # Read the JSON file to get website URLs
        import json
        with open(json_file_path, 'r') as f:
            website_data = json.load(f)
        
        websites = [item['url'] for item in website_data]
        
        if not websites:
            error("No websites found in data file")
            return
        
        success(f"Loaded {len(websites)} websites")
        
        # Create base directory for images
        base_save_dir = "downloaded_images"
        os.makedirs(base_save_dir, exist_ok=True)
        info(f"Images will be saved to: {os.path.abspath(base_save_dir)}")
        
        separator()
        
        # Process websites
        results = process_websites_batch(websites, base_save_dir)
        
        # Print summary
        print_summary(results)
        
        # Calculate total time
        end_time = time.time()
        duration = end_time - start_time
        info(f"Total processing time: {duration:.1f} seconds")
        
        # Save results to file
        results_file = os.path.join(base_save_dir, "processing_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        success(f"Results saved to: {results_file}")
        
    except Exception as e:
        error(f"Main function error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()