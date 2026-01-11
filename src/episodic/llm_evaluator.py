"""
LLM Evaluator - Evaluates LLM responses and retrieval quality
"""
from typing import Dict, Any, List, Optional
from .llm import call_llm


class LLMEvaluator:
    """
    Evaluates the quality of LLM responses and retrieval results
    """
    
    def __init__(self, llm_model: str = "openai/gpt-oss-120b"):
        """Initialize LLM evaluator"""
        self.llm_model = llm_model
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        context: str
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of an answer
        
        Args:
            question: Original question
            answer: Generated answer
            context: Context used to generate answer
        
        Returns:
            Dict with evaluation metrics
        """
        prompt = f"""Evaluate the following answer to a question:

Question: {question}

Context provided:
{context[:1000]}

Answer: {answer}

Rate the answer on these criteria (0-10):
1. Relevance: Does the answer address the question?
2. Accuracy: Is the information correct based on the context?
3. Completeness: Does it provide a complete answer?
4. Clarity: Is it clear and well-structured?

Respond in JSON format:
{{
    "relevance": 0-10,
    "accuracy": 0-10,
    "completeness": 0-10,
    "clarity": 0-10,
    "overall": 0-10,
    "feedback": "brief explanation"
}}
"""
        
        messages = [
            {"role": "system", "content": "You are an expert evaluator of question-answering systems."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = call_llm(messages, model=self.llm_model)
            
            import json
            evaluation = json.loads(response)
            return evaluation
        except Exception as e:
            print(f"Error evaluating answer: {e}")
            return {
                "relevance": 0,
                "accuracy": 0,
                "completeness": 0,
                "clarity": 0,
                "overall": 0,
                "feedback": f"Error: {str(e)}"
            }
    
    def evaluate_retrieval(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate retrieval quality
        
        Args:
            query: Search query
            retrieved_docs: List of retrieved documents
            ground_truth: Optional expected answer
        
        Returns:
            Dict with retrieval metrics
        """
        if not retrieved_docs:
            return {
                'precision': 0.0,
                'recall': 0.0,
                'relevance_scores': [],
                'avg_relevance': 0.0
            }
        
        # Evaluate each document's relevance
        relevance_scores = []
        
        for doc in retrieved_docs[:3]:  # Evaluate top 3
            content = doc.get('content', doc.get('content_text', ''))[:500]
            
            prompt = f"""How relevant is this document to the query?

Query: {query}

Document:
{content}

Rate relevance from 0 (not relevant) to 10 (highly relevant).
Respond with just the number.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert at evaluating document relevance."},
                {"role": "user", "content": prompt}
            ]
            
            try:
                response = call_llm(messages, model=self.llm_model)
                score = float(response.strip())
                relevance_scores.append(score)
            except:
                relevance_scores.append(5.0)  # Default mid-range
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        
        return {
            'num_retrieved': len(retrieved_docs),
            'relevance_scores': relevance_scores,
            'avg_relevance': avg_relevance,
            'top_doc_relevant': relevance_scores[0] >= 7 if relevance_scores else False
        }
    
    def compare_answers(
        self,
        question: str,
        answer1: str,
        answer2: str,
        labels: tuple = ("Answer A", "Answer B")
    ) -> Dict[str, Any]:
        """
        Compare two answers and determine which is better
        
        Args:
            question: Original question
            answer1: First answer
            answer2: Second answer
            labels: Labels for the answers
        
        Returns:
            Dict with comparison results
        """
        prompt = f"""Compare these two answers to the question:

Question: {question}

{labels[0]}: {answer1}

{labels[1]}: {answer2}

Which answer is better overall? Consider:
- Relevance to the question
- Accuracy of information
- Completeness
- Clarity and structure

Respond in JSON format:
{{
    "winner": "{labels[0]}" or "{labels[1]}" or "tie",
    "reasoning": "brief explanation",
    "scores": {{
        "{labels[0]}": 0-10,
        "{labels[1]}": 0-10
    }}
}}
"""
        
        messages = [
            {"role": "system", "content": "You are an expert evaluator comparing answers."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = call_llm(messages, model=self.llm_model)
            
            import json
            comparison = json.loads(response)
            return comparison
        except Exception as e:
            print(f"Error comparing answers: {e}")
            return {
                "winner": "tie",
                "reasoning": f"Error: {str(e)}",
                "scores": {labels[0]: 0, labels[1]: 0}
            }
    
    def detect_hallucination(
        self,
        context: str,
        answer: str
    ) -> Dict[str, Any]:
        """
        Detect if answer contains hallucinated information not in context
        
        Args:
            context: Source context
            answer: Generated answer
        
        Returns:
            Dict with hallucination detection results
        """
        prompt = f"""Check if the answer contains information not present in the context.

Context:
{context[:1500]}

Answer:
{answer}

Does the answer contain facts or claims not supported by the context?

Respond in JSON format:
{{
    "hallucinated": true/false,
    "confidence": 0-100,
    "unsupported_claims": ["claim1", "claim2", ...] or [],
    "explanation": "brief explanation"
}}
"""
        
        messages = [
            {"role": "system", "content": "You are an expert at detecting factual inconsistencies."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = call_llm(messages, model=self.llm_model)
            
            import json
            detection = json.loads(response)
            return detection
        except Exception as e:
            print(f"Error detecting hallucination: {e}")
            return {
                "hallucinated": False,
                "confidence": 0,
                "unsupported_claims": [],
                "explanation": f"Error: {str(e)}"
            }
