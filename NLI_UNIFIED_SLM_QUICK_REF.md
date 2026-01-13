# NLI & Unified SLM - Quick Reference Card

## 🚀 Quick Start

### Installation
```bash
pip install sentence-transformers
pip install faiss-cpu  # optional, for faster search
```

### Basic Usage

```python
from src.services.nli_contradiction_detector import (
    NLIContradictionDetector,
    UnifiedSemanticProcessor
)

# Initialize
nli = NLIContradictionDetector()
slm = UnifiedSemanticProcessor()

# Deduplicate
deduplicated, removed = slm.deduplicate_by_similarity(contexts, threshold=0.85)

# Detect contradictions
checked = nli.detect_contradictions_batch(deduplicated)

# Rank by relevance
ranked = slm.rank_by_relevance(query, checked, top_k=10)
```

---

## 📊 Model Selection Cheat Sheet

```python
from src.services.nli_contradiction_detector import get_recommended_models

# Choose profile
models = get_recommended_models("balanced")  # fast | balanced | accurate | multilingual
```

| Profile | Bi-Encoder | NLI Model | Use When |
|---------|-----------|-----------|----------|
| **fast** | all-MiniLM-L6-v2 | nli-deberta-v3-small | Production, low latency |
| **balanced** ⭐ | all-mpnet-base-v2 | nli-deberta-v3-base | General use (RECOMMENDED) |
| **accurate** | all-roberta-large-v1 | nli-deberta-v3-large | Accuracy critical |
| **multilingual** | paraphrase-multilingual-mpnet | nli-xlm-roberta | 50+ languages |

---

## 🎯 API Reference

### NLIContradictionDetector

```python
# Initialize
detector = NLIContradictionDetector(
    nli_model="cross-encoder/nli-deberta-v3-small",
    contradiction_threshold=0.5,  # 0-1, default 0.5
    use_bidirectional=True        # Check both directions
)

# Single pair
is_contradiction, details = detector.detect_contradiction(
    text1="Server is online",
    text2="Server crashed",
    return_details=True
)

# Batch
contexts = [{"content": "..."}]
results = detector.detect_contradictions_batch(contexts)
```

**Returns**:
```python
{
    'contradiction_score': 0.87,      # 0-1
    'entailment_score': 0.08,         # 0-1
    'neutral_score': 0.05,            # 0-1
    'predicted_label': 'contradiction',
    'threshold': 0.5,
    'bidirectional_checked': True
}
```

### UnifiedSemanticProcessor

```python
# Initialize
processor = UnifiedSemanticProcessor(
    model_name="sentence-transformers/all-mpnet-base-v2",
    batch_size=32
)

# Deduplicate
deduplicated, removed = processor.deduplicate_by_similarity(
    contexts,
    threshold=0.85,            # 0-1, default 0.85
    content_key='content'
)

# Rank
ranked = processor.rank_by_relevance(
    query="search query",
    contexts=contexts,
    top_k=10,                  # Optional, returns all if None
    content_key='content'
)

# Compute embeddings (for custom tasks)
embeddings = processor.compute_embeddings(
    texts=["text1", "text2"],
    show_progress=True
)
```

---

## 🔧 Threshold Tuning Guide

### Deduplication Threshold

```
0.70 ─────┬───── Aggressive (removes more)
0.75      │
0.80 ─────┼───── ⭐ RECOMMENDED (balanced)
0.85      │
0.90 ─────┴───── Conservative (keeps more)
```

**Guidelines**:
- **0.70-0.75**: Use when context is redundant, need maximum compression
- **0.76-0.82**: Balanced - good for most use cases ⭐
- **0.83-0.90**: Use when nuance matters, keep variations

### Contradiction Threshold

```
0.30 ─────┬───── Very sensitive (more false positives)
0.40      │
0.50 ─────┼───── ⭐ RECOMMENDED (balanced)
0.60      │
0.70 ─────┴───── Conservative (only obvious contradictions)
```

**Guidelines**:
- **0.3-0.4**: Maximum sensitivity, use with review
- **0.45-0.55**: Balanced - good for most use cases ⭐
- **0.6-0.8**: High confidence, minimal false positives

---

## 📈 Performance Comparison

### Speed vs Accuracy

```
              Speed →
Accuracy  Fast         Balanced      Accurate
  ↑
  │     MiniLM-L6    mpnet-base   roberta-large
  │     (22M)        (110M)       (355M)
  │     384 dim      768 dim      1024 dim
```

### Task Performance

| Task | Pattern-Based | Bi-Encoder | NLI Cross-Encoder |
|------|--------------|------------|------------------|
| **Deduplication** | ❌ Poor | ✅ Excellent | ⚠️ Overkill |
| **Contradiction** | ⚠️ Limited | ⚠️ Good | ✅ Excellent |
| **Ranking** | ❌ N/A | ✅ Excellent | ⚠️ Slower |
| **Speed** | ⚡⚡⚡⚡⚡ | ⚡⚡⚡⚡ | ⚡⚡⚡ |

