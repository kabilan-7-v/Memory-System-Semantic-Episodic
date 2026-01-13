"""
Enhanced Context Optimization with NLI and Unified SLM
Demonstration script showing advanced features
"""
from src.services.nli_contradiction_detector import (
    NLIContradictionDetector,
    UnifiedSemanticProcessor,
    get_recommended_models,
    print_model_comparison,
    SENTENCE_BERT_ALTERNATIVES
)


def demo_nli_contradiction_detection():
    """Demonstrate NLI-based contradiction detection"""
    print("\n" + "="*90)
    print("DEMO: NLI-BASED CONTRADICTION DETECTION")
    print("="*90 + "\n")
    
    # Initialize NLI detector
    detector = NLIContradictionDetector(
        nli_model="cross-encoder/nli-deberta-v3-small",
        contradiction_threshold=0.5,
        use_bidirectional=True
    )
    
    # Test cases
    test_cases = [
        {
            "text1": "The project deadline is next Friday.",
            "text2": "We have until next Friday to complete the project.",
            "expected": "Entailment (same meaning)"
        },
        {
            "text1": "The meeting is scheduled for 3 PM.",
            "text2": "The meeting was cancelled.",
            "expected": "Contradiction"
        },
        {
            "text1": "Python is a programming language.",
            "text2": "JavaScript is used for web development.",
            "expected": "Neutral (unrelated)"
        },
        {
            "text1": "The server is running on port 8080.",
            "text2": "The server is not running on port 8080.",
            "expected": "Contradiction"
        }
    ]
    
    print("Testing NLI contradiction detection:\n")
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}:")
        print(f"   Text 1: {case['text1']}")
        print(f"   Text 2: {case['text2']}")
        print(f"   Expected: {case['expected']}")
        
        is_contradiction, details = detector.detect_contradiction(
            case['text1'],
            case['text2'],
            return_details=True
        )
        
        print(f"   Result: {'✅ CONTRADICTION' if is_contradiction else '✓ No contradiction'}")
        print(f"   Scores:")
        print(f"      ├─ Contradiction: {details['contradiction_score']:.3f}")
        print(f"      ├─ Entailment: {details['entailment_score']:.3f}")
        print(f"      ├─ Neutral: {details['neutral_score']:.3f}")
        print(f"      └─ Predicted: {details['predicted_label']}")
        print()


def demo_unified_slm():
    """Demonstrate unified SLM for dedup and ranking"""
    print("\n" + "="*90)
    print("DEMO: UNIFIED SEMANTIC PROCESSOR")
    print("="*90 + "\n")
    
    # Initialize unified processor
    processor = UnifiedSemanticProcessor(
        model_name="sentence-transformers/all-mpnet-base-v2",
        batch_size=32
    )
    
    # Sample contexts
    contexts = [
        {"content": "Machine learning is a subset of artificial intelligence.", "source": "doc1"},
        {"content": "ML is part of AI technology.", "source": "doc2"},  # Duplicate
        {"content": "Python is a popular programming language.", "source": "doc3"},
        {"content": "Deep learning uses neural networks.", "source": "doc4"},
        {"content": "Neural networks are the foundation of deep learning.", "source": "doc5"},  # Duplicate
        {"content": "Cloud computing provides on-demand resources.", "source": "doc6"}
    ]
    
    print(f"Original contexts: {len(contexts)}\n")
    
    # 1. Deduplicate
    print("Step 1: Semantic Deduplication")
    deduplicated, removed = processor.deduplicate_by_similarity(
        contexts,
        threshold=0.85
    )
    
    # 2. Rank by relevance
    query = "What is machine learning?"
    print("Step 2: Semantic Ranking")
    ranked = processor.rank_by_relevance(
        query=query,
        contexts=deduplicated,
        top_k=3
    )
    
    print("Final Results:")
    for i, ctx in enumerate(ranked, 1):
        print(f"{i}. Score: {ctx['semantic_score']:.3f} | {ctx['content']}")
    print()


def demo_batch_contradiction_detection():
    """Demonstrate batch contradiction detection across multiple contexts"""
    print("\n" + "="*90)
    print("DEMO: BATCH CONTRADICTION DETECTION")
    print("="*90 + "\n")
    
    # Initialize detector
    detector = NLIContradictionDetector(
        nli_model="cross-encoder/nli-deberta-v3-small",
        contradiction_threshold=0.5
    )
    
    # Sample contexts with contradictions
    contexts = [
        {"content": "The database server is running normally."},
        {"content": "All systems are operational."},
        {"content": "The database server crashed and is offline."},  # Contradicts #1
        {"content": "User authentication is working correctly."},
        {"content": "Users cannot log in due to authentication failure."}  # Contradicts #4
    ]
    
    # Detect contradictions
    contexts_with_flags = detector.detect_contradictions_batch(contexts)
    
    # Display results
    print("Results:")
    for i, ctx in enumerate(contexts_with_flags):
        has_contradiction = ctx.get('has_contradiction', False)
        contradicts_with = ctx.get('contradicts_with', [])
        
        status = "⚠️  HAS CONTRADICTION" if has_contradiction else "✓ No contradiction"
        print(f"\nContext {i}: {status}")
        print(f"   Content: {ctx['content']}")
        if contradicts_with:
            print(f"   Contradicts with:")
            for c in contradicts_with:
                print(f"      ├─ Context {c['index']} (score: {c['score']:.3f})")


