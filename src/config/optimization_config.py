"""
Context Optimization Configuration
Centralized settings for memory and token optimization
"""

# ==================== Deduplication Settings ====================

# Similarity threshold for removing duplicate/similar content (0.7-0.85)
# RECOMMENDED RANGE: 0.7-0.85
# - 0.70-0.75: Aggressive deduplication (may lose nuanced variants)
# - 0.76-0.82: Balanced (recommended range)
# - 0.83-0.85: Conservative (keeps more variations)
SIMILARITY_THRESHOLD = 0.80

# ==================== Diversity Sampling ====================

# Maximum contexts from same source (prevents over-representation)
MAX_PER_SOURCE = 3

# ==================== Contradiction Detection ====================

# Enable contradiction detection
ENABLE_CONTRADICTION_DETECTION = True

# Contradiction threshold (how similar but opposite)
CONTRADICTION_THRESHOLD = 0.25

# ==================== Entropy Filtering Settings ====================

# Minimum entropy score to keep content (0-1)
# Higher = only keep high-information content
# Lower = more permissive
ENTROPY_THRESHOLD = 0.3

# Minimum character length for meaningful content
MIN_INFO_CONTENT = 10

# ==================== Token Limits ====================

# Maximum tokens allowed in final context
# Adjust based on your LLM's context window
MAX_CONTEXT_TOKENS = 4000

# Maximum tokens per individual context item
MAX_TOKENS_PER_ITEM = 1000

# ==================== Re-ranking Settings ====================

# Enable adaptive threshold (recommended)
# Dynamically adjusts threshold based on score distribution
ENABLE_ADAPTIVE_THRESHOLD = True

# Base minimum relevance score for re-ranking threshold (0-1)
# This serves as the baseline - will be adjusted if adaptive enabled
# 
# THRESHOLD RATIONALE (0.65 = 65% relevance):
# - Below 0.60: Too permissive, allows weak/noisy matches
# - 0.65-0.70: Sweet spot - filters noise while keeping relevant context
# - Above 0.70: Too strict, may lose valuable peripheral information
# - Research shows 65% relevance optimally balances precision/recall for RAG systems
RERANK_THRESHOLD = 0.65

# Maximum re-ranking iterations
# More iterations = better quality but slower
#
# ITERATION RATIONALE (3 iterations optimal):
# - 1 iteration: Basic filtering only, may miss low-quality contexts
# - 2 iterations: Good for simple queries, adequate filtering
# - 3 iterations: Optimal for complex queries (convergence point)
# - 4+ iterations: Diminishing returns (<5% improvement), adds latency
MAX_ITERATIONS = 3

# ==================== Compression Settings ====================

# Enable text compression (remove redundant phrases, whitespace)
ENABLE_COMPRESSION = True

# Compression aggressiveness (0-1)
# Higher = more aggressive compression
COMPRESSION_RATIO = 0.3

# Context window for compression (sentences to keep around relevant content)
# 0 = only relevant sentences
# 1 = relevant + 1 sentence before/after
# 2 = relevant + 2 sentences before/after
COMPRESSION_CONTEXT_WINDOW = 1

# ==================== Summarization Settings ====================

# Enable automatic summarization when contexts are redundant
ENABLE_AUTO_SUMMARIZATION = False

# Summarization threshold (how similar contexts trigger summarization)
SUMMARIZATION_SIMILARITY_THRESHOLD = 0.8

# Target compression ratio for summarization (0-1)
SUMMARIZATION_COMPRESSION_RATIO = 0.3

# ==================== Model-Specific Settings ====================

# Different models have different context windows
# Adjust MAX_CONTEXT_TOKENS based on your model

MODEL_CONFIGS = {
    "gpt-4": {
        "max_context_tokens": 8000,
        "aggressive_optimization": False
    },
    "gpt-3.5-turbo": {
        "max_context_tokens": 4000,
        "aggressive_optimization": True
    },
    "claude-3": {
        "max_context_tokens": 8000,
        "aggressive_optimization": False
    },
    "llama-3-70b": {
        "max_context_tokens": 3000,
        "aggressive_optimization": True
    },
    "groq": {
        "max_context_tokens": 4000,
        "aggressive_optimization": True
    }
}

# ==================== Performance Settings ====================

# Enable parallel processing for optimization
ENABLE_PARALLEL_PROCESSING = True

# Batch size for processing contexts
BATCH_SIZE = 50

# ==================== Logging Settings ====================

