import requests
from bs4 import BeautifulSoup
import json
import re
import sys
from urllib.parse import urlparse

def scrape_wiki_page(url):
    """
    Scrape any page from the Elden Ring wiki and extract:
    - Title
    - Clean text content
    - URL
    - Page type (boss, weapon, magic, etc.)
    
    Args:
        url: URL of the wiki page to scrape
        
    Returns:
        Dictionary containing page metadata and content
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for HTTP errors
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract page title (remove "| Elden Ring Wiki" suffix)
        title_tag = soup.find('h1')
        title = title_tag.text.strip() if title_tag else None
        if title and '|' in title:
            title = title.split('|')[0].strip()
            
        # Try to determine page type based on URL pattern and content
        page_type = determine_page_type(url, soup)
        
        # Extract the main content
        main_content = soup.find('div', {'id': 'wiki-content-block'})
        
        # If we can't find the main content div, take the whole body
        if not main_content:
            main_content = soup.body
            
        # Extract all text, ignoring navigation, comments, and scripts
        clean_text = extract_clean_text(main_content)
        
        # Create the result dictionary
        result = {
            'title': title,
            'url': url,
            'type': page_type,
            'content': clean_text
        }
        
        return result
        
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def determine_page_type(url, soup):
    """
    Try to determine the page type (boss, weapon, sorcery, etc.) based on URL and content
    """
    # First check for breadcrumbs which are most reliable
    breadcrumb_div = soup.find('div', id='breadcrumbs-container')
    if breadcrumb_div:
        breadcrumb_text = breadcrumb_div.text.lower()
        
        # Check for specific page types in breadcrumbs
        if 'weapons' in breadcrumb_text:
            return 'weapon'
        if 'bosses' in breadcrumb_text:
            return 'boss'
        if 'sorceries' in breadcrumb_text:
            return 'sorcery'
        if 'incantations' in breadcrumb_text:
            return 'incantation'
        if 'armor' in breadcrumb_text:
            return 'armor'
        if 'talismans' in breadcrumb_text:
            return 'talisman'
        if 'location' in breadcrumb_text or 'locations' in breadcrumb_text:
            return 'location'
        if 'npc' in breadcrumb_text or 'npcs' in breadcrumb_text:
            return 'npc'
        if 'items' in breadcrumb_text:
            return 'item'
        if 'ashes' in breadcrumb_text:
            return 'ash'
        if 'talismans' in breadcrumb_text:
            return 'talisman'
    
    # Default to "other" if we can't determine the type
    return 'other'

def extract_clean_text(element):
    """
    Extract clean text from a BeautifulSoup element, ignoring scripts, styles, and navigation elements
    """
    # Elements to ignore
    ignore_elements = ['script', 'style', 'nav', 'footer', 'header']
    
    # Make a copy to avoid modifying the original
    element_copy = element
    
    # Remove unwanted elements
    for ignore_tag in ignore_elements:
        for tag in element_copy.find_all(ignore_tag):
            tag.decompose()
    
    # Get all text and normalize whitespace
    text = element_copy.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    
    return text

def main():
    """Main function to handle command-line usage"""
    if len(sys.argv) > 1:
        url = sys.argv[1]
        result = scrape_wiki_page(url)
        
        if result:
            # Print the result as JSON
            print(json.dumps(result, indent=2))
            
            # Optionally save to a file
            if len(sys.argv) > 2:
                output_file = sys.argv[2]
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
                print(f"Saved result to {output_file}")
    else:
        print("Usage: python scrape_page.py <url> [output_file]")

if __name__ == "__main__":
    main()