"""
Web scraping module for Scout Agent PoC.
Handles fetching web pages and comparing content for changes.
"""

import hashlib
import requests
from bs4 import BeautifulSoup
from typing import Tuple, Optional, Dict, Any
import difflib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, user_agent: str = None):
        """Initialize the web scraper with optional user agent."""
        self.headers = {
            'User-Agent': user_agent or 'Scout Agent/1.0 (PoC Monitoring Bot)'
        }
    
    def fetch_page(self, url: str) -> Tuple[bool, str]:
        """
        Fetch a web page and return its content.
        
        Args:
            url: The URL to fetch
            
        Returns:
            Tuple of (success, content)
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return True, response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return False, str(e)
    
    def compare_content(self, old_content: str, new_content: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Compare old and new content to detect changes.
        
        Args:
            old_content: Previous HTML content
            new_content: Current HTML content
            
        Returns:
            Tuple of (changed, details)
        """
        # Simple hash comparison
        old_hash = hashlib.sha256(old_content.encode()).hexdigest()
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()
        
        if old_hash == new_hash:
            return False, {"message": "No changes detected"}
        
        # If hashes differ, generate a more detailed diff
        # Parse HTML to focus on text content
        old_soup = BeautifulSoup(old_content, 'html.parser')
        new_soup = BeautifulSoup(new_content, 'html.parser')
        
        # Extract text content
        old_text = old_soup.get_text(separator=' ', strip=True)
        new_text = new_soup.get_text(separator=' ', strip=True)
        
        # Generate diff
        diff = list(difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            lineterm='',
            n=3  # Context lines
        ))
        
        # Count additions and removals
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removals = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        return True, {
            "changed": True,
            "old_hash": old_hash,
            "new_hash": new_hash,
            "additions": additions,
            "removals": removals,
            "diff_sample": '\n'.join(diff[:20]) if len(diff) > 0 else "Content changed but diff couldn't be generated"
        }
    
    def extract_relevant_content(self, html_content: str, task_prompt: str) -> str:
        """
        Extract content relevant to the task prompt.
        This is a simplified version that could be enhanced with LLM-based extraction.
        
        Args:
            html_content: The HTML content of the page
            task_prompt: Description of what to monitor
            
        Returns:
            Extracted relevant content
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # For now, just return the cleaned text
        # In a more advanced version, this could use an LLM to extract
        # only the parts relevant to the task_prompt
        return text
