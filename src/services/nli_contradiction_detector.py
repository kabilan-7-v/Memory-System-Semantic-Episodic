"""
NLI-Based Contradiction Detection
Uses Natural Language Inference models for advanced contradiction detection
"""
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

# Optional dependencies
try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None
    CrossEncoder = None


class NLIContradictionDetector:
    """
    Advanced contradiction detection using NLI (Natural Language Inference)
    
    NLI models are trained to classify text pairs as:
    - Entailment: Text B follows from Text A
    - Contradiction: Text B contradicts Text A
    - Neutral: No clear relationship
    
    This is more accurate than simple negation pattern matching.
    """
    
    def __init__(
        self,
        nli_model: str = "cross-encoder/nli-deberta-v3-small",
        contradiction_threshold: float = 0.5,
        use_bidirectional: bool = True
    ):
        """
        Initialize NLI-based contradiction detector
        
        Args:
            nli_model: Cross-encoder NLI model name
            contradiction_threshold: Threshold for contradiction score (0-1)
            use_bidirectional: Check both A→B and B→A for contradictions
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not available. "
                "Install with: pip install sentence-transformers"
            )
        
        self.nli_model_name = nli_model
        self.contradiction_threshold = contradiction_threshold
        self.use_bidirectional = use_bidirectional
        
        print(f"🔬 Loading NLI model: {nli_model}")
        self.model = CrossEncoder(nli_model)
        print(f"✅ NLI model loaded successfully")
        
        # Label mapping (model-dependent, but common structure)
        # Most NLI models output: [contradiction, entailment, neutral]
        self.label_mapping = {
            0: "contradiction",
            1: "entailment", 
            2: "neutral"
        }
    
    def detect_contradiction(
        self,
        text1: str,
        text2: str,
        return_details: bool = False
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if text2 contradicts text1 using NLI
        
        Args:
            text1: First text
            text2: Second text
            return_details: Whether to return detailed scores
            
        Returns:
            (is_contradiction, details_dict) tuple
        """
        # Get NLI scores
        scores = self.model.predict([[text1, text2]])
        
        if isinstance(scores, np.ndarray):
            if len(scores.shape) > 1:
                scores = scores[0]
        
        # Get contradiction score (usually index 0)
        contradiction_score = float(scores[0] if len(scores) > 0 else 0.0)
        
        is_contradiction = contradiction_score > self.contradiction_threshold
        
        # Bidirectional check if enabled
        if self.use_bidirectional and not is_contradiction:
            scores_reverse = self.model.predict([[text2, text1]])
            if isinstance(scores_reverse, np.ndarray):
                if len(scores_reverse.shape) > 1:
                    scores_reverse = scores_reverse[0]
            
            contradiction_score_reverse = float(scores_reverse[0] if len(scores_reverse) > 0 else 0.0)
            is_contradiction = contradiction_score_reverse > self.contradiction_threshold
            
            if is_contradiction:
                contradiction_score = max(contradiction_score, contradiction_score_reverse)
        
        if not return_details:
            return is_contradiction, None
        
        # Build detailed response
        details = {
            'contradiction_score': contradiction_score,
            'entailment_score': float(scores[1]) if len(scores) > 1 else 0.0,
            'neutral_score': float(scores[2]) if len(scores) > 2 else 0.0,
            'predicted_label': self.label_mapping.get(int(np.argmax(scores)), "unknown"),
            'threshold': self.contradiction_threshold,
            'bidirectional_checked': self.use_bidirectional
        }
        
        return is_contradiction, details
    
    def detect_contradictions_batch(
        self,
        contexts: List[Dict[str, Any]],
        content_key: str = 'content'
    ) -> List[Dict[str, Any]]:
        """
        Detect contradictions across multiple contexts
        
        Args:
            contexts: List of context dictionaries
            content_key: Key to access text content in each context
            
        Returns:
            Contexts with contradiction flags added
        """
        print(f"\n🔬 NLI-BASED CONTRADICTION DETECTION")
        print(f"{'='*70}")
        print(f"Model: {self.nli_model_name}")
        print(f"Contexts: {len(contexts)}")
        print(f"Threshold: {self.contradiction_threshold}")
        print(f"Bidirectional: {self.use_bidirectional}")
        print(f"{'='*70}\n")
        
        contradictions_found = 0
        pairs_checked = 0
        
        # Compare each pair
        for i, ctx1 in enumerate(contexts):
            content1 = ctx1.get(content_key, '')
            if not content1 or len(content1.strip()) < 10:
                continue
            
            for j in range(i + 1, len(contexts)):
                ctx2 = contexts[j]
                content2 = ctx2.get(content_key, '')
                if not content2 or len(content2.strip()) < 10:
                    continue
                
                pairs_checked += 1
                
                # Check for contradiction
                is_contradiction, details = self.detect_contradiction(
                    content1, 
                    content2,
                    return_details=True
                )
                
                if is_contradiction:
                    # Flag both contexts
                    if 'contradicts_with' not in ctx1:
                        ctx1['contradicts_with'] = []
                    if 'contradicts_with' not in ctx2:
                        ctx2['contradicts_with'] = []
                    
                    ctx1['contradicts_with'].append({
                        'index': j,
                        'score': details['contradiction_score']
                    })
                    ctx2['contradicts_with'].append({
                        'index': i,
                        'score': details['contradiction_score']
                    })
                    
                    ctx1['has_contradiction'] = True
                    ctx2['has_contradiction'] = True
                    
                    contradictions_found += 1
                    
                    print(f"⚠️  CONTRADICTION DETECTED:")
                    print(f"   Context {i} ↔ Context {j}")
                    print(f"   Score: {details['contradiction_score']:.3f}")
                    print(f"   Label: {details['predicted_label']}")
                    print(f"   Text 1: {content1[:100]}...")
                    print(f"   Text 2: {content2[:100]}...")
                    print()
        
        print(f"{'='*70}")
        print(f"✅ NLI CONTRADICTION DETECTION COMPLETE")
        print(f"   ├─ Pairs checked: {pairs_checked}")
        print(f"   ├─ Contradictions found: {contradictions_found}")
        print(f"   └─ Contradiction rate: {(contradictions_found/pairs_checked*100) if pairs_checked > 0 else 0:.1f}%")
        print(f"{'='*70}\n")
        
        return contexts


