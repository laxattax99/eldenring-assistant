import os
import sys
import time
import json
import uuid
import chromadb
import argparse
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import hashlib

# Add the parent directory to the path to import from scraping module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraping.scrape_page import scrape_wiki_page
from scraping.langchain_chunker import process_page
from scraping.wiki_crawler import get_urls_to_process

# Configuration
DATA_DIR = "data"
DB_DIR = os.path.join(DATA_DIR, "chroma_db")
PROCESSED_URLS_FILE = os.path.join(DATA_DIR, "db_processed_urls.json")
PAGE_CONTENT_DIR = os.path.join(DATA_DIR, "page_content")  # New directory to store page content
COLLECTION_NAME = "elden_ring_wiki"
# Upgraded to a more powerful embedding model - better accuracy for question-answering
EMBEDDING_MODEL = "all-mpnet-base-v2"  # Upgraded from all-MiniLM-L6-v2
BATCH_SIZE = 100  # How many chunks to process in one batch
DELAY = 0.3  # Delay between scraping pages to be nice to the server

def ensure_dirs():
    """Make sure data directories exist"""
    for directory in [DATA_DIR, DB_DIR, PAGE_CONTENT_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

def load_processed_urls() -> List[str]:
    """Load list of URLs that have been processed and added to the DB"""
    if os.path.exists(PROCESSED_URLS_FILE):
        with open(PROCESSED_URLS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_processed_urls(urls: List[str]):
    """Save list of processed URLs"""
    with open(PROCESSED_URLS_FILE, 'w') as f:
        json.dump(urls, f, indent=2)

def init_chroma_db():
    """Initialize and return ChromaDB client and collection"""
    # Initialize ChromaDB client with persistent storage
    client = chromadb.PersistentClient(path=DB_DIR)
    
    # Set up sentence transformer embedding function
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    
    # Get or create collection
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
        print(f"Loaded existing collection '{COLLECTION_NAME}' with {collection.count()} documents")
    except:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
        print(f"Created new collection '{COLLECTION_NAME}'")
        
    return client, collection

def get_filename_from_url(url: str) -> str:
    """Generate a filename for storing page content based on URL"""
    # Extract the title from the URL - this matches existing files in the directory
    page_name = url.rstrip('/').split('/')[-1].replace('%27', "'").replace('%28', '(').replace('%29', ')').replace('%2C', ',')
    
    # Replace URL special characters with underscores
    page_name = page_name.replace('-', '_').replace(' ', '_')
    
    # If the URL ends with a trailing slash, use the part before it
    if not page_name:
        page_name = url.rstrip('/').split('/')[-2].replace('-', '_')
        
    # If we still have empty page name after trying, fall back to MD5 hash
    if not page_name:
        hash_object = hashlib.md5(url.encode())
        return hash_object.hexdigest() + '.json'
    
    return page_name + '.json'

def save_page_to_disk(page_data: Dict[str, Any]) -> bool:
    """Save page content to disk using title as filename"""
    if not page_data or 'title' not in page_data or 'url' not in page_data:
        return False
    
    # Use title for filename, replacing spaces and special chars with underscores
    title = page_data['title']
    safe_title = title.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    
    # To avoid filename collisions, add a hash of URL for duplicates
    base_filename = safe_title + '.json'
    filepath = os.path.join(PAGE_CONTENT_DIR, base_filename)
    
    # If a file with this name already exists but has different content, add a hash to make it unique
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if existing_data.get('url') != page_data['url']:
                    # File exists but has different URL, create a unique name
                    hash_suffix = hashlib.md5(page_data['url'].encode()).hexdigest()[:8]
                    base_filename = f"{safe_title}_{hash_suffix}.json"
                    filepath = os.path.join(PAGE_CONTENT_DIR, base_filename)
        except Exception as e:
            print(f"Error checking existing file: {e}")
            # If we can't read the file, use a unique name
            hash_suffix = hashlib.md5(page_data['url'].encode()).hexdigest()[:8]
            base_filename = f"{safe_title}_{hash_suffix}.json"
            filepath = os.path.join(PAGE_CONTENT_DIR, base_filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving page content to disk: {e}")
        return False

def load_page_from_disk(url: str) -> Optional[Dict[str, Any]]:
    """Load page content from disk by scanning for matching URL in JSON files"""
    # Check if the directory exists
    if not os.path.exists(PAGE_CONTENT_DIR):
        print(f"Page content directory {PAGE_CONTENT_DIR} does not exist")
        return None
    
    # List all JSON files in the directory
    files = [f for f in os.listdir(PAGE_CONTENT_DIR) if f.endswith('.json')]
    
    for filename in files:
        filepath = os.path.join(PAGE_CONTENT_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check if this file contains data for the requested URL
                if data.get('url') == url:
                    return data
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
    
    # If we get here, no matching file was found
    print(f"No file found with URL: {url}")
    return None

def process_urls(urls: List[str], collection, chunk_size: int = 500, chunk_overlap: int = 50, 
                write_to_disk: bool = True, read_from_disk: bool = False, 
                disk_only: bool = False):
    """
    Process a batch of URLs, extract content, chunk, embed, and store in ChromaDB
    
    Args:
        urls: List of URLs to process
        collection: ChromaDB collection to store chunks in
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
        write_to_disk: Whether to save scraped content to disk
        read_from_disk: Whether to read content from disk instead of scraping
        disk_only: Whether to only write content to disk without updating the DB
    """
    processed_urls = load_processed_urls()
    urls_to_process = [url for url in urls if url not in processed_urls or read_from_disk]
    
    print(f"Processing {len(urls_to_process)} URLs out of {len(urls)} total")
    if read_from_disk:
        print("Reading content from disk instead of scraping")
    if disk_only:
        print("Writing content to disk only (not updating the database)")
    
    # Counters for statistics
    total_chunks = 0
    total_processed = 0
    
    for i, url in enumerate(tqdm(urls_to_process, desc="Processing URLs")):
        try:
            # Try to load from disk first if requested
            page_data = None
            if read_from_disk:
                page_data = load_page_from_disk(url)
                if not page_data:
                    if disk_only:
                        print(f"Skipping {url} - not found on disk and disk_only mode is enabled")
                        continue
                    print(f"Content for {url} not found on disk, will scrape instead")
            
            # Scrape if not reading from disk or content not found on disk
            if not page_data:
                page_data = scrape_wiki_page(url)
                
                if not page_data:
                    print(f"Failed to scrape {url}")
                    continue
                
                # Save to disk if requested
                if write_to_disk:
                    success = save_page_to_disk(page_data)
                    if success:
                        print(f"Saved content for {url} to disk")
            
            # If disk_only mode, skip database operations
            if disk_only:
                processed_urls.append(url)
                total_processed += 1
                continue
                
            # Process into chunks
            chunks = process_page(page_data, chunk_size, chunk_overlap)
            
            if not chunks:
                print(f"No chunks generated for {url}")
                continue
            
            # Prepare data for ChromaDB
            ids = [str(uuid.uuid4()) for _ in chunks]
            texts = [chunk["text"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]
            
            # Add to ChromaDB
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            
            # Record as processed and update counters
            if url not in processed_urls:
                processed_urls.append(url)
            total_chunks += len(chunks)
            total_processed += 1
            
            # Save progress periodically
            if i % 10 == 0:
                save_processed_urls(processed_urls)
                print(f"Progress: {total_processed} URLs processed, {total_chunks} chunks added to DB")
            
            # Be nice to the server (only if scraping)
            if not read_from_disk:
                time.sleep(DELAY)
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    # Save final progress
    save_processed_urls(processed_urls)
    
    print(f"Processing complete.")
    print(f"Total URLs processed: {total_processed}")
    
    if not disk_only:
        print(f"Total chunks added to DB: {total_chunks}")
        print(f"Total documents in collection: {collection.count()}")
    else:
        print("No chunks were added to the database (disk_only mode)")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Create Elden Ring Vector Database")
    parser.add_argument("--disk-only", action="store_true", 
                        help="Only save page content to disk without updating the database")
    parser.add_argument("--from-disk", action="store_true", 
                        help="Read page content from disk instead of scraping")
    parser.add_argument("--no-disk-write", action="store_true", 
                        help="Don't save page content to disk")
    parser.add_argument("--chunk-size", type=int, default=500,
                        help="Maximum size of each chunk (default: 500)")
    parser.add_argument("--chunk-overlap", type=int, default=50,
                        help="Number of characters to overlap between chunks (default: 50)")
    return parser.parse_args()

def main():
    """Main function to run the database creation process"""
    args = parse_arguments()
    
    print("Initializing Elden Ring Vector Database...")
    ensure_dirs()
    
    # Initialize ChromaDB only if not in disk-only mode
    client, collection = (None, None) if args.disk_only else init_chroma_db()
    
    # Get URLs from crawler results
    print("Finding URLs to process...")
    urls = get_urls_to_process()
    
    if not urls:
        print("No URLs found to process. Run the wiki_crawler.py script first.")
        return
        
    print(f"Found {len(urls)} URLs to process")
    
    # Process URLs based on command line arguments
    process_urls(
        urls, 
        collection,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        write_to_disk=not args.no_disk_write,
        read_from_disk=args.from_disk,
        disk_only=args.disk_only
    )
    
    print("Database creation complete!")

if __name__ == "__main__":
    main()
