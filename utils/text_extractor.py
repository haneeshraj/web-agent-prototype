"""
Text extraction utility for converting HTML content to clean text for MCC classification.
Extracts meaningful business information while removing noise and HTML structure.
"""

import re
import os
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, NavigableString
from utils.terminal_prettify import info, warning, error


class TextExtractor:
    """
    Extracts clean, meaningful text from HTML content for MCC classification analysis.
    """
    
    def __init__(self):
        """Initialize the text extractor."""
        # Keywords that indicate important business information
        self.business_keywords = [
            'about', 'services', 'products', 'company', 'business', 'industry',
            'specializing', 'expertise', 'offerings', 'solutions', 'provider',
            'restaurant', 'food', 'retail', 'shop', 'store', 'medical', 'health',
            'legal', 'consulting', 'technology', 'software', 'manufacturing',
            'construction', 'education', 'finance', 'insurance', 'real estate',
            'transportation', 'logistics', 'hospitality', 'travel', 'entertainment'
        ]
        
        # Tags that typically contain important content
        self.important_tags = [
            'title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'nav', 'header', 'main', 'section', 'article',
            'p', 'div', 'span', 'li', 'td', 'th'
        ]
        
        # Tags to completely ignore
        self.ignore_tags = [
            'script', 'style', 'noscript', 'iframe', 'object', 'embed',
            'link', 'meta', 'base', 'area', 'br', 'hr', 'img',
            'input', 'button', 'select', 'textarea', 'form'
        ]
        
        # Common noise patterns to remove
        self.noise_patterns = [
            r'cookie\s+policy',
            r'privacy\s+policy',
            r'terms\s+of\s+service',
            r'subscribe\s+to\s+newsletter',
            r'follow\s+us',
            r'social\s+media',
            r'copyright\s+\d{4}',
            r'all\s+rights\s+reserved',
            r'loading\.\.\.?',
            r'please\s+wait',
            r'javascript\s+required',
            r'enable\s+javascript',
            r'accept\s+cookies',
            r'cookie\s+consent'
        ]
    
    def extract_from_html_file(self, html_file_path: str) -> Dict[str, any]:
        """
        Extract text from HTML file.
        
        Args:
            html_file_path (str): Path to HTML file
            
        Returns:
            Dict[str, any]: Extracted text data with metadata
        """
        try:
            if not os.path.exists(html_file_path):
                return self._create_error_result("HTML file not found")
            
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            return self.extract_from_html_string(html_content)
            
        except Exception as e:
            return self._create_error_result(f"Failed to read HTML file: {str(e)}")
    
    def extract_from_html_string(self, html_content: str) -> Dict[str, any]:
        """
        Extract clean text from HTML string.
        
        Args:
            html_content (str): Raw HTML content
            
        Returns:
            Dict[str, any]: Extracted text data with metadata
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted tags completely
            for tag_name in self.ignore_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
            
            # Extract different types of content
            result = {
                'page_title': self._extract_page_title(soup),
                'headings': self._extract_headings(soup),
                'navigation': self._extract_navigation(soup),
                'main_content': self._extract_main_content(soup),
                'business_keywords_found': [],
                'clean_full_text': '',
                'word_count': 0,
                'extraction_metadata': {
                    'success': True,
                    'original_html_length': len(html_content),
                    'extraction_method': 'html_parsing'
                }
            }
            
            # Combine all text and clean it
            all_text_parts = [
                result['page_title'],
                ' '.join(result['headings']),
                result['navigation'],
                result['main_content']
            ]
            
            combined_text = ' '.join([part for part in all_text_parts if part])
            result['clean_full_text'] = self._clean_and_normalize_text(combined_text)
            result['word_count'] = len(result['clean_full_text'].split())
            
            # Find business-related keywords
            result['business_keywords_found'] = self._find_business_keywords(result['clean_full_text'])
            
            return result
            
        except Exception as e:
            return self._create_error_result(f"HTML parsing failed: {str(e)}")
    
    def _extract_page_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        return ""
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[str]:
        """Extract all heading text (h1-h6)."""
        headings = []
        for level in range(1, 7):
            for heading in soup.find_all(f'h{level}'):
                text = self._get_text_from_element(heading)
                if text and text not in headings:  # Avoid duplicates
                    headings.append(text)
        return headings
    
    def _extract_navigation(self, soup: BeautifulSoup) -> str:
        """Extract navigation menu text."""
        nav_text = []
        
        # Look for nav tags
        for nav in soup.find_all('nav'):
            text = self._get_text_from_element(nav)
            if text:
                nav_text.append(text)
        
        # Look for elements with navigation-related classes
        nav_classes = ['nav', 'menu', 'navigation', 'navbar', 'header-menu']
        for class_name in nav_classes:
            for element in soup.find_all(class_=lambda x: x and class_name in str(x).lower()):
                text = self._get_text_from_element(element)
                if text and text not in nav_text:
                    nav_text.append(text)
        
        return ' '.join(nav_text)
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content text."""
        content_text = []
        
        # Priority order for main content areas
        main_selectors = [
            'main',
            '[role="main"]',
            '.main-content',
            '.content',
            '.page-content',
            'article',
            '.article',
            'section',
            '.section'
        ]
        
        # Try to find main content container
        main_container = None
        for selector in main_selectors:
            main_container = soup.select_one(selector)
            if main_container:
                break
        
        if main_container:
            # Extract from main container
            content_text.append(self._get_text_from_element(main_container))
        else:
            # Fallback: extract from body or entire document
            body = soup.find('body') or soup
            
            # Extract from paragraphs and divs
            for tag in body.find_all(['p', 'div'], recursive=True):
                text = self._get_text_from_element(tag, direct_only=True)
                if text and len(text.strip()) > 10:  # Ignore very short text
                    content_text.append(text)
        
        return ' '.join(content_text)
    
    def _get_text_from_element(self, element, direct_only: bool = False) -> str:
        """
        Extract clean text from a BeautifulSoup element.
        
        Args:
            element: BeautifulSoup element
            direct_only (bool): If True, only get direct text, not from children
            
        Returns:
            str: Clean text content
        """
        if not element:
            return ""
        
        if direct_only:
            # Only get direct text content, not from nested elements
            text_parts = []
            for item in element.contents:
                if isinstance(item, NavigableString):
                    text_parts.append(str(item).strip())
            text = ' '.join(text_parts)
        else:
            # Get all text including from nested elements
            text = element.get_text(separator=' ', strip=True)
        
        return self._clean_text_fragment(text)
    
    def _clean_text_fragment(self, text: str) -> str:
        """Clean a fragment of text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove noise patterns
        for pattern in self.noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove very short fragments (likely noise)
        if len(text.strip()) < 3:
            return ""
        
        return text.strip()
    
    def _clean_and_normalize_text(self, text: str) -> str:
        """Final cleaning and normalization of combined text."""
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove duplicate sentences (simple approach)
        sentences = text.split('.')
        unique_sentences = []
        seen_sentences = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and sentence not in seen_sentences and len(sentence) > 10:
                unique_sentences.append(sentence)
                seen_sentences.add(sentence)
        
        # Rejoin sentences
        clean_text = '. '.join(unique_sentences)
        
        # Final cleanup
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Limit length for LLM processing (adjust as needed)
        max_length = 8000  # Adjust based on your LLM's context limit
        if len(clean_text) > max_length:
            # Truncate at sentence boundary
            truncated = clean_text[:max_length]
            last_period = truncated.rfind('.')
            if last_period > max_length * 0.8:  # Only truncate if we don't lose too much
                clean_text = truncated[:last_period + 1]
            else:
                clean_text = truncated + "..."
        
        return clean_text
    
    def _find_business_keywords(self, text: str) -> List[str]:
        """Find business-related keywords in the text."""
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.business_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _create_error_result(self, reason: str) -> Dict[str, any]:
        """Create an error result."""
        return {
            'page_title': '',
            'headings': [],
            'navigation': '',
            'main_content': '',
            'business_keywords_found': [],
            'clean_full_text': '',
            'word_count': 0,
            'extraction_metadata': {
                'success': False,
                'error': reason,
                'extraction_method': 'failed'
            }
        }
    
    def extract_for_mcc_classification(self, html_file_path: str) -> str:
        """
        Extract text specifically optimized for MCC classification.
        Returns just the clean text string ready for LLM analysis.
        
        Args:
            html_file_path (str): Path to HTML file
            
        Returns:
            str: Clean text optimized for MCC classification
        """
        result = self.extract_from_html_file(html_file_path)
        
        if not result['extraction_metadata']['success']:
            return ""
        
        # Create a focused text for MCC classification
        mcc_text_parts = []
        
        # Add title (very important for business type)
        if result['page_title']:
            mcc_text_parts.append(f"Page Title: {result['page_title']}")
        
        # Add headings (important for understanding business focus)
        if result['headings']:
            mcc_text_parts.append(f"Main Headings: {' | '.join(result['headings'][:5])}")  # Limit to top 5
        
        # Add navigation (shows business structure/services)
        if result['navigation']:
            nav_clean = result['navigation'][:500]  # Limit navigation text
            mcc_text_parts.append(f"Navigation: {nav_clean}")
        
        # Add main content (but prioritize business-relevant parts)
        if result['main_content']:
            content = result['main_content']
            
            # If content is too long, try to extract business-relevant parts
            if len(content) > 3000:
                # Look for sentences containing business keywords
                sentences = content.split('.')
                relevant_sentences = []
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if any(keyword in sentence.lower() for keyword in self.business_keywords):
                        relevant_sentences.append(sentence)
                        if len(' '.join(relevant_sentences)) > 2000:  # Limit size
                            break
                
                if relevant_sentences:
                    content = '. '.join(relevant_sentences)
                else:
                    content = content[:3000] + "..."
            
            mcc_text_parts.append(f"Main Content: {content}")
        
        # Add found business keywords summary
        if result['business_keywords_found']:
            mcc_text_parts.append(f"Business Keywords Detected: {', '.join(result['business_keywords_found'][:10])}")
        
        final_text = '\n\n'.join(mcc_text_parts)
        
        # Final length check
        if len(final_text) > 6000:
            final_text = final_text[:6000] + "... [content truncated for analysis]"
        
        return final_text


# Convenience function
def extract_text_for_mcc(html_file_path: str) -> str:
    """
    Convenience function to extract text for MCC classification.
    
    Args:
        html_file_path (str): Path to HTML file
        
    Returns:
        str: Clean text ready for MCC classification
    """
    extractor = TextExtractor()
    return extractor.extract_for_mcc_classification(html_file_path)


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        html_path = sys.argv[1]
        
        extractor = TextExtractor()
        result = extractor.extract_for_mcc_classification(html_path)
        
        print("=" * 60)
        print("EXTRACTED TEXT FOR MCC CLASSIFICATION")
        print("=" * 60)
        print(result)
        print("=" * 60)
        print(f"Length: {len(result)} characters")
        
    else:
        print("Usage: python text_extractor.py <html_file_path>")