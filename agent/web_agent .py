"""
Web Agent for extracting potential logo images from small business websites.
Focuses on finding images that could be logos based on HTML structure and attributes.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class WebAgent:
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        """
        Initialize the Web Agent with configuration for web scraping.
        
        Args:
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retries for failed requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()
        
        # Common logo-related keywords and patterns
        self.logo_keywords = [
            'logo', 'brand', 'header-logo', 'site-logo', 'company-logo',
            'navbar-brand', 'brand-logo', 'main-logo', 'logo-img',
            'logo-image', 'brand-image', 'site-brand', 'header-brand'
        ]
        
        # Common logo file patterns
        self.logo_patterns = [
            r'logo',
            r'brand',
            r'header',
            r'nav',
            r'site',
            r'company'
        ]
        
        # Image extensions to look for
        self.image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy and headers."""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set user agent to mimic a real browser
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        return session
    
    def _is_likely_logo(self, img_tag, img_url: str) -> int:
        """
        Score how likely an image is to be a logo based on various criteria.
        
        Args:
            img_tag: BeautifulSoup img tag
            img_url (str): URL of the image
            
        Returns:
            int: Score (higher = more likely to be logo)
        """
        score = 0
        
        # Check alt text
        alt_text = img_tag.get('alt', '').lower()
        for keyword in self.logo_keywords:
            if keyword in alt_text:
                score += 3
        
        # Check class names
        class_names = ' '.join(img_tag.get('class', [])).lower()
        for keyword in self.logo_keywords:
            if keyword in class_names:
                score += 4
        
        # Check id
        img_id = img_tag.get('id', '').lower()
        for keyword in self.logo_keywords:
            if keyword in img_id:
                score += 5
        
        # Check if image is in header/nav area
        parent_tags = []
        parent = img_tag.parent
        levels = 0
        while parent and levels < 5:  # Check up to 5 levels up
            if parent.name:
                parent_tags.append(parent.name.lower())
                # Check parent classes and ids
                parent_class = ' '.join(parent.get('class', [])).lower()
                parent_id = parent.get('id', '').lower()
                
                if any(tag in ['header', 'nav', 'navbar'] for tag in [parent.name.lower()]):
                    score += 3
                
                for keyword in self.logo_keywords:
                    if keyword in parent_class:
                        score += 2
                    if keyword in parent_id:
                        score += 3
            
            parent = parent.parent
            levels += 1
        
        # Check image URL/filename
        img_filename = os.path.basename(urlparse(img_url).path).lower()
        for pattern in self.logo_patterns:
            if re.search(pattern, img_filename):
                score += 2
        
        # Check image dimensions (if available)
        width = img_tag.get('width')
        height = img_tag.get('height')
        if width and height:
            try:
                w, h = int(width), int(height)
                # Logos are often rectangular and not too large
                if 50 <= w <= 400 and 20 <= h <= 200:
                    score += 1
                # Square logos
                elif 50 <= w <= 200 and abs(w - h) < 20:
                    score += 1
            except ValueError:
                pass
        
        # Check if it's the first image in header/nav
        if 'header' in parent_tags or 'nav' in parent_tags:
            score += 2
        
        return score
    
    def extract_logo_images(self, url: str) -> Dict:
        """
        Extract potential logo images from a website.
        
        Args:
            url (str): Website URL to analyze
            
        Returns:
            Dict: Results containing potential logo images and metadata
        """
        result = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'logo_candidates': [],
            'error': None,
            'total_images': 0,
            'processed_images': 0
        }
        
        try:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Fetch the webpage
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all image tags
            img_tags = soup.find_all('img')
            result['total_images'] = len(img_tags)
            
            logo_candidates = []
            
            for img_tag in img_tags:
                try:
                    # Get image source
                    img_src = img_tag.get('src') or img_tag.get('data-src')
                    if not img_src:
                        continue
                    
                    # Convert relative URLs to absolute
                    img_url = urljoin(url, img_src)
                    
                    # Check if it's a valid image URL
                    parsed_url = urlparse(img_url)
                    if not any(parsed_url.path.lower().endswith(ext) for ext in self.image_extensions):
                        # Skip if no clear image extension (might be data URI or non-image)
                        if not img_url.startswith('data:image/'):
                            continue
                    
                    # Calculate logo likelihood score
                    logo_score = self._is_likely_logo(img_tag, img_url)
                    
                    # Only include images with some logo potential
                    if logo_score > 0:
                        logo_candidate = {
                            'url': img_url,
                            'alt_text': img_tag.get('alt', ''),
                            'class': img_tag.get('class', []),
                            'id': img_tag.get('id', ''),
                            'width': img_tag.get('width'),
                            'height': img_tag.get('height'),
                            'logo_score': logo_score,
                            'parent_info': self._get_parent_info(img_tag)
                        }
                        logo_candidates.append(logo_candidate)
                    
                    result['processed_images'] += 1
                    
                except Exception as e:
                    # Skip individual images that cause errors
                    continue
            
            # Sort by logo score (highest first)
            logo_candidates.sort(key=lambda x: x['logo_score'], reverse=True)
            result['logo_candidates'] = logo_candidates
            
        except requests.exceptions.RequestException as e:
            result['status'] = 'error'
            result['error'] = f"Request error: {str(e)}"
        except Exception as e:
            result['status'] = 'error'
            result['error'] = f"Parsing error: {str(e)}"
        
        return result
    
    def _get_parent_info(self, img_tag) -> Dict:
        """Get information about the image's parent elements."""
        parent_info = {
            'immediate_parent': None,
            'header_nav_context': False,
            'parent_classes': [],
            'parent_ids': []
        }
        
        if img_tag.parent:
            parent_info['immediate_parent'] = img_tag.parent.name
            
            # Check up to 3 levels for header/nav context
            parent = img_tag.parent
            levels = 0
            while parent and levels < 3:
                if parent.name:
                    if parent.name.lower() in ['header', 'nav', 'navbar']:
                        parent_info['header_nav_context'] = True
                    
                    parent_classes = parent.get('class', [])
                    parent_id = parent.get('id', '')
                    
                    if parent_classes:
                        parent_info['parent_classes'].extend(parent_classes)
                    if parent_id:
                        parent_info['parent_ids'].append(parent_id)
                
                parent = parent.parent
                levels += 1
        
        return parent_info
    
    def save_results(self, website_data: Dict, results: Dict, base_output_dir: str) -> str:
        """
        Save the logo extraction results to a structured directory.
        
        Args:
            website_data (Dict): Original website data with id and url
            results (Dict): Logo extraction results
            base_output_dir (str): Base directory for saving results
            
        Returns:
            str: Path to the saved results file
        """
        # Create directory structure
        website_id = website_data['id']
        website_dir = os.path.join(base_output_dir, 'logos', website_id)
        os.makedirs(website_dir, exist_ok=True)
        
        # Prepare complete results
        complete_results = {
            'website_info': website_data,
            'extraction_results': results,
            'saved_at': datetime.now().isoformat()
        }
        
        # Save results to JSON file
        results_file = os.path.join(website_dir, f"logo_extraction_{website_id}.json")
        with open(results_file, 'w') as f:
            json.dump(complete_results, f, indent=2)
        
        return results_file

def extract_logos_from_website(url: str, website_data: Dict = None) -> Dict:
    """
    Convenience function to extract logos from a single website.
    
    Args:
        url (str): Website URL
        website_data (Dict, optional): Additional website metadata
        
    Returns:
        Dict: Logo extraction results
    """
    agent = WebAgent()
    results = agent.extract_logo_images(url)
    
    if website_data:
        results['website_info'] = website_data
    
    return results