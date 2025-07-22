"""
Reader Agent using Jina AI Reader API to extract markdown content from websites
including images, SVGs, and any format that could represent a logo.
"""

import os
import json
import requests
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

from utils.terminal_prettify import success, error, warning, info, processing, completed, separator
from utils.llm import create_llm_client
from utils.file_utils import parse_json_from_markdown
import yaml

# Load environment variables
load_dotenv()

class ReaderAgent:
    """
    Agent for extracting website content using Jina AI Reader API.
    """

    def __init__(self, wait_time: int = 5, config_path: str = "config.yaml"):
        """Initialize the Reader Agent with API configuration.

        Args:
            wait_time (int): Time to wait (in seconds) before making requests to allow page loading
            config_path (str): Path to the configuration YAML file
        """
        self.api_key = os.getenv('JINA_API_KEY')
        self.base_url = "https://r.jina.ai"
        self.session = requests.Session()
        self.wait_time = wait_time
        
        # Load configuration from YAML file
        self.config = self._load_config(config_path)
        self.llm_model = self.config.get('agent', {}).get('content-analysis-agent', {}).get('model', 'gpt-4o-mini')
        self.llm_max_tokens = self.config.get('agent', {}).get('content-analysis-agent', {}).get('max_tokens', 2048)
        self.llm_temperature = self.config.get('agent', {}).get('content-analysis-agent', {}).get('temperature', 0.3)
        
        self.llm_client = create_llm_client()

        # Set headers if API key is provided
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'X-With-Generated-Alt': 'true'  # Generate alt text for images
            })
        else:
            warning("No Jina API key found. Using free tier with rate limits.")

        if self.wait_time > 0:
            info(f"Configured with {self.wait_time} second wait time for page loading")

        info(f"Using LLM model: {self.llm_model} for logo identification")
        info(f"LLM settings - Max tokens: {self.llm_max_tokens}, Temperature: {self.llm_temperature}")
    
    def _load_config(self, config_path: str) -> dict:
        """
        Load configuration from YAML file.
        
        Args:
            config_path (str): Path to the configuration file
            
        Returns:
            dict: Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            success(f"Loaded configuration from {config_path}")
            return config
        except FileNotFoundError:
            error(f"Configuration file not found: {config_path}")
            warning("Using default configuration")
            return {}
        except yaml.YAMLError as e:
            error(f"Error parsing YAML configuration: {e}")
            warning("Using default configuration")
            return {}
        except Exception as e:
            error(f"Error loading configuration: {e}")
            warning("Using default configuration")
            return {}

    def _get_domain_name(self, url: str) -> str:
        """
        Extract domain name from URL for directory naming.

        Args:
            url (str): The website URL

        Returns:
            str: Clean domain name suitable for directory naming
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            # Replace dots and other characters with underscores
            domain = domain.replace('.', '_').replace('-', '_')
            return domain
        except Exception as e:
            error(f"Error parsing URL {url}: {e}")
            return "unknown_domain"

    def _analyze_logo_with_llm(self, markdown_content: str, url: str) -> Dict:
        """
        Analyze markdown content with LLM to identify potential logo.

        Args:
            markdown_content (str): Extracted markdown content
            url (str): Original website URL

        Returns:
            Dict: Logo analysis result
        """
        try:
            processing(f"Analyzing content with LLM to identify logo for {url}")

            # System prompt for logo identification
            system_prompt = """
You are an expert assistant specializing in analyzing markdown content extracted from websites via the Reader API by Jinai. Your task is to identify the image URL most likely to be the website's logo and return a JSON object with the following structure:
{
  "logo_url": "<URL string or 'No logo found'>",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<brief explanation of the selection logic>"
}
**Instructions for Logo Identification:**
1. **Prioritize Position**: Logos are typically placed early in the markdown (e.g., near the top of the page or in header sections). Favor images appearing first unless other criteria strongly suggest otherwise.
2. **Evaluate Dimensions**: Logos often have small to medium dimensions (e.g., 100–500 pixels in width/height, often square or near-square). Use URL parameters (e.g., `w_`, `h_`) to infer size where available.
3. **Analyze Filenames**: Look for filenames containing keywords like 'logo', 'brand', 'icon', or generic terms like 'screenshot', which may indicate branding assets.
4. **Check Alt Text/Captions**: Use alt text or captions for clues, prioritizing those mentioning the business name, 'logo', or 'brand', and excluding descriptions of products, interiors, or people (e.g., 'interior of a room', 'group of people').
5. **Exclude Non-Logo Content**: Ignore images clearly depicting non-logo elements (e.g., exteriors, interiors, products, or large photos with complex scenes).
6. **Confidence Scoring**:
   - Assign 0.9–1.0 for clear logo indicators (e.g., filename includes 'logo', early position, and appropriate size).
   - Assign 0.6–0.89 for probable logos (e.g., early position and generic filename but no explicit 'logo' keyword).
   - Assign 0.3–0.59 for uncertain cases (e.g., multiple similar images with no clear indicators).
   - Assign 0.0 for no suitable logo found.
7. **Default Case**: If no image meets the criteria, return:
   {
     "logo_url": "No logo found",
     "confidence": 0.0,
     "reason": "No image identified as a logo based on position, size, filename, or description"
   }
8. **NO GIFS **: GIFs are not accepted, check the other parts of the markdown which could potentially be a logo. If you cannot find it, consider that as No logo found.
9. **Small Business Websites**: For small business websites (e.g., Wix-hosted), prioritize early images and generic filenames, as logos are often less explicitly labeled.
10. **Other company logos**: If the website has major company logos, such as Google in their file name, ignore them and focus on what could be the logo based on the website's content and context.
**Output Requirements**:
- Return only the JSON object, with no additional text, comments, or formatting.
- Ensure the `logo_url` is a single string (or 'No logo found'), `confidence` is a float between 0.0 and 1.0, and `reason` is a concise string explaining the logic.
- Handle small business websites (e.g., Wix-hosted) by prioritizing early images and generic filenames, as logos are often less explicitly labeled.
"""

            # User prompt for logo identification
            user_prompt = f"""
Analyze the following markdown content extracted from a website using Reader API by Jinai, including image URLs, alt text, and other data:
{markdown_content}
Identify the image most likely to be the website's logo and return a JSON object with the following structure:
{{
  "logo_url": "<URL string or 'No logo found'>",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<brief explanation of the selection logic>"
}}
Follow the system instructions precisely, returning only the JSON object with no additional text, comments, or formatting.
"""

            # Query LLM
            response = self.llm_client.query(
                model=self.llm_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=self.llm_temperature,
                max_tokens=self.llm_max_tokens
            )

            # Parse JSON response
            logo_analysis = parse_json_from_markdown(response['content'])

            success(f"LLM logo analysis completed for {url}")

            return {
                'success': True,
                'logo_analysis': logo_analysis,
                'llm_response': response,
                'analyzed_at': datetime.now().isoformat()
            }

        except Exception as e:
            error(f"Error analyzing logo with LLM for {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'logo_analysis': {
                    'logo_url': 'No logo found',
                    'confidence': 0.0,
                    'reason': f'LLM analysis failed: {str(e)}'
                },
                'analyzed_at': datetime.now().isoformat()
            }

    def _download_logo_image(self, logo_url: str, logo_dir: str, website_dir_name: str) -> Dict:
        """
        Download logo image from URL and save it locally.
        
        Args:
            logo_url (str): URL of the logo image
            logo_dir (str): Directory to save logo images
            website_dir_name (str): Name of the website directory for filename
            
        Returns:
            Dict: Download result information
        """
        try:
            if logo_url == "No logo found" or not logo_url:
                return {
                    'success': False,
                    'error': 'No logo URL provided',
                    'local_path': None
                }
            
            processing(f"Downloading logo from: {logo_url}")
            
            # Make request to download image
            response = self.session.get(logo_url, timeout=30, stream=True)
            
            if response.status_code == 200:
                # Determine file extension from content type or URL
                content_type = response.headers.get('content-type', '').lower()
                if 'image/png' in content_type:
                    extension = '.png'
                elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
                    extension = '.jpg'
                elif 'image/svg' in content_type:
                    extension = '.svg'
                elif 'image/webp' in content_type:
                    extension = '.webp'
                else:
                    # Try to get extension from URL
                    url_ext = logo_url.split('.')[-1].lower()
                    if url_ext in ['png', 'jpg', 'jpeg', 'svg', 'webp']:
                        extension = f'.{url_ext}'
                    else:
                        extension = '.png'  # Default fallback
                
                # Create filename
                logo_filename = f"{website_dir_name}_logo{extension}"
                logo_path = os.path.join(logo_dir, logo_filename)
                
                # Save image
                with open(logo_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                success(f"Downloaded logo: {logo_filename}")
                
                return {
                    'success': True,
                    'local_path': logo_path,
                    'filename': logo_filename,
                    'content_type': content_type,
                    'file_size': os.path.getsize(logo_path),
                    'downloaded_at': datetime.now().isoformat()
                }
            else:
                error(f"Failed to download logo. Status: {response.status_code}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'local_path': None
                }
                
        except Exception as e:
            error(f"Error downloading logo from {logo_url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'local_path': None
            }

    def _ensure_workspace_directory(self, workspace_path: str) -> str:
        """
        Ensure the workspace directory exists for saving markdown files.

        Args:
            workspace_path (str): Path to the workspace directory from load_website_data

        Returns:
            str: Path to the workspace directory
        """
        try:
            os.makedirs(workspace_path, exist_ok=True)
            # Also create logo directory
            logo_dir = os.path.join(workspace_path, "logos")
            os.makedirs(logo_dir, exist_ok=True)
            info(f"Using workspace directory: {workspace_path}")
            info(f"Created logos directory: {logo_dir}")
            return workspace_path
        except Exception as e:
            error(f"Error ensuring workspace directory: {e}")
            raise

    def _create_website_directory(self, workspace_path: str, url: str) -> str:
        """
        Create website-specific directory within workspace directory under "websites" folder.

        Args:
            workspace_path (str): Path to the workspace directory
            url (str): Website URL

        Returns:
            str: Path to the created website directory
        """
        domain = self._get_domain_name(url)
        timestamp = datetime.now().strftime("%H%M%S")

        # Create websites subdirectory
        websites_dir = os.path.join(workspace_path, "websites")
        website_dir = os.path.join(websites_dir, f"{domain}_{timestamp}")

        try:
            os.makedirs(website_dir, exist_ok=True)
            info(f"Created website directory: {website_dir}")
            return website_dir
        except Exception as e:
            error(f"Error creating website directory: {e}")
            raise

    def _extract_content_with_reader_api(self, url: str) -> Dict:
        """
        Extract markdown content from URL using Jina Reader API.

        Args:
            url (str): The website URL to process

        Returns:
            Dict: Response containing markdown content and metadata
        """
        try:
            processing(f"Extracting content from: {url}")

            # Wait for configured time to allow page loading
            if self.wait_time > 0:
                info(f"Waiting {self.wait_time} seconds for page to load...")
                import time
                time.sleep(self.wait_time)

            # Construct the Reader API URL
            reader_url = f"{self.base_url}/{url}"

            # Make request to Jina Reader API with longer timeout
            response = self.session.get(
                reader_url,
                params={
                    'output': 'markdown',  # Request markdown output
                    'with-images': 'true',  # Include images
                    'with-links': 'true',   # Include links
                    'with-generated-alt': 'true'  # Generate alt text for images
                },
                timeout=60  # Increased timeout to 60 seconds
            )

            if response.status_code == 200:
                success(f"Successfully extracted content from {url}")
                return {
                    'success': True,
                    'content': response.text,
                    'url': url,
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'extracted_at': datetime.now().isoformat()
                }
            else:
                error(f"Failed to extract content. Status: {response.status_code}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'content': response.text,
                    'url': url,
                    'status_code': response.status_code,
                    'extracted_at': datetime.now().isoformat()
                }

        except requests.exceptions.Timeout:
            error(f"Timeout while extracting content from {url}")
            return {
                'success': False,
                'error': 'Request timeout',
                'url': url,
                'extracted_at': datetime.now().isoformat()
            }
        except Exception as e:
            error(f"Error extracting content from {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'extracted_at': datetime.now().isoformat()
            }

    def _save_content(self, workspace_path: str, website_dir: str, url: str, extraction_result: Dict, logo_analysis: Dict) -> Dict:
        """
        Save extracted content and logo analysis to files in the website directory.

        Args:
            workspace_path (str): Path to workspace directory
            website_dir (str): Path to website directory
            url (str): Original website URL
            extraction_result (Dict): Result from content extraction
            logo_analysis (Dict): Result from logo analysis

        Returns:
            Dict: Information about saved files
        """
        saved_files = {}
        domain = self._get_domain_name(url)

        try:
            # Save markdown content
            if extraction_result.get('success') and extraction_result.get('content'):
                md_filename = f"{domain}_content.md"
                md_path = os.path.join(website_dir, md_filename)

                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(extraction_result['content'])

                saved_files['markdown'] = {
                    'filename': md_filename,
                    'path': md_path,
                    'size': len(extraction_result['content'])
                }
                success(f"Saved markdown content: {md_filename}")

            # Download logo image if available
            logo_download_result = {}
            if logo_analysis.get('success') and logo_analysis.get('logo_analysis', {}).get('logo_url') != 'No logo found':
                logo_url = logo_analysis['logo_analysis']['logo_url']
                logos_dir = os.path.join(workspace_path, "logos")
                website_dir_name = os.path.basename(website_dir)

                # Download the actual logo image
                logo_download_result = self._download_logo_image(logo_url, logos_dir, website_dir_name)

                if logo_download_result.get('success'):
                    success(f"Logo saved locally: {logo_download_result['filename']}")
                else:
                    warning(f"Failed to download logo: {logo_download_result.get('error', 'Unknown error')}")
            else:
                info("No logo to download - either analysis failed or no logo found")
                logo_download_result = {
                    'success': False,
                    'error': 'No logo URL available for download',
                    'local_path': None
                }

            saved_files['logo_download'] = logo_download_result

            # Save metadata/extraction info (including logo analysis and download info)
            metadata_filename = f"{domain}_metadata.json"
            metadata_path = os.path.join(website_dir, metadata_filename)

            metadata = {
                'url': url,
                'domain': domain,
                'extraction_result': extraction_result,
                'logo_analysis': logo_analysis,
                'logo_download': saved_files.get('logo_download', {}),
                'processing_info': {
                    'processed_at': datetime.now().isoformat(),
                    'agent': 'ReaderAgent',
                    'api': 'Jina Reader API',
                    'llm_model': self.llm_model
                }
            }

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            saved_files['metadata'] = {
                'filename': metadata_filename,
                'path': metadata_path,
                'content': metadata
            }
            success(f"Saved metadata: {metadata_filename}")

            return saved_files

        except Exception as e:
            error(f"Error saving content for {url}: {e}")
            return {'error': str(e)}

    def _save_run_summary(self, workspace_path: str, processed_websites: List[Dict]) -> str:
        """
        Save summary of the entire run to the workspace directory.

        Args:
            workspace_path (str): Path to workspace directory
            processed_websites (List[Dict]): List of processed website information

        Returns:
            str: Path to the summary file
        """
        try:
            summary_path = os.path.join(workspace_path, "run_summary.json")

            # Calculate statistics
            total_websites = len(processed_websites)
            successful_extractions = sum(1 for w in processed_websites if w.get('extraction_result', {}).get('success', False))
            successful_logo_analyses = sum(1 for w in processed_websites if w.get('logo_analysis', {}).get('success', False))
            logos_found = sum(1 for w in processed_websites if w.get('logo_analysis', {}).get('logo_analysis', {}).get('logo_url', 'No logo found') != 'No logo found')
            logos_downloaded = sum(1 for w in processed_websites if w.get('saved_files', {}).get('logo_download', {}).get('success', False))
            failed_extractions = total_websites - successful_extractions

            summary = {
                'run_info': {
                    'workspace_directory': os.path.basename(workspace_path),
                    'start_time': processed_websites[0]['processed_at'] if processed_websites else None,
                    'end_time': datetime.now().isoformat(),
                    'agent': 'ReaderAgent',
                    'api_used': 'Jina Reader API',
                    'llm_model': self.llm_model
                },
                'statistics': {
                    'total_websites': total_websites,
                    'successful_extractions': successful_extractions,
                    'failed_extractions': failed_extractions,
                    'successful_logo_analyses': successful_logo_analyses,
                    'logos_found': logos_found,
                    'logos_downloaded': logos_downloaded,
                    'extraction_success_rate': f"{(successful_extractions/total_websites*100):.1f}%" if total_websites > 0 else "0%",
                    'logo_detection_rate': f"{(logos_found/total_websites*100):.1f}%" if total_websites > 0 else "0%",
                    'logo_download_rate': f"{(logos_downloaded/total_websites*100):.1f}%" if total_websites > 0 else "0%"
                },
                'processed_websites': processed_websites
            }

            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            success(f"Saved run summary: {summary_path}")
            return summary_path

        except Exception as e:
            error(f"Error saving run summary: {e}")
            return ""

    def process_websites(self, websites: List[str], workspace_path: str) -> Tuple[str, List[Dict]]:
        """
        Process multiple websites and extract their content.

        Args:
            websites (List[str]): List of website URLs to process.
            workspace_path (str): Path to the workspace directory where files will be saved.

        Returns:
            Tuple[str, List[Dict]]: Workspace directory path and list of processing results
        """
        if not websites:
            warning("No websites to process")
            return "", []

        # Ensure workspace directory exists
        workspace_path = self._ensure_workspace_directory(workspace_path)
        processed_websites = []

        separator()
        info(f"Starting content extraction for {len(websites)} websites")
        separator()

        for i, url in enumerate(websites, 1):
            try:
                info(f"Processing website {i}/{len(websites)}: {url}")

                # Create website-specific directory
                website_dir = self._create_website_directory(workspace_path, url)

                # Extract content using Reader API
                extraction_result = self._extract_content_with_reader_api(url)

                # Analyze logo with LLM if extraction was successful
                logo_analysis = {}
                if extraction_result.get('success') and extraction_result.get('content'):
                    logo_analysis = self._analyze_logo_with_llm(extraction_result['content'], url)
                else:
                    warning(f"Skipping logo analysis for {url} - extraction failed")
                    logo_analysis = {
                        'success': False,
                        'error': 'Content extraction failed',
                        'logo_analysis': {
                            'logo_url': 'No logo found',
                            'confidence': 0.0,
                            'reason': 'Content extraction failed - cannot analyze for logo'
                        },
                        'analyzed_at': datetime.now().isoformat()
                    }

                # Save content to files
                saved_files = self._save_content(workspace_path, website_dir, url, extraction_result, logo_analysis)

                # Record processing information
                website_info = {
                    'url': url,
                    'domain': self._get_domain_name(url),
                    'website_directory': os.path.basename(website_dir),
                    'extraction_result': extraction_result,
                    'logo_analysis': logo_analysis,
                    'saved_files': saved_files,
                    'processed_at': datetime.now().isoformat()
                }

                processed_websites.append(website_info)

                if extraction_result.get('success'):
                    completed(f"Successfully processed: {url}")
                else:
                    warning(f"Failed to process: {url}")

                separator()

            except Exception as e:
                error(f"Error processing {url}: {e}")
                website_info = {
                    'url': url,
                    'domain': self._get_domain_name(url),
                    'extraction_result': {'success': False, 'error': str(e)},
                    'logo_analysis': {
                        'success': False,
                        'error': f'Processing failed: {str(e)}',
                        'logo_analysis': {
                            'logo_url': 'No logo found',
                            'confidence': 0.0,
                            'reason': f'Processing failed: {str(e)}'
                        }
                    },
                    'processed_at': datetime.now().isoformat()
                }
                processed_websites.append(website_info)

        # Save run summary
        self._save_run_summary(workspace_path, processed_websites)

        # Print final statistics
        successful = sum(1 for w in processed_websites if w.get('extraction_result', {}).get('success', False))
        total = len(processed_websites)

        separator()
        info(f"Content extraction completed!")
        success(f"Successfully processed: {successful}/{total} websites")
        if successful < total:
            warning(f"Failed to process: {total - successful} websites")
        info(f"Results saved in: {workspace_path}")
        separator()

        return workspace_path, processed_websites