import requests
from bs4 import BeautifulSoup
import markdown
import re

class URLHandler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def open_url(self, url: str) -> str:
        """
        Fetches content from a URL and converts it to markdown
        
        Args:
            url: The URL to fetch
            
        Returns:
            str: Website content in markdown format
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Limit content length to avoid token limits
            if len(text) > 4000:
                text = text[:4000] + "\n\n[Content truncated...]"
                
            return text
            
        except Exception as e:
            return f"Error fetching URL: {str(e)}" 