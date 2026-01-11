"""
File Summarizer - Generates summaries of file content using LLM
"""
from typing import Dict, Any, Optional
from .llm import call_llm


class FileSummarizer:
    """
    Generates summaries and extracts key information from files
    """
    
    def __init__(self, llm_model: str = "openai/gpt-oss-120b"):
        """Initialize file summarizer"""
        self.llm_model = llm_model
    
    def summarize_file(
        self,
        content: str,
        file_type: str,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Generate summary of file content
        
        Args:
            content: File content
            file_type: Type of file
            max_tokens: Maximum tokens for summary
        
        Returns:
            Dict with summary and metadata
        """
        if not content or len(content.strip()) == 0:
            return {
                'summary': '',
                'key_points': [],
                'topics': []
            }
        
        # Truncate content if too long
        max_content_length = 10000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        # Create prompt
        prompt = f"""Analyze the following {file_type} file content and provide:
1. A concise summary (2-3 sentences)
2. Key points (3-5 bullet points)
3. Main topics/themes (3-5 words)

Content:
{content}

Respond in JSON format:
{{
    "summary": "...",
    "key_points": ["point1", "point2", ...],
    "topics": ["topic1", "topic2", ...]
}}
"""
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes documents."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = call_llm(messages, model=self.llm_model)
            
            # Try to parse JSON response
            import json
            result = json.loads(response)
            return result
        except Exception as e:
            print(f"Error summarizing file: {e}")
            return {
                'summary': content[:200] + "...",
                'key_points': [],
                'topics': []
            }
    
    def extract_entities(self, content: str) -> Dict[str, list]:
        """
        Extract named entities from content
        
        Args:
            content: File content
        
        Returns:
            Dict with entity types and values
        """
        # Truncate content if too long
        max_content_length = 5000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""Extract named entities from the following text:
- People (names)
- Organizations
- Locations
- Dates
- Technologies/Tools

Content:
{content}

Respond in JSON format:
{{
    "people": [],
    "organizations": [],
    "locations": [],
    "dates": [],
    "technologies": []
}}
"""
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that extracts information."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = call_llm(messages, model=self.llm_model)
            
            import json
            result = json.loads(response)
            return result
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return {
                "people": [],
                "organizations": [],
                "locations": [],
                "dates": [],
                "technologies": []
            }
    
    def generate_questions(self, content: str, num_questions: int = 5) -> list:
        """
        Generate questions that can be answered by the content
        
        Args:
            content: File content
            num_questions: Number of questions to generate
        
        Returns:
            List of questions
        """
        # Truncate content if too long
        max_content_length = 5000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""Generate {num_questions} questions that can be answered by reading this content:

{content}

Return only the questions as a JSON array: ["question1", "question2", ...]
"""
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that generates questions."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = call_llm(messages, model=self.llm_model)
            
            import json
            questions = json.loads(response)
            return questions if isinstance(questions, list) else []
        except Exception as e:
            print(f"Error generating questions: {e}")
            return []
