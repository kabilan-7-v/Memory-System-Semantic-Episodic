"""
User Persona Repository - Database operations for user personas
"""
from typing import List, Optional, Dict, Any
import json
from src.config.database import db_config
from src.models.semantic_memory import UserPersona, SearchResult


class UserPersonaRepository:
 """Repository for user persona CRUD operations"""
 
 def create(self, persona: UserPersona) -> UserPersona:
 """Create a new user persona"""
 with db_config.get_cursor() as cursor:
 cursor.execute("""
 INSERT INTO user_personas (
 user_id, name, preferences, traits, communication_style,
 interests, expertise_areas, embedding, metadata
 )
 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
 RETURNING id, created_at, updated_at
 """, (
 persona.user_id,
 persona.name,
 json.dumps(persona.preferences),
 json.dumps(persona.traits),
 persona.communication_style,
 persona.interests,
 persona.expertise_areas,
 persona.embedding,
 json.dumps(persona.metadata)
 ))
 
 result = cursor.fetchone()
 persona.id = str(result['id'])
 persona.created_at = result['created_at']
 persona.updated_at = result['updated_at']
 
 return persona
 
 def get_by_user_id(self, user_id: str) -> Optional[UserPersona]:
 """Get user persona by user_id"""
 with db_config.get_cursor() as cursor:
 cursor.execute("""
 SELECT * FROM user_personas WHERE user_id = %s
 """, (user_id,))
 
 row = cursor.fetchone()
 if not row:
 return None
 
 return self._row_to_persona(row)
 
 def get_by_id(self, persona_id: str) -> Optional[UserPersona]:
 """Get user persona by ID"""
 with db_config.get_cursor() as cursor:
 cursor.execute("""
 SELECT * FROM user_personas WHERE id = %s
 """, (persona_id,))
 
 row = cursor.fetchone()
 if not row:
 return None
 
 return self._row_to_persona(row)
 
 def update(self, persona: UserPersona) -> UserPersona:
 """Update an existing user persona"""
 with db_config.get_cursor() as cursor:
 cursor.execute("""
 UPDATE user_personas
 SET name = %s, preferences = %s, traits = %s,
 communication_style = %s, interests = %s,
 expertise_areas = %s, embedding = %s, metadata = %s
 WHERE user_id = %s
 RETURNING updated_at
 """, (
 persona.name,
 json.dumps(persona.preferences),
 json.dumps(persona.traits),
 persona.communication_style,
 persona.interests,
 persona.expertise_areas,
 persona.embedding,
 json.dumps(persona.metadata),
 persona.user_id
 ))
 
 result = cursor.fetchone()
 if result:
 persona.updated_at = result['updated_at']
 
 return persona
 
 def delete(self, user_id: str) -> bool:
 """Delete a user persona"""
 with db_config.get_cursor() as cursor:
 cursor.execute("""
 DELETE FROM user_personas WHERE user_id = %s
 """, (user_id,))
 
 return cursor.rowcount > 0
 
 def search_similar(
 self,
 embedding: List[float],
 limit: int = 5,
 min_similarity: float = 0.7
 ) -> List[SearchResult]:
 """Search for similar user personas using vector similarity"""
 with db_config.get_cursor() as cursor:
 cursor.execute("""
 SELECT *,
 1 - (embedding <=> %s::vector) as similarity
 FROM user_personas
 WHERE 1 - (embedding <=> %s::vector) >= %s
 ORDER BY embedding <=> %s::vector
 LIMIT %s
 """, (
 embedding,
 embedding,
 min_similarity,
 embedding,
 limit
 ))
 
 results = []
 for row in cursor.fetchall():
 similarity = row.pop('similarity')
 persona = self._row_to_persona(row)
 results.append(SearchResult(
 item=persona,
 similarity_score=float(similarity)
 ))
 
 return results
 
 def list_all(self, limit: int = 100, offset: int = 0) -> List[UserPersona]:
 """List all user personas with pagination"""
 with db_config.get_cursor() as cursor:
 cursor.execute("""
 SELECT * FROM user_personas
 ORDER BY created_at DESC
 LIMIT %s OFFSET %s
 """, (limit, offset))
 
 return [self._row_to_persona(row) for row in cursor.fetchall()]
 
 def _row_to_persona(self, row: Dict[str, Any]) -> UserPersona:
 """Convert database row to UserPersona object"""
 return UserPersona(
 id=str(row['id']),
 user_id=row['user_id'],
 name=row['name'],
 preferences=row['preferences'] or {},
 traits=row['traits'] or {},
 communication_style=row['communication_style'],
 interests=row['interests'] or [],
 expertise_areas=row['expertise_areas'] or [],
 embedding=row['embedding'],
 metadata=row['metadata'] or {},
 created_at=row['created_at'],
 updated_at=row['updated_at']
 )
