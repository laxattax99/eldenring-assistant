import os
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple

# Configuration
DATA_DIR = "data"
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.pkl")
MODEL_NAME = "all-MiniLM-L6-v2"  # Same model used for embedding

class EldenRingQueryEngine:
    """
    Query engine for Elden Ring information using vector similarity search
    """
    
    def __init__(self, embeddings_file: str = EMBEDDINGS_FILE, model_name: str = MODEL_NAME):
        """Initialize the query engine with pre-computed embeddings"""
        print(f"Loading embeddings from {embeddings_file}...")
        with open(embeddings_file, 'rb') as f:
            self.data = pickle.load(f)
            
        self.chunks = self.data['chunks']
        self.embeddings = self.data['embeddings']
        self.model_name = self.data.get('model', model_name)
        
        # Load the embedding model
        print(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        print(f"Query engine initialized with {len(self.chunks)} chunks of Elden Ring knowledge")
    
    def similarity_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find the most similar chunks to the query
        
        Args:
            query: The user's question
            top_k: Number of results to return
            
        Returns:
            List of the most relevant chunks with their metadata
        """
        # Convert query to embedding
        query_embedding = self.model.encode([query])[0]
        
        # Calculate cosine similarity
        similarities = []
        for i, embedding in enumerate(self.embeddings):
            # Cosine similarity = dot product of normalized vectors
            similarity = np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding))
            similarities.append((i, similarity))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results
        results = []
        for idx, score in similarities[:top_k]:
            result = {
                "chunk": self.chunks[idx],
                "score": float(score),
                "text": self.chunks[idx]["text"],
                "metadata": self.chunks[idx]["metadata"]
            }
            results.append(result)
            
        return results
    
    def answer_question(self, question: str, top_k: int = 5) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Answer a question about Elden Ring using the retrieved context
        
        Args:
            question: The user's question
            top_k: Number of chunks to retrieve for context
            
        Returns:
            A tuple containing the formatted answer and the relevant chunks
        """
        # Retrieve relevant chunks
        relevant_chunks = self.similarity_search(question, top_k)
        
        # Format the context for the answer
        context = "\n\n".join([chunk["text"] for chunk in relevant_chunks])
        
        # Format sources for citation
        sources = []
        for chunk in relevant_chunks:
            metadata = chunk["metadata"]
            source = f"{metadata['title']}"
            if 'section' in metadata and metadata['section']:
                source += f" - {metadata['section']}"
            sources.append(f"- {source} ({metadata['url']})")
        
        sources_text = "\n".join(sources)
        
        # Combined answer with both context and sources
        answer = f"Based on the Elden Ring wiki, here's what I found:\n\n{context}\n\nSources:\n{sources_text}"
        
        return answer, relevant_chunks

if __name__ == "__main__":
    # Simple CLI for testing the query engine
    engine = EldenRingQueryEngine()
    
    print("\nElden Ring Assistant")
    print("===================")
    print("Ask questions about weapons, bosses, locations, or builds in Elden Ring")
    print("Type 'quit' or 'exit' to end the session\n")
    
    while True:
        question = input("\nYour question: ")
        if question.lower() in ['quit', 'exit']:
            break
            
        answer, _ = engine.answer_question(question)
        print("\n" + answer)