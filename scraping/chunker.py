import re
import json
from typing import List, Dict, Any, Optional

def chunk_text(content: str, title: str, url: str, content_type: str, 
              chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Split content into chunks suitable for embedding
    
    Args:
        content: The text content to chunk
        title: The title of the page
        url: The URL of the page
        content_type: The type of content (boss, weapon, etc.)
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of dictionaries, each containing a chunk and its metadata
    """
    # Clean up the content by removing excessive whitespace
    cleaned_content = re.sub(r'\s+', ' ', content).strip()
    
    # Split into paragraphs first to try to maintain logical breaks
    paragraphs = re.split(r'\n+', cleaned_content)
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed chunk size, store the current chunk and start a new one
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            # Store the current chunk with metadata
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {
                    "title": title,
                    "url": url,
                    "type": content_type
                }
            })
            
            # Start a new chunk with overlap from previous chunk if possible
            if len(current_chunk) > chunk_overlap:
                # Get the last N characters from the previous chunk for context
                current_chunk = current_chunk[-chunk_overlap:] + " " + paragraph
            else:
                current_chunk = paragraph
        else:
            # Add the paragraph to the current chunk
            if current_chunk:
                current_chunk += " " + paragraph
            else:
                current_chunk = paragraph
    
    # Don't forget the last chunk if there's anything left
    if current_chunk:
        chunks.append({
            "text": current_chunk.strip(),
            "metadata": {
                "title": title,
                "url": url,
                "type": content_type
            }
        })
    
    return chunks

def chunk_with_headers(content: str, title: str, url: str, content_type: str,
                      chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    More advanced chunking that attempts to preserve header-content relationships
    
    Args:
        content: The text content to chunk
        title: The title of the page
        url: The URL of the page
        content_type: The type of content (boss, weapon, etc.)
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of dictionaries, each containing a chunk and its metadata
    """
    # Try to identify headers in the content
    # This regex looks for patterns like "Header: Text" or "Header Text" (in all caps or title case)
    header_pattern = r'([A-Z][a-z]+(?: [A-Z][a-z]+)*:?\s)'
    
    # Split by potential headers but keep the headers
    segments = re.split(f'({header_pattern})', content)
    
    chunks = []
    current_chunk = ""
    current_header = None
    
    for i, segment in enumerate(segments):
        # If this segment looks like a header
        if re.match(header_pattern, segment):
            current_header = segment.strip()
            continue
            
        # If we have content after a header
        if current_header and segment.strip():
            section_text = f"{current_header} {segment.strip()}"
            
            # If adding this section would exceed chunk size
            if len(current_chunk) + len(section_text) > chunk_size and current_chunk:
                # Store the current chunk
                chunks.append({
                    "text": current_chunk.strip(),
                    "metadata": {
                        "title": title,
                        "url": url,
                        "type": content_type,
                        "section": current_header if current_header != title else None
                    }
                })
                
                # Start a new chunk
                current_chunk = section_text
            else:
                # Add the section to the current chunk
                if current_chunk:
                    current_chunk += " " + section_text
                else:
                    current_chunk = section_text
        else:
            # Handle content without a clear header
            if current_chunk and len(current_chunk) + len(segment) > chunk_size:
                chunks.append({
                    "text": current_chunk.strip(),
                    "metadata": {
                        "title": title,
                        "url": url,
                        "type": content_type,
                        "section": current_header if current_header != title else None
                    }
                })
                current_chunk = segment
            else:
                if current_chunk:
                    current_chunk += " " + segment
                else:
                    current_chunk = segment
    
    # Add the final chunk if anything is left
    if current_chunk:
        chunks.append({
            "text": current_chunk.strip(),
            "metadata": {
                "title": title,
                "url": url,
                "type": content_type,
                "section": current_header if current_header != title else None
            }
        })
    
    return chunks

def save_chunks_to_jsonl(chunks: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save chunks to a JSONL file for later processing
    
    Args:
        chunks: List of chunk dictionaries
        output_file: Path to the output file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + '\n')
    
    print(f"Saved {len(chunks)} chunks to {output_file}")

def process_page(page_data: Dict[str, Any], chunk_size: int = 500, 
                chunk_overlap: int = 50, advanced: bool = True) -> List[Dict[str, Any]]:
    """
    Process a page and chunk its content
    
    Args:
        page_data: Dictionary containing page data (title, url, type, content)
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
        advanced: Whether to use advanced chunking with header detection
        
    Returns:
        List of chunk dictionaries
    """
    if advanced:
        return chunk_with_headers(
            page_data['content'], 
            page_data['title'], 
            page_data['url'], 
            page_data['type'],
            chunk_size,
            chunk_overlap
        )
    else:
        return chunk_text(
            page_data['content'], 
            page_data['title'], 
            page_data['url'], 
            page_data['type'],
            chunk_size,
            chunk_overlap
        )

if __name__ == "__main__":
    # Example usage
    import sys
    from scrape_page import scrape_wiki_page
    
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
        print("Usage: python chunker.py <url> [output_file]")