class UnifiedSemanticProcessor:
    """
    Unified SLM for both deduplication and ranking
    Uses a single bi-encoder model for multiple tasks
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        batch_size: int = 32
    ):
        """
        Initialize unified semantic processor
        
        Args:
            model_name: Sentence transformer model name
            batch_size: Batch size for encoding
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not available. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        self.batch_size = batch_size
        
        print(f"🤖 UNIFIED SEMANTIC PROCESSOR")
        print(f"{'='*70}")
        print(f"Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"✅ Model loaded - unified for dedup + ranking")
        print(f"{'='*70}\n")
    
    def compute_embeddings(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> np.ndarray:
        """Compute embeddings for texts"""
        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True
        )
    
    def deduplicate_by_similarity(
        self,
        contexts: List[Dict[str, Any]],
        threshold: float = 0.85,
        content_key: str = 'content'
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Remove semantic duplicates using unified embeddings
        
        Args:
            contexts: List of context dictionaries
            threshold: Similarity threshold for deduplication
            content_key: Key to access content
            
        Returns:
            (deduplicated_contexts, num_removed) tuple
        """
        if len(contexts) <= 1:
            return contexts, 0
        
        print(f"🔍 SEMANTIC DEDUPLICATION")
        print(f"   ├─ Model: {self.model_name}")
        print(f"   ├─ Threshold: {threshold}")
        print(f"   └─ Contexts: {len(contexts)}\n")
        
        # Extract texts
        texts = [ctx.get(content_key, '') for ctx in contexts]
        
        # Compute embeddings
        embeddings = self.compute_embeddings(texts)
        
        # Find duplicates using cosine similarity
        to_remove = set()
        for i in range(len(embeddings)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(embeddings)):
                if j in to_remove:
                    continue
                
                similarity = np.dot(embeddings[i], embeddings[j])
                if similarity >= threshold:
                    to_remove.add(j)
                    print(f"   ├─ Duplicate: Context {j} similar to {i} ({similarity:.3f})")
        
        # Remove duplicates
        deduplicated = [ctx for i, ctx in enumerate(contexts) if i not in to_remove]
        removed_count = len(to_remove)
        
        print(f"\n   ✅ Removed {removed_count} duplicates")
        print(f"   └─ Remaining: {len(deduplicated)}\n")
        
        return deduplicated, removed_count
    
    def rank_by_relevance(
        self,
        query: str,
        contexts: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        content_key: str = 'content'
    ) -> List[Dict[str, Any]]:
        """
        Rank contexts by relevance to query using unified embeddings
        
        Args:
            query: Query text
            contexts: List of context dictionaries
            top_k: Return only top K results (None = all)
            content_key: Key to access content
            
        Returns:
            Ranked contexts with scores
        """
        if not contexts:
            return contexts
        
        print(f"📊 SEMANTIC RANKING")
        print(f"   ├─ Model: {self.model_name}")
        print(f"   ├─ Query: {query[:100]}...")
        print(f"   └─ Contexts: {len(contexts)}\n")
        
        # Compute query embedding
        query_embedding = self.compute_embeddings([query])[0]
        
        # Compute context embeddings
        texts = [ctx.get(content_key, '') for ctx in contexts]
        context_embeddings = self.compute_embeddings(texts)
        
        # Compute similarities
        similarities = np.dot(context_embeddings, query_embedding)
        
        # Add scores to contexts and sort
        for i, ctx in enumerate(contexts):
            ctx['semantic_score'] = float(similarities[i])
        
        ranked = sorted(contexts, key=lambda x: x.get('semantic_score', 0), reverse=True)
        
        # Apply top_k filter
        if top_k:
            ranked = ranked[:top_k]
        
        print(f"   ✅ Ranked {len(ranked)} contexts")
        if ranked:
            print(f"   └─ Top score: {ranked[0].get('semantic_score', 0):.3f}\n")
        
        return ranked


# Model recommendations
RECOMMENDED_MODELS = {
    "fast": {
        "bi_encoder": "sentence-transformers/all-MiniLM-L6-v2",
        "nli": "cross-encoder/nli-deberta-v3-small",
        "description": "Fast models for production use"
    },
    "balanced": {
        "bi_encoder": "sentence-transformers/all-mpnet-base-v2",
        "nli": "cross-encoder/nli-deberta-v3-base",
        "description": "Balanced accuracy and speed"
    },
    "accurate": {
        "bi_encoder": "sentence-transformers/all-roberta-large-v1",
        "nli": "cross-encoder/nli-deberta-v3-large",
        "description": "Most accurate but slower"
    },
    "multilingual": {
        "bi_encoder": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "nli": "cross-encoder/nli-xlm-roberta-base",
        "description": "Multilingual support (50+ languages)"
    }
}


def get_recommended_models(profile: str = "balanced") -> Dict[str, str]:
    """
    Get recommended models for a specific use case
    
    Args:
        profile: One of 'fast', 'balanced', 'accurate', 'multilingual'
        
    Returns:
        Dictionary with model names
    """
    return RECOMMENDED_MODELS.get(profile, RECOMMENDED_MODELS["balanced"])


# Sentence-BERT alternatives evaluation
SENTENCE_BERT_ALTERNATIVES = {
    "all-MiniLM-L6-v2": {
        "params": "22M",
        "speed": "Very Fast",
        "accuracy": "Good",
        "use_case": "Production systems with tight latency requirements",
        "embedding_dim": 384
    },
    "all-mpnet-base-v2": {
        "params": "110M",
        "speed": "Fast",
        "accuracy": "Very Good",
        "use_case": "Best balance of speed and quality (RECOMMENDED)",
        "embedding_dim": 768
    },
    "all-roberta-large-v1": {
        "params": "355M",
        "speed": "Moderate",
        "accuracy": "Excellent",
        "use_case": "When accuracy is critical and latency is acceptable",
        "embedding_dim": 1024
    },
    "msmarco-distilbert-base-v4": {
        "params": "66M",
        "speed": "Fast",
        "accuracy": "Very Good",
        "use_case": "Trained on MS MARCO - great for search/retrieval",
        "embedding_dim": 768
    },
    "paraphrase-MiniLM-L6-v2": {
        "params": "22M",
        "speed": "Very Fast",
        "accuracy": "Good",
        "use_case": "Specifically optimized for paraphrase detection",
        "embedding_dim": 384
    }
}


def print_model_comparison():
    """Print comparison table of Sentence-BERT alternatives"""
    print(f"\n{'='*90}")
    print(f"SENTENCE-BERT ALTERNATIVES EVALUATION")
    print(f"{'='*90}\n")
    print(f"{'Model':<40} {'Params':<10} {'Speed':<15} {'Accuracy':<15}")
    print(f"{'-'*90}")
    
    for model_name, specs in SENTENCE_BERT_ALTERNATIVES.items():
        print(f"{model_name:<40} {specs['params']:<10} {specs['speed']:<15} {specs['accuracy']:<15}")
    
    print(f"\n{'='*90}")
    print(f"RECOMMENDATIONS:")
    print(f"{'='*90}")
    for model_name, specs in SENTENCE_BERT_ALTERNATIVES.items():
        print(f"\n📌 {model_name}")
        print(f"   ├─ Parameters: {specs['params']}")
        print(f"   ├─ Embedding Dimension: {specs['embedding_dim']}")
        print(f"   └─ Use Case: {specs['use_case']}")
    print(f"\n{'='*90}\n")
