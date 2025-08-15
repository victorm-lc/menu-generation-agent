#!/usr/bin/env python3
"""
Convert restaurant_report.pdf to markdown using LangChain native tools.
"""

from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from typing import List


def convert_pdf_to_markdown(pdf_path: str = "restaurant_report.pdf", output_path: str = "restaurant_report.md") -> None:
    """Convert PDF to markdown using LangChain PDF loader."""
    
    # Check if PDF exists
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF file '{pdf_path}' not found")
    
    # Load PDF using LangChain's PyPDFLoader
    loader = PyPDFLoader(pdf_path)
    documents: List[Document] = loader.load()
    
    # Convert documents to markdown format
    markdown_content = ""
    
    for i, doc in enumerate(documents):
        # Add page separator for multi-page documents
        if i > 0:
            markdown_content += "\n\n---\n\n"
        
        # Add page header
        markdown_content += f"# Page {i + 1}\n\n"
        
        # Add document content with basic formatting
        content = doc.page_content.strip()
        
        # Basic markdown formatting
        # Convert common patterns to markdown
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue
                
            # Check if line looks like a header (all caps, short)
            if line.isupper() and len(line) < 100:
                formatted_lines.append(f"## {line}")
            else:
                formatted_lines.append(line)
        
        markdown_content += '\n'.join(formatted_lines)
        
        # Add metadata if available
        if doc.metadata:
            markdown_content += f"\n\n*Source: {doc.metadata.get('source', 'Unknown')}*"
    
    # Save to markdown file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"Successfully converted '{pdf_path}' to '{output_path}'")
    print(f"Total pages processed: {len(documents)}")


if __name__ == "__main__":
    convert_pdf_to_markdown()