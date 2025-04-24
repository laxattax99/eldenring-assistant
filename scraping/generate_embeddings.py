import os
import json
import sys
from typing import List, Dict, Any
import pickle

from sentence_transformers import SentenceTransformer

# Configuration
DATA_DIR = "data"
CHUNKS_FILE = os.path.join(DATA_DIR, "chunks.jsonl")
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.pkl")
# Upgraded to a more powerful model - better accuracy for question-answering
MODEL_NAME = "multi-qa-mpnet-base-dot-v1"  # Upgraded from all-MiniLM-L6-v2

def ensure_data_dir():
    """Make sure data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created data directory: {DATA_DIR}")

def load_chunks(chunks_file: str) -> List[Dict[str, Any]]:
    """Load chunks from a JSONL file"""
    chunks = []
    with open(chunks_file, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))
    
    print(f"Loaded {len(chunks)} chunks from {chunks_file}")
    return chunks

def generate_embeddings(chunks: List[Dict[str, Any]], model_name: str = MODEL_NAME) -> Dict[str, Any]:
    """Generate embeddings for chunks using sentence-transformers"""
    # Initialize the embedding model
    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Extract just the text content for embedding
    texts = [chunk["text"] for chunk in chunks]
    
    # Generate embeddings
    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True)
    
    # Create a dictionary with chunks and their embeddings
    embeddings_data = {
        "chunks": chunks,
        "embeddings": embeddings,
        "model": model_name
    }
    
    print(f"Generated {len(embeddings)} embeddings with dimension {embeddings[0].shape[0]}")
    return embeddings_data

def save_embeddings(embeddings_data: Dict[str, Any], output_file: str):
    """Save embeddings and chunks to a pickle file"""
    with open(output_file, 'wb') as f:
        pickle.dump(embeddings_data, f)
    
    print(f"Saved embeddings to {output_file}")

def main():
    """Main function to generate embeddings"""
    ensure_data_dir()
    
    # Check if chunks file exists
    if not os.path.exists(CHUNKS_FILE):
        print(f"Error: Chunks file not found at {CHUNKS_FILE}")
        print("Run batch_process.py first to generate chunks.")
        return
    
    # Load the chunks
    chunks = load_chunks(CHUNKS_FILE)
    
    # Generate embeddings
    embeddings_data = generate_embeddings(chunks)
    
    # Save embeddings
    save_embeddings(embeddings_data, EMBEDDINGS_FILE)
    
    print("Embedding generation complete!")
    print(f"Total chunks: {len(chunks)}")
    print(f"Model used: {MODEL_NAME}")
    print(f"Output file: {EMBEDDINGS_FILE}")
    print("\nYou can now use these embeddings for similarity search!")

if __name__ == "__main__":
    main()