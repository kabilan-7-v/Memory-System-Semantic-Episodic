#!/usr/bin/env python3
"""
Quick test to verify bi-encoder integration
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test all imports"""
    print("Testing imports...")
    
    try:
        from services.biencoder_reranker import (
            BiEncoderReranker,
            get_recommended_config,
            SENTENCE_TRANSFORMERS_AVAILABLE,
            FAISS_AVAILABLE
        )
        print("✅ biencoder_reranker imports successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    print(f"   sentence-transformers: {'✅' if SENTENCE_TRANSFORMERS_AVAILABLE else '❌'}")
    print(f"   FAISS: {'✅' if FAISS_AVAILABLE else '❌'}")
    
    return True

def test_basic_functionality():
    """Test basic re-ranking"""
    print("\nTesting basic functionality...")
    
    from services.biencoder_reranker import BiEncoderReranker, get_recommended_config
    
    # Get fast config
    config = get_recommended_config("fast")
    print(f"✅ Config loaded: {config['description']}")
    
    # Initialize reranker
    reranker = BiEncoderReranker(
        model_name=config['model_name'],
        batch_size=config['batch_size']
    )
    print("✅ Reranker initialized")
    
    # Test documents
    docs = [
        "Python is a programming language",
        "Machine learning uses neural networks",
        "Databases store data efficiently"
    ]
    
    # Build index
    reranker.build_index(docs)
    print(f"✅ Index built with {len(docs)} documents")
    
    # Re-rank
    results = reranker.rerank(
        query="What is machine learning?",
        top_k=3,
        score_threshold=0.3
    )
    print(f"✅ Re-ranking successful: {len(results)} results")
    
    if results:
        print(f"   Top result: {results[0]['document'][:50]}... (score: {results[0]['score']:.4f})")
    
    return True

def main():
    """Run all tests"""
    print("="*80)
    print("🧪 BI-ENCODER INTEGRATION TEST")
    print("="*80)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed!")
        return
    
    # Test functionality
    try:
        if test_basic_functionality():
            print("\n" + "="*80)
            print("✅ ALL TESTS PASSED - Bi-encoder is ready to use!")
            print("="*80)
        else:
            print("\n❌ Functionality test failed!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
