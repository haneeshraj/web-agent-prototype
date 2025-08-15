import os
import requests
import time
from typing import Dict, List, Any, Optional
from utils.terminal_prettify import error, warning, info


class SerpAPIClient:
    """
    SerpAPI client for performing Google search queries.
    """
    
    def __init__(self):
        """Initialize SerpAPI client with API key from environment."""
        self.api_key = os.getenv('SERPAPI_KEY')
        self.base_url = "https://serpapi.com/search.json"
        
        if not self.api_key:
            warning("SERPAPI_KEY not found in environment variables. Address search via SerpAPI will be disabled.")
    
    def is_available(self) -> bool:
        """Check if SerpAPI is available (API key provided)."""
        return self.api_key is not None
    
    def search(self, query: str, num_results: int = 5) -> Optional[Dict[str, Any]]:
        """
        Perform a Google search using SerpAPI.
        
        Args:
            query (str): Search query
            num_results (int): Number of results to return (default: 5)
            
        Returns:
            Optional[Dict[str, Any]]: Search results or None if failed
        """
        if not self.is_available():
            error("SerpAPI not available - missing API key")
            return None
        
        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "num": num_results,
                "hl": "en",
                "gl": "us"
            }
            
            info(f"Searching: {query}")
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                error(f"SerpAPI error: {data['error']}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            error(f"SerpAPI request failed: {e}")
            return None
        except Exception as e:
            error(f"SerpAPI search failed: {e}")
            return None
    
    def extract_business_info(self, search_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract business information from SerpAPI search results.
        
        Args:
            search_results (Dict[str, Any]): Raw SerpAPI search results
            
        Returns:
            List[Dict[str, Any]]: List of business information dictionaries
        """
        business_info = []
        
        # Extract from organic results
        organic_results = search_results.get("organic_results", [])
        for result in organic_results:
            info_item = {
                "title": result.get("title", ""),
                "link": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "source": "organic"
            }
            business_info.append(info_item)
        
        # Extract from knowledge graph (business information panel)
        knowledge_graph = search_results.get("knowledge_graph", {})
        if knowledge_graph:
            kg_info = {
                "title": knowledge_graph.get("title", ""),
                "description": knowledge_graph.get("description", ""),
                "address": knowledge_graph.get("address", ""),
                "phone": knowledge_graph.get("phone", ""),
                "website": knowledge_graph.get("website", ""),
                "type": knowledge_graph.get("type", ""),
                "source": "knowledge_graph"
            }
            business_info.append(kg_info)
        
        # Extract from local results (Google My Business listings)
        local_results = search_results.get("local_results", [])
        for result in local_results:
            local_info = {
                "title": result.get("title", ""),
                "address": result.get("address", ""),
                "phone": result.get("phone", ""),
                "website": result.get("website", ""),
                "rating": result.get("rating", ""),
                "reviews": result.get("reviews", ""),
                "hours": result.get("hours", ""),
                "type": result.get("type", ""),
                "snippet": result.get("snippet", ""),
                "source": "local_results"
            }
            business_info.append(local_info)
        
        # Extract from answer box (if present)
        answer_box = search_results.get("answer_box", {})
        if answer_box:
            ab_info = {
                "title": answer_box.get("title", ""),
                "answer": answer_box.get("answer", ""),
                "link": answer_box.get("link", ""),
                "snippet": answer_box.get("snippet", ""),
                "source": "answer_box"
            }
            business_info.append(ab_info)
        
        return business_info


def create_serpapi_client() -> SerpAPIClient:
    """Create and return a SerpAPI client instance."""
    return SerpAPIClient()
