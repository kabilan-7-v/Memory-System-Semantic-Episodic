#!/usr/bin/env python3
"""
Test Redis Semantic Cache Integration
Tests persona and knowledge caching functionality
"""
import sys
sys.path.append('/Users/sharan/Downloads/September-Test')

from src.services.redis_semantic_cache import (
    cache_persona, get_cached_persona, invalidate_persona_cache,
    cache_knowledge_search, search_knowledge_cache, invalidate_knowledge_cache,
    get_cache_stats, clear_all_semantic_cache
)

def test_redis_connection():
    """Test basic Redis connection"""
    print("="*70)
    print("TEST 1: Redis Connection")
    print("="*70)
    
    try:
        from src.services.redis_semantic_client import get_redis_semantic
        r = get_redis_semantic()
        result = r.ping()
        print(f"✅ Redis connection successful: {result}")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def test_persona_caching():
    """Test persona caching"""
    print("\n" + "="*70)
    print("TEST 2: Persona Caching")
    print("="*70)
    
    user_id = "test_user_123"
    persona_data = {
        "name": "John Doe",
        "interests": ["AI", "Machine Learning", "Python"],
        "expertise_areas": ["NLP", "Computer Vision"],
        "communication_style": "Technical and detailed",
        "metadata": {"test": True}
    }
    
    # Cache persona
    print(f"\n1. Caching persona for {user_id}...")
    cache_persona(user_id, persona_data)
    
    # Retrieve from cache
    print(f"\n2. Retrieving cached persona...")
    cached = get_cached_persona(user_id)
    
    if cached:
        print(f"✅ Persona retrieved from cache!")
        print(f"   Name: {cached['name']}")
        print(f"   Interests: {cached['interests']}")
    else:
        print(f"❌ Persona not found in cache")
        return False
    
    # Test cache invalidation
    print(f"\n3. Invalidating cache...")
    invalidate_persona_cache(user_id)
    
    cached_after = get_cached_persona(user_id)
    if not cached_after:
        print(f"✅ Cache successfully invalidated")
    else:
        print(f"❌ Cache invalidation failed")
        return False
    
    return True


def test_knowledge_caching():
    """Test knowledge search caching"""
    print("\n" + "="*70)
    print("TEST 3: Knowledge Search Caching")
    print("="*70)
    
    user_id = "test_user_456"
    query = "What is machine learning?"
    results = [
        {
            "id": "1",
            "content": "Machine learning is a subset of AI that enables systems to learn from data",
            "similarity_score": 0.95,
            "category": "AI Concepts"
        },
        {
            "id": "2",
            "content": "ML algorithms can be supervised, unsupervised, or reinforcement learning",
            "similarity_score": 0.88,
            "category": "AI Concepts"
        }
    ]
    
    # Cache knowledge search
    print(f"\n1. Caching knowledge search...")
    cache_knowledge_search(user_id, query, results)
    
    # Test exact query match
    print(f"\n2. Searching with same query...")
    cached = search_knowledge_cache(user_id, query)
    if cached:
        print(f"✅ Exact match found! {len(cached)} results")
    
    # Test semantic similarity
    print(f"\n3. Searching with similar query...")
    similar_query = "Explain machine learning to me"
    cached_similar = search_knowledge_cache(user_id, similar_query)
    
    if cached_similar:
        print(f"⚡ Semantic match found! {len(cached_similar)} results")
        print(f"   Original: '{query}'")
        print(f"   Similar:  '{similar_query}'")
    else:
        print(f"ℹ️  No semantic match (similarity below threshold)")
    
    # Test different query
    print(f"\n4. Searching with different query...")
    diff_query = "What is the weather today?"
    cached_diff = search_knowledge_cache(user_id, diff_query)
    
    if not cached_diff:
        print(f"✅ Correctly returned None for unrelated query")
    else:
        print(f"⚠️  Unexpected match for unrelated query")
    
    return True


def test_cache_stats():
    """Test cache statistics"""
    print("\n" + "="*70)
    print("TEST 4: Cache Statistics")
    print("="*70)
    
    # Cache some data first
    cache_persona("user_1", {"name": "Alice", "interests": ["AI"]})
    cache_persona("user_2", {"name": "Bob", "interests": ["ML"]})
    cache_knowledge_search("user_1", "test query", [{"id": "1"}])
    
    # Get global stats
    print(f"\n1. Global statistics:")
    stats = get_cache_stats()
    print(f"   Total personas cached: {stats['total_personas']}")
    print(f"   Total knowledge entries: {stats['total_knowledge']}")
    
    # Get user-specific stats
    print(f"\n2. User-specific statistics (user_1):")
    user_stats = get_cache_stats("user_1")
    if "user_stats" in user_stats:
        ustats = user_stats["user_stats"]["user_1"]
        print(f"   Persona cached: {ustats['persona_cached']}")
        print(f"   Knowledge entries: {ustats['knowledge_entries']}")
        print(f"   Persona TTL: {ustats['persona_ttl']}s")
    
    return True


def test_cache_lifecycle():
    """Test complete cache lifecycle"""
    print("\n" + "="*70)
    print("TEST 5: Cache Lifecycle")
    print("="*70)
    
    user_id = "lifecycle_test"
    
    # 1. Cache persona
    print(f"\n1. Caching persona...")
    persona = {"name": "Test User", "interests": ["Testing"]}
    cache_persona(user_id, persona)
    
    # 2. Verify cached
    cached = get_cached_persona(user_id)
    print(f"   Status: {'✅ Cached' if cached else '❌ Not cached'}")
    
    # 3. Cache knowledge
    print(f"\n2. Caching knowledge...")
    cache_knowledge_search(user_id, "test query", [{"id": "test"}])
    
    # 4. Get stats
    stats = get_cache_stats(user_id)
    print(f"\n3. Cache stats:")
    if "user_stats" in stats and user_id in stats["user_stats"]:
        print(f"   {stats['user_stats'][user_id]}")
    
    # 5. Invalidate
    print(f"\n4. Invalidating caches...")
    invalidate_persona_cache(user_id)
    invalidate_knowledge_cache(user_id)
    
    # 6. Verify invalidated
    cached_after = get_cached_persona(user_id)
    knowledge_after = search_knowledge_cache(user_id, "test query")
    
    success = not cached_after and not knowledge_after
    print(f"   Status: {'✅ All caches cleared' if success else '❌ Caches not cleared'}")
    
    return success


def main():
    """Run all tests"""
    print("\n" + "🚀"*35)
    print("REDIS SEMANTIC CACHE TEST SUITE")
    print("🚀"*35 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Redis Connection", test_redis_connection()))
    results.append(("Persona Caching", test_persona_caching()))
    results.append(("Knowledge Caching", test_knowledge_caching()))
    results.append(("Cache Statistics", test_cache_stats()))
    results.append(("Cache Lifecycle", test_cache_lifecycle()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {test_name}")
    
    print(f"\n{'='*70}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*70}\n")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Redis semantic cache is working perfectly!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
