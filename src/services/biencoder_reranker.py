"""
Bi-Encoder Re-Ranking Service
Uses sentence transformers for fast semantic re-ranking with FAISS indexing
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Optional dependencies
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None


class BiEncoderReranker:
    """
    Fast bi-encoder re-ranking using sentence transformers and FAISS
    
    Features:
    - Precompute document embeddings once
    - Fast query-time similarity search with FAISS
    - Batch processing support
    - Score threshold filtering
    - Detailed ranking visualization
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        batch_size: int = 32,
        normalize_embeddings: bool = True
    ):
        """
        Initialize bi-encoder reranker
        
        Args:
            model_name: Sentence transformer model name
            batch_size: Batch size for encoding
            normalize_embeddings: Whether to normalize embeddings for cosine similarity
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not available. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings
        
        print(f"🤖 Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        self.documents: List[str] = []
        self.document_embeddings: Optional[np.ndarray] = None
        self.faiss_index = None
        
    def build_index(self, documents: List[str]) -> None:
        """
        Build FAISS index from documents
        
        Args:
            documents: List of document strings to index
        """
        self.documents = documents
        
        # Encode documents
        print(f"📝 Encoding {len(documents)} documents...")
        self.document_embeddings = self.model.encode(
            documents,
            batch_size=self.batch_size,
            show_progress_bar=True,
            normalize_embeddings=self.normalize_embeddings
        )
        
        # Build FAISS index if available
        if FAISS_AVAILABLE:
            print(f"🔍 Building FAISS index...")
            dimension = self.document_embeddings.shape[1]
            
            # Use IndexFlatIP for cosine similarity (with normalized embeddings)
            self.faiss_index = faiss.IndexFlatIP(dimension)
            self.faiss_index.add(self.document_embeddings.astype(np.float32))
            print(f"✅ FAISS index built with {self.faiss_index.ntotal} vectors")
        else:
            print("⚠️  FAISS not available, using numpy for similarity search")
    
    def rerank(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Re-rank documents for a query
        
        Args:
            query: Query string
            top_k: Number of top results to return
            score_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of ranked results with scores
        """
        if self.document_embeddings is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        # Encode query
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=self.normalize_embeddings
        )[0]
        
        # Search
        if FAISS_AVAILABLE and self.faiss_index is not None:
            # Use FAISS for fast search
            scores, indices = self.faiss_index.search(
                query_embedding.reshape(1, -1).astype(np.float32),
                min(top_k * 2, len(self.documents))  # Get more for filtering
            )
            scores = scores[0]
            indices = indices[0]
        else:
            # Fallback to numpy
            scores = np.dot(self.document_embeddings, query_embedding)
            indices = np.argsort(scores)[::-1][:top_k * 2]
            scores = scores[indices]
        
        # Build results
        results = []
        for rank, (idx, score) in enumerate(zip(indices, scores), 1):
            if score_threshold is not None and score < score_threshold:
                continue
            
            if len(results) >= top_k:
                break
                
            results.append({
                'rank': rank,
                'index': int(idx),
                'document': self.documents[idx],
                'score': float(score)
            })
        
        return results
    
    def batch_rerank(
        self,
        queries: List[str],
        top_k: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Re-rank documents for multiple queries
        
        Args:
            queries: List of query strings
            top_k: Number of top results per query
            score_threshold: Minimum similarity score
            
        Returns:
            List of ranked results for each query
        """
        if self.document_embeddings is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        # Encode all queries
        print(f"🔍 Encoding {len(queries)} queries...")
        query_embeddings = self.model.encode(
            queries,
            batch_size=self.batch_size,
            show_progress_bar=True,
            normalize_embeddings=self.normalize_embeddings
        )
        
        # Search for each query
        all_results = []
        for query_embedding in query_embeddings:
            if FAISS_AVAILABLE and self.faiss_index is not None:
                scores, indices = self.faiss_index.search(
                    query_embedding.reshape(1, -1).astype(np.float32),
                    min(top_k * 2, len(self.documents))
                )
                scores = scores[0]
                indices = indices[0]
            else:
                scores = np.dot(self.document_embeddings, query_embedding)
                indices = np.argsort(scores)[::-1][:top_k * 2]
                scores = scores[indices]
            
            # Build results
            results = []
            for rank, (idx, score) in enumerate(zip(indices, scores), 1):
                if score_threshold is not None and score < score_threshold:
                    continue
                
                if len(results) >= top_k:
                    break
                    
                results.append({
                    'rank': rank,
                    'index': int(idx),
                    'document': self.documents[idx],
                    'score': float(score)
                })
            
            all_results.append(results)
        
        return all_results
    
    def print_ranking(
        self,
        query: str,
        results: List[Dict[str, Any]],
        show_documents: bool = True,
        max_doc_length: Optional[int] = None
    ) -> None:
        """Print detailed ranking results"""
        print(f"\n📊 Ranking Results for: \"{query}\"")
        print(f"{'='*80}")
        
        if not results:
            print("   No results found")
            return
        
        print(f"   Found {len(results)} results\n")
        
        for r in results:
            doc = r['document']
            if max_doc_length and len(doc) > max_doc_length:
                doc = doc[:max_doc_length] + "..."
            
            print(f"   {r['rank']:2d}. [Score: {r['score']:.4f}] ", end="")
            
            if show_documents:
                print(f"{doc}")
            else:
                print(f"Document #{r['index']}")
        
        print(f"{'='*80}\n")
    
    def print_ranking_comparison(
        self,
        query: str,
        original_ranking: List[Dict[str, Any]],
        reranked_results: List[Dict[str, Any]],
        show_top_n: int = 10
    ) -> None:
        """Compare original vs reranked results"""
        print(f"\n🔄 Ranking Comparison for: \"{query}\"")
        print(f"{'='*80}")
        
        print(f"\n{'Original Rank':^15} | {'Score':^10} | {'Reranked':^15} | {'Score':^10}")
        print(f"{'-'*15}-+-{'-'*10}-+-{'-'*15}-+-{'-'*10}")
        
        for i in range(min(show_top_n, max(len(original_ranking), len(reranked_results)))):
            # Original
            if i < len(original_ranking):
                orig = original_ranking[i]
                orig_text = f"#{orig['index']} ({orig['score']:.3f})"
                orig_score = f"{orig['score']:.4f}"
            else:
                orig_text = "-"
                orig_score = "-"
            
            # Reranked
            if i < len(reranked_results):
                rerank = reranked_results[i]
                rerank_text = f"#{rerank['index']} ({rerank['score']:.3f})"
                rerank_score = f"{rerank['score']:.4f}"
            else:
                rerank_text = "-"
                rerank_score = "-"
            
            print(f"{orig_text:^15} | {orig_score:^10} | {rerank_text:^15} | {rerank_score:^10}")
        
        print(f"{'='*80}\n")


def get_recommended_config(profile: str = "balanced") -> Dict[str, Any]:
    """
    Get recommended configuration for different use cases
    
    Args:
        profile: One of "fast", "balanced", "quality"
        
    Returns:
        Configuration dictionary
    """
    configs = {
        "fast": {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "batch_size": 64,
            "top_k": 10,
            "score_threshold": 0.60,
            "description": "Fast model for low-latency applications"
        },
        "balanced": {
            "model_name": "sentence-transformers/all-MiniLM-L12-v2",
            "batch_size": 32,
            "top_k": 15,
            "score_threshold": 0.65,
            "description": "Balanced speed and quality"
        },
        "quality": {
            "model_name": "BAAI/bge-base-en-v1.5",
            "batch_size": 16,
            "top_k": 20,
            "score_threshold": 0.70,
            "description": "High-quality embeddings for best results"
        }
    }
    
    return configs.get(profile, configs["balanced"])
