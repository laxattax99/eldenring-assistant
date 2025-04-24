import time
import re
import argparse
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from typing import List, Set, Dict, Any
import json
import os

# Configuration
BASE_URL = "https://eldenring.wiki.fextralife.com/"
OUTPUT_DIR = "data"
URLS_FILE = os.path.join(OUTPUT_DIR, "wiki_urls.json")
DELAY = 0.5  # Delay between requests in seconds to avoid hitting the server too hard

# Pages to exclude from crawling (e.g., user pages, edit pages, etc.)
EXCLUDE_PATTERNS = [
    r"/Special:",
    r"/File:",
    r"/User:",
    r"/Talk:",
    r"/Category:",
    r"/Template:",
    r"\?action=",
    r"\?title=",
    r"&action=",
    r"&title=",
    r"edit$",
    r"history$",
    r"diff=",
    r"facebook.com",
    r"twitter.com",
    r"youtube.com",
    r"twitch.tv",
    r"discord.gg",
    r"instagram.com",
]

def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

def load_crawled_urls() -> Dict[str, bool]:
    """Load list of already crawled URLs"""
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_crawled_urls(urls: Dict[str, bool]):
    """Save list of crawled URLs"""
    with open(URLS_FILE, 'w') as f:
        json.dump(urls, f, indent=2)

def should_crawl(url: str) -> bool:
    """Check if a URL should be crawled"""
    # Ensure it's a wiki URL
    if not url.startswith(BASE_URL):
        return False
    
    # Check against exclusion patterns
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, url):
            return False
    
    return True

def get_links_from_page(url: str) -> Set[str]:
    """Extract all links from a page"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip empty links and fragment identifiers
            if not href or href.startswith('#'):
                continue
                
            # Convert relative URLs to absolute
            absolute_url = urljoin(url, href)
            
            # Ensure it's from the same domain
            if urlparse(absolute_url).netloc == urlparse(BASE_URL).netloc:
                links.add(absolute_url)
                
        return links
    
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return set()

def crawl_wiki(start_url: str, max_pages: int = None) -> Dict[str, bool]:
    """
    Crawl the wiki starting from the given URL
    
    Args:
        start_url: URL to start crawling from
        max_pages: Maximum number of pages to crawl (None for unlimited)
        
    Returns:
        Dictionary of crawled URLs and their status
    """
    ensure_output_dir()
    crawled_urls = load_crawled_urls()
    to_crawl = [start_url]
    
    page_count = 0
    
    while to_crawl and (max_pages is None or page_count < max_pages):
        current_url = to_crawl.pop(0)
        
        # Skip if already crawled
        if current_url in crawled_urls:
            continue
            
        if not should_crawl(current_url):
            crawled_urls[current_url] = False  # Mark as not to be processed
            continue
        
        print(f"Crawling: {current_url}")
        new_links = get_links_from_page(current_url)
        
        # Mark as crawled
        crawled_urls[current_url] = True
        page_count += 1
        
        # Add new links to the queue
        for link in new_links:
            if link not in crawled_urls and link not in to_crawl:
                to_crawl.append(link)
        
        # Save progress periodically
        if page_count % 10 == 0:
            save_crawled_urls(crawled_urls)
            print(f"Progress: {page_count} pages crawled, {len(to_crawl)} pages in queue")
        
        # Be nice to the server
        time.sleep(DELAY)
    
    # Save final state
    save_crawled_urls(crawled_urls)
    print(f"Crawling complete. {page_count} pages crawled.")
    return crawled_urls

def get_urls_to_process() -> List[str]:
    """Get list of URLs that should be processed"""
    crawled_urls = load_crawled_urls()
    return [url for url, should_process in crawled_urls.items() if should_process]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Crawl the Elden Ring wiki')
    parser.add_argument('--start', type=str, default=BASE_URL, help='URL to start crawling from')
    parser.add_argument('--max', type=int, default=None, help='Maximum number of pages to crawl')
    parser.add_argument('--list', action='store_true', help='List URLs to process')
    
    args = parser.parse_args()
    
    if args.list:
        urls = get_urls_to_process()
        print(f"Found {len(urls)} URLs to process:")
        for url in urls:
            print(url)
    else:
        crawled_urls = crawl_wiki(args.start, args.max)
        
        # Print summary
        to_process = [url for url, should_process in crawled_urls.items() if should_process]
        print(f"Total URLs found: {len(crawled_urls)}")
        print(f"URLs to process: {len(to_process)}")