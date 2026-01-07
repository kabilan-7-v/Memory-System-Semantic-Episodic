"""
Semantic Memory Service - High-level service for semantic memory operations
"""
from typing import List, Optional, Dict, Any
from src.models.semantic_memory import UserPersona, KnowledgeItem, SearchResult
from src.repositories.user_persona_repository import UserPersonaRepository
from src.repositories.knowledge_repository import KnowledgeRepository
from src.services.embedding_service import EmbeddingService
from src.config.database import db_config


class SemanticMemoryService:
 """Service for managing semantic memory operations"""
 
 def __init__(
 self,
 embedding_service: EmbeddingService = None,
 persona_repo: UserPersonaRepository = None,
 knowledge_repo: KnowledgeRepository = None
 ):
 self.embedding_service = embedding_service or EmbeddingService()
 self.persona_repo = persona_repo or UserPersonaRepository()
 self.knowledge_repo = knowledge_repo or KnowledgeRepository()
 
 # ========== User Persona Operations ==========
 
 def create_user_persona(
 self,
 user_id: str,
 name: Optional[str] = None,
 preferences: Dict[str, Any] = None,
 traits: Dict[str, Any] = None,
 communication_style: Optional[str] = None,
 interests: List[str] = None,
 expertise_areas: List[str] = None,
 metadata: Dict[str, Any] = None
 ) -> UserPersona:
 """Create or update a user persona with auto-generated embedding"""
 # Check if persona already exists
 existing = self.persona_repo.get_by_user_id(user_id)
 
 persona = UserPersona(
 user_id=user_id,
 name=name,
 preferences=preferences or {},
 traits=traits or {},
 communication_style=communication_style,
 interests=interests or [],
 expertise_areas=expertise_areas or [],
 metadata=metadata or {}
 )
 
 # Generate embedding
 persona.embedding = self.embedding_service.embed_user_persona(
 persona.to_dict()
 )
 
 if existing:
 persona.id = existing.id
 return self.persona_repo.update(persona)
 else:
 return self.persona_repo.create(persona)
 
 def get_user_persona(self, user_id: str) -> Optional[UserPersona]:
 """Get user persona by user_id"""
 return self.persona_repo.get_by_user_id(user_id)
 
 def update_user_persona(
 self,
 user_id: str,
 **updates
 ) -> Optional[UserPersona]:
 """Update specific fields of a user persona"""
 persona = self.persona_repo.get_by_user_id(user_id)
 if not persona:
 return None
 
 # Update fields
 for key, value in updates.items():
 if hasattr(persona, key):
 setattr(persona, key, value)
 
 # Regenerate embedding if content changed
 if any(k in updates for k in ['name', 'interests', 'expertise_areas', 'communication_style']):
 persona.embedding = self.embedding_service.embed_user_persona(
 persona.to_dict()
 )
 
 return self.persona_repo.update(persona)
 
 def delete_user_persona(self, user_id: str) -> bool:
 """Delete a user persona"""
 return self.persona_repo.delete(user_id)
 
 def find_similar_personas(
 self,
 query_text: str,
 limit: int = 5,
 min_similarity: float = 0.7
 ) -> List[SearchResult]:
 """Find similar user personas based on query text"""
 query_embedding = self.embedding_service.embed_text(query_text)
 return self.persona_repo.search_similar(
 embedding=query_embedding,
 limit=limit,
 min_similarity=min_similarity
 )
 
 # ========== Knowledge Base Operations ==========
 
 def add_knowledge(
 self,
 content: str,
 user_id: Optional[str] = None,
 title: Optional[str] = None,
 content_type: str = 'text',
 category: Optional[str] = None,
 tags: List[str] = None,
 source: Optional[str] = None,
 confidence_score: float = 1.0,
 importance_score: float = 0.5,
 metadata: Dict[str, Any] = None
 ) -> KnowledgeItem:
 """Add a new knowledge item with auto-generated embedding"""
 knowledge = KnowledgeItem(
 content=content,
 user_id=user_id,
 title=title,
 content_type=content_type,
 category=category,
 tags=tags or [],
 source=source,
 confidence_score=confidence_score,
 importance_score=importance_score,
 metadata=metadata or {}
 )
 
 # Generate embedding from content
 knowledge.embedding = self.embedding_service.embed_text(content)
 
 return self.knowledge_repo.create(knowledge)
 
 def get_knowledge(self, knowledge_id: str) -> Optional[KnowledgeItem]:
 """Get knowledge item by ID"""
 return self.knowledge_repo.get_by_id(knowledge_id)
 
 def update_knowledge(
 self,
 knowledge_id: str,
 **updates
 ) -> Optional[KnowledgeItem]:
 """Update specific fields of a knowledge item"""
 knowledge = self.knowledge_repo.get_by_id(knowledge_id)
 if not knowledge:
 return None
 
 # Update fields
 for key, value in updates.items():
 if hasattr(knowledge, key):
 setattr(knowledge, key, value)
 
 # Regenerate embedding if content changed
 if 'content' in updates:
 knowledge.embedding = self.embedding_service.embed_text(
 knowledge.content
 )
 
 return self.knowledge_repo.update(knowledge)
 
 def delete_knowledge(self, knowledge_id: str) -> bool:
 """Delete a knowledge item"""
 return self.knowledge_repo.delete(knowledge_id)
 
 # ========== Search Operations ==========
 
 def search_knowledge(
 self,
 query: str,
 user_id: Optional[str] = None,
 limit: int = 10,
 min_similarity: float = 0.7,
 category: Optional[str] = None,
 tags: Optional[List[str]] = None,
 search_type: str = 'semantic' # 'semantic' or 'text'
 ) -> List[SearchResult]:
 """
 Search knowledge base using semantic or text search
 
 Args:
 query: Search query text
 user_id: Optional user ID to filter results
 limit: Maximum number of results
 min_similarity: Minimum similarity threshold (for semantic search)
 category: Filter by category
 tags: Filter by tags
 search_type: 'semantic' for vector search or 'text' for keyword search
 """
 if search_type == 'semantic':
 query_embedding = self.embedding_service.embed_text(query)
 return self.knowledge_repo.search_by_vector(
 embedding=query_embedding,
 user_id=user_id,
 limit=limit,
 min_similarity=min_similarity,
 category=category,
 tags=tags
 )
 else:
 items = self.knowledge_repo.search_by_text(
 query=query,
 user_id=user_id,
 limit=limit
 )
 return [SearchResult(item=item, similarity_score=1.0) for item in items]
 
 def get_contextual_knowledge(
 self,
 user_id: str,
 query: str,
 limit: int = 5
 ) -> List[SearchResult]:
 """
 Get contextual knowledge for a user based on their persona and query
 Combines user persona understanding with knowledge search
 """
 # Get user persona
 persona = self.persona_repo.get_by_user_id(user_id)
 
 # Enhance query with user context if available
 enhanced_query = query
 if persona:
 context_parts = [query]
 if persona.interests:
 context_parts.append(f"User interests: {', '.join(persona.interests[:3])}")
 if persona.expertise_areas:
 context_parts.append(f"Expertise: {', '.join(persona.expertise_areas[:3])}")
 enhanced_query = " | ".join(context_parts)
 
 # Search with enhanced query
 return self.search_knowledge(
 query=enhanced_query,
 user_id=user_id,
 limit=limit,
 search_type='semantic'
 )
 
 def get_knowledge_by_category(
 self,
 category: str,
 user_id: Optional[str] = None,
 limit: int = 50
 ) -> List[KnowledgeItem]:
 """Get all knowledge items in a specific category"""
 return self.knowledge_repo.get_by_category(
 category=category,
 user_id=user_id,
 limit=limit
 )
 
 def get_knowledge_by_tags(
 self,
 tags: List[str],
 user_id: Optional[str] = None,
 limit: int = 50
 ) -> List[KnowledgeItem]:
 """Get all knowledge items matching specific tags"""
 return self.knowledge_repo.get_by_tags(
 tags=tags,
 user_id=user_id,
 limit=limit
 )
 
 # ========== Batch Operations ==========
 
 def add_knowledge_batch(
 self,
 knowledge_items: List[Dict[str, Any]]
 ) -> List[KnowledgeItem]:
 """Add multiple knowledge items in batch"""
 results = []
 for item_data in knowledge_items:
 knowledge = self.add_knowledge(**item_data)
 results.append(knowledge)
 return results
 
 def close(self):
 """Close database connections"""
 db_config.close_pool()
