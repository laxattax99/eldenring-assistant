import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any

# Configuration
DATA_DIR = "data"
DB_DIR = os.path.join(DATA_DIR, "chroma_db")
COLLECTION_NAME = "elden_ring_wiki"
EMBEDDING_MODEL = "all-mpnet-base-v2"

# Test queries
TEST_QUERIES = [
    "Hookclaws",
    "malenia",
    "stormveil",
    "rykard",
    "stormhill",
    "mistwood",
    "renala"
]

def connect_to_db():
    """Connect to the ChromaDB and return the collection"""
    print(f"Connecting to ChromaDB at {DB_DIR}...")
    client = chromadb.PersistentClient(path=DB_DIR)
    
    # Set up embedding function
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    
    # Get the collection
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
        doc_count = collection.count()
        print(f"Connected to collection '{COLLECTION_NAME}' with {doc_count} documents")
        return collection
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")
        return None

def test_search(collection, query: str, n_results: int = 5):
    """Test a specific search query and display results"""
    print(f"\n\n{'='*80}")
    print(f"SEARCH QUERY: '{query}'")
    print(f"{'='*80}")
    
    # Perform the search
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    if not results or not results["documents"] or not results["documents"][0]:
        print("No results found for this query.")
        return
    
    # Display results
    for i, (doc, metadata) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        # Calculate a snippet (show first 150 chars)
        snippet = doc[:150] + "..." if len(doc) > 150 else doc
        
        # Format and display the result
        print(f"\nResult {i+1}:")
        print(f"Title: {metadata.get('title', 'Unknown')}")
        if 'section' in metadata and metadata['section']:
            print(f"Section: {metadata['section']}")
        print(f"Source: {metadata.get('url', 'Unknown URL')}")
        print(f"Snippet: {snippet}")
        print("-" * 80)

def main():
    """Main function to test specific searches"""
    print("Testing Specific Searches in Elden Ring ChromaDB...")
    collection = connect_to_db()
    
    if not collection:
        print("Failed to connect to the database.")
        return
    
    # Run each test query
    for query in TEST_QUERIES:
        test_search(collection, query, n_results=5)
    
    print("\nSearch testing complete!")

if __name__ == "__main__":
    main()