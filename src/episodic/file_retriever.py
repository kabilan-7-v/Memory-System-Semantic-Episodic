"""
File Retriever - Searches and retrieves file content from database
"""
from typing import List, Dict, Any, Optional
from datetime import datetime


class FileRetriever:
    """
    Retrieves files and file content from the memory system
    """
    
    def __init__(self, db_conn=None, embedding_service=None):
        """Initialize file retriever"""
        self.db_conn = db_conn
        self.embedding_service = embedding_service
    
    def search_files(
        self,
        user_id: str,
        query: str,
        file_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for files using hybrid search
        
        Args:
            user_id: User ID
            query: Search query
            file_type: Optional file type filter
            limit: Maximum results
        
        Returns:
            List of matching files
        """
        if not self.db_conn:
            return []
        
        # Generate embedding for query
        query_embedding = None
        if self.embedding_service:
            query_embedding = self.embedding_service.encode(query)
        
        # Build SQL query
        sql = """
            SELECT 
                id,
                filename,
                file_type,
                content_text,
                upload_date,
                metadata,
                1 - (content_embedding <=> %s::vector) AS similarity
            FROM user_files
            WHERE user_id = %s
        """
        
        params = [query_embedding, user_id] if query_embedding else [None, user_id]
        
        if file_type:
            sql += " AND file_type = %s"
            params.append(file_type)
        
        sql += " ORDER BY similarity DESC LIMIT %s"
        params.append(limit)
        
        # Execute query
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            print(f"Error searching files: {e}")
            return []
    
    def get_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get file by ID
        
        Args:
            file_id: File ID
        
        Returns:
            File data or None
        """
        if not self.db_conn:
            return None
        
        sql = """
            SELECT 
                id,
                user_id,
                filename,
                file_type,
                content_text,
                content_embedding,
                upload_date,
                metadata
            FROM user_files
            WHERE id = %s
        """
        
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(sql, [file_id])
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"Error getting file: {e}")
            return None
    
    def get_user_files(
        self,
        user_id: str,
        file_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all files for a user
        
        Args:
            user_id: User ID
            file_type: Optional file type filter
            limit: Maximum results
        
        Returns:
            List of user files
        """
        if not self.db_conn:
            return []
        
        sql = """
            SELECT 
                id,
                filename,
                file_type,
                upload_date,
                metadata
            FROM user_files
            WHERE user_id = %s
        """
        
        params = [user_id]
        
        if file_type:
            sql += " AND file_type = %s"
            params.append(file_type)
        
        sql += " ORDER BY upload_date DESC LIMIT %s"
        params.append(limit)
        
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            print(f"Error getting user files: {e}")
            return []
    
    def delete_file(self, file_id: int) -> bool:
        """
        Delete a file
        
        Args:
            file_id: File ID
        
        Returns:
            True if deleted, False otherwise
        """
        if not self.db_conn:
            return False
        
        sql = "DELETE FROM user_files WHERE id = %s"
        
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(sql, [file_id])
                self.db_conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
