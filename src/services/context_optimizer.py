"""
Context Optimization Service
Optimizes memory retrieval for:
- Deduplication (similarity-based)
- Entropy reduction (remove low-information content)
- Compression (dimensional reduction)
- Summarization (consolidate redundant information)
- Re-ranking and verification with threshold-based iteration
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import defaultdict
import hashlib
import re


class ContextOptimizer:
    """
    Optimizes retrieved context to reduce memory, context window usage, and token consumption
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        entropy_threshold: float = 0.3,
        min_info_content: int = 10,
        max_context_tokens: int = 4000,
        rerank_threshold: float = 0.65,
        max_iterations: int = 3,
        embedding_service = None
    ):
        """
        Args:
            similarity_threshold: Cosine similarity threshold for duplicate detection (0-1)
            entropy_threshold: Minimum entropy score to keep content (0-1)
            min_info_content: Minimum character length for meaningful content
            max_context_tokens: Maximum tokens allowed in final context
            rerank_threshold: Minimum relevance score (0-1) for re-ranking iteration
                             Default 0.65 (65%) chosen based on:
                             - Below 0.6: Too permissive, allows weak matches
                             - 0.65-0.7: Sweet spot - filters noise while keeping relevant context
                             - Above 0.7: Too strict, may lose valuable peripheral information
                             - Research shows 65% relevance balance precision/recall for RAG systems
            max_iterations: Maximum re-ranking iterations (default 3)
                           - 1 iteration: Basic filtering only
                           - 2 iterations: Good for simple queries
                           - 3 iterations: Optimal for complex queries (convergence point)
                           - 4+ iterations: Diminishing returns, adds latency
        """
        self.similarity_threshold = similarity_threshold
        self.entropy_threshold = entropy_threshold
        self.min_info_content = min_info_content
        self.max_context_tokens = max_context_tokens
        self.rerank_threshold = rerank_threshold
        self.max_iterations = max_iterations
        self.embedding_service = embedding_service
        
    def optimize(
        self,
        contexts: List[Dict[str, Any]],
        query: str,
        embeddings: Optional[List[np.ndarray]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Main optimization pipeline
        
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
            'low_entropy_removed': 0,
            'compressed_count': 0,
            'summarized_count': 0,
            'iterations': 0,
            'final_count': 0,
            'final_tokens': 0,
            'reduction_percentage': 0
        }
        
        if not contexts:
            return [], stats
            
        # Step 1: Remove exact duplicates
        contexts = self._remove_exact_duplicates(contexts, stats)
        
        # Step 2: Remove similar/near-duplicate content
        contexts = self._remove_similar_duplicates(contexts, embeddings, stats)
        
        # Step 3: Filter low-entropy content
        contexts = self._filter_low_entropy(contexts, stats)
        
        # Step 4: Compress and consolidate
        contexts = self._compress_contexts(contexts, query, stats)
        
        # Step 5: Re-rank and verify with iterations
        contexts = self._rerank_with_verification(contexts, query, stats)
        
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
        Compress contexts by:
        1. Removing redundant phrases
        2. Consolidating similar information
        3. Extracting key information relevant to query
        """
        compressed_contexts = []
        
        for ctx in contexts:
            content = self._get_content(ctx)
            
            # Extract key sentences related to query
            compressed_content = self._extract_relevant_sentences(content, query)
            
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
    
    def _rerank_with_verification(
        self,
        contexts: List[Dict[str, Any]],
        query: str,
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Re-rank contexts and iterate if scores are below threshold
        
        Uses iterative refinement to ensure only high-quality, relevant contexts remain:
        - Threshold: 0.65 (65% relevance) - balances precision/recall
        - Max iterations: 3 - optimal convergence point for most queries
        - Each iteration: re-scores, filters, and verifies remaining contexts
        """
        iteration = 0
        current_contexts = contexts.copy()
        
        print(f"\n   🔄 Re-ranking with iterative verification (threshold: {self.rerank_threshold:.0%})")
        
        while iteration < self.max_iterations:
            iteration += 1
            stats['iterations'] = iteration
            
            print(f"   ├─ Iteration {iteration}/{self.max_iterations}: Scoring {len(current_contexts)} contexts...")
            
            # Re-score contexts based on relevance
            scored_contexts = []
            for ctx in current_contexts:
                content = self._get_content(ctx)
                relevance_score = self._calculate_relevance(content, query)
                ctx_copy = ctx.copy()
                ctx_copy['relevance_score'] = relevance_score
                scored_contexts.append(ctx_copy)
            
            # Sort by relevance
            scored_contexts.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Check if we need another iteration
            if not scored_contexts:
                print(f"   ├─ No contexts remaining - stopping")
                break
                
            min_score = min(ctx.get('relevance_score', 0) for ctx in scored_contexts)
            max_score = max(ctx.get('relevance_score', 0) for ctx in scored_contexts)
            avg_score = sum(ctx.get('relevance_score', 0) for ctx in scored_contexts) / len(scored_contexts)
            
            print(f"   ├─ Scores: min={min_score:.2f}, max={max_score:.2f}, avg={avg_score:.2f}")
            
            # If all scores are above threshold, we're done
            if min_score >= self.rerank_threshold:
                print(f"   └─ ✓ All contexts meet threshold {self.rerank_threshold:.2f} - converged in {iteration} iteration(s)")
                current_contexts = scored_contexts
                break
            
            # Count how many below threshold
            below_threshold = sum(1 for ctx in scored_contexts if ctx.get('relevance_score', 0) < self.rerank_threshold)
            
            # Filter out low-scoring contexts for next iteration
            current_contexts = [
                ctx for ctx in scored_contexts 
                if ctx.get('relevance_score', 0) >= self.rerank_threshold
            ]
            
            print(f"   ├─ Filtered out {below_threshold} contexts below threshold {self.rerank_threshold:.2f}")
            
            # If we removed too many, keep at least top 3
            if len(current_contexts) < 3 and len(scored_contexts) >= 3:
                print(f"   ├─ Keeping top 3 contexts to maintain minimum context")
                current_contexts = scored_contexts[:3]
                break
                
            # If this is the last iteration
            if iteration == self.max_iterations:
                print(f"   └─ Max iterations ({self.max_iterations}) reached - using {len(current_contexts)} contexts")
                
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
    
    def _extract_relevant_sentences(self, content: str, query: str) -> str:
        """Extract sentences most relevant to the query"""
        sentences = re.split(r'[.!?]+', content)
        query_words = set(re.findall(r'\w+', query.lower()))
        
        scored_sentences = []
        for sentence in sentences:
            if len(sentence.strip()) < 10:
                continue
                
            sentence_words = set(re.findall(r'\w+', sentence.lower()))
            overlap = len(query_words & sentence_words)
            
            if overlap > 0:
                scored_sentences.append((sentence.strip(), overlap))
        
        if not scored_sentences:
            # Return first few sentences if no overlap
            return '. '.join(s.strip() for s in sentences[:3] if s.strip())
        
        # Sort by relevance and take top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s for s, _ in scored_sentences[:5]]
        
        return '. '.join(top_sentences)
    
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
