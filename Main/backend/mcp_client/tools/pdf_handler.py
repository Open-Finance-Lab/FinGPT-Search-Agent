"""simple pdf file handler for pageindex integration"""

from agents import function_tool
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# track uploaded pdfs
_uploaded_pdfs = {}

# upload directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "pdfs"


@function_tool
def register_uploaded_pdf(filename: str, file_id: str = "", description: str = "") -> str:
    """
    register an uploaded pdf file for reading
    use this after user uploads a pdf through the ui
    
    args:
        filename: name of the uploaded file
        file_id: unique file id (optional)
        description: optional description of what the pdf contains
    
    returns:
        confirmation message with file path for pageindex
    """
    try:
        # check uploads directory
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # find the file
        matches = list(UPLOAD_DIR.glob(f"*{filename}*"))
        if file_id:
            matches = [p for p in matches if file_id in p.name]
        
        if not matches:
            return f"error: uploaded pdf not found: {filename}\ncheck uploads with list_uploaded_pdfs()"
        
        path = matches[0]
        
        # store for reference
        _uploaded_pdfs[str(path)] = {
            "path": str(path),
            "name": path.name,
            "size": path.stat().st_size,
            "description": description,
            "file_id": file_id
        }
        
        logger.info(f"registered uploaded pdf: {path.name}")
        return f"registered uploaded pdf: {path.name}\npath: {path}\nsize: {path.stat().st_size / 1024:.1f} KB\n\nnow use pageindex tools to read this pdf. pass path: {path}"
    
    except Exception as e:
        return f"error: {str(e)}"


@function_tool
def list_uploaded_pdfs() -> str:
    """
    show all pdfs available in the uploads directory
    use this to see what pdfs the user has uploaded
    """
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        pdfs = list(UPLOAD_DIR.glob("*.pdf"))
        
        if not pdfs:
            return "no pdfs uploaded yet. user needs to upload a pdf file first."
        
        output = f"uploaded pdfs ({len(pdfs)}):\n\n"
        for pdf_path in pdfs:
            output += f"• {pdf_path.name}\n"
            output += f"  path: {pdf_path}\n"
            output += f"  size: {pdf_path.stat().st_size / 1024:.1f} KB\n"
            
            # check if registered
            if str(pdf_path) in _uploaded_pdfs:
                desc = _uploaded_pdfs[str(pdf_path)].get('description', '')
                if desc:
                    output += f"  description: {desc}\n"
            output += "\n"
        
        return output
    
    except Exception as e:
        return f"error: {str(e)}"


@function_tool
def get_pdf_info(pdf_name: str) -> str:
    """
    get information about a registered pdf by name
    
    args:
        pdf_name: name of the pdf file
    """
    # find by name
    for path, info in _uploaded_pdfs.items():
        if info['name'].lower() == pdf_name.lower():
            output = f"pdf: {info['name']}\n"
            output += f"path: {path}\n"
            output += f"size: {info['size'] / 1024:.1f} KB\n"
            if info['description']:
                output += f"description: {info['description']}\n"
            return output
    
    return f"pdf not found: {pdf_name}\navailable pdfs: {', '.join([info['name'] for info in _uploaded_pdfs.values()])}"

