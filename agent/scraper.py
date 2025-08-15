import os
import json
import time
import base64
import re
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
from agent.logo_detector import LogoDetector
from agent.mcc_classifier import MCCClassifier
from agent.address_extractor import AddressExtractor


class WebsiteScraper:
    def __init__(self):
        self.driver = None
        self.run_timestamp = None  # Will be set from loaded data
        self.base_data_dir = None  # Will be set from loaded data
        self.summary_data = []
        self.download_images_dir = None  # Will be set when needed
        
        # Initialize logo detector and MCC classifier
        self.logo_detector = LogoDetector()
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
            
            # Suppress Chrome DevTools and other Chrome logs by redirecting stderr
            import sys
            from contextlib import redirect_stderr
            from io import StringIO
            
            chrome_options = Options()
            # Don't use headless mode as requested
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # Speed up loading
            
            # Suppress Chrome logs and warnings
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
            
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            # Set Chrome logging preferences to suppress console output
            chrome_options.set_capability('goog:loggingPrefs', {'browser': 'OFF', 'driver': 'OFF', 'performance': 'OFF'})
            
            # Try multiple approaches to fix Windows WebDriver issue
            driver_path = None
            
            try:
                # Method 1: Try with explicit version and architecture
                info("Attempting Method 1: ChromeDriverManager with explicit settings...")
                driver_path = ChromeDriverManager().install()
                
                # Check if the downloaded file is actually executable
                if os.path.exists(driver_path):
                    # Try to make it executable (Windows permissions issue)
                    import stat
                    os.chmod(driver_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
                
                # Suppress stderr during WebDriver initialization
                with redirect_stderr(StringIO()):
                    service = Service(driver_path, log_path=os.devnull)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
            except Exception as e1:
                warning(f"Method 1 failed: {e1}")
                
                try:
                    # Method 2: Clean cache and try again
                    info("Attempting Method 2: Clearing cache and reinstalling...")
                    import shutil
                    import tempfile
                    
                    # Clear webdriver manager cache
                    cache_dir = os.path.join(os.path.expanduser("~"), ".wdm")
                    if os.path.exists(cache_dir):
                        shutil.rmtree(cache_dir)
                        info("Cleared WebDriver cache")
                    
                    driver_path = ChromeDriverManager().install()
                    
                    service = Service(driver_path, log_path=os.devnull)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    
                except Exception as e2:
                    warning(f"Method 2 failed: {e2}")
                    
                    # Method 3: Try using system Chrome if available
                    info("Attempting Method 3: Using system Chrome installation...")
                    
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
                        info(f"Found Chrome at: {chrome_binary}")
                        
                        # Try without specifying chromedriver path (let system find it)
                        try:
                            with redirect_stderr(StringIO()):
                                self.driver = webdriver.Chrome(options=chrome_options)
                        except:
                            # Last resort: download a specific version
                            driver_path = ChromeDriverManager(version="131.0.6778.85").install()
                            service = Service(driver_path, log_path=os.devnull)
                            with redirect_stderr(StringIO()):
                                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    else:
                        raise Exception("Chrome browser not found on system")
            
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
    
    def is_likely_logo(self, src: str, alt_or_class: str) -> bool:
        """Simple heuristic to identify potential logos (not used in output)"""
        logo_keywords = ['logo', 'brand', 'header', 'nav', 'identity', 'company']
        text_to_check = (src + ' ' + alt_or_class).lower()
        return any(keyword in text_to_check for keyword in logo_keywords)
    
    def take_screenshot(self, domain_dir: str, domain_name: str) -> str:
        """Take a screenshot of the current page"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(domain_dir, f"screenshot_{domain_name}_{timestamp}.png")
            self.driver.save_screenshot(screenshot_path)
            return screenshot_path
        except Exception as e:
            return ""
    
    def download_logo_image(self, logo_url: str, domain_name: str, timestamp: str) -> str:
        """
        Download logo image from URL and save it locally.
        
        Args:
            logo_url (str): URL of the logo image
            domain_name (str): Domain name for filename
            timestamp (str): Timestamp for filename
            
        Returns:
            str: Local path where image was saved, empty string if failed
        """
        if not logo_url or not logo_url.startswith(('http://', 'https://')):
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
            
            response = requests.get(logo_url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Save the image
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Return relative path from base_data_dir
            return local_path
            
        except requests.exceptions.RequestException as e:
            warning(f"Failed to download logo from {logo_url}: {e}")
            return ""
        except Exception as e:
            warning(f"Error saving logo image: {e}")
            return ""
    
    def scrape_website(self, url: str) -> Dict[str, Any]:
        """Scrape a single website"""
        start_time = time.time()
        processing(f"Scraping: {url}")
        
        # Create domain-specific directory
        domain_name = self.get_domain_name(url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain_dir = os.path.join(self.base_data_dir, f"{domain_name}_{timestamp}")
        os.makedirs(domain_dir, exist_ok=True)
        
        scrape_data = {
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
            "logo_detection": {},  # Will store logo detection results
            "downloaded_logo_path": "",  # Logo download path
            "merchant_name": "",  # Extracted merchant name
            "merchant_name_confidence": 0.0,  # Merchant name confidence
            "merchant_name_source": "",  # Where merchant name was found
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
            self.driver.get(url)
            
            # Wait for page to load (5 seconds as requested)
            time.sleep(5)
            
            # Take screenshot first
            screenshot_path = self.take_screenshot(domain_dir, domain_name)
            if screenshot_path:
                scrape_data["screenshot_path"] = screenshot_path
                scrape_data["files_created"].append(f"screenshot_{domain_name}_{timestamp}.png")
            
            # Get page title and meta description
            try:
                scrape_data["page_title"] = self.driver.title
                meta_desc_element = self.driver.find_element(By.CSS_SELECTOR, "meta[name='description']")
                scrape_data["meta_description"] = meta_desc_element.get_attribute("content")
            except:
                pass
            
            # Get and clean HTML
            html_content = self.driver.page_source
            cleaned_html = self.clean_html(html_content)
            
            # Save cleaned HTML
            html_file_path = os.path.join(domain_dir, "page.html")
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_html)
            scrape_data["files_created"].append("page.html")
            
            # Extract images
            images_data = self.extract_images(url)
            scrape_data["total_images"] = len(images_data)
            
            # Save images data
            images_file_path = os.path.join(domain_dir, "images.json")
            with open(images_file_path, 'w', encoding='utf-8') as f:
                json.dump(images_data, f, indent=2, ensure_ascii=False)
            scrape_data["files_created"].append("images.json")
            
            # Perform logo detection using all three files (screenshot, HTML, images)
            info("   🔍 Detecting logo & extracting merchant name...")
            logo_result = self.logo_detector.detect_logo(domain_dir, domain_name)
            scrape_data["logo_detection"] = logo_result
            
            # Extract merchant name data from logo detection result
            if logo_result.get('merchant_name'):
                scrape_data["merchant_name"] = logo_result['merchant_name']
                scrape_data["merchant_name_confidence"] = logo_result.get('merchant_name_confidence', 0.0)
                scrape_data["merchant_name_source"] = logo_result.get('merchant_name_source', '')
                success(f"   🏢 Merchant: {scrape_data['merchant_name']} (confidence: {scrape_data['merchant_name_confidence']:.2f})")
            else:
                warning("   🏢 Merchant name not identified")
            
            # Download logo image if one was detected
            if logo_result.get('logo_found') and logo_result.get('selected_image'):
                logo_url = logo_result['selected_image'].get('src', '')
                if logo_url:
                    info(f"   📥 Downloading logo: {logo_url}")
                    downloaded_path = self.download_logo_image(logo_url, domain_name, timestamp)
                    if downloaded_path:
                        scrape_data["downloaded_logo_path"] = downloaded_path
                        success(f"   ✅ Logo saved: {downloaded_path}")
                    else:
                        warning("   ❌ Failed to download logo")
            
            # Save logo detection result
            logo_file_path = self.logo_detector.save_logo_result(domain_dir, logo_result)
            if logo_file_path:
                scrape_data["files_created"].append("logo_detection.json")
            
            # Perform MCC classification
            info("   🏷️  Classifying MCC code...")
            mcc_result = self.mcc_classifier.classify_mcc(domain_dir, domain_name)
            scrape_data["mcc_classification"] = mcc_result
            
            # Extract key MCC results for easy access
            if mcc_result.get("classification_success"):
                scrape_data["final_mcc_code"] = mcc_result.get("final_mcc")
                scrape_data["mcc_confidence"] = mcc_result.get("final_confidence", 0.0)
                success(f"   🎯 MCC: {scrape_data['final_mcc_code']} (confidence: {scrape_data['mcc_confidence']:.2f})")
            else:
                warning(f"   ❌ MCC classification failed: {mcc_result.get('error', 'Unknown error')}")
            
            # Save MCC classification result
            mcc_file_path = self.mcc_classifier.save_mcc_result(domain_dir, mcc_result)
            if mcc_file_path:
                scrape_data["files_created"].append("mcc_classification.json")
            
            # Perform address extraction
            info("   📍 Extracting business address...")
            merchant_name = scrape_data.get("merchant_name", "")
            business_type = ""
            
            # Try to extract business type from MCC classification for better search context
            if mcc_result.get("classification_success"):
                stage1_result = mcc_result.get("stage1_result", {})
                business_type = stage1_result.get("business_type_identified", "")
                
            address_result = self.address_extractor.extract_address(
                domain_dir, domain_name, merchant_name, business_type
            )
            scrape_data["address_extraction"] = address_result
            
            # Extract key address results for easy access
            if address_result.get("final_address"):
                scrape_data["final_address"] = address_result.get("final_address", "")
                scrape_data["address_confidence"] = address_result.get("final_confidence", 0.0)
                scrape_data["address_source"] = address_result.get("final_source", "")
                success(f"   🏠 Address: {scrape_data['final_address']} (confidence: {scrape_data['address_confidence']:.2f})")
            else:
                warning(f"   ❌ No address found: {address_result.get('reasoning', 'Unknown reason')}")
            
            # Save address extraction result
            address_file_path = self.address_extractor.save_address_result(domain_dir, address_result)
            if address_file_path:
                scrape_data["files_created"].append("address_extraction.json")
            
            # Add delay to respect rate limits
            info("   ⏳ Rate limit delay...")
            time.sleep(10)
            
            scrape_data["status"] = "success"
            scrape_data["load_time_seconds"] = round(time.time() - start_time, 2)
            
            success(f"✅ {url}")
            
            # Show summary of all extractions
            if logo_result.get('logo_found'):
                info(f"   🎯 Logo detected ({logo_result.get('confidence', 'unknown')} confidence)")
            else:
                info(f"   ❌ No logo found")
            
            if scrape_data["final_mcc_code"]:
                info(f"   🏷️  MCC: {scrape_data['final_mcc_code']}")
            else:
                info(f"   🏷️  MCC: Classification failed")
            
            if scrape_data["final_address"]:
                info(f"   📍 Address: Found via {scrape_data['address_source']}")
            else:
                info(f"   📍 Address: Not found")
                
            info(f"   📁 {domain_name}_{timestamp}/ • {len(images_data)} images")
            
        except TimeoutException:
            error_msg = f"⏱️ Timeout loading {url}"
            error(error_msg)
            scrape_data["error"] = error_msg
            
        except WebDriverException as e:
            error_msg = f"🚫 WebDriver error: {url}"
            error(error_msg)
            scrape_data["error"] = error_msg
            
        except Exception as e:
            error_msg = f"❌ Failed: {url}"
            error(error_msg)
            scrape_data["error"] = error_msg
        
        scrape_data["load_time_seconds"] = round(time.time() - start_time, 2)
        return scrape_data
    
    def save_summary(self):
        """Save summary data to JSON file"""
        summary_file_path = os.path.join(self.base_data_dir, "summary.json")
        
        # Calculate merchant name statistics
        merchants_identified = sum(1 for site in self.summary_data if site.get("merchant_name", ""))
        average_merchant_confidence = 0.0
        if merchants_identified > 0:
            total_confidence = sum(site.get("merchant_name_confidence", 0.0) for site in self.summary_data if site.get("merchant_name", ""))
            average_merchant_confidence = round(total_confidence / merchants_identified, 3)
        
        # Calculate address statistics
        addresses_found = sum(1 for site in self.summary_data if site.get("final_address", ""))
        average_address_confidence = 0.0
        if addresses_found > 0:
            total_address_confidence = sum(site.get("address_confidence", 0.0) for site in self.summary_data if site.get("final_address", ""))
            average_address_confidence = round(total_address_confidence / addresses_found, 3)
        
        summary = {
            "run_timestamp": self.run_timestamp,
            "total_websites": len(self.summary_data),
            "successful_scrapes": sum(1 for site in self.summary_data if site["status"] == "success"),
            "failed_scrapes": sum(1 for site in self.summary_data if site["status"] == "failed"),
            "total_images_found": sum(site.get("total_images", 0) for site in self.summary_data),
            "logos_detected": sum(1 for site in self.summary_data if site.get("logo_detection", {}).get("logo_found", False)),
            "logos_downloaded": sum(1 for site in self.summary_data if site.get("downloaded_logo_path", "")),
            "merchants_identified": merchants_identified,
            "average_merchant_confidence": average_merchant_confidence,
            "mcc_classifications_successful": sum(1 for site in self.summary_data if site.get("final_mcc_code") is not None),
            "mcc_classifications_failed": sum(1 for site in self.summary_data if site.get("final_mcc_code") is None and site["status"] == "success"),
            "average_mcc_confidence": round(sum(site.get("mcc_confidence", 0.0) for site in self.summary_data if site.get("mcc_confidence", 0.0) > 0) / max(1, sum(1 for site in self.summary_data if site.get("mcc_confidence", 0.0) > 0)), 3),
            "addresses_found": addresses_found,
            "average_address_confidence": average_address_confidence,
            "addresses_from_website": sum(1 for site in self.summary_data if site.get("address_source", "").startswith("website")),
            "addresses_from_search": sum(1 for site in self.summary_data if site.get("address_source", "").startswith("search")),
            "average_load_time": round(sum(site.get("load_time_seconds", 0) for site in self.summary_data) / len(self.summary_data), 2) if self.summary_data else 0,
            "websites": self.summary_data
        }
        
        with open(summary_file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        success(f"Summary saved: summary.json")
        
        # Create logo summary, merchant summary, MCC summary, and address summary
        self.save_logo_summary()
        self.save_merchant_summary()
        self.save_mcc_summary()
        self.save_address_summary()
        
        return summary_file_path
    
    def save_logo_summary(self):
        """Save logo-specific summary to a separate JSON file"""
        logo_summary_path = os.path.join(self.base_data_dir, "logo_summary.json")
        
        logo_summary = []
        
        for site in self.summary_data:
            logo_detection = site.get("logo_detection", {})
            
            # Get logo URL from selected_image (only if logo was actually found)
            logo_url = ""
            if logo_detection.get("logo_found") and logo_detection.get("selected_image"):
                logo_url = logo_detection["selected_image"].get("src", "")
            
            # Get downloaded logo path
            downloaded_logo_path = site.get("downloaded_logo_path", "")
            
            # Create entry for both successful scrapes and failed ones
            logo_entry = {
                "website": site["url"],
                "logo_url": logo_url,
                "downloaded_logo_path": downloaded_logo_path,
                "reasoning": logo_detection.get("reasoning", "Website scraping failed - no analysis performed" if site["status"] == "failed" else "No logo analysis performed"),
                "confidence": logo_detection.get("confidence", "none"),
                "merchant_name": site.get("merchant_name", ""),
                "merchant_name_confidence": site.get("merchant_name_confidence", 0.0)
            }
            
            logo_summary.append(logo_entry)
        
        with open(logo_summary_path, 'w', encoding='utf-8') as f:
            json.dump(logo_summary, f, indent=2, ensure_ascii=False)
        
        success(f"Logo summary saved: logo_summary.json")
        return logo_summary_path
    
    def save_merchant_summary(self):
        """Save merchant-specific summary to a separate JSON file"""
        merchant_summary_path = os.path.join(self.base_data_dir, "merchant_summary.json")
        
        merchant_summary = []
        
        for site in self.summary_data:
            logo_detection = site.get("logo_detection", {})
            
            # Create entry for both successful and failed extractions
            merchant_entry = {
                "website": site["url"],
                "merchant_name": site.get("merchant_name", ""),
                "merchant_name_confidence": site.get("merchant_name_confidence", 0.0),
                "merchant_name_source": site.get("merchant_name_source", ""),
                "alternative_names": logo_detection.get("alternative_names", []),
                "extraction_success": bool(site.get("merchant_name", "")),
                "logo_found": logo_detection.get("logo_found", False),
                "error": "" if site["status"] == "success" else "Website scraping failed"
            }
            
            merchant_summary.append(merchant_entry)
        
        with open(merchant_summary_path, 'w', encoding='utf-8') as f:
            json.dump(merchant_summary, f, indent=2, ensure_ascii=False)
        
        success(f"Merchant summary saved: merchant_summary.json")
        return merchant_summary_path
    
    def save_mcc_summary(self):
        """Save MCC-specific summary to a separate JSON file"""
        mcc_summary_path = os.path.join(self.base_data_dir, "mcc_summary.json")
        
        mcc_summary = []
        
        for site in self.summary_data:
            mcc_classification = site.get("mcc_classification", {})
            
            # Create entry for both successful and failed classifications
            mcc_entry = {
                "website": site["url"],
                "merchant_name": site.get("merchant_name", ""),
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
        
        success(f"MCC summary saved: mcc_summary.json")
        return mcc_summary_path
    
    def save_address_summary(self):
        """Save address-specific summary to a separate JSON file"""
        address_summary_path = os.path.join(self.base_data_dir, "address_summary.json")
        
        address_summary = []
        
        for site in self.summary_data:
            address_extraction = site.get("address_extraction", {})
            
            # Create entry for both successful scrapes and failed ones
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
                "merchant_name_used": address_extraction.get("merchant_name_used", ""),
                "business_type_used": address_extraction.get("business_type_used", ""),
                "error": address_extraction.get("error", "" if site["status"] == "success" else "Website scraping failed"),
                "scrape_status": site["status"]
            }
            
            address_summary.append(address_entry)
        
        with open(address_summary_path, 'w', encoding='utf-8') as f:
            json.dump(address_summary, f, indent=2, ensure_ascii=False)
        
        success(f"Address summary saved: address_summary.json")
        return address_summary_path
    
    def run(self):
        """Main execution method"""
        header("Website Scraper Agent with Logo Detection & MCC Classification")
        
        # Setup WebDriver
        if not self.setup_driver():
            return
        
        try:
            # Load websites from file
            info("Loading websites from data/load_websites.txt...")
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
            
            info(f"Loaded {len(websites_data)} websites to scrape")
            
            # Scrape each website
            for i, website_info in enumerate(websites_data, 1):
                url = website_info["url"]
                processing(f"[{i}/{len(websites_data)}] {url}")
                
                scrape_result = self.scrape_website(url)
                self.summary_data.append(scrape_result)
                
                # Small delay between requests to be respectful
                if i < len(websites_data):
                    time.sleep(2)
            
            # Save summary
            summary_path = self.save_summary()
            
            # Final report with location statistics
            header("Scraping Completed!")
            completed(f"Run timestamp: {self.run_timestamp}")
            completed(f"Total websites processed: {len(self.summary_data)}")
            completed(f"Successful: {sum(1 for site in self.summary_data if site['status'] == 'success')}")
            completed(f"Failed: {sum(1 for site in self.summary_data if site['status'] == 'failed')}")
            completed(f"Total images found: {sum(site.get('total_images', 0) for site in self.summary_data)}")
            completed(f"Logos detected: {sum(1 for site in self.summary_data if site.get('logo_detection', {}).get('logo_found', False))}")
            completed(f"Logos downloaded: {sum(1 for site in self.summary_data if site.get('downloaded_logo_path', ''))}")
            
            # Merchant name statistics
            merchants_identified = sum(1 for site in self.summary_data if site.get("merchant_name", ""))
            completed(f"Merchant names extracted: {merchants_identified}")
            if merchants_identified > 0:
                avg_merchant_confidence = sum(site.get("merchant_name_confidence", 0.0) for site in self.summary_data if site.get("merchant_name", "")) / merchants_identified
                completed(f"Average merchant name confidence: {avg_merchant_confidence:.2f}")
            
            # MCC statistics
            completed(f"MCC classifications successful: {sum(1 for site in self.summary_data if site.get('final_mcc_code') is not None)}")
            mcc_successful_sites = [site for site in self.summary_data if site.get('mcc_confidence', 0.0) > 0]
            if mcc_successful_sites:
                avg_mcc_confidence = sum(site.get('mcc_confidence', 0.0) for site in mcc_successful_sites) / len(mcc_successful_sites)
                completed(f"Average MCC confidence: {avg_mcc_confidence:.2f}")
            
            # Address statistics
            addresses_found = sum(1 for site in self.summary_data if site.get("final_address", ""))
            completed(f"Addresses found: {addresses_found}")
            if addresses_found > 0:
                avg_address_confidence = sum(site.get("address_confidence", 0.0) for site in self.summary_data if site.get("final_address", "")) / addresses_found
                completed(f"Average address confidence: {avg_address_confidence:.2f}")
                
                # Address source breakdown
                website_addresses = sum(1 for site in self.summary_data if site.get("address_source", "").startswith("website"))
                search_addresses = sum(1 for site in self.summary_data if site.get("address_source", "").startswith("search"))
                completed(f"Addresses from website: {website_addresses}")
                completed(f"Addresses from search: {search_addresses}")
            
            completed(f"Data saved in: {self.base_data_dir}")
            
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