---

## 🎨 Output Examples

### Contradiction Detection Output

```
🔬 NLI-BASED CONTRADICTION DETECTION
======================================================================
Model: cross-encoder/nli-deberta-v3-small
Contexts: 5
Threshold: 0.5
Bidirectional: True
======================================================================

⚠️  CONTRADICTION DETECTED:
   Context 0 ↔ Context 2
   Score: 0.873
   Label: contradiction
   Text 1: The database is online.
   Text 2: The database crashed.

======================================================================
✅ NLI CONTRADICTION DETECTION COMPLETE
   ├─ Pairs checked: 10
   ├─ Contradictions found: 1
   └─ Contradiction rate: 10.0%
======================================================================
```

### Deduplication Output

```
🔍 SEMANTIC DEDUPLICATION
   ├─ Model: sentence-transformers/all-mpnet-base-v2
   ├─ Threshold: 0.85
   └─ Contexts: 20

   ├─ Duplicate: Context 5 similar to 2 (0.912)
   ├─ Duplicate: Context 12 similar to 8 (0.887)

   ✅ Removed 2 duplicates
   └─ Remaining: 18
```

### Ranking Output

```
📊 SEMANTIC RANKING
   ├─ Model: sentence-transformers/all-mpnet-base-v2
   ├─ Query: What is machine learning?
   └─ Contexts: 18

   ✅ Ranked 10 contexts
   └─ Top score: 0.847

Results:
1. Score: 0.847 | Machine learning is a subset of AI.
2. Score: 0.782 | Deep learning uses neural networks.
3. Score: 0.691 | AI systems learn from data.
```

---

## ⚠️ Common Issues & Solutions

### ImportError: sentence-transformers

```bash
pip install sentence-transformers
```

### Out of Memory

```python
# Use smaller model
processor = UnifiedSemanticProcessor(
    model_name="sentence-transformers/all-MiniLM-L6-v2",  # 22M params
    batch_size=16  # Reduce batch size
)
```

### Slow Model Download

```python
# Pre-download models
from sentence_transformers import SentenceTransformer
SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
```

### Low Accuracy

```python
# Use more accurate model
models = get_recommended_models("accurate")
```

### High Latency

```python
# Use faster model
models = get_recommended_models("fast")
```

---

## 💡 Pro Tips

1. **Reuse embeddings** when possible:
   ```python
   # Compute once
   embeddings = processor.compute_embeddings(texts)
   # Use for multiple tasks
   ```

2. **Batch processing** for efficiency:
   ```python
   # Process in batches of 32-64 for best performance
   processor = UnifiedSemanticProcessor(batch_size=32)
   ```

3. **Cache models** for faster startup:
   ```python
   # Models auto-cache after first download
   # Location: ~/.cache/huggingface/hub/
   ```

4. **Use bidirectional NLI** for better accuracy:
   ```python
   # Check both A→B and B→A
   detector = NLIContradictionDetector(use_bidirectional=True)
   ```

5. **Tune thresholds** based on your data:
   ```python
   # Start with defaults, then adjust
   # Monitor false positives/negatives
   ```

---

## 📝 Complete Example

```python
from src.services.nli_contradiction_detector import (
    NLIContradictionDetector,
    UnifiedSemanticProcessor,
    get_recommended_models
)

# Setup
models = get_recommended_models("balanced")
nli = NLIContradictionDetector(nli_model=models['nli'])
slm = UnifiedSemanticProcessor(model_name=models['bi_encoder'])

# Data
contexts = [
    {"content": "ML is part of AI."},
    {"content": "Machine learning is a subset of artificial intelligence."},
    {"content": "Python is a programming language."},
]
query = "What is machine learning?"

# Pipeline
print("1. Deduplication")
contexts, _ = slm.deduplicate_by_similarity(contexts, threshold=0.85)

print("2. Contradiction Detection")
contexts = nli.detect_contradictions_batch(contexts)

print("3. Ranking")
contexts = slm.rank_by_relevance(query, contexts, top_k=5)

# Results
for ctx in contexts:
    score = ctx.get('semantic_score', 0)
    contradiction = "⚠️" if ctx.get('has_contradiction') else "✓"
    print(f"{contradiction} {score:.3f} | {ctx['content']}")
```

---

## 📚 See Also

- Full Documentation: `docs/NLI_AND_UNIFIED_SLM_GUIDE.md`
- Demo Script: `demo_nli_enhanced_optimization.py`
- Context Optimizer: `src/services/context_optimizer.py`
- Bi-Encoder Reranker: `src/services/biencoder_reranker.py`
