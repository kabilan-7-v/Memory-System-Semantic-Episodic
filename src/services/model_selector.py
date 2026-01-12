"""
Model Selection Service
Automatically selects the best LLM model based on task requirements
Inspired by intelligent model routing for optimal performance and cost
"""
from typing import Dict, Tuple


class ModelSelector:
    """
    Intelligent model selection for different tasks
    Routes to optimal models based on task characteristics
    """
    
    # Model registry with task-specific optimizations
    MODEL_REGISTRY = {
        "chat": {
            "model": "llama-3.3-70b-versatile",
            "reason": "Conversational AI - Best for natural dialogue and context understanding",
            "use_case": "General chat, Q&A, contextual conversations"
        },
        "optimization": {
            "model": "llama-3.1-8b-instant",
            "reason": "Fast inference - Optimal for real-time content optimization and filtering",
            "use_case": "Content deduplication, entropy filtering, compression"
        },
        "summarization": {
            "model": "llama-3.1-70b-versatile",
            "reason": "Compression & summarization - Excellent at condensing information accurately",
            "use_case": "Episode creation, context summarization, content consolidation"
        },
        "analysis": {
            "model": "mixtral-8x7b-32768",
            "reason": "Deep analysis - Superior reasoning for complex queries and data interpretation",
            "use_case": "Memory retrieval, context analysis, complex reasoning"
        },
        "code": {
            "model": "llama-3.1-70b-versatile",
            "reason": "Code generation - Specialized for technical tasks and structured output",
            "use_case": "Code generation, technical documentation, structured data"
        },
        "embedding": {
            "model": "llama-3.1-8b-instant",
            "reason": "Fast embedding generation - Efficient for vector operations",
            "use_case": "Semantic search, similarity calculations, clustering"
        },
        "classification": {
            "model": "llama-3.1-8b-instant",
            "reason": "Quick classification - Fast and accurate for categorization tasks",
            "use_case": "Content categorization, intent detection, routing"
        },
        "long_context": {
            "model": "mixtral-8x7b-32768",
            "reason": "Large context window (32K) - Handles extensive historical data",
            "use_case": "Long conversation history, large document processing"
        }
    }
    
    @classmethod
    def select_model(cls, task_type: str, verbose: bool = False) -> Tuple[str, str]:
        """
        Select the best model for a given task
        
        Args:
            task_type: Type of task (chat, optimization, summarization, etc.)
            verbose: Whether to print selection details
            
        Returns:
            Tuple of (model_name, reason)
        """
        config = cls.MODEL_REGISTRY.get(task_type, cls.MODEL_REGISTRY["chat"])
        model_name = config["model"]
        reason = config["reason"]
        
        if verbose:
            print(f"\n🤖 Model Selection: {model_name}")
            print(f"   ├─ Task: {task_type}")
            print(f"   ├─ Reason: {reason}")
            print(f"   └─ Use Case: {config['use_case']}")
        
        return model_name, reason
    
    @classmethod
    def get_all_models(cls) -> Dict:
        """Get all available models in registry"""
        return cls.MODEL_REGISTRY
    
    @classmethod
    def get_model_info(cls, task_type: str) -> Dict:
        """Get detailed information about model for a task"""
        return cls.MODEL_REGISTRY.get(task_type, cls.MODEL_REGISTRY["chat"])


def select_model_for_task(task_type: str, verbose: bool = False) -> Tuple[str, str]:
    """
    Convenience function for model selection
    
    Args:
        task_type: Type of task
        verbose: Whether to print details
        
    Returns:
        Tuple of (model_name, reason)
    """
    return ModelSelector.select_model(task_type, verbose)