def demo_model_comparison():
    """Show comparison of different Sentence-BERT alternatives"""
    print_model_comparison()
    
    # Show recommended models for different profiles
    print("\n" + "="*90)
    print("RECOMMENDED MODEL PROFILES")
    print("="*90 + "\n")
    
    profiles = ["fast", "balanced", "accurate", "multilingual"]
    for profile in profiles:
        models = get_recommended_models(profile)
        print(f"📌 {profile.upper()} Profile:")
        print(f"   ├─ Bi-Encoder: {models['bi_encoder']}")
        print(f"   ├─ NLI Model: {models['nli']}")
        print(f"   └─ {models['description']}")
        print()


def demo_integration_with_context_optimizer():
    """Show how to integrate with existing context optimizer"""
    print("\n" + "="*90)
    print("INTEGRATION GUIDE: Context Optimizer + NLI + Unified SLM")
    print("="*90 + "\n")
    
    code_example = """
# Enhanced Context Optimizer with NLI and Unified SLM

from src.services.context_optimizer import ContextOptimizer
from src.services.nli_contradiction_detector import (
    NLIContradictionDetector,
    UnifiedSemanticProcessor
)

# Option 1: Use with existing optimizer (add NLI detector separately)
optimizer = ContextOptimizer(
    similarity_threshold=0.80,
    max_context_tokens=4000,
    enable_contradiction_detection=True
)

# Initialize NLI detector
nli_detector = NLIContradictionDetector(
    nli_model="cross-encoder/nli-deberta-v3-small",
    contradiction_threshold=0.5
)

# Initialize unified SLM
unified_slm = UnifiedSemanticProcessor(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

# Optimize contexts
contexts = [...]  # Your contexts
optimized, stats = optimizer.optimize(contexts, query="your query")

# Apply NLI contradiction detection
contexts_with_nli = nli_detector.detect_contradictions_batch(optimized)

# Apply unified SLM ranking
final_contexts = unified_slm.rank_by_relevance(
    query="your query",
    contexts=contexts_with_nli,
    top_k=10
)

# Option 2: Use unified SLM for deduplication
deduplicated, removed = unified_slm.deduplicate_by_similarity(
    contexts,
    threshold=0.85
)

print(f"Removed {removed} semantic duplicates")
print(f"Detected {len([c for c in final_contexts if c.get('has_contradiction')])} contradictions")
"""
    
    print(code_example)
    
    print("\n" + "="*90)
    print("KEY BENEFITS")
    print("="*90)
    print("""
✅ NLI-Based Contradiction Detection:
   - More accurate than pattern matching
   - Understands semantic relationships
   - Trained specifically for contradiction detection
   
✅ Unified SLM:
   - Single model for multiple tasks (efficiency)
   - Consistent embeddings across pipeline
   - Reduced memory footprint
   
✅ Enhanced Observability:
   - Detailed logs for each step
   - Contradiction scores and explanations
   - Semantic similarity metrics
""")


def demo_performance_comparison():
    """Compare different approaches"""
    print("\n" + "="*90)
    print("PERFORMANCE COMPARISON")
    print("="*90 + "\n")
    
    comparison_table = """
┌─────────────────────────┬──────────────┬─────────────┬────────────────┐
│ Approach                │ Accuracy     │ Speed       │ Use Case       │
├─────────────────────────┼──────────────┼─────────────┼────────────────┤
│ Pattern-based           │ Good         │ Very Fast   │ Simple cases   │
│ Cosine similarity       │ Very Good    │ Fast        │ General dedup  │
│ NLI cross-encoder      │ Excellent    │ Moderate    │ Contradictions │
│ Unified bi-encoder     │ Very Good    │ Fast        │ Multi-task     │
└─────────────────────────┴──────────────┴─────────────┴────────────────┘

RECOMMENDATIONS:
- Use NLI for: Contradiction detection, entailment checking
- Use bi-encoder for: Deduplication, ranking, clustering
- Use unified SLM when: Multiple tasks need consistent embeddings
- Use pattern-based when: Latency is critical, simple cases only
"""
    
    print(comparison_table)


if __name__ == "__main__":
    print("\n" + "="*90)
    print("ENHANCED CONTEXT OPTIMIZATION - FULL DEMONSTRATION")
    print("="*90)
    
    try:
        # Run all demos
        demo_nli_contradiction_detection()
        demo_unified_slm()
        demo_batch_contradiction_detection()
        demo_model_comparison()
        demo_integration_with_context_optimizer()
        demo_performance_comparison()
        
        print("\n" + "="*90)
        print("✅ ALL DEMONSTRATIONS COMPLETE")
        print("="*90 + "\n")
        
    except ImportError as e:
        print(f"\n⚠️  Missing dependencies: {e}")
        print("\nInstall required packages:")
        print("   pip install sentence-transformers")
        print("\nOptional (for faster similarity search):")
        print("   pip install faiss-cpu  # or faiss-gpu for GPU support")
