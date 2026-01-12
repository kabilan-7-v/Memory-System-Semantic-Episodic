# Bi-Encoder Re-Ranking Guide

## Overview

The Bi-Encoder Re-Ranking feature provides fast, scalable semantic re-ranking using sentence transformers and FAISS indexing. It's designed to improve retrieval quality while maintaining high performance.

## Features

✅ **Fast Similarity Search** - Uses FAISS for efficient vector search  
✅ **Precomputed Embeddings** - Documents encoded once, reused for all queries  
✅ **Batch Processing** - Process multiple queries efficiently  
✅ **Configurable Profiles** - Choose between speed, balance, or quality  
✅ **Score Filtering** - Control precision with similarity thresholds  
✅ **Detailed Visualization** - Compare rankings and analyze results  

## Installation

```bash
pip install sentence-transformers faiss-cpu
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```python
from src.services.biencoder_reranker import BiEncoderReranker, get_recommended_config

# Initialize with recommended config
config = get_recommended_config("balanced")
reranker = BiEncoderReranker(
    model_name=config['model_name'],
    batch_size=config['batch_size']
)

# Index your documents
documents = [
    "Python is a programming language",
    "Machine learning uses neural networks",
    "Databases store structured data"
]
reranker.build_index(documents)

# Re-rank for a query
results = reranker.rerank(
    query="What is machine learning?",
    top_k=10,
    score_threshold=0.65
)

# View results
for r in results:
    print(f"{r['rank']}. {r['document']} (score: {r['score']:.4f})")
```

### Run the Demo

```bash
python demo_biencoder_reranking.py
```

The demo includes:
1. Basic re-ranking with visualization
2. Original vs reranked comparison
3. Batch processing multiple queries
4. Score threshold filtering
5. Model comparison

## Configuration Profiles

### Fast Profile
```python
config = get_recommended_config("fast")
# model: all-MiniLM-L6-v2
# batch_size: 64
# threshold: 0.60
# Best for: Low-latency applications
```

### Balanced Profile (Default)
```python
config = get_recommended_config("balanced")
# model: all-MiniLM-L12-v2
# batch_size: 32
# threshold: 0.65
# Best for: General use cases
```

### Quality Profile
```python
config = get_recommended_config("quality")
# model: BAAI/bge-base-en-v1.5
# batch_size: 16
# threshold: 0.70
# Best for: High-accuracy requirements
```

## Advanced Usage

### Batch Processing

```python
# Process multiple queries at once
queries = [
    "machine learning algorithms",
    "database systems",
    "natural language processing"
]

all_results = reranker.batch_rerank(
    queries=queries,
    top_k=5,
    score_threshold=0.65
)

for query, results in zip(queries, all_results):
    print(f"Query: {query}")
    for r in results[:3]:
        print(f"  {r['rank']}. {r['document'][:60]}...")
```

### Custom Model

```python
# Use a specific sentence transformer model
reranker = BiEncoderReranker(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    batch_size=32,
    normalize_embeddings=True
)
```

### Score Threshold Filtering

```python
# Get only high-confidence results
results = reranker.rerank(
    query="semantic search",
    top_k=50,
    score_threshold=0.75  # Only scores >= 0.75
)
```

### Ranking Visualization

```python
# Print detailed ranking with documents
reranker.print_ranking(
    query="What is AI?",
    results=results,
    show_documents=True,
    max_doc_length=80
)

# Compare original vs reranked
reranker.print_ranking_comparison(
    query="vector search",
    original_ranking=original_results,
    reranked_results=reranked_results,
    show_top_n=10
)
```

## Integration with Memory System

You can integrate bi-encoder re-ranking into the interactive memory system:

```python
# In interactive_memory_app.py
from src.services.biencoder_reranker import BiEncoderReranker, get_recommended_config

class InteractiveMemorySystem:
    def __init__(self):
        # ... existing initialization ...
        
        # Initialize bi-encoder reranker
        config = get_recommended_config("balanced")
        self.biencoder = BiEncoderReranker(
            model_name=config['model_name'],
            batch_size=config['batch_size']
        )
    
    def enhanced_search(self, query: str, top_k: int = 10):
        """Search with bi-encoder re-ranking"""
        # 1. Get initial results from hybrid search
        initial_results = self.hybrid_search(query, top_k=50)
        
        # 2. Extract documents
        documents = [r['content'] for r in initial_results]
        
        # 3. Build index and re-rank
        self.biencoder.build_index(documents)
        reranked = self.biencoder.rerank(
            query=query,
            top_k=top_k,
            score_threshold=0.65
        )
        
        return reranked
```

## Performance Tips

1. **Precompute Once** - Build the index once and reuse for multiple queries
2. **Batch Queries** - Use `batch_rerank()` for multiple queries
3. **Choose Right Profile** - Balance speed vs quality based on your needs
4. **Set Thresholds** - Filter low-quality results with `score_threshold`
5. **Use FAISS** - Install `faiss-cpu` or `faiss-gpu` for faster search

## Model Selection

### Recommended Models

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| all-MiniLM-L6-v2 | 80MB | Fast | Good | Production, low-latency |
| all-MiniLM-L12-v2 | 120MB | Medium | Better | General purpose |
| BAAI/bge-base-en-v1.5 | 420MB | Slower | Best | High-accuracy tasks |

### Multilingual Support

```python
reranker = BiEncoderReranker(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
```

## Troubleshooting

### ImportError: sentence-transformers not available
```bash
pip install sentence-transformers
```

### FAISS not available warning
```bash
pip install faiss-cpu
# Or for GPU support:
pip install faiss-gpu
```

### Out of memory errors
- Reduce `batch_size`
- Use smaller model (e.g., all-MiniLM-L6-v2)
- Process documents in chunks

## API Reference

### BiEncoderReranker

```python
BiEncoderReranker(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    batch_size: int = 32,
    normalize_embeddings: bool = True
)
```

**Methods:**
- `build_index(documents: List[str])` - Index documents for searching
- `rerank(query: str, top_k: int, score_threshold: float)` - Re-rank for query
- `batch_rerank(queries: List[str], top_k: int, score_threshold: float)` - Batch process
- `print_ranking(...)` - Visualize results
- `print_ranking_comparison(...)` - Compare rankings

### get_recommended_config

```python
get_recommended_config(profile: str = "balanced") -> Dict[str, Any]
```

**Profiles:** "fast", "balanced", "quality"

## Examples

See `demo_biencoder_reranking.py` for complete examples covering:
- Basic re-ranking
- Ranking comparison
- Batch processing
- Threshold filtering
- Model comparison

## Performance Benchmarks

On a typical laptop (M1 Mac):
- **Indexing**: ~1000 docs/sec
- **Query**: <10ms with FAISS (100k docs)
- **Batch (10 queries)**: ~50ms

## Further Reading

- [Sentence Transformers Documentation](https://www.sbert.net/)
- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [BGE Embeddings](https://huggingface.co/BAAI/bge-base-en-v1.5)
