"""
File RAG (Retrieval-Augmented Generation) - Answers questions using file content
"""
from typing import List, Dict, Any, Optional
from .file_retriever import FileRetriever
from .llm import call_llm


class FileRAG:
    """
    RAG system for answering questions using uploaded file content
    """
    
    def __init__(
        self,
        file_retriever: FileRetriever,
        llm_model: str = "openai/gpt-oss-120b"
    ):
        """Initialize File RAG"""
        self.file_retriever = file_retriever
        self.llm_model = llm_model
    
    def answer_question(
        self,
        user_id: str,
        question: str,
        file_type: Optional[str] = None,
        num_sources: int = 3
    ) -> Dict[str, Any]:
        """
        Answer a question using file content
        
        Args:
            user_id: User ID
            question: Question to answer
            file_type: Optional file type filter
            num_sources: Number of source files to use
        
        Returns:
            Dict with answer and sources
        """
        # Search for relevant files
        relevant_files = self.file_retriever.search_files(
            user_id=user_id,
            query=question,
            file_type=file_type,
            limit=num_sources
        )
        
        if not relevant_files:
            return {
                'answer': "I couldn't find any relevant files to answer your question.",
                'sources': [],
                'confidence': 0.0
            }
        
        # Build context from file content
        context_parts = []
        sources = []
        
        for i, file in enumerate(relevant_files):
            context_parts.append(f"[Source {i+1}: {file['filename']}]")
            context_parts.append(file['content_text'][:2000])  # Limit per file
            context_parts.append("")
            
            sources.append({
                'filename': file['filename'],
                'file_type': file['file_type'],
                'similarity': file.get('similarity', 0)
            })
        
        context = "\n".join(context_parts)
        
        # Create prompt
        prompt = f"""Based on the following file content, answer the question.
Be specific and cite which source you're using.

Context:
{context}

Question: {question}

Answer:"""
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that answers questions based on provided documents."},
            {"role": "user", "content": prompt}
        ]
        
        # Generate answer
        try:
            answer = call_llm(messages, model=self.llm_model)
            
            # Estimate confidence based on file similarity
            avg_similarity = sum(s['similarity'] for s in sources) / len(sources) if sources else 0
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': avg_similarity
            }
        except Exception as e:
            print(f"Error generating answer: {e}")
            return {
                'answer': f"Error generating answer: {str(e)}",
                'sources': sources,
                'confidence': 0.0
            }
    
    def chat_with_files(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        file_type: Optional[str] = None
    ) -> str:
        """
        Have a conversation with context from files
        
        Args:
            user_id: User ID
            messages: Chat history
            file_type: Optional file type filter
        
        Returns:
            Assistant's response
        """
        if not messages:
            return "No messages provided."
        
        # Get last user message
        last_message = messages[-1]['content']
        
        # Search for relevant files
        relevant_files = self.file_retriever.search_files(
            user_id=user_id,
            query=last_message,
            file_type=file_type,
            limit=2
        )
        
        # Add file context to system message
        context_parts = ["You have access to the following documents:"]
        
        for file in relevant_files:
            context_parts.append(f"\n[{file['filename']}]")
            context_parts.append(file['content_text'][:1500])
        
        context = "\n".join(context_parts)
        
        # Build messages with context
        chat_messages = [
            {"role": "system", "content": f"You are a helpful assistant. {context}"},
            *messages
        ]
        
        # Generate response
        try:
            response = call_llm(chat_messages, model=self.llm_model)
            return response
        except Exception as e:
            print(f"Error in chat: {e}")
            return f"Error: {str(e)}"
    
    def summarize_all_files(
        self,
        user_id: str,
        file_type: Optional[str] = None
    ) -> str:
        """
        Generate a summary of all user's files
        
        Args:
            user_id: User ID
            file_type: Optional file type filter
        
        Returns:
            Summary text
        """
        files = self.file_retriever.get_user_files(
            user_id=user_id,
            file_type=file_type,
            limit=10
        )
        
        if not files:
            return "No files found."
        
        # Retrieve full content for each file
        file_contents = []
        for file in files:
            full_file = self.file_retriever.get_file_by_id(file['id'])
            if full_file:
                file_contents.append({
                    'filename': full_file['filename'],
                    'content': full_file['content_text'][:1000]  # Limit per file
                })
        
        # Build prompt
        content_text = "\n\n".join([
            f"[{fc['filename']}]\n{fc['content']}"
            for fc in file_contents
        ])
        
        prompt = f"""Provide a comprehensive summary of the following documents:

{content_text}

Summary:"""
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes documents."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            summary = call_llm(messages, model=self.llm_model)
            return summary
        except Exception as e:
            print(f"Error generating summary: {e}")
            return f"Error: {str(e)}"
