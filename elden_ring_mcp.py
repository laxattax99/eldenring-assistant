import os
import json
import random
import sys
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional, Union
from mcp.server.fastmcp import FastMCP
import re

# Print diagnostics to help debug
print("Starting Elden Ring MCP server...", file=sys.stderr)
print(f"Current working directory: {os.getcwd()}", file=sys.stderr)

# Configuration
DATA_DIR = "data"
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chroma_db")
COLLECTION_NAME = "elden_ring_wiki"
EMBEDDING_MODEL = "all-mpnet-base-v2"
MIN_RELEVANCE_SCORE = 0.05  # Lowered from 0.15 to allow more results

# Initialize FastMCP server
mcp = FastMCP("elden_ring")

# Initialize vector database connection
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

try:
    print(f"Trying to connect to ChromaDB at {DB_DIR}", file=sys.stderr)
    
    # Configure ChromaDB to be in read-only mode when used with Claude
    client = chromadb.PersistentClient(
        path=DB_DIR,
        settings=chromadb.Settings(
            anonymized_telemetry=False,  # Disable telemetry
            allow_reset=False,           # Disallow reset
            is_persistent=True           # Make sure it's persistent
        )
    )
    
    # Get the collection - using read-only mode
    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_func
    )
    
    doc_count = collection.count()
    print(f"Connected to collection '{COLLECTION_NAME}' with {doc_count} documents", file=sys.stderr)
    
except Exception as e:
    print(f"Error connecting to ChromaDB: {str(e)}", file=sys.stderr)
    print("Will use dummy responses for demonstration purposes", file=sys.stderr)
    collection = None
    


@mcp.tool()
async def search_elden_ring(query: str, n_results: int = 25) -> str:
    """
    Search for any Elden Ring related information using natural language queries.
    
    Args:
        query: A natural language query about anything in Elden Ring (items, locations, NPCs, ashes of war, etc.)
        
    Returns:
        Relevant information matching the query from the Elden Ring wiki
    """
    print(f"Searching for: '{query}'", file=sys.stderr)
    
    # Debug: Check if ChromaDB connection is working
    if not collection:
        print("WARNING: ChromaDB collection is not available - using dummy responses", file=sys.stderr)
        return f"The Elden Ring database is currently unavailable. This could be due to a connection issue with ChromaDB. Please check your database setup and ensure the ChromaDB collection is properly loaded."
    
    # query chroma DB with our query
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas"],
    )
    
    # Format the response
    if not results:
        # More descriptive error response with database diagnostics
        return (f"No results found for query: '{query}'\n\n"
                f"Database diagnostics:\n"
                f"- ChromaDB collection available: {collection is not None}\n"
                f"- DB directory: {DB_DIR}\n"
                f"- Collection name: {COLLECTION_NAME}\n"
                f"- Embedding model: {EMBEDDING_MODEL}\n"
                f"- Document count: {collection.count() if collection else 'N/A'}\n\n"
                f"Please try the following:\n"
                f"1. Check that your ChromaDB is properly initialized with data\n"
                f"2. Try using more specific keywords in your query\n"
                f"3. If you've recently modified the database, verify the changes were properly saved")
    
    formatted_results = []

    for i, (doc, metadata) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        formatted_results.append({"metadata": metadata, "document": doc})  

    
    return formatted_results

@mcp.tool()
async def search_elden_ring_by_title(title: str, n_results: int = 100) -> str:
    """
    Search for any Elden Ring related information using a title. 
    Sort by chunk_index so the wiki page can be read in order.
    
    Args:
        title: The title of the page to search for.
        n_results: The number of results to return.

    Returns:
        Relevant wiki page information matching the title from the Elden Ring wiki
    """
    print(f"Searching for: '{title}'", file=sys.stderr)
    
    # query chroma DB with our query
    results = collection.query(
        query_texts=[""],
        where={"title": title},
        n_results=n_results,
        include=["documents", "metadatas"],
    )
    
    # Format the response
    if not results:
        return f"No results found for title: '{title}'"
    
    formatted_results = []

    for i, (doc, metadata) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        formatted_results.append({"metadata": metadata, "document": doc})  


    #order formatted results by the metadata filed chunk_index
    formatted_results.sort(key=lambda x: x["metadata"].get("chunk_index", 0))

    #remove any duplicate chunks that have the same chunk_index
    seen_chunk_indices = set()
    unique_results = []
    for result in formatted_results:
        chunk_index = result["metadata"].get("chunk_index")
        if chunk_index not in seen_chunk_indices:
            unique_results.append(result)
            seen_chunk_indices.add(chunk_index)
    formatted_results = unique_results
    
    return formatted_results



if __name__ == "__main__":
    print("Starting Elden Ring MCP server...", file=sys.stderr)
    # Initialize and run the server
    mcp.run(transport='stdio')