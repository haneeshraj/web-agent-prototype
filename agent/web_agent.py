"""
Web Agent for extracting and downloading images from business websites.
Focuses on finding potential logo images and other relevant business imagery.
"""

import os
import requests
import time
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import hashlib
from typing import List, Dict, Tuple
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from terminal_prettify import success, error, warning, info, processing


class WebAgent:
    """
    Web Agent for extracting images from business websites with focus on logos.
    """
    
    def __init__(self, headless: bool = True, timeout: int = 15):
        """
        Initialize the Web Agent with Selenium WebDriver.
        
        Args:
            headless (bool): Run browser in headless mode
            timeout (int): Page load timeout in seconds
        """
        self.timeout = timeout
        self.driver = None
        self._setup_driver(headless)
        
        # All possible image-related selectors - we want EVERYTHING
        self.image_selectors = [
            'img',           # All img tags
            'svg',           # All SVG elements  
            'image',         # SVG image elements
            'object[type*="image"]',     # Object tags with images
            'embed[type*="image"]',      # Embed tags with images
            'picture source',            # Picture element sources
            'video[poster]',             # Video poster images
            '*[style*="background-image"]',  # Elements with CSS background images
        ]
        
        # All image/media file extensions
        self.image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp', '.tiff', '.avif']
        
        # CSS background image pattern
        self.bg_image_pattern = r'background-image\s*:\s*url\(["\']?([^"\'()]+)["\']?\)'
        
        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def _setup_driver(self, headless: bool):
        """Setup Chrome WebDriver with appropriate options."""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-extensions')
            
            # Try different approaches for ChromeDriver setup
            try:
                # First try: Use ChromeDriverManager with cache disabled and specific version
                from webdriver_manager.chrome import ChromeDriverManager
                from webdriver_manager.utils import ChromeType
                
                # Get the latest stable version and install
                driver_path = ChromeDriverManager(
                    cache_valid_range=1,  # Force fresh download
                    chrome_type=ChromeType.GOOGLE
                ).install()
                
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
            except Exception as e1:
                warning(f"ChromeDriverManager failed: {str(e1)}")
                
                # Second try: Use Chrome without explicit service (let selenium find driver)
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                except Exception as e2:
                    warning(f"Default Chrome setup failed: {str(e2)}")
                    
                    # Third try: Try to find Chrome manually
                    import shutil
                    chrome_path = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chromium")
                    if chrome_path:
                        chrome_options.binary_location = chrome_path
                    
                    self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.set_page_load_timeout(self.timeout)
            self.driver.implicitly_wait(5)
            
            success("WebDriver initialized successfully")
            
        except Exception as e:
            error(f"Failed to initialize WebDriver: {str(e)}")
            error("Please ensure Chrome browser is installed and accessible")
            error("You may need to manually download ChromeDriver from https://chromedriver.chromium.org/")
            raise
    
    def extract_domain(self, url: str) -> str:
        """
        Extract domain name from URL for directory naming.
        
        Args:
            url (str): Website URL
            
        Returns:
            str: Clean domain name
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            # Replace dots and special characters with underscores
            domain = domain.replace('.', '_').replace('-', '_')
            return domain
        except:
            return "unknown_domain"
    
    def get_all_images(self, url: str) -> List[Dict]:
        """
        Extract ALL images from a website - img tags, SVGs, background images, etc.
        
        Args:
            url (str): Website URL
            
        Returns:
            List[Dict]: List of ALL image information dictionaries
        """
        images = []
        
        try:
            processing(f"Loading website: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Allow additional time for dynamic content
            time.sleep(3)
            
            # Extract images from all possible sources
            all_found_images = []
            
            # 1. Regular IMG tags
            all_found_images.extend(self._find_img_elements())
            
            # 2. SVG elements
            all_found_images.extend(self._find_svg_elements())
            
            # 3. CSS background images
            all_found_images.extend(self._find_background_images())
            
            # 4. Object/Embed tags
            all_found_images.extend(self._find_object_embed_images())
            
            # 5. Picture elements
            all_found_images.extend(self._find_picture_elements())
            
            # 6. Video poster images
            all_found_images.extend(self._find_video_posters())
            
            # Deduplicate based on source URL
            seen_urls = set()
            for img_info in all_found_images:
                if img_info and img_info.get('src') and img_info['src'] not in seen_urls:
                    images.append(img_info)
                    seen_urls.add(img_info['src'])
            
            success(f"Found {len(images)} unique images/media on {url}")
            
        except TimeoutException:
            error(f"Timeout loading {url}")
        except WebDriverException as e:
            error(f"WebDriver error for {url}: {str(e)}")
        except Exception as e:
            error(f"Unexpected error processing {url}: {str(e)}")
        
        return images
    
    def _find_img_elements(self) -> List[Dict]:
        """Find all IMG tag elements."""
        images = []
        try:
            img_elements = self.driver.find_elements(By.TAG_NAME, "img")
            for element in img_elements:
                img_info = self._extract_img_info(element)
                if img_info:
                    images.append(img_info)
        except Exception as e:
            warning(f"Error finding IMG elements: {str(e)}")
        return images
    
    def _find_svg_elements(self) -> List[Dict]:
        """Find all SVG elements and convert them to downloadable format."""
        svgs = []
        try:
            svg_elements = self.driver.find_elements(By.TAG_NAME, "svg")
            for i, element in enumerate(svg_elements):
                try:
                    # Get SVG content
                    svg_content = element.get_attribute('outerHTML')
                    if svg_content:
                        # Create SVG info
                        svg_info = {
                            'src': f"svg_element_{i}",  # Placeholder - will be replaced with data URL
                            'alt': element.get_attribute('alt') or element.get_attribute('title') or f'SVG Element {i}',
                            'title': element.get_attribute('title') or '',
                            'class': element.get_attribute('class') or '',
                            'id': element.get_attribute('id') or f'svg_{i}',
                            'width': element.get_attribute('width') or element.size.get('width'),
                            'height': element.get_attribute('height') or element.size.get('height'),
                            'type': 'svg',
                            'svg_content': svg_content
                        }
                        svgs.append(svg_info)
                except Exception as e:
                    warning(f"Error processing SVG {i}: {str(e)}")
        except Exception as e:
            warning(f"Error finding SVG elements: {str(e)}")
        return svgs
    
    def _find_background_images(self) -> List[Dict]:
        """Find CSS background images."""
        bg_images = []
        try:
            import re
            # Find all elements with style attribute
            elements_with_style = self.driver.find_elements(By.XPATH, "//*[@style]")
            
            for i, element in enumerate(elements_with_style):
                try:
                    style = element.get_attribute('style') or ''
                    matches = re.findall(self.bg_image_pattern, style, re.IGNORECASE)
                    
                    for match in matches:
                        bg_url = match.strip()
                        if bg_url and not bg_url.startswith('data:'):
                            # Convert relative URLs
                            if bg_url.startswith('//'):
                                bg_url = 'https:' + bg_url
                            elif bg_url.startswith('/'):
                                bg_url = urljoin(self.driver.current_url, bg_url)
                            
                            bg_info = {
                                'src': bg_url,
                                'alt': f'Background image {i}',
                                'title': element.get_attribute('title') or '',
                                'class': element.get_attribute('class') or '',
                                'id': element.get_attribute('id') or f'bg_img_{i}',
                                'width': None,
                                'height': None,
                                'type': 'background'
                            }
                            bg_images.append(bg_info)
                except Exception as e:
                    warning(f"Error processing background image {i}: {str(e)}")
        except Exception as e:
            warning(f"Error finding background images: {str(e)}")
        return bg_images
    
    def _find_object_embed_images(self) -> List[Dict]:
        """Find images in object and embed tags."""
        media_images = []
        try:
            # Object tags
            object_elements = self.driver.find_elements(By.TAG_NAME, "object")
            for i, element in enumerate(object_elements):
                data_url = element.get_attribute('data')
                type_attr = element.get_attribute('type') or ''
                if data_url and 'image' in type_attr.lower():
                    obj_info = self._create_media_info(data_url, f'object_{i}', 'object', element)
                    if obj_info:
                        media_images.append(obj_info)
            
            # Embed tags
            embed_elements = self.driver.find_elements(By.TAG_NAME, "embed")
            for i, element in enumerate(embed_elements):
                src_url = element.get_attribute('src')
                type_attr = element.get_attribute('type') or ''
                if src_url and 'image' in type_attr.lower():
                    embed_info = self._create_media_info(src_url, f'embed_{i}', 'embed', element)
                    if embed_info:
                        media_images.append(embed_info)
        except Exception as e:
            warning(f"Error finding object/embed images: {str(e)}")
        return media_images
    
    def _find_picture_elements(self) -> List[Dict]:
        """Find images in picture elements."""
        picture_images = []
        try:
            picture_elements = self.driver.find_elements(By.TAG_NAME, "picture")
            for i, picture in enumerate(picture_elements):
                # Get all source elements
                sources = picture.find_elements(By.TAG_NAME, "source")
                for j, source in enumerate(sources):
                    srcset = source.get_attribute('srcset')
                    if srcset:
                        # Parse srcset to get individual URLs
                        urls = [url.strip().split(' ')[0] for url in srcset.split(',')]
                        for k, url in enumerate(urls):
                            if url:
                                pic_info = self._create_media_info(url, f'picture_{i}_source_{j}_{k}', 'picture', source)
                                if pic_info:
                                    picture_images.append(pic_info)
                
                # Also check img inside picture
                img_element = picture.find_element(By.TAG_NAME, "img") if picture.find_elements(By.TAG_NAME, "img") else None
                if img_element:
                    img_info = self._extract_img_info(img_element)
                    if img_info:
                        img_info['type'] = 'picture_img'
                        picture_images.append(img_info)
        except Exception as e:
            warning(f"Error finding picture elements: {str(e)}")
        return picture_images
    
    def _find_video_posters(self) -> List[Dict]:
        """Find poster images from video elements."""
        poster_images = []
        try:
            video_elements = self.driver.find_elements(By.TAG_NAME, "video")
            for i, element in enumerate(video_elements):
                poster_url = element.get_attribute('poster')
                if poster_url:
                    poster_info = self._create_media_info(poster_url, f'video_poster_{i}', 'video_poster', element)
                    if poster_info:
                        poster_images.append(poster_info)
        except Exception as e:
            warning(f"Error finding video posters: {str(e)}")
        return poster_images
    
    def _create_media_info(self, url: str, alt_id: str, media_type: str, element) -> Dict:
        """Create media info dict for non-img elements."""
        if not url:
            return None
        
        # Convert relative URLs
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = urljoin(self.driver.current_url, url)
        
        return {
            'src': url,
            'alt': element.get_attribute('alt') or element.get_attribute('title') or alt_id,
            'title': element.get_attribute('title') or '',
            'class': element.get_attribute('class') or '',
            'id': element.get_attribute('id') or alt_id,
            'width': element.get_attribute('width') or element.size.get('width'),
            'height': element.get_attribute('height') or element.size.get('height'),
            'type': media_type
        }
    
    def _extract_img_info(self, element) -> Dict:
        """
        Extract information from an IMG element.
        
        Args:
            element: Selenium WebElement
            
        Returns:
            Dict: Image information or None if invalid
        """
        try:
            src = element.get_attribute('src')
            if not src:
                return None
            
            # Skip data URLs for now (can be processed later if needed)
            if src.startswith('data:'):
                return None
            
            # Convert relative URLs to absolute
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = urljoin(self.driver.current_url, src)
            
            # Get all available attributes
            alt = element.get_attribute('alt') or ''
            title = element.get_attribute('title') or ''
            class_name = element.get_attribute('class') or ''
            img_id = element.get_attribute('id') or ''
            
            # Try to get dimensions
            try:
                width = element.get_attribute('width') or element.size['width']
                height = element.get_attribute('height') or element.size['height']
            except:
                width = height = None
            
            # Get additional attributes that might be useful
            srcset = element.get_attribute('srcset') or ''
            sizes = element.get_attribute('sizes') or ''
            loading = element.get_attribute('loading') or ''
            
            return {
                'src': src,
                'alt': alt,
                'title': title,
                'class': class_name,
                'id': img_id,
                'width': width,
                'height': height,
                'srcset': srcset,
                'sizes': sizes,
                'loading': loading,
                'type': 'img'
            }
            
        except Exception as e:
            warning(f"Error extracting IMG info: {str(e)}")
            return None
    
    def _calculate_logo_score(self, alt: str, title: str, class_name: str, img_id: str, src: str) -> int:
        """
        Calculate a score for how likely an image is to be a logo.
        Higher score = more likely to be a logo.
        """
        score = 0
        text_to_check = f"{alt} {title} {class_name} {img_id} {src}".lower()
        
        logo_keywords = ['logo', 'brand', 'header', 'nav', 'site-title', 'company']
        for keyword in logo_keywords:
            if keyword in text_to_check:
                score += 10
        
        # Bonus for being in header/nav areas
        if any(word in text_to_check for word in ['header', 'nav', 'top', 'brand']):
            score += 5
        
        return score
    
    def download_image_or_svg(self, img_info: Dict, save_path: str) -> bool:
        """
        Download an image or save SVG content to local path.
        
        Args:
            img_info (Dict): Image information dictionary
            save_path (str): Local file path to save
            
        Returns:
            bool: Success status
        """
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Handle SVG content directly
            if img_info.get('type') == 'svg' and img_info.get('svg_content'):
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(img_info['svg_content'])
                return True
            
            # Handle regular image downloads
            img_url = img_info.get('src')
            if not img_url or img_url.startswith('svg_element_'):
                return False
                
            response = self.session.get(img_url, timeout=10, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            error(f"Failed to download {img_info.get('src', 'unknown')}: {str(e)}")
            return False
    
    def process_website(self, url: str, base_save_dir: str = "downloaded_images") -> Dict:
        """
        Process a website: extract all images and download them.
        
        Args:
            url (str): Website URL
            base_save_dir (str): Base directory for saving images
            
        Returns:
            Dict: Processing results
        """
        domain = self.extract_domain(url)
        website_dir = os.path.join(base_save_dir, domain)
        
        info(f"Processing website: {url} -> {domain}")
        
        # Extract all images
        images = self.get_all_images(url)
        
        if not images:
            warning(f"No images found on {url}")
            return {
                'url': url,
                'domain': domain,
                'total_images': 0,
                'downloaded_images': 0,
                'failed_downloads': 0,
                'image_types': {}
            }
        
        # Count image types
        image_types = {}
        for img in images:
            img_type = img.get('type', 'unknown')
            image_types[img_type] = image_types.get(img_type, 0) + 1
        
        downloaded = 0
        failed = 0
        
        for i, img in enumerate(images):
            try:
                # Generate filename based on type and source
                img_type = img.get('type', 'unknown')
                
                if img_type == 'svg':
                    extension = '.svg'
                    prefix = f"svg_{i:03d}"
                else:
                    img_url = img.get('src', '')
                    extension = os.path.splitext(urlparse(img_url).path)[1] or '.jpg'
                    prefix = f"{img_type}_{i:03d}"
                
                # Use hash to avoid duplicates and handle special characters
                if img.get('src'):
                    url_hash = hashlib.md5(str(img['src']).encode()).hexdigest()[:8]
                else:
                    url_hash = hashlib.md5(str(i).encode()).hexdigest()[:8]
                    
                filename = f"{prefix}_{url_hash}{extension}"
                save_path = os.path.join(website_dir, filename)
                
                if self.download_image_or_svg(img, save_path):
                    downloaded += 1
                    info(f"Downloaded: {filename} (type: {img_type})")
                else:
                    failed += 1
                    
            except Exception as e:
                error(f"Error processing image {i}: {str(e)}")
                failed += 1
        
        result = {
            'url': url,
            'domain': domain,
            'total_images': len(images),
            'downloaded_images': downloaded,
            'failed_downloads': failed,
            'image_types': image_types,
            'save_directory': website_dir
        }
        
        success(f"Completed {url}: {downloaded}/{len(images)} images downloaded")
        return result
    
    def close(self):
        """Close the WebDriver and session."""
        if hasattr(self, 'session'):
            self.session.close()
        if self.driver:
            try:
                self.driver.quit()
                success("WebDriver closed")
            except:
                pass  # Ignore errors during cleanup


# Convenience function for single website processing
def process_single_website(url: str, base_save_dir: str = "downloaded_images") -> Dict:
    """
    Process a single website and return results.
    
    Args:
        url (str): Website URL
        base_save_dir (str): Base directory for saving images
        
    Returns:
        Dict: Processing results
    """
    agent = WebAgent()
    try:
        return agent.process_website(url, base_save_dir)
    finally:
        agent.close()
