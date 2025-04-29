import os
import sys
import time
import json
import uuid
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Add the parent directory to the path to import from scraping module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraping.scrape_page import scrape_wiki_page
from scraping.langchain_chunker import process_page
from scraping.wiki_crawler import get_urls_to_process

# Configuration
DATA_DIR = "data"
DB_DIR = os.path.join(DATA_DIR, "chroma_db")
PROCESSED_URLS_FILE = os.path.join(DATA_DIR, "db_processed_urls.json")
COLLECTION_NAME = "elden_ring_wiki"
# Upgraded to a more powerful embedding model - better accuracy for question-answering
EMBEDDING_MODEL = "multi-qa-mpnet-base-dot-v1"  # Upgraded from all-MiniLM-L6-v2
BATCH_SIZE = 100  # How many chunks to process in one batch
DELAY = 0.3  # Delay between scraping pages to be nice to the server

def ensure_dirs():
    """Make sure data directories exist"""
    for directory in [DATA_DIR, DB_DIR]:
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

def process_urls(urls: List[str], collection, chunk_size: int = 500, chunk_overlap: int = 50):
    """
    Process a batch of URLs, extract content, chunk, embed, and store in ChromaDB
    
    Args:
        urls: List of URLs to process
        collection: ChromaDB collection to store chunks in
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
    """
    processed_urls = load_processed_urls()
    urls_to_process = [url for url in urls if url not in processed_urls]
    
    print(f"Processing {len(urls_to_process)} new URLs out of {len(urls)} total")
    
    # Counters for statistics
    total_chunks = 0
    total_processed = 0
    
    for i, url in enumerate(tqdm(urls_to_process, desc="Processing URLs")):
        try:
            # Extract page content
            page_data = scrape_wiki_page(url)
            
            if not page_data:
                print(f"Failed to scrape {url}")
                continue
                
            # Process into chunks
            chunks = process_page(page_data, chunk_size, chunk_overlap)
            
            if not chunks:
                print(f"No chunks generated for {url}")
                continue
            
            # Create a special title-focused chunk for better title matching
            if page_data.get("title") and page_data.get("content"):
                title = page_data["title"]
                # Add a special chunk with title and first 200 characters of content
                title_chunk_text = f"{title} - {page_data['content'][:200]}..."
                title_chunk = {
                    "text": title_chunk_text,
                    "metadata": {
                        "url": page_data["url"],
                        "title": title,
                        "chunk_type": "title_focused",  # Mark as special title chunk
                        "page_type": page_data.get("type", "unknown"),
                        "chunk_index": 0  # Always the first chunk
                    }
                }
                # Add title chunk to regular chunks
                chunks.append(title_chunk)
                
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
            processed_urls.append(url)
            total_chunks += len(chunks)
            total_processed += 1
            
            # Save progress periodically
            if i % 10 == 0:
                save_processed_urls(processed_urls)
                print(f"Progress: {total_processed} URLs processed, {total_chunks} chunks added to DB")
            
            # Be nice to the server
            time.sleep(DELAY)
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    # Save final progress
    save_processed_urls(processed_urls)
    
    print(f"Processing complete.")
    print(f"Total URLs processed: {total_processed}")
    print(f"Total chunks added to DB: {total_chunks}")
    print(f"Total documents in collection: {collection.count()}")

def main():
    """Main function to run the database creation process"""
    print("Initializing Elden Ring Vector Database...")
    ensure_dirs()
    client, collection = init_chroma_db()
    
    # Get URLs from crawler results
    print("Finding URLs to process...")
    urls = get_urls_to_process()
    
    if not urls:
        print("No URLs found to process. Run the wiki_crawler.py script first.")
        return
        
    print(f"Found {len(urls)} URLs to process")
    
    # Process URLs and store in ChromaDB
    process_urls(urls, collection)
    
    print("Database creation complete!")

if __name__ == "__main__":
    main()
