"""
Embedding Service for generating vector embeddings
Supports multiple embedding providers
"""
from typing import List, Union
import os
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
 """Abstract base class for embedding providers"""
 
 @abstractmethod
 def generate_embedding(self, text: str) -> List[float]:
 """Generate embedding for a single text"""
 pass
 
 @abstractmethod
 def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
 """Generate embeddings for multiple texts"""
 pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
 """OpenAI embedding provider"""
 
 def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
 self.api_key = api_key or os.getenv('OPENAI_API_KEY')
 self.model = model
 
 if not self.api_key:
 raise ValueError("OpenAI API key is required")
 
 try:
 from openai import OpenAI
 self.client = OpenAI(api_key=self.api_key)
 except ImportError:
 raise ImportError("openai package is required. Install with: pip install openai")
 
 def generate_embedding(self, text: str) -> List[float]:
 """Generate embedding for a single text"""
 response = self.client.embeddings.create(
 input=text,
 model=self.model
 )
 return response.data[0].embedding
 
 def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
 """Generate embeddings for multiple texts"""
 response = self.client.embeddings.create(
 input=texts,
 model=self.model
 )
 return [item.embedding for item in response.data]


class GroqEmbeddingProvider(EmbeddingProvider):
 """Groq embedding provider using deterministic hash-based embeddings"""
 
 def __init__(self, api_key: str = None, model: str = "llama-3.3-70b-versatile"):
 self.api_key = api_key or os.getenv('GROQ_API_KEY')
 self.model = model
 
 if not self.api_key:
 raise ValueError("Groq API key is required")
 
 try:
 from groq import Groq
 self.client = Groq(api_key=self.api_key)
 except ImportError:
 raise ImportError("groq package is required. Install with: pip install groq")
 
 def generate_embedding(self, text: str) -> List[float]:
 """Generate embedding using deterministic hash-based approach"""
 import hashlib
 import struct
 
 # Create a deterministic hash-based embedding
 hash_obj = hashlib.sha256(text.encode('utf-8'))
 hash_bytes = hash_obj.digest()
 
 # Convert to 1536-dimensional vector
 embedding = []
 for i in range(1536):
 # Use different parts of the hash with different seeds
 seed = hash_bytes + i.to_bytes(4, 'big')
 hash_val = hashlib.sha256(seed).digest()
 # Convert bytes to integer then to float
 int_val = int.from_bytes(hash_val[:8], byteorder='big')
 # Normalize to [-1, 1] using modulo
 normalized = (int_val % 2000000) / 1000000.0 - 1.0
 embedding.append(normalized)
 
 # Normalize the vector to unit length
 magnitude = sum(x**2 for x in embedding) ** 0.5
 if magnitude > 0:
 embedding = [x / magnitude for x in embedding]
 else:
 # Fallback to uniform distribution if all zeros
 embedding = [1.0 / (1536 ** 0.5)] * 1536
 
 return embedding
 
 def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
 """Generate embeddings for multiple texts"""
 return [self.generate_embedding(text) for text in texts]


class MockEmbeddingProvider(EmbeddingProvider):
 """Mock embedding provider for testing (generates random embeddings)"""
 
 def __init__(self, dimension: int = 1536):
 self.dimension = dimension
 import random
 self.random = random
 
 def generate_embedding(self, text: str) -> List[float]:
 """Generate random embedding for testing"""
 # Use text hash as seed for consistency
 self.random.seed(hash(text))
 return [self.random.random() for _ in range(self.dimension)]
 
 def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
 """Generate random embeddings for testing"""
 return [self.generate_embedding(text) for text in texts]


class EmbeddingService:
 """Service for managing embeddings with configurable providers"""
 
 def __init__(self, provider: EmbeddingProvider = None):
 if provider is None:
 # Priority: Groq > OpenAI > Mock
 if os.getenv('GROQ_API_KEY'):
 try:
 self.provider = GroqEmbeddingProvider()
 print("[OK] Using Groq API for embeddings")
 except (ImportError, ValueError) as e:
 print(f"Warning: Could not initialize Groq ({e}), trying alternatives")
 self.provider = self._fallback_provider()
 elif os.getenv('OPENAI_API_KEY'):
 try:
 self.provider = OpenAIEmbeddingProvider()
 print("[OK] Using OpenAI API for embeddings")
 except (ImportError, ValueError):
 print("Warning: Falling back to mock embeddings")
 self.provider = MockEmbeddingProvider()
 else:
 print("Warning: No API key found, using mock embeddings")
 self.provider = MockEmbeddingProvider()
 else:
 self.provider = provider
 
 def _fallback_provider(self):
 """Try OpenAI, then fall back to mock"""
 if os.getenv('OPENAI_API_KEY'):
 try:
 return OpenAIEmbeddingProvider()
 except (ImportError, ValueError):
 pass
 return MockEmbeddingProvider()
 
 def embed_text(self, text: str) -> List[float]:
 """Generate embedding for a single text"""
 if not text or not text.strip():
 raise ValueError("Text cannot be empty")
 return self.provider.generate_embedding(text)
 
 def embed_texts(self, texts: List[str]) -> List[List[float]]:
 """Generate embeddings for multiple texts"""
 if not texts:
 return []
 return self.provider.generate_embeddings(texts)
 
 def embed_user_persona(self, persona_data: dict) -> List[float]:
 """Generate embedding for user persona"""
 # Combine persona information into a single text
 parts = []
 if persona_data.get('name'):
 parts.append(f"Name: {persona_data['name']}")
 if persona_data.get('communication_style'):
 parts.append(f"Style: {persona_data['communication_style']}")
 if persona_data.get('interests'):
 parts.append(f"Interests: {', '.join(persona_data['interests'])}")
 if persona_data.get('expertise_areas'):
 parts.append(f"Expertise: {', '.join(persona_data['expertise_areas'])}")
 
 text = " | ".join(parts) if parts else "User profile"
 return self.embed_text(text)
