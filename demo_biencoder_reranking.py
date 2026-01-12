#!/usr/bin/env python3
"""
Demo: Bi-Encoder Re-Ranking with Ranking Visualization
Shows complete pipeline with detailed ranking lists

This demo demonstrates:
1. Precomputing document embeddings
2. Query-time re-ranking
3. Detailed ranking visualization
4. Comparison with original ranking
5. Batch processing
"""
import sys
import os
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from services.biencoder_reranker import (
        BiEncoderReranker,
        get_recommended_config,
        SENTENCE_TRANSFORMERS_AVAILABLE,
        FAISS_AVAILABLE
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nInstall required packages:")
    print("  pip install sentence-transformers faiss-cpu")
    sys.exit(1)


# Sample document corpus (simulating knowledge base)
SAMPLE_DOCUMENTS = [
    "Python is a high-level programming language with dynamic typing and garbage collection",
    "Machine learning involves training models on data to make predictions",
    "Docker containers provide lightweight virtualization for applications",
    "PostgreSQL is a powerful open-source relational database system",
    "Redis is an in-memory data structure store used as a database and cache",
    "Natural language processing enables computers to understand human language",
    "Deep learning uses neural networks with multiple layers for complex tasks",
    "Kubernetes orchestrates containerized applications across multiple hosts",
    "FastAPI is a modern web framework for building APIs with Python",
    "Vector databases store high-dimensional embeddings for similarity search",
    "Transformers revolutionized NLP with attention mechanisms",
    "FAISS provides efficient similarity search for dense vectors",
    "Semantic search finds results based on meaning rather than keywords",
    "Embeddings are dense vector representations of text or data",
    "Cosine similarity measures the angle between two vectors",
    "RAG combines retrieval and generation for better AI responses",
    "LangChain helps build applications with large language models",
    "Prompt engineering optimizes instructions for language models",
    "Fine-tuning adapts pre-trained models to specific tasks",
    "Zero-shot learning performs tasks without task-specific training"
]


def demo_basic_reranking():
    """Demo 1: Basic re-ranking with ranking visualization"""
    print("\n" + "="*80)
    print("🎯 DEMO 1: Basic Bi-Encoder Re-Ranking")
    print("="*80)

    # Initialize reranker with recommended config
    config = get_recommended_config("fast")
    print(f"\nUsing configuration: {config['description']}")

    reranker = BiEncoderReranker(
        model_name=config['model_name'],
        batch_size=config['batch_size']
    )

    # Build index
    print(f"\n📦 Indexing {len(SAMPLE_DOCUMENTS)} documents...")
    reranker.build_index(SAMPLE_DOCUMENTS)

    # Query 1: Machine Learning
    query1 = "How does machine learning work?"
    print(f"\n🔍 Query: \"{query1}\"")

    results1 = reranker.rerank(
        query=query1,
        top_k=config['top_k'],
        score_threshold=config['score_threshold']
    )

    # Print detailed ranking
    reranker.print_ranking(
        query=query1,
        results=results1,
        show_documents=True,
        max_doc_length=80
    )

    # Query 2: Databases
    query2 = "What are the best databases for caching?"
    print(f"\n🔍 Query: \"{query2}\"")

    results2 = reranker.rerank(
        query=query2,
        top_k=10,
        score_threshold=0.65
    )

    reranker.print_ranking(
        query=query2,
        results=results2,
        show_documents=True
    )


def demo_ranking_comparison():
    """Demo 2: Compare original vs reranked results"""
    print("\n" + "="*80)
    print("🔄 DEMO 2: Ranking Comparison (Original vs Reranked)")
    print("="*80)

    reranker = BiEncoderReranker()
    reranker.build_index(SAMPLE_DOCUMENTS)

    query = "vector similarity search"

    # Simulate original ranking (simple keyword match)
    original_ranking = []
    query_words = set(query.lower().split())
    for i, doc in enumerate(SAMPLE_DOCUMENTS):
        doc_words = set(doc.lower().split())
        score = len(query_words & doc_words) / len(query_words)  # Simple overlap
        original_ranking.append({
            'index': i,
            'document': doc,
            'score': score
        })

    original_ranking.sort(key=lambda x: x['score'], reverse=True)

    # Bi-encoder reranking
    reranked_results = reranker.rerank(
        query=query,
        top_k=10,
        score_threshold=0.60
    )

    # Print comparison
    reranker.print_ranking_comparison(
        query=query,
        original_ranking=original_ranking,
        reranked_results=reranked_results,
        show_top_n=10
    )


def demo_batch_processing():
    """Demo 3: Batch processing multiple queries"""
    print("\n" + "="*80)
    print("📊 DEMO 3: Batch Processing Multiple Queries")
    print("="*80)

    config = get_recommended_config("balanced")
    reranker = BiEncoderReranker(
        model_name=config['model_name'],
        batch_size=config['batch_size']
    )

    reranker.build_index(SAMPLE_DOCUMENTS)

    # Multiple queries
    queries = [
        "machine learning algorithms",
        "database systems",
        "natural language processing",
        "container orchestration",
        "vector search"
    ]

    print(f"\n🔍 Processing {len(queries)} queries in batch...")

    # Batch rerank
    all_results = reranker.batch_rerank(
        queries=queries,
        top_k=5
    )

    # Print results for each query
    for i, (query, results) in enumerate(zip(queries, all_results), 1):
        print(f"\n--- Query {i}: \"{query}\" ---")
        print(f"Top 3 Results:")
        for r in results[:3]:
            print(f"   {r['rank']}. [Score: {r['score']:.4f}] {r['document'][:70]}...")


def demo_threshold_filtering():
    """Demo 4: Score threshold filtering"""
    print("\n" + "="*80)
    print("🎚️ DEMO 4: Score Threshold Filtering")
    print("="*80)

    reranker = BiEncoderReranker()
    reranker.build_index(SAMPLE_DOCUMENTS)

    query = "semantic search with embeddings"

    # Try different thresholds
    thresholds = [0.60, 0.70, 0.80]

    for threshold in thresholds:
        print(f"\n📊 Threshold: {threshold}")
        results = reranker.rerank(
            query=query,
            top_k=50,
            score_threshold=threshold
        )
        print(f"   Results above threshold: {len(results)}")
        if results:
            print(f"   Highest score: {results[0]['score']:.4f}")
            print(f"   Lowest score: {results[-1]['score']:.4f}")


def demo_model_comparison():
    """Demo 5: Compare different models"""
    print("\n" + "="*80)
    print("⚖️ DEMO 5: Model Comparison")
    print("="*80)

    query = "deep learning with transformers"

    models = [
        ("Fast", "sentence-transformers/all-MiniLM-L6-v2"),
        ("Balanced", "sentence-transformers/all-MiniLM-L12-v2")
    ]

    for model_name, model_id in models:
        print(f"\n🤖 Testing: {model_name} ({model_id})")

        try:
            reranker = BiEncoderReranker(model_name=model_id, batch_size=32)
            reranker.build_index(SAMPLE_DOCUMENTS[:10])  # Use subset for speed

            results = reranker.rerank(
                query=query,
                top_k=5,
                score_threshold=0.60
            )

            print(f"   Results: {len(results)}")
            if results:
                print(f"   Top Score: {results[0]['score']:.4f}")
                print(f"   Top Result: {results[0]['document'][:60]}...")

        except Exception as e:
            print(f"   ❌ Error: {e}")


def print_system_info():
    """Print system information"""
    print("\n" + "="*80)
    print("ℹ️  SYSTEM INFORMATION")
    print("="*80)
    print(f"   sentence-transformers: {'✅ Available' if SENTENCE_TRANSFORMERS_AVAILABLE else '❌ Not Available'}")
    print(f"   FAISS: {'✅ Available' if FAISS_AVAILABLE else '❌ Not Available'}")

    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("\n   Install with: pip install sentence-transformers")
    if not FAISS_AVAILABLE:
        print("   Install with: pip install faiss-cpu")

    print("="*80)


def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("🚀 BI-ENCODER RE-RANKING DEMONSTRATION")
    print("="*80)
    print("This demo shows the complete bi-encoder re-ranking pipeline")
    print("with detailed ranking visualization and comparison")
    print("="*80)

    # Check dependencies
    print_system_info()

    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("\n❌ Required dependencies not installed!")
        print("   Install with: pip install sentence-transformers faiss-cpu")
        return

    try:
        # Run demos
        demo_basic_reranking()
        demo_ranking_comparison()
        demo_batch_processing()
        demo_threshold_filtering()

        # Optional: Model comparison (slower)
        response = input("\n🤔 Run model comparison demo? (slower) [y/N]: ")
        if response.lower() == 'y':
            demo_model_comparison()

    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("✅ DEMO COMPLETE")
    print("="*80)
    print("\nKey Takeaways:")
    print("  1. Bi-encoder provides fast, scalable re-ranking")
    print("  2. Detailed ranking lists show score distributions")
    print("  3. Comparison view highlights ranking changes")
    print("  4. Batch processing enables high throughput")
    print("  5. Threshold filtering controls precision")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
