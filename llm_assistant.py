import os
import json
import requests
from typing import List, Dict, Any, Optional
from query_engine import EldenRingQueryEngine

# Load your API key from environment variable or config file
# You should set this in your environment or create a .env file
import dotenv
dotenv.load_dotenv()

# Configuration
API_KEY = os.getenv("OPENAI_API_KEY")  # Set your OpenAI API key as an environment variable
API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-3.5-turbo"  # Or another model like "gpt-4" if available to you

class EldenRingLLMAssistant:
    """
    Elden Ring assistant that combines vector search with LLM capabilities
    """
    
    def __init__(self, api_key: Optional[str] = API_KEY, model: str = MODEL):
        """Initialize the LLM assistant with the query engine"""
        self.query_engine = EldenRingQueryEngine()
        self.api_key = api_key
        self.model = model
        
        if not self.api_key:
            print("Warning: No API key found. Please set the OPENAI_API_KEY environment variable.")
    
    def call_llm_api(self, messages: List[Dict[str, str]]) -> str:
        """
        Call the OpenAI API with the given messages
        
        Args:
            messages: List of message dictionaries in the format expected by the API
            
        Returns:
            The LLM's response text
        """
        if not self.api_key:
            return "Error: No API key provided. Please set your OpenAI API key."
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
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
    
    def answer_question(self, question: str, top_k: int = 5) -> str:
        """
        Answer a question about Elden Ring using the query engine and LLM
        
        Args:
            question: The user's question
            top_k: Number of chunks to retrieve for context
            
        Returns:
            The LLM's answer based on retrieved context
        """
        # Retrieve relevant chunks from the query engine
        relevant_chunks = self.query_engine.similarity_search(question, top_k)
        
        # Format the context for the LLM
        context = "\n\n".join([chunk["text"] for chunk in relevant_chunks])
        
        # Format sources for citation
        sources = []
        for chunk in relevant_chunks:
            metadata = chunk["metadata"]
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
        
        user_prompt = f"""Question: {question}
        
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

if __name__ == "__main__":
    # First check if API key is available
    if not API_KEY:
        print("Warning: No OpenAI API key found. Set the OPENAI_API_KEY environment variable.")
        print("Switching to basic query mode (no LLM enhancement)...")
        from query_engine import EldenRingQueryEngine
        engine = EldenRingQueryEngine()
        
        print("\nElden Ring Assistant (Basic Mode)")
        print("================================")
        print("Ask questions about weapons, bosses, locations, or builds in Elden Ring")
        print("Type 'quit' or 'exit' to end the session\n")
        
        while True:
            question = input("\nYour question: ")
            if question.lower() in ['quit', 'exit']:
                break
                
            answer, _ = engine.answer_question(question)
            print("\n" + answer)
    else:
        # Interactive CLI for the LLM assistant
        assistant = EldenRingLLMAssistant()
        
        print("\nElden Ring LLM Assistant")
        print("========================")
        print("Ask questions about weapons, bosses, locations, or builds in Elden Ring")
        print("Type 'quit' or 'exit' to end the session\n")
        
        while True:
            question = input("\nYour question: ")
            if question.lower() in ['quit', 'exit']:
                break
                
            print("\nThinking...")
            answer = assistant.answer_question(question)
            print("\n" + answer)