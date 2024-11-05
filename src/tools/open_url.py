import requests
from bs4 import BeautifulSoup
from openai import OpenAI

class URLContent:
    def __init__(self):
        self.client = OpenAI()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def _fetch_raw_content(self, url: str) -> str:
        """Fetches raw content from URL"""
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        code_blocks = []
        for code in soup.find_all(['pre', 'code']):
            code_blocks.append(code.get_text())
            code.replace_with('[CODE_BLOCK_PLACEHOLDER]')
        
        for element in soup(['script', 'style', 'header', 'footer', 'nav']):
            element.decompose()
            
        text = soup.get_text()
        
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        for code in code_blocks:
            text = text.replace('[CODE_BLOCK_PLACEHOLDER]', f'\n```\n{code}\n```\n', 1)
            
        return text

    def _clean_with_gpt(self, content: str) -> str:
        """Uses GPT-4-mini to clean and format content"""
        prompt = """Clean and format the following web content into clear markdown. 
        Preserve any code blocks, remove redundant elements, and organize the content logically.
        Keep important information while removing noise like navigation menus, ads, etc.
        Format code examples in appropriate markdown code blocks with language hints where possible."""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ],
            max_tokens=4000
        )
        
        return response.choices[0].message.content

    def fetch(self, url: str) -> str:
        """
        Fetches URL content and returns cleaned markdown
        
        Args:
            url: The URL to fetch
            
        Returns:
            str: Cleaned website content in markdown format
        """
        try:
            raw_content = self._fetch_raw_content(url)
            cleaned_content = self._clean_with_gpt(raw_content)
            
            if len(cleaned_content) > 4000:
                cleaned_content = cleaned_content[:4000] + "\n\n[Content truncated...]"
                
            return cleaned_content
            
        except Exception as e:
            return f"Error processing URL: {str(e)}"
