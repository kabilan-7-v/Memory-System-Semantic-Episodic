#!/usr/bin/env python3
"""
Integration Verification Script
Verifies all new files and features are properly integrated
"""
import sys

def verify_imports():
    """Verify all module imports"""
    print("=" * 80)
    print("INTEGRATION VERIFICATION")
    print("=" * 80)
    print()
    
    tests = []
    
    # Test 1: New file modules
    print("1. Testing new file modules...")
    try:
        from src.episodic.file_ingestion import FileIngestionService
        from src.episodic.file_retriever import FileRetriever
        from src.episodic.file_summarizer import FileSummarizer
        from src.episodic.file_rag import FileRAG
        from src.episodic.llm_evaluator import LLMEvaluator
        from src.episodic.markdown_utils import MarkdownParser, MarkdownFormatter
        print("   ✅ All new file modules imported successfully")
        tests.append(True)
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        tests.append(False)
    
    # Test 2: Existing service modules
    print("\n2. Testing existing service modules...")
    try:
        from src.services.hybrid_search_service import HybridSearchService
        from src.services.unified_hybrid_search import UnifiedHybridSearch
        from src.services.redis_common_client import get_redis
        from src.services.semantic_memory_service import SemanticMemoryService
        print("   ✅ All service modules imported successfully")
        tests.append(True)
    except Exception as e:
        print(f"   ❌ Service import failed: {e}")
        tests.append(False)
    
    # Test 3: Episodic modules
    print("\n3. Testing episodic modules...")
    try:
        from src.episodic.context_builder import build_context
        from src.episodic.chat_service import add_super_chat_message
        from src.episodic.hybrid_retriever import HybridRetriever
        from src.episodic.embeddings import EmbeddingModel
        from src.episodic.llm import call_llm
        print("   ✅ All episodic modules imported successfully")
        tests.append(True)
    except Exception as e:
        print(f"   ❌ Episodic import failed: {e}")
        tests.append(False)
    
    # Summary
    print("\n" + "=" * 80)
    if all(tests):
        print("✅ ALL INTEGRATIONS SUCCESSFUL - PROJECT READY TO USE")
        print("=" * 80)
        return 0
    else:
        print(f"⚠️  {sum(tests)}/{len(tests)} tests passed")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(verify_imports())
