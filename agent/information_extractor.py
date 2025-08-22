import os
import json
import time
import base64
import re
import sys
import threading
from datetime import datetime
from urllib.parse import urlparse, urljoin, urlunparse
from typing import List, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests

# Import your utility functions
from utils.file_utils import load_website_data
from utils.terminal_prettify import success, error, warning, info, processing, completed, header
from utils.config import get_config
from agent.brand_image_detector import BrandImageDetector
from agent.mcc_classifier import MCCClassifier
from agent.address_extractor import AddressExtractor


class LoadingAnimation:
    """Simple loading animation for long-running tasks"""
    def __init__(self, message="Loading"):
        self.message = message
        self.running = False
        self.thread = None
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._animate)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        # Clear the line
        sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
        sys.stdout.flush()
        
    def _animate(self):
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while self.running:
            sys.stdout.write(f'\r{chars[i % len(chars)]} {self.message}...')
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1


def print_tree_item(text, level=1, is_last=False, status="processing"):
    """Print formatted tree-style output with proper indentation"""
    # Tree characters
    if level == 1:
        prefix = "    ├─ " if not is_last else "    └─ "
    elif level == 2:
        prefix = "       ├─ " if not is_last else "       └─ "
    else:
        prefix = "    " * level + ("├─ " if not is_last else "└─ ")
    
    # Status icons and colors
    if status == "processing":
        icon = "⏳"
        color = "\033[96m"  # Cyan
    elif status == "success":
        icon = "✓"
        color = "\033[92m"  # Green
    elif status == "warning":
        icon = "⚠"
        color = "\033[93m"  # Yellow
    elif status == "error":
        icon = "✗"
        color = "\033[91m"  # Red
    elif status == "info":
        icon = "ℹ"
        color = "\033[94m"  # Blue
    else:
        icon = "•"
        color = "\033[97m"  # White
    
    reset = "\033[0m"
    print(f"{color}{prefix}{icon} {text}{reset}")


def print_website_header(index, total, url):
    """Print website processing header"""
    print(f"\n\033[1m\033[96m⏳ [{index}/{total}] {url}\033[0m")


def suppress_chrome_logs():
    """Suppress Chrome GPU and other unwanted logs"""
    # Redirect stderr to devnull to suppress Chrome logs
    devnull = open(os.devnull, 'w')
    os.dup2(devnull.fileno(), sys.stderr.fileno())


