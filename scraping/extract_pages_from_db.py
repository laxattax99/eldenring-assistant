#!/usr/bin/env python3

import os
import sys
import json
import hashlib
import re
from tqdm import tqdm
import chromadb
from chromadb.utils import embedding_functions
from collections import defaultdict
import argparse
from typing import Dict, List, Any, Optional, Set

# Add the parent directory to the path to import from scraping module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration - matching create_eldenring_db.py
DATA_DIR = "data"
DB_DIR = os.path.join(DATA_DIR, "chroma_db")
PAGE_CONTENT_DIR = os.path.join(DATA_DIR, "page_content")
PROCESSED_URLS_FILE = os.path.join(DATA_DIR, "db_processed_urls.json")
COLLECTION_NAME = "elden_ring_wiki"
EMBEDDING_MODEL = "all-mpnet-base-v2"

def ensure_dirs():
    """Make sure data directories exist"""
    for directory in [DATA_DIR, PAGE_CONTENT_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

def sanitize_filename(title: str) -> str:
    """Convert a title to a valid filename"""
    # Replace invalid filename characters with underscores
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", title)
    # Replace spaces with underscores
    sanitized = sanitized.replace(" ", "_")
    # Remove other problematic characters
    sanitized = re.sub(r'[^\w\-_\.]', '', sanitized)
    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    # Ensure filename is not empty
    if not sanitized:
        return "unknown"
    return sanitized

def get_filename_from_title_and_url(title: str, url: str) -> str:
    """Generate a filename for storing page content based on title and URL"""
    if title:
        # Use sanitized title
        filename = sanitize_filename(title)
        return filename + ".json"
    else:
        # Fall back to URL hash if no title
        hash_object = hashlib.md5(url.encode())
        return hash_object.hexdigest() + '.json'

def save_page_to_disk(page_data: Dict[str, Any]) -> bool:
    """Save page content to disk using title as filename"""
    if not page_data or 'url' not in page_data:
        return False
    
    url = page_data['url']
    title = page_data.get('title', '')
    
    filename = get_filename_from_title_and_url(title, url)
    filepath = os.path.join(PAGE_CONTENT_DIR, filename)
    
    # If file exists with this name but different content, append a hash to avoid conflicts
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if existing_data.get('url') != url:
                    # Title collision with different URL, append part of URL hash
                    hash_suffix = hashlib.md5(url.encode()).hexdigest()[:8]
                    base_name, ext = os.path.splitext(filename)
                    filename = f"{base_name}_{hash_suffix}{ext}"
                    filepath = os.path.join(PAGE_CONTENT_DIR, filename)
        except:
            # If we can't read the file, use a unique name
            hash_suffix = hashlib.md5(url.encode()).hexdigest()[:8]
            base_name, ext = os.path.splitext(filename)
            filename = f"{base_name}_{hash_suffix}{ext}"
            filepath = os.path.join(PAGE_CONTENT_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving page content to disk: {e}")
        return False

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
    except Exception as e:
        print(f"Error loading collection: {e}")
        print("Make sure your database has been created first.")
        sys.exit(1)
        
    return client, collection

def create_url_to_filename_map() -> Dict[str, str]:
    """Create a mapping of URLs to filenames for existing files"""
    url_to_filename = {}
    
    if not os.path.exists(PAGE_CONTENT_DIR):
        return url_to_filename
        
    for filename in os.listdir(PAGE_CONTENT_DIR):
        if not filename.endswith('.json'):
            continue
            
        filepath = os.path.join(PAGE_CONTENT_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'url' in data:
                    url_to_filename[data['url']] = filename
        except:
            continue
            
    return url_to_filename

def extract_pages_from_db(collection, batch_size: int = 1000):
    """
    Extract page content from ChromaDB and reconstruct original pages
    """
    print("Extracting page content from ChromaDB...")
    
    # Get total count of documents in collection
    total_docs = collection.count()
    print(f"Found {total_docs} documents in collection")
    
    if total_docs == 0:
        print("No documents found in the database.")
        return
    
    # Dictionary to store page content by URL
    pages_by_url = defaultdict(lambda: {"content": "", "title": "", "url": "", "type": ""})
    
    # Create mapping of existing files
    url_to_filename = create_url_to_filename_map()
    processed_urls = set(url_to_filename.keys())
    
    # Process in batches to avoid memory issues
    offset = 0
    
    progress_bar = tqdm(total=total_docs, desc="Extracting pages")
    
    while offset < total_docs:
        # Get a batch of documents
        batch = collection.get(
            limit=batch_size,
            offset=offset,
            include=["metadatas", "documents"]
        )
        
        batch_metadatas = batch["metadatas"]
        batch_documents = batch["documents"]
        
        # Process each document in the batch
        for i, (metadata, document) in enumerate(zip(batch_metadatas, batch_documents)):
            if not metadata or "url" not in metadata:
                continue
            
            url = metadata["url"]
            # Directly use the title from metadata as you suggested
            title = metadata.get("title", "")
            page_type = metadata.get("page_type", "")
            
            # Skip if URL has been processed
            if url in processed_urls:
                continue
            
            # Update page data
            pages_by_url[url]["url"] = url
            # Use the title directly from the chunk metadata
            if title and not pages_by_url[url]["title"]:
                pages_by_url[url]["title"] = title
            pages_by_url[url]["type"] = page_type if page_type else pages_by_url[url]["type"]
            
            # Append content (we'll sort and clean up later)
            if "chunk_index" in metadata and document:
                pages_by_url[url]["content_chunks"] = pages_by_url[url].get("content_chunks", [])
                pages_by_url[url]["content_chunks"].append({
                    "index": metadata.get("chunk_index", 0),
                    "text": document
                })
        
        # Update offset and progress
        offset += batch_size
        progress_bar.update(min(batch_size, total_docs - (offset - batch_size)))
        
    progress_bar.close()
    
    # Process pages - sort chunks and combine content
    print("Reconstructing pages from chunks...")
    pages_processed = 0
    pages_saved = 0
    
    for url, page_data in tqdm(pages_by_url.items(), desc="Saving pages"):
        # Skip if URL has been processed already
        if url in processed_urls:
            continue
            
        # If page has chunks, sort them by index and combine
        if "content_chunks" in page_data:
            chunks = sorted(page_data["content_chunks"], key=lambda x: x.get("index", 0))
            page_data["content"] = "\n".join(chunk["text"] for chunk in chunks)
            del page_data["content_chunks"]  # Remove the chunks to keep the file clean
        
        # Ensure we have at least some content
        if not page_data.get("content"):
            continue
        
        # Print filename that will be used for debugging
        title = page_data.get('title', '')
        filename = get_filename_from_title_and_url(title, url)
        if pages_processed < 5:  # Just show the first few for verification
            print(f"URL: {url} -> Title: '{title}' -> Filename: {filename}")
            
        # Save page to disk
        if save_page_to_disk(page_data):
            processed_urls.add(url)
            pages_saved += 1
            
        pages_processed += 1
    
    print(f"Processed {pages_processed} pages extracted from the database")
    print(f"Saved {pages_saved} pages to disk")
    
    return processed_urls

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Extract page content from Chroma DB and save to disk")
    parser.add_argument("--batch-size", type=int, default=1000,
                        help="Number of documents to process in one batch (default: 1000)")
    parser.add_argument("--rename-existing", action="store_true",
                        help="Rename existing files to use title-based filenames")
    parser.add_argument("--print-metadata-sample", action="store_true",
                        help="Print a sample of metadata from the database to inspect")
    return parser.parse_args()


def print_metadata_sample(collection, sample_size=5):
    """Print a sample of metadata from the database to inspect"""
    print(f"Printing sample of {sample_size} metadata entries from the database:")
    try:
        # Get a small batch of documents
        batch = collection.get(
            limit=sample_size,
            include=["metadatas"]
        )
        
        for i, metadata in enumerate(batch["metadatas"]):
            print(f"\nMetadata {i+1}:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error retrieving metadata: {e}")

def main():
    """Main function"""
    args = parse_arguments()
    
    print("Initializing...")
    ensure_dirs()
    
    # Initialize ChromaDB
    client, collection = init_chroma_db()
    
    # Print metadata sample if requested
    if args.print_metadata_sample:
        print_metadata_sample(collection)
        return
    
    # Extract pages from DB
    processed_urls = extract_pages_from_db(collection, batch_size=args.batch_size)
    
    print("Page extraction complete!")
    print(f"Page content saved to: {os.path.abspath(PAGE_CONTENT_DIR)}")

if __name__ == "__main__":
    main()