# Log optimization statistics
LOG_OPTIMIZATION_STATS = True

# Detailed logging (verbose)
VERBOSE_LOGGING = False

# ==================== Advanced Settings ====================

# Weight for vector similarity in hybrid search
VECTOR_WEIGHT = 0.6

# Weight for BM25 keyword search
BM25_WEIGHT = 0.3

# Weight for recency in scoring
RECENCY_WEIGHT = 0.1

# Minimum total score to keep a context
MIN_TOTAL_SCORE = 0.3

# Enable dimensional reduction for embeddings
ENABLE_DIMENSIONAL_REDUCTION = False

# Target dimensions for dimensional reduction (if enabled)
EMBEDDING_DIMENSIONS = 384


def get_config_for_model(model_name: str) -> dict:
    """
    Get optimized configuration for a specific model
    
    Args:
        model_name: Name of the LLM model
        
    Returns:
        Configuration dict optimized for that model
    """
    base_config = {
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "entropy_threshold": ENTROPY_THRESHOLD,
        "min_info_content": MIN_INFO_CONTENT,
        "max_context_tokens": MAX_CONTEXT_TOKENS,
        "rerank_threshold": RERANK_THRESHOLD,
        "max_iterations": MAX_ITERATIONS,
        "compression_ratio": COMPRESSION_RATIO,
    }
    
    # Override with model-specific settings
    if model_name in MODEL_CONFIGS:
        model_config = MODEL_CONFIGS[model_name]
        base_config.update(model_config)
        
        # Aggressive optimization adjustments
        if model_config.get("aggressive_optimization"):
            base_config["similarity_threshold"] = 0.80  # More aggressive dedup
            base_config["entropy_threshold"] = 0.4      # Stricter entropy filter
            base_config["compression_ratio"] = 0.4      # More compression
    
    return base_config


def get_optimization_profile(profile: str = "balanced") -> dict:
    """
    Get pre-configured optimization profiles
    
    Profiles:
        - conservative: Minimal optimization, preserve most content
        - balanced: Good balance of quality and efficiency (default)
        - aggressive: Maximum optimization, focus on token reduction
        - quality: Prioritize quality over token savings
        
    Returns:
        Configuration dict for the profile
    """
    profiles = {
        "conservative": {
            "similarity_threshold": 0.85,  # Conservative dedup (within 0.7-0.85 range)
            "entropy_threshold": 0.2,      # Keep most content
            "min_info_content": 5,
            "max_context_tokens": 6000,
            "rerank_threshold": 0.5,
            "max_iterations": 1,
            "compression_ratio": 0.5,      # Light compression
            "max_per_source": 5,
            "enable_contradiction_detection": True,
            "enable_adaptive_threshold": False,  # Static threshold
            "contradiction_threshold": 0.25,
        },
        "balanced": {
            "similarity_threshold": 0.80,  # Balanced dedup (optimal in 0.7-0.85 range)
            "entropy_threshold": 0.3,
            "min_info_content": 10,
            "max_context_tokens": 4000,
            "rerank_threshold": 0.65,
            "max_iterations": 3,
            "compression_ratio": 0.3,
            "max_per_source": 3,
            "enable_contradiction_detection": True,
            "enable_adaptive_threshold": True,  # Adaptive threshold
            "contradiction_threshold": 0.25,
        },
        "aggressive": {
            "similarity_threshold": 0.70,  # Aggressive dedup (lower bound of 0.7-0.85)
            "entropy_threshold": 0.4,      # Stricter entropy
            "min_info_content": 15,
            "max_context_tokens": 3000,
            "rerank_threshold": 0.70,      # Higher threshold
            "max_iterations": 2,
            "compression_ratio": 0.2,      # More compression
            "max_per_source": 2,
            "enable_contradiction_detection": True,
            "enable_adaptive_threshold": True,
            "contradiction_threshold": 0.20,
        },
        "quality": {
            "similarity_threshold": 0.82,  # High quality dedup
            "entropy_threshold": 0.25,
            "min_info_content": 8,
            "max_context_tokens": 5000,
            "rerank_threshold": 0.60,      # Lower threshold = more content
            "max_iterations": 4,           # More iterations for quality
            "compression_ratio": 0.4,      # Less compression
            "max_per_source": 4,
            "enable_contradiction_detection": True,
            "enable_adaptive_threshold": True,
            "contradiction_threshold": 0.30,
        }
    }
    
    return profiles.get(profile, profiles["balanced"])
