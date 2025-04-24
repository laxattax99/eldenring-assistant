import os
import sys
import json
import time
from typing import List, Dict, Any
from urllib.parse import urlparse, unquote

from scrape_page import scrape_wiki_page
from langchain_chunker import process_page, save_chunks_to_jsonl

# Configuration
OUTPUT_DIR = "data"
CHUNKS_FILE = os.path.join(OUTPUT_DIR, "chunks.jsonl")
URLS_FILE = os.path.join(OUTPUT_DIR, "processed_urls.json")
DELAY = 1  # Delay between requests in seconds to avoid hitting the server too hard

def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

def load_processed_urls() -> List[str]:
    """Load list of already processed URLs"""
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_processed_urls(urls: List[str]):
    """Save list of processed URLs"""
    with open(URLS_FILE, 'w') as f:
        json.dump(urls, f, indent=2)

def process_url_batch(urls: List[str], chunk_size: int = 500, chunk_overlap: int = 50) -> None:
    """
    Process a batch of URLs, chunk their content, and save to JSONL
    
    Args:
        urls: List of URLs to process
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
    """
    ensure_output_dir()
    processed_urls = load_processed_urls()
    all_chunks = []
    
    for url in urls:
        if url in processed_urls:
            print(f"Skipping already processed URL: {url}")
            continue
        
        print(f"Processing {url}...")
        try:
            # Extract page content
            page_data = scrape_wiki_page(url)
            
            if not page_data:
                print(f"Failed to scrape {url}")
                continue
                
            # Process into chunks
            chunks = process_page(page_data, chunk_size, chunk_overlap)
            all_chunks.extend(chunks)
            
            # Record as processed
            processed_urls.append(url)
            print(f"Successfully processed {url} - {len(chunks)} chunks")
            
            # Be nice to the server
            time.sleep(DELAY)
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    # Save all chunks to JSONL file
    if all_chunks:
        save_chunks_to_jsonl(all_chunks, CHUNKS_FILE)
    
    # Update processed URLs file
    save_processed_urls(processed_urls)
    
    print(f"Batch processing complete. {len(all_chunks)} total chunks from {len(processed_urls)} URLs.")

def get_urls_from_file(file_path: str) -> List[str]:
    """Load URLs from a text file, one per line"""
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def extract_wiki_page_name(url: str) -> str:
    """Extract page name from a wiki URL to use for metadata"""
    path = urlparse(url).path
    page_name = path.split('/')[-1]
    return unquote(page_name).replace('+', ' ')

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1].endswith('.txt'):
            # Process URLs from a file
            urls = get_urls_from_file(sys.argv[1])
            process_url_batch(urls)
        else:
            # Process a single URL
            url = sys.argv[1]
            process_url_batch([url])
    else:
        print("Usage: python batch_process.py <url_or_urls_file>")
        print("Example: python batch_process.py https://eldenring.wiki.fextralife.com/Malenia+Blade+of+Miquella")
        print("Example: python batch_process.py urls.txt")