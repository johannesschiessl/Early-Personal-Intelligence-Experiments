import os
import argparse
import requests
from bs4 import BeautifulSoup
from typing import Optional
from openai import OpenAI

class DocsCollectorAgent:
    def __init__(self):
        self.client = OpenAI()
        self.output_dir = "ai_docs"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def fetch_url_content(self, url: str) -> str:
        """
        Fetches and processes content from a URL
        
        Args:
            url: The URL to fetch
            
        Returns:
            str: Website content in text format
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
            
            return text
            
        except Exception as e:
            return f"Error fetching URL: {str(e)}"

    def process_url(self, url: str, instructions: Optional[str] = None) -> str:
        """
        Process a URL into clean markdown documentation
        
        Args:
            url: The URL to process
            instructions: Optional processing instructions
            
        Returns:
            str: Path to the saved markdown file
        """
        # Get raw content
        raw_content = self.fetch_url_content(url)
        
        # Prepare prompt for GPT
        prompt = f"""Please convert this raw scraped web content into clean, well-formatted markdown.
Remove any navigation elements, footers, or other web artifacts.
Keep only the main content and structure it with appropriate markdown headings and formatting. If there are code examples, keep them in markdown code blocks.

Raw content:
{raw_content}"""

        if instructions:
            prompt += f"\n\nAdditional instructions:\n{instructions}"

        # Process with GPT-4o-mini
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a documentation cleanup specialist. Convert raw web content into clean markdown while preserving important information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        cleaned_content = response.choices[0].message.content

        # Generate filename from URL
        filename = url.split('/')[-1].split('.')[0]
        if not filename:
            filename = 'doc'
        filename = f"{filename}.md"
        
        # Save to file
        output_path = "ai_docs/" + filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
            
        return output_path

def main():
    parser = argparse.ArgumentParser(description='Process URLs into clean markdown documentation')
    parser.add_argument('url', help='URL to process')
    parser.add_argument('--instructions', '-i', help='Additional processing instructions')
    
    args = parser.parse_args()
    
    agent = DocsCollectorAgent()
    output_path = agent.process_url(args.url, args.instructions)
    print(f"Documentation saved to: {output_path}")

if __name__ == "__main__":
    main()
