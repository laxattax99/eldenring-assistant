import json
import sys
import re
from typing import List, Dict, Any

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain.schema import Document

from scrape_page import scrape_wiki_page

def clean_text(text: str) -> str:
    """Clean and normalize text for better chunking"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove duplicate newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def chunk_with_langchain(
    content: str,
    title: str,
    url: str,
    content_type: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Use LangChain's RecursiveCharacterTextSplitter to chunk content
    
    Args:
        content: Text content to chunk
        title: Page title
        url: Page URL
        content_type: Type of content (boss, weapon, etc.)
        chunk_size: Maximum size for each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of dictionaries with chunks and metadata
    """
    # Create a document with metadata
    metadata = {
        "title": title,
        "url": url,
        "type": content_type
    }
    
    # First try to split by headers (treating the content as having markdown-like headers)
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "header1"),
            ("##", "header2"),
            ("###", "header3"),
        ]
    )
    
    # Convert potential wiki headers to markdown headers for better splitting
    # This won't affect the actual content, just helps the splitter find section breaks
    processed_content = content
    header_indicators = ["Location", "Guide", "Notes", "Where to Find", "Combat information"]
    
    for indicator in header_indicators:
        processed_content = processed_content.replace(f"{indicator}:", f"\n# {indicator}\n")
        processed_content = processed_content.replace(f"{indicator} ", f"\n# {indicator}\n")
    
    try:
        # Try to split by headers first
        header_splits = header_splitter.split_text(processed_content)
        
        # Update metadata for each split with any headers found
        docs = []
        for split in header_splits:
            split_metadata = metadata.copy()
            
            # Add header info to metadata if available
            for header_key in ["header1", "header2", "header3"]:
                if header_key in split.metadata:
                    split_metadata["section"] = split.metadata[header_key]
                    break
                    
            docs.append(Document(page_content=split.page_content, metadata=split_metadata))
    except:
        # If header splitting fails, create a single document
        docs = [Document(page_content=content, metadata=metadata)]
    
    # Apply the text splitter to each document to get final chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    chunks = []
    for doc in docs:
        # Split the document by characters
        split_docs = text_splitter.split_documents([doc])
        
        # Convert Document objects to dictionaries
        for split_doc in split_docs:
            chunks.append({
                "text": split_doc.page_content,
                "metadata": split_doc.metadata
            })
    
    return chunks

def process_page(page_data: Dict[str, Any], chunk_size: int = 500, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Process a page into chunks suitable for embedding
    
    Args:
        page_data: Dictionary with page content and metadata
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of chunks with metadata
    """
    if not page_data or "content" not in page_data:
        return []
    
    # Extract page metadata
    url = page_data.get("url", "")
    title = page_data.get("title", "")
    page_type = page_data.get("type", "")
    
    # Handle different content types
    content = page_data["content"]
    
    # Special handling for item pages - keep smaller chunks to preserve item details

    is_item_page = (page_type in ["item", "weapon", "armor", "spell", "incantation", "sorcery", "tear", "talisman", "shield", "staff", "sacred", "flask"])
    
    # Special handling for location pages - larger chunks for better context
    
    is_location_page = (page_type == "location")
    
    # Adjust chunk size based on content type
    adjusted_chunk_size = chunk_size
    adjusted_chunk_overlap = chunk_overlap
    
    if is_item_page:
        # Smaller chunks for items to capture specific details
        adjusted_chunk_size = 400
        adjusted_chunk_overlap = 150  # Higher overlap for items to maintain context
    elif is_location_page:
        # Larger chunks for locations to keep more context
        adjusted_chunk_size = 600
        adjusted_chunk_overlap = 100
    
    # Create text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=adjusted_chunk_size,
        chunk_overlap=adjusted_chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    # Clean and prepare text
    cleaned_content = clean_text(content)
    
    chunks = []
    
    text_chunks = text_splitter.create_documents([cleaned_content])
    
    for i, chunk in enumerate(text_chunks):
        chunks.append({
            "text": chunk.page_content,
            "metadata": {
                "url": url,
                "title": title,
                "page_type": page_type,
                "chunk_index": i
            }
        })
    
    # Special handling for title page - make sure the first chunk has the title information
    if chunks and title:
        first_chunk = chunks[0]
        if title.lower() not in first_chunk["text"].lower():
            title_info = f"{title}\n\n"
            chunks[0]["text"] = title_info + chunks[0]["text"]
    
    return chunks

def save_chunks_to_jsonl(chunks: List[Dict[str, Any]], output_file: str) -> None:
    """Save chunks to a JSONL file for later processing"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + '\n')
    
    print(f"Saved {len(chunks)} chunks to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else "chunks.jsonl"
        
        # Scrape the page
        page_data = scrape_wiki_page(url)
        
        if page_data:
            # Process the page into chunks
            chunks = process_page(page_data)
            
            # Save the chunks to a file
            save_chunks_to_jsonl(chunks, output)
        else:
            print(f"Failed to scrape {url}")
    else:
        print("Usage: python langchain_chunker.py <url> [output_file]")