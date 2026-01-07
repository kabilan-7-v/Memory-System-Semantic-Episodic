"""
Semantic Memory Models and Data Classes
Based on BAP Memory System Schema - Semantic Memory Layer
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid


@dataclass
class UserPersona:
    """
    User persona data model
    Stores user preferences, communication style, and behavioral patterns
    """
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    communication_style: Dict[str, Any] = field(default_factory=dict)
    behavior_patterns: Dict[str, Any] = field(default_factory=dict)
    # Legacy fields for backward compatibility
    name: Optional[str] = None
    traits: Dict[str, Any] = field(default_factory=dict)
    interests: List[str] = field(default_factory=list)
    expertise_areas: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        if self.id is None:
            data.pop('id', None)
        if self.created_at is None:
            data.pop('created_at', None)
        if self.updated_at is None:
            data.pop('updated_at', None)
        return data


@dataclass
class SemanticKnowledge:
    """
    Semantic knowledge data model
    Supports: knowledge, entities, processes, and skills
    """
    user_id: str
    type: str  # 'knowledge', 'entity', 'process', 'skill'
    subject: str
    content: Dict[str, Any]
    content_embedding: Optional[List[float]] = None
    confidence_score: Optional[float] = None
    source_type: Optional[str] = None  # 'user_stated', 'inferred', 'asset_derived'
    source_refs: Optional[Dict[str, Any]] = None
    verified: bool = False
    tenant_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        if self.id is None:
            data.pop('id', None)
        if self.created_at is None:
            data.pop('created_at', None)
        if self.updated_at is None:
            data.pop('updated_at', None)
        return data


@dataclass
class Entity(SemanticKnowledge):
    """
    Entity data model (specialized semantic knowledge)
    Represents people, organizations, locations, etc.
    """
    def __init__(self, user_id: str, subject: str, content: Dict[str, Any], **kwargs):
        super().__init__(user_id=user_id, type='entity', subject=subject, content=content, **kwargs)


@dataclass
class Process(SemanticKnowledge):
    """
    Process data model (specialized semantic knowledge)
    Represents workflows, procedures, methodologies
    """
    def __init__(self, user_id: str, subject: str, content: Dict[str, Any], **kwargs):
        super().__init__(user_id=user_id, type='process', subject=subject, content=content, **kwargs)


@dataclass
class Skill(SemanticKnowledge):
    """
    Skill data model (specialized semantic knowledge)
    Represents user skills, capabilities, expertise
    """
    def __init__(self, user_id: str, subject: str, content: Dict[str, Any], **kwargs):
        super().__init__(user_id=user_id, type='skill', subject=subject, content=content, **kwargs)


@dataclass
class KnowledgeItem:
    """
    Knowledge base item data model (legacy/general purpose)
    For backward compatibility with existing system
    """
    content: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    content_type: str = 'text'
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    source: Optional[str] = None
    confidence_score: float = 1.0
    importance_score: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        if self.id is None:
            data.pop('id', None)
        if self.created_at is None:
            data.pop('created_at', None)
        if self.updated_at is None:
            data.pop('updated_at', None)
        if self.last_accessed_at is None:
            data.pop('last_accessed_at', None)
        return data


@dataclass
class Concept:
    """Concept data model for knowledge graph"""
    concept_name: str
    user_id: Optional[str] = None
    description: Optional[str] = None
    concept_type: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        if self.id is None:
            data.pop('id', None)
        if self.created_at is None:
            data.pop('created_at', None)
        if self.updated_at is None:
            data.pop('updated_at', None)
        return data


@dataclass
class ConceptRelationship:
    """Concept relationship data model"""
    source_concept_id: str
    target_concept_id: str
    relationship_type: str
    strength: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        if self.id is None:
            data.pop('id', None)
        if self.created_at is None:
            data.pop('created_at', None)
        return data


@dataclass
class SearchResult:
    """Search result with similarity score"""
    item: Any
    similarity_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
