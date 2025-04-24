import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Tuple, Optional
import dotenv
import json
import requests

# Load environment variables for API key
dotenv.load_dotenv()

# Configuration
DATA_DIR = "data"
DB_DIR = os.path.join(DATA_DIR, "chroma_db")
COLLECTION_NAME = "elden_ring_wiki"
# Upgraded to a more powerful embedding model - better accuracy for question-answering
EMBEDDING_MODEL = "multi-qa-mpnet-base-dot-v1"  # Upgraded from all-MiniLM-L6-v2
API_KEY = os.getenv("OPENAI_API_KEY")  # For LLM integration
API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-3.5-turbo"  # Or another model like "gpt-4" if available

class EldenRingChromaEngine:
    """
    Advanced query engine for Elden Ring information using ChromaDB vector database
    """
    
    def __init__(self, db_dir: str = DB_DIR, collection_name: str = COLLECTION_NAME):
        """Initialize the query engine with ChromaDB"""
        print(f"Connecting to ChromaDB at {db_dir}...")
        self.client = chromadb.PersistentClient(path=db_dir)
        
        # Set up embedding function
        self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        
        # Get the collection
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_func
            )
            doc_count = self.collection.count()
            print(f"Connected to collection '{collection_name}' with {doc_count} documents")
        except Exception as e:
            print(f"Error connecting to ChromaDB: {e}")
            print("Make sure to run create_eldenring_db.py first to build the vector database.")
            self.collection = None
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search the vector database for relevant chunks
        
        Args:
            query: The search query
            n_results: Number of results to return
            
        Returns:
            List of search results with documents and metadata
        """
        if not self.collection:
            return []
            
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format the results
        formatted_results = []
        
        if results and 'documents' in results and len(results['documents']) > 0:
            docs = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]
            
            for i, (doc, metadata, distance) in enumerate(zip(docs, metadatas, distances)):
                formatted_results.append({
                    "text": doc,
                    "metadata": metadata,
                    "relevance_score": 1.0 - distance,  # Convert distance to similarity score
                })
        
        return formatted_results
    
    def get_raw_answer(self, query: str, n_results: int = 5) -> str:
        """
        Get a simple answer to a query based on the retrieved documents
        
        Args:
            query: The user's question
            n_results: Number of chunks to retrieve for context
            
        Returns:
            A formatted answer with the relevant information
        """
        results = self.search(query, n_results)
        
        if not results:
            return "I couldn't find any relevant information in the Elden Ring wiki for your question."
        
        # Format the context 
        context = "\n\n".join([result["text"] for result in results])
        
        # Format sources for citation
        sources = []
        for result in results:
            metadata = result["metadata"]
            source = f"{metadata['title']}"
            if 'section' in metadata and metadata['section']:
                source += f" - {metadata['section']}"
            sources.append(f"- {source} ({metadata['url']})")
        
        sources_text = "\n".join(sources)
        
        # Combine into a full answer
        answer = f"Based on the Elden Ring wiki, here's what I found:\n\n{context}\n\nSources:\n{sources_text}"
        return answer
    
    def call_llm_api(self, messages: List[Dict[str, str]]) -> str:
        """
        Call the OpenAI API with the given messages
        
        Args:
            messages: List of message dictionaries in the format expected by the API
            
        Returns:
            The LLM's response text
        """
        if not API_KEY:
            return "Error: No API key provided. Please set your OpenAI API key."
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        data = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error calling LLM API: {str(e)}"
    
    def get_llm_answer(self, query: str, n_results: int = 5) -> str:
        """
        Get an AI-enhanced answer to a query using the LLM API
        
        Args:
            query: The user's question
            n_results: Number of chunks to retrieve for context
            
        Returns:
            The LLM's enhanced answer based on retrieved context
        """
        if not API_KEY:
            print("No OpenAI API key found. Using raw document retrieval instead.")
            return self.get_raw_answer(query, n_results)
        
        results = self.search(query, n_results)
        
        if not results:
            return "I couldn't find any relevant information in the Elden Ring wiki for your question."
        
        # Format the context for the LLM
        context = "\n\n".join([result["text"] for result in results])
        
        # Format sources for citation
        sources = []
        for result in results:
            metadata = result["metadata"]
            source = f"{metadata['title']}"
            if 'section' in metadata and metadata['section']:
                source += f" - {metadata['section']}"
            sources.append(f"{source} ({metadata['url']})")
        
        # Create a prompt for the LLM
        system_prompt = """You are an expert Elden Ring guide who helps players with strategies, builds, and game information.
Answer the user's question based ONLY on the context provided. If the context doesn't contain enough information to answer the question fully, 
acknowledge what you know and what you don't. Always be helpful and guide the player as best as possible based on the available information.
Do not make up information that isn't in the context. Use a friendly, helpful tone as if you're guiding a fellow player.
"""
        
        user_prompt = f"""Question: {query}
        
Context information from the Elden Ring Wiki:
{context}

Remember to only use the information provided in the context to answer the question.
If you need to cite specific information, you can reference these sources: {', '.join(sources)}
"""
        
        # Prepare messages for the API call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call the LLM API
        response = self.call_llm_api(messages)
        return response

def main():
    """CLI interface for the query engine"""
    engine = EldenRingChromaEngine()
    
    if not engine.collection:
        print("Exiting: No valid collection found.")
        return
    
    print("\nElden Ring Knowledge Engine")
    print("===========================")
    print("Ask any question about Elden Ring (weapons, bosses, locations, builds, etc.)")
    print("Type 'quit' or 'exit' to end the session\n")
    
    # Check if API key is available
    use_llm = bool(API_KEY)
    if not use_llm:
        print("Note: No OpenAI API key found. Using raw document retrieval mode.")
        print("For enhanced answers, set the OPENAI_API_KEY environment variable.\n")
    
    while True:
        query = input("\nYour question: ")
        if query.lower() in ['quit', 'exit']:
            break
            
        print("\nSearching the Elden Ring knowledge base...")
        
        if use_llm:
            answer = engine.get_llm_answer(query)
        else:
            answer = engine.get_raw_answer(query)
            
        print("\n" + answer)

if __name__ == "__main__":
    main()