class WebsiteInformationExtractor:
    def __init__(self):
        self.driver = None
        self.run_timestamp = None  # Will be set from loaded data
        self.base_data_dir = None  # Will be set from loaded data
        self.summary_data = []
        self.download_images_dir = None  # Will be set when needed
        
        # Load configuration
        self.config = get_config()
        self.website_delay = self.config.get('processing.website_delay_seconds', 60)
        self.rate_limit_delay = self.config.get('processing.rate_limit_delay_seconds', 10)
        
        # Initialize brand image detector and MCC classifier
        self.brand_image_detector = BrandImageDetector()
        self.mcc_classifier = MCCClassifier()
        self.address_extractor = AddressExtractor()
        
    def setup_driver(self):
        """Setup Chrome WebDriver with proper options for Windows"""
        try:
            info("Setting up Chrome WebDriver...")
            
            # Suppress Python warnings and TensorFlow messages
            import warnings
            warnings.filterwarnings("ignore")
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logs
            os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimizations logs
            
            # Suppress Chrome DevTools and other Chrome logs
            import subprocess
            
            chrome_options = Options()
            # Run in headless mode to avoid browser popup
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # Speed up loading
            
            # Comprehensive log suppression
            chrome_options.add_argument("--log-level=3")  # Suppress INFO, WARNING, ERROR
            chrome_options.add_argument("--silent")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--disable-dev-tools")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI,VizDisplayCompositor")

            # Disable GPU hardware acceleration
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            

            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            # Set Chrome logging preferences to suppress console output
            chrome_options.set_capability('goog:loggingPrefs', {'browser': 'OFF', 'driver': 'OFF', 'performance': 'OFF'})
            
            # Suppress stderr during Chrome startup
            original_stderr = sys.stderr
            sys.stderr = open(os.devnull, 'w')
            
            # Try multiple approaches to fix Windows WebDriver issue
            driver_path = None
            
            try:
                # Method 1: Try with explicit version and architecture
                print_tree_item("Attempting Method 1: ChromeDriverManager with explicit settings", level=1, status="info")
                driver_path = ChromeDriverManager().install()
                
                # Check if the downloaded file is actually executable
                if os.path.exists(driver_path):
                    # Try to make it executable (Windows permissions issue)
                    import stat
                    os.chmod(driver_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
                
                service = Service(driver_path, log_path=os.devnull)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
            except Exception as e1:
                print_tree_item(f"Method 1 failed: {e1}", level=1, status="warning")
                
                try:
                    # Method 2: Clean cache and try again
                    print_tree_item("Attempting Method 2: Clearing cache and reinstalling", level=1, status="info")
                    import shutil
                    
                    # Clear webdriver manager cache
                    cache_dir = os.path.join(os.path.expanduser("~"), ".wdm")
                    if os.path.exists(cache_dir):
                        shutil.rmtree(cache_dir)
                        print_tree_item("Cleared WebDriver cache", level=2, status="info")
                    
                    driver_path = ChromeDriverManager().install()
                    service = Service(driver_path, log_path=os.devnull)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    
                except Exception as e2:
                    print_tree_item(f"Method 2 failed: {e2}", level=1, status="warning")
                    
                    # Method 3: Try using system Chrome if available
                    print_tree_item("Attempting Method 3: Using system Chrome installation", level=1, status="info")
                    
                    # Common Chrome paths on Windows
                    chrome_paths = [
                        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                    ]
                    
                    chrome_binary = None
                    for path in chrome_paths:
                        if os.path.exists(path):
                            chrome_binary = path
                            break
                    
                    if chrome_binary:
                        chrome_options.binary_location = chrome_binary
                        print_tree_item(f"Found Chrome at: {chrome_binary}", level=2, status="info")
                        
                        # Try without specifying chromedriver path (let system find it)
                        try:
                            self.driver = webdriver.Chrome(options=chrome_options)
                        except:
                            # Last resort: download a specific version
                            driver_path = ChromeDriverManager(version="131.0.6778.85").install()
                            service = Service(driver_path, log_path=os.devnull)
                            self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    else:
                        raise Exception("Chrome browser not found on system")
            
            finally:
                # Restore stderr
                sys.stderr.close()
                sys.stderr = original_stderr
            
            # Test the driver
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            success("Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            error(f"Failed to initialize WebDriver: {e}")
            error("Troubleshooting suggestions:")
            error("1. Make sure Google Chrome is installed")
            error("2. Try running: pip uninstall webdriver-manager && pip install webdriver-manager")
            error("3. Clear cache manually: delete %USERPROFILE%\\.wdm folder")
            error("4. Try running as administrator")
            return False
    
    def get_domain_name(self, url: str) -> str:
        """Extract clean domain name from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain.replace('.', '_')
        except:
            return "unknown_domain"
    
    def clean_html(self, html_content: str) -> str:
        """Remove specified tags from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove CSS links and font links
        for link in soup.find_all('link'):
            href = link.get('href', '')
            rel = link.get('rel', [])
            if isinstance(rel, list):
                rel = ' '.join(rel).lower()
            else:
                rel = str(rel).lower()
            
            # Remove if href contains .css, font, or if rel contains stylesheet
            if (href and any(ext in href.lower() for ext in ['.css', 'font'])) or 'stylesheet' in rel:
                link.decompose()
        
        # Remove ALL script tags (including those with src links)
        for script in soup.find_all('script'):
            script.decompose()
        
        # Remove noscript tags
        for noscript in soup.find_all('noscript'):
            noscript.decompose()
        
        # Remove iframe tags
        for iframe in soup.find_all('iframe'):
            iframe.decompose()
        
        # Process style tags - keep only lines with background-image or image URLs
        for style in soup.find_all('style'):
            css_content = style.get_text()
            
            # Find lines that contain image references
            lines_with_images = []
            
            for line in css_content.split('\n'):
                line_stripped = line.strip()
                # Check for background-image, background, or url() containing image extensions
                if (re.search(r'background-image\s*:', line_stripped, re.IGNORECASE) or
                    re.search(r'background\s*:.*url\(', line_stripped, re.IGNORECASE) or
                    re.search(r'url\([^)]*\.(png|jpg|jpeg|gif|svg|webp|ico)', line_stripped, re.IGNORECASE)):
                    lines_with_images.append(line)
            
            if lines_with_images:
                # Keep the style tag but only with image-related CSS
                style.clear()
                style.string = '\n'.join(lines_with_images)
            else:
                # Remove the entire style tag if no images found
                style.decompose()
        
        # Convert back to string and clean up empty lines
        html_string = str(soup)
        
        # Remove excessive empty lines (more than 2 consecutive newlines)
        html_string = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_string)
        
        # Remove lines that only contain whitespace
        lines = html_string.split('\n')
        cleaned_lines = []
        for line in lines:
            # Keep the line if it's not just whitespace, or if it's a single newline for spacing
            if line.strip() or (not cleaned_lines or cleaned_lines[-1].strip()):
                cleaned_lines.append(line)
        
        # Join back and ensure no more than 2 consecutive empty lines
        html_string = '\n'.join(cleaned_lines)
        html_string = re.sub(r'\n\n\n+', '\n\n', html_string)
        
        return html_string
    
    def extract_images(self, url: str) -> List[Dict[str, Any]]:
        """Extract all image URLs from the page"""
        images_data = []
        
        try:
            # Find all img elements
            img_elements = self.driver.find_elements(By.TAG_NAME, "img")
            
            for idx, img in enumerate(img_elements):
                try:
                    src = img.get_attribute("src")
                    alt = img.get_attribute("alt") or ""
                    width = img.get_attribute("width") or "auto"
                    height = img.get_attribute("height") or "auto"
                    
                    if src:
                        # Convert relative URLs to absolute
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = urljoin(url, src)
                        elif not src.startswith(('http://', 'https://')):
                            src = urljoin(url, src)
                        
                        images_data.append({
                            "index": idx,
                            "src": src,
                            "alt": alt,
                            "width": width,
                            "height": height
                        })
                        
                except Exception as e:
                    warning(f"Error extracting image {idx}: {e}")
                    continue
            
            # Also check for background images in CSS
            try:
                elements_with_bg = self.driver.execute_script("""
                    var elements = [];
                    var all = document.querySelectorAll('*');
                    for (var i = 0; i < all.length; i++) {
                        var style = window.getComputedStyle(all[i]);
                        var bgImage = style.backgroundImage;
                        if (bgImage && bgImage !== 'none' && bgImage.includes('url(')) {
                            elements.push({
                                tagName: all[i].tagName,
                                className: all[i].className,
                                id: all[i].id,
                                backgroundImage: bgImage
                            });
                        }
                    }
                    return elements;
                """)
                
                for idx, element in enumerate(elements_with_bg):
                    bg_image = element['backgroundImage']
                    # Extract URL from CSS background-image
                    url_match = re.search(r'url\(["\']?([^"\']+)["\']?\)', bg_image)
                    if url_match:
                        bg_url = url_match.group(1)
                        if bg_url.startswith('//'):
                            bg_url = 'https:' + bg_url
                        elif bg_url.startswith('/'):
                            bg_url = urljoin(url, bg_url)
                        elif not bg_url.startswith(('http://', 'https://')):
                            bg_url = urljoin(url, bg_url)
                        
                        images_data.append({
                            "index": f"bg_{idx}",
                            "src": bg_url,
                            "alt": f"Background image from {element['tagName']}",
                            "width": "auto",
                            "height": "auto",
                            "element_info": element
                        })
            
            except Exception as e:
                warning(f"Error extracting background images: {e}")
        
        except Exception as e:
            error(f"Error extracting images: {e}")
        
        return images_data
    
    def is_likely_brand_image(self, src: str, alt_or_class: str) -> bool:
        """Simple heuristic to identify potential brand images (not used in output)"""
        brand_image_keywords = ['brand', 'header', 'nav', 'identity', 'company']
        text_to_check = (src + ' ' + alt_or_class).lower()
        return any(keyword in text_to_check for keyword in brand_image_keywords)
    
    def take_screenshot(self, domain_dir: str, domain_name: str) -> str:
        """Take a screenshot of the current page"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(domain_dir, f"screenshot_{domain_name}_{timestamp}.png")
            self.driver.save_screenshot(screenshot_path)
            return screenshot_path
        except Exception as e:
            return ""
    
    def download_brand_image(self, brand_image_url: str, domain_name: str, timestamp: str) -> str:
        """
        Download brand image from URL and save it locally.
        
        Args:
            brand_image_url (str): URL of the brand image
            domain_name (str): Domain name for filename
            timestamp (str): Timestamp for filename
            
        Returns:
            str: Local path where image was saved, empty string if failed
        """
        if not brand_image_url or not brand_image_url.startswith(('http://', 'https://')):
            return ""
        
        try:
            # Create download_images directory if it doesn't exist
            if not self.download_images_dir:
                self.download_images_dir = os.path.join(self.base_data_dir, "download_images")
                os.makedirs(self.download_images_dir, exist_ok=True)
            
            # Create filename: domain_name_timestamp.png
            filename = f"{domain_name}_{timestamp}.png"
            local_path = os.path.join(self.download_images_dir, filename)
            
            # Download the image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(brand_image_url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Save the image
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Return relative path from base_data_dir
            return local_path
            
        except requests.exceptions.RequestException as e:
            warning(f"Failed to download brand image from {brand_image_url}: {e}")
            return ""
        except Exception as e:
            warning(f"Error saving brand image: {e}")
            return ""
    
    def extract_website_information(self, url: str) -> Dict[str, Any]:
        """Extract information from a single website"""
        start_time = time.time()
        
        # Create domain-specific directory
        domain_name = self.get_domain_name(url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain_dir = os.path.join(self.base_data_dir, f"{domain_name}_{timestamp}")
        os.makedirs(domain_dir, exist_ok=True)
        
        extraction_data = {
            "url": url,
            "domain": domain_name,
            "timestamp": timestamp,
            "status": "failed",
            "error": None,
            "files_created": [],
            "page_title": "",
            "meta_description": "",
            "total_images": 0,
            "load_time_seconds": 0,
            "screenshot_path": "",
            "brand_image_detection": {},  # Will store brand image detection results
            "downloaded_brand_image_path": "",  # Brand image download path
            "company_name": "",  # Extracted company name
            "company_name_confidence": 0.0,  # Company name confidence
            "company_name_source": "",  # Where company name was found
            "mcc_classification": {},  # Will store MCC classification results
            "final_mcc_code": None,  # Final MCC code
            "mcc_confidence": 0.0,  # MCC classification confidence
            "address_extraction": {},  # Will store address extraction results
            "final_address": "",  # Final extracted address
            "address_confidence": 0.0,  # Address extraction confidence
            "address_source": "",  # Where address was found
        }
        
        try:
            # Navigate to the website
            print_tree_item("Loading website", level=1, status="processing")
            self.driver.get(url)
            
            # Wait for page to load (5 seconds as requested)
            time.sleep(5)
            
            # Take screenshot first
            screenshot_path = self.take_screenshot(domain_dir, domain_name)
            if screenshot_path:
                extraction_data["screenshot_path"] = screenshot_path
                extraction_data["files_created"].append(f"screenshot_{domain_name}_{timestamp}.png")
            
            # Get page title and meta description
            try:
                extraction_data["page_title"] = self.driver.title
                meta_desc_element = self.driver.find_element(By.CSS_SELECTOR, "meta[name='description']")
                extraction_data["meta_description"] = meta_desc_element.get_attribute("content")
            except:
                pass
            
            # Get and clean HTML
            html_content = self.driver.page_source
            cleaned_html = self.clean_html(html_content)
            
            # Save cleaned HTML
            html_file_path = os.path.join(domain_dir, "page.html")
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_html)
            extraction_data["files_created"].append("page.html")
            
            # Extract images
            images_data = self.extract_images(url)
            extraction_data["total_images"] = len(images_data)
            
            # Save images data
            images_file_path = os.path.join(domain_dir, "images.json")
            with open(images_file_path, 'w', encoding='utf-8') as f:
                json.dump(images_data, f, indent=2, ensure_ascii=False)
            extraction_data["files_created"].append("images.json")
            
            # Phase 1: Brand Detection & Initial Analysis
            print_tree_item("Brand detection & initial analysis", level=1, status="processing")
            
            # Start loading animation for brand detection
            brand_animation = LoadingAnimation("Analyzing brand images and extracting company info")
            brand_animation.start()
            
            try:
                brand_image_result = self.brand_image_detector.detect_brand_image(domain_dir, domain_name)
                extraction_data["brand_image_detection"] = brand_image_result
                brand_animation.stop()
                
                # Extract company name data from brand image detection result
                if brand_image_result.get('company_name'):
                    extraction_data["company_name"] = brand_image_result['company_name']
                    extraction_data["company_name_confidence"] = brand_image_result.get('company_name_confidence', 0.0)
                    extraction_data["company_name_source"] = brand_image_result.get('company_name_source', '')
                    print_tree_item(f"Company: {extraction_data['company_name']} (confidence: {extraction_data['company_name_confidence']:.2f})", level=2, status="success")
                else:
                    print_tree_item("Company name not identified", level=2, status="warning")
                
                # Handle brand image download
                if brand_image_result.get('brand_image_found') and brand_image_result.get('selected_image'):
                    brand_image_url = brand_image_result['selected_image'].get('src', '')
                    if brand_image_url:
                        print_tree_item(f"Downloading brand image: {brand_image_url[:50]}...", level=2, status="info")
                        downloaded_path = self.download_brand_image(brand_image_url, domain_name, timestamp)
                        if downloaded_path:
                            extraction_data["downloaded_brand_image_path"] = downloaded_path
                            print_tree_item("Brand image saved successfully", level=2, status="success")
                        else:
                            print_tree_item("Failed to download brand image", level=2, status="warning")
                
            except Exception as e:
                brand_animation.stop()
                print_tree_item(f"Brand detection failed: {str(e)}", level=2, status="error")
            
            # Extract initial address analysis from brand image detection result
            address_analysis = brand_image_result.get('address_analysis', {})
            location_context = brand_image_result.get('location_context', {})
            
            # Check if we found a good address in the combined analysis
            address_found_in_brand_analysis = False
            if address_analysis.get('addresses_found') and address_analysis.get('confidence') in ['high', 'medium']:
                address_found_in_brand_analysis = True
                extraction_data["final_address"] = address_analysis.get('primary_address', '')
                extraction_data["address_confidence"] = 0.8 if address_analysis.get('confidence') == 'high' else 0.6
                extraction_data["address_source"] = f"brand_analysis_{address_analysis.get('source', '')}"
                print_tree_item(f"Address found in brand analysis: {extraction_data['final_address']}", level=2, status="success")
            elif address_analysis.get('addresses_found'):
                print_tree_item(f"Found {len(address_analysis['addresses_found'])} potential addresses in brand analysis", level=2, status="info")
            
            # Check location context (with null safety)
            if location_context and (location_context.get('city') or location_context.get('state')):
                location_info = []
                if location_context.get('city') and location_context['city'].strip():
                    location_info.append(location_context['city'].strip())
                if location_context.get('state') and location_context['state'].strip():
                    location_info.append(location_context['state'].strip())
                if location_context.get('country') and location_context['country'].strip():
                    location_info.append(location_context['country'].strip())
                if location_info:
                    print_tree_item(f"Location context: {', '.join(location_info)}", level=2, status="info")
            
            # Save brand image detection result
            brand_image_file_path = self.brand_image_detector.save_brand_image_result(domain_dir, brand_image_result)
            if brand_image_file_path:
                extraction_data["files_created"].append("brand_image_detection.json")
            
            # Phase 2: MCC Classification
            print_tree_item("Business classification (MCC)", level=1, status="processing")
            
            mcc_animation = LoadingAnimation("Analyzing business type and determining MCC code")
            mcc_animation.start()
            
            try:
                mcc_result = self.mcc_classifier.classify_mcc(domain_dir, domain_name)
                extraction_data["mcc_classification"] = mcc_result
                mcc_animation.stop()
                
                # Show MCC stages with proper tree structure
                if mcc_result.get("stage1_result"):
                    stage1 = mcc_result["stage1_result"]
                    stage1_range = stage1.get('selected_category_range', 'Unknown range')
                    stage1_name = stage1.get('selected_category_name', '')
                    range_display = f"{stage1_range} - {stage1_name}" if stage1_name else stage1_range
                    print_tree_item(f"Stage 1 complete: {range_display}", level=2, status="success")
                
                if mcc_result.get("stage2_result"):
                    stage2 = mcc_result["stage2_result"]
                    print_tree_item(f"Stage 2: MCC code selected", level=2, status="success")
                
                # Extract key MCC results for easy access
                if mcc_result.get("classification_success"):
                    extraction_data["final_mcc_code"] = mcc_result.get("final_mcc")
                    extraction_data["mcc_confidence"] = mcc_result.get("final_confidence", 0.0)
                    
                    # Get MCC description from the result
                    mcc_description = mcc_result.get("final_mcc_description", f"MCC {extraction_data['final_mcc_code']}")
                    print_tree_item(f"Business MCC: {extraction_data['final_mcc_code']} - {mcc_description} (confidence: {extraction_data['mcc_confidence']:.2f})", level=2, status="success")
                else:
                    print_tree_item(f"MCC classification failed: {mcc_result.get('error', 'Unknown error')}", level=2, status="error")
                    
            except Exception as e:
                mcc_animation.stop()
                print_tree_item(f"MCC classification error: {str(e)}", level=2, status="error")
            
            # Save MCC classification result
            mcc_file_path = self.mcc_classifier.save_mcc_result(domain_dir, mcc_result)
            if mcc_file_path:
                extraction_data["files_created"].append("mcc_classification.json")
            
            # Phase 3: Address Extraction
            if address_found_in_brand_analysis:
                print_tree_item("Address extraction (already found in brand analysis)", level=1, status="success")
                # Create a minimal address result that matches the expected format
                address_result = {
                    'final_address': extraction_data["final_address"],
                    'final_confidence': extraction_data["address_confidence"], 
                    'final_source': extraction_data["address_source"],
                    'stage_0_result': location_context,
                    'stage_1_result': address_analysis,
                    'stage_2_result': None,
                    'reasoning': f"Address found during brand analysis with {address_analysis.get('confidence', 'unknown')} confidence",
                    'stages_completed': ['stage_0', 'stage_1'],
                    'optimized_extraction': True
                }
                extraction_data["address_extraction"] = address_result
                print_tree_item(f"Address: {extraction_data['final_address']} (confidence: {extraction_data['address_confidence']:.2f})", level=2, status="success")
                
                # Display source
                source_display = extraction_data["address_source"].replace("_", " ").replace("brand analysis ", "Brand analysis ")
                print_tree_item(f"Source: {source_display}", level=2, status="info")
            else:
                print_tree_item("Detailed address extraction", level=1, status="processing")
                
                address_animation = LoadingAnimation("Searching for business address information")
                address_animation.start()
                
                try:
                    company_name = extraction_data.get("company_name", "")
                    business_type = ""
                    
                    # Try to extract business type from MCC classification for better search context
                    if mcc_result.get("classification_success"):
                        stage1_result = mcc_result.get("stage1_result", {})
                        business_type = stage1_result.get("business_type_identified", "")
                    
                    # Pass the complete brand image result for optimization
                    address_result = self.address_extractor.extract_address(
                        domain_dir, domain_name, company_name, business_type,
                        brand_image_result=brand_image_result
                    )
                    extraction_data["address_extraction"] = address_result
                    address_animation.stop()
                    
                    # Show address extraction stages
                    stages_completed = address_result.get('stages_completed', [])
                    if 'stage_0' in stages_completed:
                        print_tree_item("Stage 0: Location context analysis complete", level=2, status="success")
                    if 'stage_1' in stages_completed:
                        print_tree_item("Stage 1: Website content analysis complete", level=2, status="success") 
                    if 'stage_2' in stages_completed:
                        print_tree_item("Stage 2: External search analysis complete", level=2, status="success")
                    
                    # Extract key address results for easy access
                    if address_result.get("final_address"):
                        extraction_data["final_address"] = address_result.get("final_address", "")
                        extraction_data["address_confidence"] = address_result.get("final_confidence", 0.0)
                        extraction_data["address_source"] = address_result.get("final_source", "")
                        
                        # Display address with confidence - handle both numeric and string confidence
                        confidence = extraction_data["address_confidence"]
                        if isinstance(confidence, (int, float)):
                            confidence_str = f"{confidence:.2f}"
                        else:
                            confidence_str = str(confidence)
                        print_tree_item(f"Address: {extraction_data['final_address']} (confidence: {confidence_str})", level=2, status="success")
                        
                        # Display source
                        source_display = extraction_data["address_source"].replace("_", " ").replace("search ", "SerpAPI ").replace("website", "Website content")
                        print_tree_item(f"Source: {source_display}", level=2, status="info")
                        
                        # Display coordinates if available
                        geocoding_result = address_result.get("geocoding_result", {})
                        if geocoding_result and geocoding_result.get("lat") and geocoding_result.get("lon"):
                            print_tree_item("Coordinates:", level=2, status="info")
                            print_tree_item(f"Latitude: {geocoding_result['lat']}", level=3, status="info")
                            print_tree_item(f"Longitude: {geocoding_result['lon']}", level=3, status="info")
                    else:
                        print_tree_item(f"No address found: {address_result.get('reasoning', 'Unknown reason')}", level=2, status="warning")
                        
                except Exception as e:
                    address_animation.stop()
                    print_tree_item(f"Address extraction error: {str(e)}", level=2, status="error")
            
            # Save address extraction result
            address_file_path = self.address_extractor.save_address_result(domain_dir, address_result)
            if address_file_path:
                extraction_data["files_created"].append("address_extraction.json")
            
            # Rate limiting with better display
            print_tree_item(f"Rate limit delay ({self.rate_limit_delay} seconds)", level=1, status="info")
            time.sleep(self.rate_limit_delay)
            
            extraction_data["status"] = "success"
            extraction_data["load_time_seconds"] = round(time.time() - start_time, 2)
            
            # Final summary
            print_tree_item("Extraction Summary:", level=1, status="success")
            
            if brand_image_result.get('brand_image_found'):
                print_tree_item(f"Brand image: Detected ({brand_image_result.get('confidence', 'unknown')} confidence)", level=2, status="success")
            else:
                print_tree_item("Brand image: Not found", level=2, status="warning")
            
            if extraction_data["final_mcc_code"]:
                print_tree_item(f"MCC: {extraction_data['final_mcc_code']}", level=2, status="success")
            else:
                print_tree_item("MCC: Classification failed", level=2, status="warning")
            
            if extraction_data["final_address"]:
                source_display = extraction_data["address_source"].replace("_", " ").replace("search ", "search: ")
                print_tree_item(f"Address: Found via {source_display}", level=2, status="success")
            else:
                print_tree_item("Address: Not found", level=2, status="warning")
                
            print_tree_item(f"Files: {domain_name}_{timestamp}/ • {len(images_data)} images", level=2, status="info")
            
        except TimeoutException:
            error_msg = f"⏱️ Timeout loading {url}"
            print_tree_item(error_msg, level=1, status="error")
            extraction_data["error"] = error_msg
            
        except WebDriverException as e:
            error_msg = f"🚫 WebDriver error: {url}"
            print_tree_item(error_msg, level=1, status="error")
            extraction_data["error"] = error_msg
            
        except Exception as e:
            error_msg = f"❌ Failed: {url}"
            print_tree_item(error_msg, level=1, status="error")
            extraction_data["error"] = error_msg
        
        extraction_data["load_time_seconds"] = round(time.time() - start_time, 2)
        return extraction_data
    
    def save_summary(self):
        """Save summary data to JSON file"""
        summary_file_path = os.path.join(self.base_data_dir, "summary.json")
        
        # Calculate company name statistics
        companies_identified = sum(1 for site in self.summary_data if site.get("company_name", ""))
        
        # Convert string confidence values to numeric for averaging
        # Calculate confidence statistics
        companies_identified = sum(1 for site in self.summary_data if site.get("company_name", ""))
        
        average_company_confidence = 0.0
        if companies_identified > 0:
            total_confidence = sum(site.get("company_name_confidence", 0.0) for site in self.summary_data if site.get("company_name", ""))
            average_company_confidence = round(total_confidence / companies_identified, 3)
        
        # Calculate address statistics
        addresses_found = sum(1 for site in self.summary_data if site.get("final_address", ""))
        average_address_confidence = 0.0
        if addresses_found > 0:
            total_address_confidence = sum(site.get("address_confidence", 0.0) for site in self.summary_data if site.get("final_address", ""))
            average_address_confidence = round(total_address_confidence / addresses_found, 3)
        
        # Calculate token usage statistics
        total_input_tokens = 0
        total_output_tokens = 0
        total_tokens = 0
        
        for site in self.summary_data:
            # Brand image detection tokens
            brand_metadata = site.get("brand_image_detection", {}).get("analysis_metadata", {})
            if brand_metadata.get("tokens_used"):
                total_tokens += brand_metadata["tokens_used"]
            
            # MCC classification tokens (if available)
            mcc_metadata = site.get("mcc_metadata", {})
            if mcc_metadata.get("tokens_used"):
                total_tokens += mcc_metadata["tokens_used"]
            
            # Address extraction tokens (if available)
            address_metadata = site.get("address_metadata", {})
            if address_metadata.get("tokens_used"):
                total_tokens += address_metadata["tokens_used"]
        
        summary = {
            "run_timestamp": self.run_timestamp,
            "total_websites": len(self.summary_data),
            "successful_extractions": sum(1 for site in self.summary_data if site["status"] == "success"),
            "failed_extractions": sum(1 for site in self.summary_data if site["status"] == "failed"),
            "total_images_found": sum(site.get("total_images", 0) for site in self.summary_data),
            "brand_images_detected": sum(1 for site in self.summary_data if site.get("brand_image_detection", {}).get("brand_image_found", False)),
            "brand_images_downloaded": sum(1 for site in self.summary_data if site.get("downloaded_brand_image_path", "")),
            "companies_identified": companies_identified,
            "average_company_confidence": average_company_confidence,
            "mcc_classifications_successful": sum(1 for site in self.summary_data if site.get("final_mcc_code") is not None),
            "mcc_classifications_failed": sum(1 for site in self.summary_data if site.get("final_mcc_code") is None and site["status"] == "success"),
            "average_mcc_confidence": round(sum(site.get("mcc_confidence", 0.0) for site in self.summary_data if site.get("mcc_confidence", 0.0) > 0) / max(1, sum(1 for site in self.summary_data if site.get("mcc_confidence", 0.0) > 0)), 3),
            "addresses_found": addresses_found,
            "average_address_confidence": average_address_confidence,
            "addresses_from_website": sum(1 for site in self.summary_data if site.get("address_source", "").startswith("website")),
            "addresses_from_search": sum(1 for site in self.summary_data if site.get("address_source", "").startswith("search")),
            "average_load_time": round(sum(site.get("load_time_seconds", 0) for site in self.summary_data) / len(self.summary_data), 2) if self.summary_data else 0,
            "token_usage": {
                "total_tokens": total_tokens,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens
            },
            "websites": self.summary_data
        }
        
        with open(summary_file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Summary saved silently
        
        # Create brand image summary, company summary, MCC summary, and address summary
        self.save_brand_image_summary()
        self.save_company_summary()
        self.save_mcc_summary()
        self.save_address_summary()
        
        return summary_file_path
    
    def save_brand_image_summary(self):
        """Save brand image-specific summary to a separate JSON file"""
        brand_image_summary_path = os.path.join(self.base_data_dir, "brand_image_summary.json")
        
        brand_image_summary = []
        
        for site in self.summary_data:
            brand_image_detection = site.get("brand_image_detection", {})
            
            # Get brand image URL from selected_image (only if brand image was actually found)
            brand_image_url = ""
            if brand_image_detection.get("brand_image_found") and brand_image_detection.get("selected_image"):
                brand_image_url = brand_image_detection["selected_image"].get("src", "")
            
            # Get downloaded brand image path
            downloaded_brand_image_path = site.get("downloaded_brand_image_path", "")
            
            # Create entry for both successful extractions and failed ones
            brand_image_entry = {
                "website": site["url"],
                "brand_image_url": brand_image_url,
                "downloaded_brand_image_path": downloaded_brand_image_path,
                "reasoning": brand_image_detection.get("reasoning", "Website scraping failed - no analysis performed" if site["status"] == "failed" else "No brand image analysis performed"),
                "confidence": brand_image_detection.get("confidence", "none"),
                "company_name": site.get("company_name", ""),
                "company_name_confidence": site.get("company_name_confidence", 0.0)
            }
            
            brand_image_summary.append(brand_image_entry)
        
        with open(brand_image_summary_path, 'w', encoding='utf-8') as f:
            json.dump(brand_image_summary, f, indent=2, ensure_ascii=False)
        
        # Brand image summary saved silently
        return brand_image_summary_path
    
    def save_company_summary(self):
        """Save company-specific summary to a separate JSON file"""
        company_summary_path = os.path.join(self.base_data_dir, "company_summary.json")
        
        company_summary = []
        
        for site in self.summary_data:
            brand_image_detection = site.get("brand_image_detection", {})
            
            # Create entry for both successful and failed extractions
            company_entry = {
                "website": site["url"],
                "company_name": site.get("company_name", ""),
                "company_name_confidence": site.get("company_name_confidence", 0.0),
                "company_name_source": site.get("company_name_source", ""),
                "alternative_names": brand_image_detection.get("alternative_names", []),
                "extraction_success": bool(site.get("company_name", "")),
                "brand_image_found": brand_image_detection.get("brand_image_found", False),
                "error": "" if site["status"] == "success" else "Website scraping failed"
            }
            
            company_summary.append(company_entry)
        
        with open(company_summary_path, 'w', encoding='utf-8') as f:
            json.dump(company_summary, f, indent=2, ensure_ascii=False)
        
        # Company summary saved silently
        return company_summary_path
    
    def save_mcc_summary(self):
        """Save MCC-specific summary to a separate JSON file"""
        mcc_summary_path = os.path.join(self.base_data_dir, "mcc_summary.json")
        
        mcc_summary = []
        
        for site in self.summary_data:
            mcc_classification = site.get("mcc_classification", {})
            
            # Create entry for both successful and failed classifications
            mcc_entry = {
                "website": site["url"],
                "company_name": site.get("company_name", ""),
                "final_mcc_code": site.get("final_mcc_code"),
                "final_mcc_description": mcc_classification.get("final_mcc_description", ""),
                "confidence": site.get("mcc_confidence", 0.0),
                "classification_success": mcc_classification.get("classification_success", False),
                "stage1_category": mcc_classification.get("stage1_result", {}).get("selected_category_name", ""),
                "stage1_range": mcc_classification.get("stage1_result", {}).get("selected_category_range", ""),
                "error": mcc_classification.get("error", "" if site["status"] == "success" else "Website scraping failed"),
                "business_type_identified": mcc_classification.get("stage1_result", {}).get("business_type_identified", "")
            }
            
            mcc_summary.append(mcc_entry)
        
        with open(mcc_summary_path, 'w', encoding='utf-8') as f:
            json.dump(mcc_summary, f, indent=2, ensure_ascii=False)
        
        # MCC summary saved silently
        return mcc_summary_path
    
    def save_address_summary(self):
        """Save address-specific summary to a separate JSON file"""
        address_summary_path = os.path.join(self.base_data_dir, "address_summary.json")
        
        address_summary = []
        
        for site in self.summary_data:
            address_extraction = site.get("address_extraction", {})
            
            # Create entry for both successful extractions and failed ones
            address_entry = {
                "website": site["url"],
                "final_address": site.get("final_address", ""),
                "address_confidence": site.get("address_confidence", 0.0),
                "address_source": site.get("address_source", ""),
                "extraction_method": address_extraction.get("address_extraction_method", ""),
                "website_analysis": {
                    "address_found": address_extraction.get("website_analysis", {}).get("address_found_in_website", False),
                    "confidence": address_extraction.get("website_analysis", {}).get("address_confidence", 0.0),
                    "source": address_extraction.get("website_analysis", {}).get("address_source", ""),
                    "reasoning": address_extraction.get("website_analysis", {}).get("reasoning", "Website scraping failed" if site["status"] == "failed" else "No website analysis performed")
                },
                "search_analysis": {
                    "address_found": address_extraction.get("search_analysis", {}).get("address_found", False),
                    "confidence": address_extraction.get("search_analysis", {}).get("address_confidence", 0.0),
                    "source": address_extraction.get("search_analysis", {}).get("address_source", ""),
                    "reasoning": address_extraction.get("search_analysis", {}).get("reasoning", "No search analysis performed")
                },
                "company_name_used": address_extraction.get("company_name_used", ""),
                "business_type_used": address_extraction.get("business_type_used", ""),
                "error": address_extraction.get("error", "" if site["status"] == "success" else "Website scraping failed"),
                "extract_status": site["status"]
            }
            
            address_summary.append(address_entry)
        
        with open(address_summary_path, 'w', encoding='utf-8') as f:
            json.dump(address_summary, f, indent=2, ensure_ascii=False)
        
        # Address summary saved silently
        return address_summary_path
    
    def run(self):
        """Main execution method"""
        header("Business Insights - AI-Powered Business Intelligence Extraction")
        
        # Display LLM configuration
        try:
            from utils.config import get_model_config
            model_config = get_model_config("classifier-agent")
            model_name = model_config.get('model', 'Unknown')
            provider = "Unknown"
            
            # Determine provider based on model name
            if 'gpt' in model_name.lower():
                provider = "OpenAI"
            elif 'claude' in model_name.lower() or 'anthropic' in model_name.lower():
                provider = "Anthropic"
            elif 'gemini' in model_name.lower() or 'google' in model_name.lower():
                provider = "Google"
            elif 'llama' in model_name.lower():
                provider = "Meta"
            else:
                provider = "Custom"
            
            info(f"AI Model: {provider} {model_name}")
        except Exception:
            info("AI Model: Configuration not available")
        
        # Setup WebDriver
        if not self.setup_driver():
            return
        
        try:
            # Load websites from file
            json_file_path, run_data_dir = load_website_data()
            
            if not json_file_path or not run_data_dir:
                error("No websites loaded. Check data/load_websites.txt file.")
                return
            
            # Set the run directory and timestamp from the loaded data
            self.base_data_dir = run_data_dir
            self.run_timestamp = os.path.basename(run_data_dir).replace("run_", "")
            
            # Load the website data
            with open(json_file_path, 'r') as f:
                websites_data = json.load(f)
            
            # Process each website with cleaner output
            for i, website_info in enumerate(websites_data, 1):
                url = website_info["url"]
                
                # Display website header with index
                print_website_header(i, len(websites_data), url)
                
                extract_result = self.extract_website_information(url)
                self.summary_data.append(extract_result)
                
                # Delay between website processing (configurable)
                if i < len(websites_data):
                    if self.website_delay > 0:
                        print_tree_item(f"Website processing delay ({self.website_delay} seconds)", level=1, status="info")
                        time.sleep(self.website_delay)
            
            # Save summary
            summary_path = self.save_summary()
            
            # Final report - simplified
            header("Extraction Complete")
            completed(f"Processed: {len(self.summary_data)} websites")
            completed(f"Success rate: {sum(1 for site in self.summary_data if site['status'] == 'success')}/{len(self.summary_data)}")
            
            # Key metrics
            brands_found = sum(1 for site in self.summary_data if site.get('brand_image_detection', {}).get('brand_image_found', False))
            mcc_found = sum(1 for site in self.summary_data if site.get('final_mcc_code') is not None)
            addresses_found = sum(1 for site in self.summary_data if site.get("final_address", ""))
            
            # Calculate total tokens
            total_tokens = 0
            for site in self.summary_data:
                # Brand image detection tokens
                brand_metadata = site.get("brand_image_detection", {}).get("analysis_metadata", {})
                if brand_metadata.get("tokens_used"):
                    total_tokens += brand_metadata["tokens_used"]
                
                # MCC classification tokens (if available)
                mcc_metadata = site.get("mcc_metadata", {})
                if mcc_metadata.get("tokens_used"):
                    total_tokens += mcc_metadata["tokens_used"]
                
                # Address extraction tokens (if available)
                address_metadata = site.get("address_metadata", {})
                if address_metadata.get("tokens_used"):
                    total_tokens += address_metadata["tokens_used"]
            
            completed(f"Brand images: {brands_found} detected")
            completed(f"MCC codes: {mcc_found} classified") 
            completed(f"Addresses: {addresses_found} extracted")
            if total_tokens > 0:
                completed(f"Total tokens used: {total_tokens:,}")
            completed(f"Summary: {summary_path}")
            
        except KeyboardInterrupt:
            warning("Scraping interrupted by user")
            
        except Exception as e:
            error(f"Unexpected error during execution: {e}")
            
        finally:
            # Clean up
            if self.driver:
                info("Closing WebDriver...")
                self.driver.quit()
                success("WebDriver closed successfully")