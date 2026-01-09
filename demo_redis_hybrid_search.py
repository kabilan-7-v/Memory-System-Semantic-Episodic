#!/usr/bin/env python3
"""
Demo: Unified Hybrid Search with Redis Cache
Shows how to:
1. Store user context in single Redis index
2. Store user inputs in single indexes
3. Search Redis cache with hybrid approach (Vector + Keyword)
4. Get percentage metrics
"""
import sys
sys.path.append('/Users/sharan/Downloads/September-Test')

from src.services.unified_hybrid_search import UnifiedHybridSearch


def demo():
    print("="*70)
    print("DEMO: Hybrid Search on Redis Cached Data")
    print("="*70)
    
    # Initialize
    search = UnifiedHybridSearch(
        vector_weight=0.6,
        bm25_weight=0.4,
        k_rrf=60
    )
    
    user_id = "demo_user"
    
    # Step 1: Cache user context (persona + knowledge + process)
    print("\n📝 Step 1: Caching user context in SINGLE Redis index...")
    print(f"   Key: user_context:{user_id}")
    
    search.cache_user_context(
        user_id=user_id,
        persona={
            "name": "Demo User",
            "interests": ["AI", "Machine Learning", "Python", "Data Science"],
            "expertise_areas": ["Neural Networks", "Deep Learning"]
        },
        knowledge=[
            {"title": "ML Basics", "content": "Machine learning fundamentals and algorithms"},
            {"title": "Python Guide", "content": "Best practices for Python development"},
            {"title": "Neural Nets", "content": "Deep learning and neural network architectures"}
        ],
        recent_queries=[
            "What is machine learning?",
            "How to train neural networks?",
            "Python best practices"
        ]
    )
    print("   ✅ Context cached with persona + 3 knowledge items + 3 queries")
    
    # Step 2: Cache user inputs
    print(f"\n💬 Step 2: Caching user inputs in SINGLE indexes...")
    
    inputs = [
        ("Tell me about deep learning", "chat"),
        ("search neural networks", "command"),
        ("What are Python best practices?", "query"),
        ("How does machine learning work?", "query"),
        ("explain transformers", "chat")
    ]
    
    for query, input_type in inputs:
        search.cache_user_input(user_id=user_id, query=query, input_type=input_type)
        print(f"   ✅ Cached: {query} (type: {input_type})")
    
    # Step 3: Hybrid search on Redis cache
    print("\n🔍 Step 3: Hybrid Search on Redis Cache (No DB queries!)")
    print("   Algorithm: Vector Similarity + Keyword Matching + RRF")
    
    queries = [
        ("machine learning", "all"),
        ("Python", "inputs"),
        ("neural networks", "context")
    ]
    
    for query, search_type in queries:
        print(f"\n{'─'*70}")
        print(f"Query: '{query}' | Type: {search_type}")
        print(f"{'─'*70}")
        
        results = search.hybrid_search_redis_cache(
            query=query,
            user_id=user_id,
            search_type=search_type,
            limit=3
        )
        
        if results['results']:
            for i, result in enumerate(results['results'], 1):
                print(f"\n#{i} [{result['type'].upper()}] {result['key']}")
                print(f"   Content: {result['content'][:80]}...")
                print(f"   🎯 RRF Score: {result['rrf_score']:.4f} ({result['combined_percentage']}%)")
                print(f"      ├─ Vector Similarity: {result['vector_percentage']}%")
                print(f"      └─ Keyword Match:     {result['keyword_percentage']}%")
            
            print(f"\n📊 Metrics:")
            metrics = results['metrics']
            print(f"   • Search Time: {metrics['search_time_ms']}ms")
            print(f"   • Total Results: {metrics['total_results']}")
            print(f"   • Vector Candidates: {metrics['vector_candidates']}")
            print(f"   • Keyword Candidates: {metrics['keyword_candidates']}")
            print(f"   • Source: {metrics['source']}")
        else:
            print("   ⚠️  No results found")
    
    # Summary
    print(f"\n{'='*70}")
    print("📋 SUMMARY")
    print(f"{'='*70}")
    print("\n✅ Implementation Complete:")
    print("   • User context in SINGLE Redis index (persona + knowledge + queries)")
    print("   • User inputs in SINGLE indexes with embeddings")
    print("   • Hybrid search on Redis cache (Vector + Keyword)")
    print("   • RRF algorithm for ranking")
    print("   • Percentage metrics for transparency")
    print("   • Ultra-fast in-memory search (no DB queries)")
    
    print("\n🔑 Redis Keys Structure:")
    if search.redis_client:
        print(f"   user_context:{user_id}        → Unified context (1 key)")
        input_keys = search.redis_client.keys(f"user_input:{user_id}:*")
        print(f"   user_input:{user_id}:*      → {len(input_keys)} input keys")
        queries_key = search.redis_client.keys(f"user_queries:{user_id}")
        print(f"   user_queries:{user_id}        → Query list ({len(queries_key)} key)")
        
        total_keys = 1 + len(input_keys) + len(queries_key)
        print(f"\n   📊 Total keys for user: {total_keys}")
        print(f"   💾 Memory: {search.redis_client.info('memory')['used_memory_human']}")


if __name__ == "__main__":
    demo()
