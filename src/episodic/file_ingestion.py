"""
File Ingestion Service - Handles file uploads and processing
Supports PDF, TXT, MD, DOCX file formats
"""
from typing import Dict, Any, Optional
import os
from datetime import datetime
from pathlib import Path

# Optional dependencies for file format support
try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PDF_SUPPORT = True
    except ImportError:
        PDF_SUPPORT = False
        PdfReader = None

try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False


class FileIngestionService:
    """
    Service for ingesting files into the memory system
    """
    
    def __init__(self, db_conn=None):
        """Initialize file ingestion service"""
        self.db_conn = db_conn
        self.supported_formats = ['.txt', '.md', '.pdf', '.docx', '.json']
    
    def ingest_file(
        self,
        user_id: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest a file into the system
        
        Args:
            user_id: User ID
            file_path: Path to the file
            metadata: Optional metadata
        
        Returns:
            Dict with ingestion results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Read file content
        content = self._read_file(file_path, file_ext)
        
        # Extract metadata
        file_metadata = {
            'filename': Path(file_path).name,
            'file_type': file_ext[1:],  # Remove dot
            'file_size': os.path.getsize(file_path),
            'upload_date': datetime.now().isoformat(),
            **(metadata or {})
        }
        
        return {
            'user_id': user_id,
            'content': content,
            'metadata': file_metadata,
            'status': 'ingested'
        }
    
    def _read_file(self, file_path: str, file_ext: str) -> str:
        """
        Read file content based on format
        
        Args:
            file_path: Path to file
            file_ext: File extension
        
        Returns:
            File content as string
        """
        if file_ext in ['.txt', '.md', '.json']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif file_ext == '.pdf':
            return self._read_pdf(file_path)
        
        elif file_ext == '.docx':
            return self._read_docx(file_path)
        
        else:
            raise ValueError(f"Unsupported format: {file_ext}")
    
    def _read_pdf(self, file_path: str) -> str:
        """Read PDF file"""
        if not PDF_SUPPORT:
            return "[PDF content - pypdf not installed. Install with: pip install pypdf]"
        
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            return '\n'.join(text)
    
    def _read_docx(self, file_path: str) -> str:
        """Read DOCX file"""
        if not DOCX_SUPPORT:
            return "[DOCX content - python-docx not installed. Install with: pip install python-docx]"
        
        doc = docx.Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    
    def batch_ingest(
        self,
        user_id: str,
        file_paths: list,
        metadata: Optional[Dict[str, Any]] = None
    ) -> list:
        """
        Ingest multiple files
        
        Args:
            user_id: User ID
            file_paths: List of file paths
            metadata: Optional metadata
        
        Returns:
            List of ingestion results
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.ingest_file(user_id, file_path, metadata)
                results.append(result)
            except Exception as e:
                results.append({
                    'file_path': file_path,
                    'status': 'failed',
                    'error': str(e)
                })
        return results
