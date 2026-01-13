"""
Context Optimization Service
Optimizes memory retrieval for:
- Deduplication (similarity-based)
- Diversity sampling (balanced source representation)
- Contradiction detection (identify conflicting information)
- Entropy reduction (remove low-information content)
- Context-aware compression (preserve adjacent sentences)
- Adaptive re-ranking (dynamic threshold adjustment)
- Summarization (consolidate redundant information)
"""
from typing import List, Dict, Any, Optional, Tuple, Set
import numpy as np
from collections import defaultdict
import hashlib
import re
import warnings


class ContextOptimizer:
    """
    Optimizes retrieved context to reduce memory, context window usage, and token consumption
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.80,
        entropy_threshold: float = 0.3,
        min_info_content: int = 10,
        max_context_tokens: int = 4000,
        rerank_threshold: float = 0.65,
        max_iterations: int = 3,
        embedding_service = None,
        max_per_source: int = 3,
        enable_contradiction_detection: bool = True,
        enable_adaptive_threshold: bool = True,
        contradiction_threshold: float = 0.25
    ):
        """
        Args:
            similarity_threshold: Cosine similarity threshold for duplicate detection (0.7-0.85)
                                 Default 0.80 (80%) - balanced deduplication
                                 - 0.70-0.75: Aggressive dedup, may lose nuanced variants
                                 - 0.76-0.82: Balanced (recommended range)
                                 - 0.83-0.85: Conservative, keeps more variations
            entropy_threshold: Minimum entropy score to keep content (0-1)
            min_info_content: Minimum character length for meaningful content
            max_context_tokens: Maximum tokens allowed in final context
            rerank_threshold: Base minimum relevance score (0-1) - will be adapted if enabled
            max_iterations: Maximum re-ranking iterations (default 3)
            max_per_source: Maximum contexts from same source (diversity sampling)
            enable_contradiction_detection: Detect and flag contradicting information
            enable_adaptive_threshold: Use adaptive reranking threshold based on score distribution
            contradiction_threshold: Similarity threshold for contradiction detection (lower = more different)
        """
        # Validate and clamp similarity_threshold to recommended range
        if similarity_threshold < 0.7 or similarity_threshold > 0.85:
            warnings.warn(f"similarity_threshold {similarity_threshold} outside recommended range [0.7, 0.85]. Clamping...")
            similarity_threshold = max(0.7, min(0.85, similarity_threshold))
        
        self.similarity_threshold = similarity_threshold
        self.entropy_threshold = entropy_threshold
        self.min_info_content = min_info_content
        self.max_context_tokens = max_context_tokens
        self.rerank_threshold = rerank_threshold
        self.max_iterations = max_iterations
        self.embedding_service = embedding_service
        self.max_per_source = max_per_source
        self.enable_contradiction_detection = enable_contradiction_detection
        self.enable_adaptive_threshold = enable_adaptive_threshold
        self.contradiction_threshold = contradiction_threshold
        
    def optimize(
        self,
        contexts: List[Dict[str, Any]],
        query: str,
        embeddings: Optional[List[np.ndarray]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Main optimization pipeline with clear sequential steps
        
        Pipeline Order:
        1. Deduplication → Remove exact and semantic duplicates
        2. Diversity Sampling → Ensure balanced source representation
        3. Contradiction Detection → Identify conflicting information
        4. Entropy Filtering → Remove low-information content
        5. Context-Aware Compression → Extract relevant info with surrounding context
        6. Adaptive Re-ranking → Score and filter with dynamic threshold
        7. Token Limit Enforcement → Ensure final size constraints
        
        Args:
            contexts: List of context items with 'content' and optional 'score'
            query: Original user query
            embeddings: Optional pre-computed embeddings for contexts
            
        Returns:
            Tuple of (optimized_contexts, optimization_stats)
        """
        stats = {
            'original_count': len(contexts),
            'original_tokens': self._estimate_tokens(contexts),
            'duplicates_removed': 0,
            'diversity_filtered': 0,
            'contradictions_detected': 0,
            'low_entropy_removed': 0,
            'compressed_count': 0,
            'summarized_count': 0,
            'iterations': 0,
            'adaptive_threshold_used': None,
            'final_count': 0,
            'final_tokens': 0,
            'reduction_percentage': 0
        }
        
        if not contexts:
            return [], stats
        
        print(f"\n{'='*70}")
        print(f"🎯 CONTEXT OPTIMIZATION PIPELINE")
        print(f"{'='*70}")
        print(f"Input: {len(contexts)} contexts, ~{stats['original_tokens']} tokens")
        print(f"Target: ≤{self.max_context_tokens} tokens\n")
            
        # STEP 1: DEDUPLICATION
        print(f"📋 STEP 1/7: DEDUPLICATION")
        print(f"   ├─ Removing exact duplicates...")
        contexts = self._remove_exact_duplicates(contexts, stats)
        print(f"   ├─ Removing semantic duplicates (threshold: {self.similarity_threshold:.2f})...")
        contexts = self._remove_similar_duplicates(contexts, embeddings, stats)
        print(f"   └─ Remaining: {len(contexts)} contexts\n")
        
        # STEP 2: DIVERSITY SAMPLING
        print(f"🎲 STEP 2/7: DIVERSITY SAMPLING")
        print(f"   ├─ Ensuring balanced source representation (max {self.max_per_source} per source)...")
        contexts = self._ensure_source_diversity(contexts, stats)
        print(f"   └─ Remaining: {len(contexts)} contexts\n")
        
        # STEP 3: CONTRADICTION DETECTION
        if self.enable_contradiction_detection:
            print(f"⚠️  STEP 3/7: CONTRADICTION DETECTION")
            print(f"   ├─ Analyzing for conflicting information...")
            contexts = self._detect_contradictions(contexts, stats)
            print(f"   └─ Contradictions flagged: {stats['contradictions_detected']}\n")
        else:
            print(f"⚠️  STEP 3/7: CONTRADICTION DETECTION [DISABLED]\n")
        
        # STEP 4: ENTROPY FILTERING
        print(f"📊 STEP 4/7: ENTROPY FILTERING")
        print(f"   ├─ Filtering low-information content (threshold: {self.entropy_threshold:.2f})...")
        contexts = self._filter_low_entropy(contexts, stats)
        print(f"   └─ Remaining: {len(contexts)} contexts\n")
        
        # STEP 5: CONTEXT-AWARE COMPRESSION
        print(f"🗜️  STEP 5/7: CONTEXT-AWARE COMPRESSION")
        print(f"   ├─ Extracting relevant content while preserving context...")
        contexts = self._compress_contexts(contexts, query, stats)
        print(f"   └─ Compressed: {stats['compressed_count']} contexts\n")
        
        # STEP 6: ADAPTIVE RE-RANKING
        print(f"🔄 STEP 6/7: ADAPTIVE RE-RANKING")
        if self.enable_adaptive_threshold:
            print(f"   ├─ Using adaptive threshold (base: {self.rerank_threshold:.2f})...")
        else:
            print(f"   ├─ Using static threshold: {self.rerank_threshold:.2f}...")
        contexts = self._rerank_with_verification(contexts, query, stats)
        print(f"   └─ Remaining: {len(contexts)} contexts after {stats['iterations']} iteration(s)\n")
        
        # STEP 7: TOKEN LIMIT ENFORCEMENT
        print(f"✂️  STEP 7/7: TOKEN LIMIT ENFORCEMENT")
        print(f"   ├─ Enforcing max {self.max_context_tokens} tokens...")
        contexts = self._enforce_token_limit(contexts, stats)
        print(f"   └─ Final: {len(contexts)} contexts\n")
        
        # Update final stats
        stats['final_count'] = len(contexts)
        stats['final_tokens'] = self._estimate_tokens(contexts)
        stats['reduction_percentage'] = (
            100 * (1 - stats['final_tokens'] / max(stats['original_tokens'], 1))
        )
        
        print(f"{'='*70}")
        print(f"✅ OPTIMIZATION COMPLETE")
        print(f"   ├─ Reduction: {stats['reduction_percentage']:.1f}%")
        print(f"   ├─ Tokens: {stats['original_tokens']} → {stats['final_tokens']}")
        print(f"   └─ Contexts: {stats['original_count']} → {stats['final_count']}")
        print(f"{'='*70}\n")
        
        return contexts, stats
        
        # Step 6: Final token limit enforcement
        contexts = self._enforce_token_limit(contexts, stats)
        
        # Update final stats
        stats['final_count'] = len(contexts)
        stats['final_tokens'] = self._estimate_tokens(contexts)
        stats['reduction_percentage'] = (
            100 * (1 - stats['final_tokens'] / max(stats['original_tokens'], 1))
        )
        
        return contexts, stats
    
    def _remove_exact_duplicates(
        self,
        contexts: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Remove exact duplicate content using hash-based deduplication"""
        seen_hashes = set()
        unique_contexts = []
        
        for ctx in contexts:
            content = self._get_content(ctx)
            
            # FIRST: Remove duplicate sentences within the content itself
            content = self._remove_duplicate_sentences(content, stats)
            
            # THEN: Check for duplicate contexts
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                # Update context with deduplicated content
                ctx_copy = ctx.copy()
                ctx_copy['content'] = content
                unique_contexts.append(ctx_copy)
            else:
                stats['duplicates_removed'] += 1
                
        return unique_contexts
    
    def _ensure_source_diversity(
        self,
        contexts: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Ensure balanced representation from different sources
        Prevents over-representation from single source
        """
        source_counts = {}
        diverse_contexts = []
        
        for ctx in contexts:
            # Try multiple source identifiers
            source = (
                ctx.get('source_id') or 
                ctx.get('source_layer') or 
                ctx.get('table_name') or 
                'unknown'
            )
            
            if source_counts.get(source, 0) < self.max_per_source:
                diverse_contexts.append(ctx)
                source_counts[source] = source_counts.get(source, 0) + 1
            else:
                stats['diversity_filtered'] += 1
        
        return diverse_contexts
    
    def _detect_contradictions(
        self,
        contexts: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect contradicting information across contexts
        Flags contradictions but keeps both for user awareness
        """
        if not self.embedding_service or len(contexts) < 2:
            return contexts
        
        # Negation patterns that often indicate contradictions
        negation_patterns = [
            r'\bnot\b', r'\bno\b', r'\bnever\b', r'\bnone\b',
            r'\bdidn\'t\b', r'\bisn\'t\b', r'\bwasn\'t\b', r'\baren\'t\b',
            r'\bhaven\'t\b', r'\bhasn\'t\b', r'\bwon\'t\b', r'\bcan\'t\b'
        ]
        
        # Compare each pair of contexts
        for i, ctx1 in enumerate(contexts):
            content1 = self._get_content(ctx1).lower()
            
            for j, ctx2 in enumerate(contexts[i+1:], start=i+1):
                content2 = self._get_content(ctx2).lower()
                
                # Check if contents are similar but opposite
                try:
                    emb1 = self.embedding_service.get_embedding(content1)
                    emb2 = self.embedding_service.get_embedding(content2)
                    similarity = self._cosine_similarity(emb1, emb2)
                    
                    # Similar content with opposite sentiment/negation = potential contradiction
                    has_negation_1 = any(re.search(p, content1) for p in negation_patterns)
                    has_negation_2 = any(re.search(p, content2) for p in negation_patterns)
                    
                    # High similarity + XOR negation = likely contradiction
                    if (similarity > self.similarity_threshold - 0.15 and 
                        has_negation_1 != has_negation_2):
                        
                        # Flag both contexts as contradicting
                        if 'contradicts_with' not in ctx1:
                            ctx1['contradicts_with'] = []
                        if 'contradicts_with' not in ctx2:
                            ctx2['contradicts_with'] = []
                        
                        ctx1['contradicts_with'].append(j)
                        ctx2['contradicts_with'].append(i)
                        ctx1['has_contradiction'] = True
                        ctx2['has_contradiction'] = True
                        
                        stats['contradictions_detected'] += 1
                        print(f"   ├─ ⚠️  Contradiction detected between context {i} and {j}")
                        
                except Exception as e:
                    continue
        
        return contexts
    
    def _remove_duplicate_sentences(self, text: str, stats: Dict[str, Any]) -> str:
        """Remove duplicate sentences (exact text + semantic meaning)"""
        import re
        
        # Helper function to split text into clauses
        def split_into_clauses(text: str) -> List[str]:
            """Split text into analyzable clauses (lines, sentences, and compound clauses)"""
            clauses = []
            
            # First split by newlines
            lines = text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Split by sentence delimiters (. ! ?)
                sentences = re.split(r'[.!?]+\s*', line)
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    # Split compound sentences by conjunctions (and, or, but)
                    # This catches: "My name is Sharan and Sharan is my name"
                    parts = re.split(r'\s+(?:and|or|but)\s+', sentence, flags=re.IGNORECASE)
                    
                    for part in parts:
                        part = part.strip()
                        if len(part) > 5:  # Minimum meaningful clause length
                            clauses.append(part)
            
            return clauses
        
        # Get all clauses from text
        clauses = split_into_clauses(text)
        
        print(f"   📝 Split into {len(clauses)} clauses: {clauses[:5]}")  # Debug
        
        if len(clauses) == 0:
            return text
        
        # Track exact and semantic duplicates
        seen_exact = set()
        seen_embeddings = []
        unique_clauses = []
        duplicates_in_text = 0
        semantic_threshold = 0.88  # 88% similarity = semantic duplicate (slightly lower for clauses)
        
        for clause in clauses:
            # 1. Check exact duplicates (normalized)
            clause_normalized = re.sub(r'[.!?,;:]+$', '', clause).lower().strip()
            
            if clause_normalized in seen_exact:
                duplicates_in_text += 1
                continue
            
            # 2. Check semantic duplicates (meaning-based)
            is_semantic_duplicate = False
            if self.embedding_service and len(seen_embeddings) > 0:
                try:
                    current_embedding = self.embedding_service.get_embedding(clause)
                    
                    # Compare with existing clauses
                    for existing_emb, existing_text in seen_embeddings:
                        similarity = self._cosine_similarity(current_embedding, existing_emb)
                        if similarity >= semantic_threshold:
                            duplicates_in_text += 1
                            is_semantic_duplicate = True
                            print(f"   🔍 Semantic duplicate detected: '{clause}' ≈ '{existing_text}' (similarity: {similarity:.2%})")
                            break
                    
                    if not is_semantic_duplicate:
                        seen_embeddings.append((current_embedding, clause))
                        seen_exact.add(clause_normalized)
                        unique_clauses.append(clause)
                except Exception as e:
                    # Fallback to exact matching if embedding fails
                    print(f"   ⚠️  Embedding failed for '{clause[:50]}': {e}")
                    seen_exact.add(clause_normalized)
                    unique_clauses.append(clause)
            else:
                # No embedding service, use exact matching only
                seen_exact.add(clause_normalized)
                unique_clauses.append(clause)
        
        # Update stats
        if duplicates_in_text > 0:
            stats['duplicates_removed'] += duplicates_in_text
        
        # Rejoin clauses intelligently
        if unique_clauses:
            # If original had newlines, preserve structure
            if '\n' in text:
                return '\n'.join(unique_clauses)
            else:
                # Otherwise join as sentence
                return '. '.join(unique_clauses) + ('.' if not text.strip().endswith(('.', '!', '?')) else '')
        
        return text
    
    def _remove_similar_duplicates(
        self,
        contexts: List[Dict[str, Any]],
        embeddings: Optional[List[np.ndarray]],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Remove similar content using cosine similarity"""
        if not embeddings or len(embeddings) != len(contexts):
            # If no embeddings provided, compute them (simplified approach)
            embeddings = [self._compute_simple_embedding(self._get_content(ctx)) 
                         for ctx in contexts]
        
        unique_contexts = []
        unique_embeddings = []
        
        for i, (ctx, emb) in enumerate(zip(contexts, embeddings)):
            is_duplicate = False
            
            for unique_emb in unique_embeddings:
                similarity = self._cosine_similarity(emb, unique_emb)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    stats['duplicates_removed'] += 1
                    break
            
            if not is_duplicate:
                unique_contexts.append(ctx)
                unique_embeddings.append(emb)
                
        return unique_contexts
    
    def _filter_low_entropy(
        self,
        contexts: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter out low-information content based on entropy analysis"""
        filtered_contexts = []
        
        for ctx in contexts:
            content = self._get_content(ctx)
            
            # Skip very short content
            if len(content) < self.min_info_content:
                stats['low_entropy_removed'] += 1
                continue
            
            # Calculate information entropy
            entropy_score = self._calculate_entropy(content)
            
            if entropy_score >= self.entropy_threshold:
                filtered_contexts.append(ctx)
            else:
                stats['low_entropy_removed'] += 1
                
        return filtered_contexts
    
    def _compress_contexts(
        self,
        contexts: List[Dict[str, Any]],
        query: str,
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Context-aware compression:
        1. Extract query-relevant sentences
        2. Keep adjacent sentences for context
        3. Preserve section headers/structure
        4. Remove redundant phrases
        """
        compressed_contexts = []
        
        for ctx in contexts:
            content = self._get_content(ctx)
            
            # Extract key sentences WITH surrounding context
            compressed_content = self._extract_relevant_with_context(content, query)
            
            # Remove redundant whitespace and formatting
            compressed_content = self._clean_text(compressed_content)
            
            # Only compress if it saves significant space
            if len(compressed_content) < len(content) * 0.9:
                ctx_copy = ctx.copy()
                ctx_copy['content'] = compressed_content
                ctx_copy['compressed'] = True
                compressed_contexts.append(ctx_copy)
                stats['compressed_count'] += 1
            else:
                compressed_contexts.append(ctx)
                
        return compressed_contexts
    
    def _calculate_adaptive_threshold(
        self,
        scores: List[float],
        base_threshold: float
    ) -> float:
        """
        Calculate adaptive threshold based on score distribution
        
        Strategy:
        - High score variance → Lower threshold (diverse quality)
        - Low score variance → Higher threshold (consistent quality)
        - Uses median + percentile analysis for robustness
        """
        if len(scores) < 3:
            return base_threshold
        
        scores_sorted = sorted(scores, reverse=True)
        median = scores_sorted[len(scores) // 2]
        q75 = scores_sorted[len(scores) // 4]
        q25 = scores_sorted[3 * len(scores) // 4] if len(scores) >= 4 else scores_sorted[-1]
        
        # Calculate interquartile range (IQR)
        iqr = q75 - q25
        
        # Adaptive threshold based on distribution
        if iqr > 0.3:  # High variance
            adaptive_threshold = max(base_threshold - 0.1, median * 0.8)
        elif iqr < 0.15:  # Low variance
            adaptive_threshold = min(base_threshold + 0.05, median * 0.95)
        else:  # Medium variance
            adaptive_threshold = (base_threshold + median) / 2
        
        # Clamp to reasonable range
        adaptive_threshold = max(0.5, min(0.8, adaptive_threshold))
        
        return adaptive_threshold
    
    def _rerank_with_verification(
        self,
        contexts: List[Dict[str, Any]],
        query: str,
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Re-rank contexts with adaptive threshold adjustment
        
        Adaptive strategy:
        - Analyzes score distribution each iteration
        - Adjusts threshold based on data quality
        - Prevents over-filtering or under-filtering
        """
        iteration = 0
        current_contexts = contexts.copy()
        active_threshold = self.rerank_threshold
        
        while iteration < self.max_iterations:
            iteration += 1
            stats['iterations'] = iteration
            
            # Score all contexts
            scored_contexts = []
            for ctx in current_contexts:
                content = self._get_content(ctx)
                relevance_score = self._calculate_relevance(content, query)
                ctx_copy = ctx.copy()
                ctx_copy['relevance_score'] = relevance_score
                scored_contexts.append(ctx_copy)
            
            # Sort by relevance
            scored_contexts.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            if not scored_contexts:
                break
            
            scores = [ctx.get('relevance_score', 0) for ctx in scored_contexts]
            min_score = min(scores)
            max_score = max(scores)
            avg_score = sum(scores) / len(scores)
            
            # Calculate adaptive threshold if enabled
            if self.enable_adaptive_threshold:
                active_threshold = self._calculate_adaptive_threshold(scores, self.rerank_threshold)
                stats['adaptive_threshold_used'] = active_threshold
                print(f"\n   🔄 Iteration {iteration}: {len(scored_contexts)} contexts, adaptive threshold: {active_threshold:.3f}")
            else:
                print(f"\n   🔄 Iteration {iteration}: {len(scored_contexts)} contexts, static threshold: {active_threshold:.3f}")
            
            print(f"   ├─ Score range: [{min_score:.3f}, {max_score:.3f}], avg: {avg_score:.3f}")
            
            # Check convergence
            if min_score >= active_threshold:
                print(f"   └─ ✓ Converged - all contexts above threshold")
                current_contexts = scored_contexts
                break
            
            # Filter contexts
            filtered_contexts = [
                ctx for ctx in scored_contexts 
                if ctx.get('relevance_score', 0) >= active_threshold
            ]
            
            removed = len(scored_contexts) - len(filtered_contexts)
            print(f"   ├─ Filtered: {removed} contexts below threshold")
            
            # Ensure minimum contexts
            if len(filtered_contexts) < 3 and len(scored_contexts) >= 3:
                print(f"   ├─ Keeping top 3 to maintain minimum context")
                current_contexts = scored_contexts[:3]
                break
            
            current_contexts = filtered_contexts
            
            if iteration == self.max_iterations:
                print(f"   └─ Max iterations reached")
                
        return current_contexts
    
    def _enforce_token_limit(
        self,
        contexts: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Enforce maximum token limit by truncating or removing contexts"""
        limited_contexts = []
        current_tokens = 0
        
        for ctx in contexts:
            content = self._get_content(ctx)
            ctx_tokens = self._estimate_tokens([ctx])
            
            if current_tokens + ctx_tokens <= self.max_context_tokens:
                limited_contexts.append(ctx)
                current_tokens += ctx_tokens
            else:
                # Try to fit a truncated version
                remaining_tokens = self.max_context_tokens - current_tokens
                if remaining_tokens > 100:  # Only worth it if we have reasonable space
                    truncated_content = self._truncate_to_tokens(content, remaining_tokens)
                    ctx_copy = ctx.copy()
                    ctx_copy['content'] = truncated_content
                    ctx_copy['truncated'] = True
                    limited_contexts.append(ctx_copy)
                break
                
        return limited_contexts
    
    # ==================== Helper Methods ====================
    
    def _get_content(self, ctx: Dict[str, Any]) -> str:
        """Extract content string from context dict"""
        if isinstance(ctx, str):
            return ctx
        return ctx.get('content', ctx.get('text', str(ctx)))
    
    def _estimate_tokens(self, contexts: List[Dict[str, Any]]) -> int:
        """Estimate token count (rough approximation: 1 token ≈ 4 chars)"""
        total_chars = sum(len(self._get_content(ctx)) for ctx in contexts)
        return total_chars // 4
    
    def _compute_simple_embedding(self, text: str) -> np.ndarray:
        """Compute a simple TF-based embedding (when proper embeddings unavailable)"""
        # Simple word frequency vector (first 100 most common words)
        words = re.findall(r'\w+', text.lower())
        word_freq = defaultdict(float)
        for word in words:
            word_freq[word] += 1.0
        
        # Normalize
        total = sum(word_freq.values())
        if total > 0:
            for word in word_freq:
                word_freq[word] /= total
        
        # Convert to fixed-size vector (100 dimensions)
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:100]
        vector = np.zeros(100)
        for i, (word, freq) in enumerate(top_words):
            vector[i] = freq
            
        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def _calculate_entropy(self, text: str) -> float:
        """
        Calculate information entropy of text
        Higher entropy = more information content
        """
        if not text:
            return 0.0
        
        # Character-level entropy
        char_freq = defaultdict(int)
        for char in text:
            char_freq[char] += 1
        
        total_chars = len(text)
        entropy = 0.0
        
        for count in char_freq.values():
            probability = count / total_chars
            if probability > 0:
                entropy -= probability * np.log2(probability)
        
        # Normalize to 0-1 range (max entropy for ASCII is ~6.6 bits)
        normalized_entropy = min(entropy / 6.6, 1.0)
        
        return normalized_entropy
    
    def _extract_relevant_with_context(self, content: str, query: str, context_window: int = 1) -> str:
        """
        Extract relevant sentences WITH surrounding context
        
        Strategy:
        1. Find query-relevant sentences
        2. Include N sentences before/after for context
        3. Preserve section headers
        4. Maintain semantic coherence
        """
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
        query_words = set(re.findall(r'\w+', query.lower()))
        
        if not sentences:
            return content
        
        # Score sentences
        scored_indices = []
        for i, sentence in enumerate(sentences):
            if len(sentence) < 10:
                continue
                
            sentence_words = set(re.findall(r'\w+', sentence.lower()))
            overlap = len(query_words & sentence_words)
            
            # Boost score for headers (short, capitalized)
            is_header = len(sentence.split()) <= 5 and sentence[0].isupper()
            score = overlap + (2 if is_header else 0)
            
            if score > 0:
                scored_indices.append((i, score))
        
        if not scored_indices:
            # Return first few sentences if no matches
            return '. '.join(sentences[:min(3, len(sentences))])
        
        # Get top relevant sentence indices
        scored_indices.sort(key=lambda x: x[1], reverse=True)
        relevant_indices = set([idx for idx, _ in scored_indices[:5]])
        
        # Expand to include context window
        expanded_indices = set()
        for idx in relevant_indices:
            start = max(0, idx - context_window)
            end = min(len(sentences), idx + context_window + 1)
            expanded_indices.update(range(start, end))
        
        # Sort and extract
        final_indices = sorted(expanded_indices)
        result_sentences = [sentences[i] for i in final_indices]
        
        return '. '.join(result_sentences)
    
    def _extract_relevant_sentences(self, content: str, query: str) -> str:
        """Extract sentences most relevant to the query (legacy method)"""
        # Use context-aware version with window=0 for backward compatibility
        return self._extract_relevant_with_context(content, query, context_window=0)
    
    def _clean_text(self, text: str) -> str:
        """Remove redundant whitespace and clean formatting"""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove multiple newlines
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()
    
    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score between content and query"""
        content_words = set(re.findall(r'\w+', content.lower()))
        query_words = set(re.findall(r'\w+', query.lower()))
        
        if not query_words or not content_words:
            return 0.0
        
        # Jaccard similarity
        intersection = len(content_words & query_words)
        union = len(content_words | query_words)
        
        if union == 0:
            return 0.0
            
        return intersection / union
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximately max_tokens"""
        max_chars = max_tokens * 4  # Rough approximation
        if len(text) <= max_chars:
            return text
        
        # Truncate at sentence boundary if possible
        truncated = text[:max_chars]
        last_period = truncated.rfind('.')
        
        if last_period > max_chars * 0.8:  # If we have a sentence break near the end
            return truncated[:last_period + 1]
        
        return truncated + "..."


class SummarizationOptimizer:
    """
    Advanced summarization for highly redundant contexts
    Uses extractive and abstractive techniques
    """
    
    def __init__(self, compression_ratio: float = 0.3):
        """
        Args:
            compression_ratio: Target ratio of summary length to original (0-1)
        """
        self.compression_ratio = compression_ratio
    
    def summarize_contexts(
        self,
        contexts: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        Create a consolidated summary of multiple contexts
        
        Returns:
            Single context dict with summarized content
        """
        if not contexts:
            return {}
        
        # Combine all content
        all_content = []
        for ctx in contexts:
            content = ctx.get('content', ctx.get('text', str(ctx)))
            all_content.append(content)
        
        combined_text = "\n\n".join(all_content)
        
        # Extract key sentences
        summary = self._extractive_summary(combined_text, query)
        
        return {
            'content': summary,
            'summarized': True,
            'original_count': len(contexts),
            'compression_ratio': len(summary) / max(len(combined_text), 1)
        }
    
    def _extractive_summary(self, text: str, query: str) -> str:
        """Extract most important sentences"""
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        if not sentences:
            return text
        
        # Score sentences
        query_words = set(re.findall(r'\w+', query.lower()))
        scored_sentences = []
        
        for sentence in sentences:
            sentence_words = set(re.findall(r'\w+', sentence.lower()))
            
            # Relevance to query
            query_overlap = len(query_words & sentence_words) / max(len(query_words), 1)
            
            # Position score (earlier sentences often more important)
            position_score = 1.0 / (sentences.index(sentence) + 1)
            
            # Length score (prefer medium-length sentences)
            length_score = min(len(sentence) / 100, 1.0)
            
            total_score = query_overlap * 0.6 + position_score * 0.2 + length_score * 0.2
            scored_sentences.append((sentence, total_score))
        
        # Sort by score
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Take top sentences up to compression ratio
        target_length = int(len(text) * self.compression_ratio)
        summary_sentences = []
        current_length = 0
        
        for sentence, score in scored_sentences:
            if current_length + len(sentence) <= target_length:
                summary_sentences.append(sentence)
                current_length += len(sentence)
            elif not summary_sentences:  # Ensure at least one sentence
                summary_sentences.append(sentence)
                break
        
        return '. '.join(summary_sentences) + '.'
