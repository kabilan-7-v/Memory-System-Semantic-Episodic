#!/usr/bin/env python3
"""
Data Population Script
Generates ~250 sample entries across all memory tables with realistic data.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# Sample data templates
USERS = ['user_001', 'user_002', 'user_003', 'user_004', 'user_005']

TOPICS = [
    'machine learning', 'web development', 'cloud architecture', 'data science',
    'project management', 'API design', 'database optimization', 'security',
    'DevOps', 'mobile development', 'AI ethics', 'system design'
]

CONVERSATION_TEMPLATES = [
    "I've been working on {topic} and need help with {detail}.",
    "Can you explain how {topic} works in the context of {detail}?",
    "What are the best practices for {topic} when dealing with {detail}?",
    "I'm having trouble understanding {topic}, specifically around {detail}.",
    "Let's discuss {topic} and how it relates to {detail}.",
]

RESPONSE_TEMPLATES = [
    "Great question about {topic}! Here's what you need to know about {detail}...",
    "Let me break down {topic} for you. When it comes to {detail}, the key is...",
    "I'd be happy to help with {topic}. Regarding {detail}, consider this approach...",
    "For {topic}, especially with {detail}, I recommend the following strategy...",
    "{topic} is fascinating! Here's how {detail} fits into the bigger picture...",
]

KNOWLEDGE_ITEMS = [
    "Understanding REST API design principles and best practices",
    "PostgreSQL query optimization techniques for large datasets",
    "Implementing JWT authentication in modern web applications",
    "Docker containerization strategies for microservices",
    "React hooks patterns and performance optimization",
    "Python asyncio for concurrent programming",
    "Kubernetes deployment and scaling strategies",
    "GraphQL vs REST API architecture decisions",
    "Redis caching strategies for high-traffic applications",
    "CI/CD pipeline setup with GitHub Actions",
    "TypeScript advanced type system features",
    "NoSQL database selection criteria",
    "OAuth 2.0 implementation patterns",
    "Serverless architecture on AWS Lambda",
    "WebSocket real-time communication patterns",
]

def get_conn():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5435'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres'),
        database=os.getenv('DB_NAME', 'bap_memory')
    )

def generate_embedding(dim=1536):
    """Generate a random embedding vector (normalized)."""
    vec = np.random.randn(dim)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()

def populate_user_personas(cur, conn):
    """Create user persona entries."""
    print("Creating user personas...")
    
    personas = [
        {
            'user_id': 'user_001',
            'name': 'Alice Chen',
            'bio': 'Senior Full-Stack Developer with 8 years of experience',
            'interests': ['web development', 'cloud architecture', 'AI'],
            'expertise': ['React', 'Node.js', 'AWS', 'PostgreSQL'],
            'preferences': json.dumps({
                'communication_style': 'concise',
                'code_style': 'functional',
                'preferred_languages': ['TypeScript', 'Python']
            })
        },
        {
            'user_id': 'user_002',
            'name': 'Bob Martinez',
            'bio': 'Data Scientist specializing in ML and analytics',
            'interests': ['machine learning', 'data science', 'statistics'],
            'expertise': ['Python', 'TensorFlow', 'Pandas', 'SQL'],
            'preferences': json.dumps({
                'communication_style': 'detailed',
                'code_style': 'object-oriented',
                'preferred_languages': ['Python', 'R']
            })
        },
        {
            'user_id': 'user_003',
            'name': 'Carol Thompson',
            'bio': 'DevOps Engineer focused on automation and scalability',
            'interests': ['DevOps', 'cloud infrastructure', 'security'],
            'expertise': ['Kubernetes', 'Docker', 'Terraform', 'AWS'],
            'preferences': json.dumps({
                'communication_style': 'technical',
                'code_style': 'declarative',
                'preferred_languages': ['Go', 'Python', 'Bash']
            })
        },
        {
            'user_id': 'user_004',
            'name': 'David Kim',
            'bio': 'Mobile Developer with expertise in cross-platform apps',
            'interests': ['mobile development', 'UI/UX', 'performance'],
            'expertise': ['React Native', 'Swift', 'Kotlin', 'Firebase'],
            'preferences': json.dumps({
                'communication_style': 'visual',
                'code_style': 'modular',
                'preferred_languages': ['JavaScript', 'Swift']
            })
        },
        {
            'user_id': 'user_005',
            'name': 'Emma Wilson',
            'bio': 'Tech Lead and Software Architect',
            'interests': ['system design', 'architecture', 'team leadership'],
            'expertise': ['microservices', 'API design', 'PostgreSQL', 'Redis'],
            'preferences': json.dumps({
                'communication_style': 'strategic',
                'code_style': 'clean-architecture',
                'preferred_languages': ['Java', 'Python', 'Go']
            })
        }
    ]
    
    for persona in personas:
        embedding = generate_embedding()
        cur.execute("""
            INSERT INTO user_persona 
            (user_id, name, bio, interests, expertise, preferences, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        """, (
            persona['user_id'],
            persona['name'],
            persona['bio'],
            persona['interests'],
            persona['expertise'],
            persona['preferences'],
            embedding
        ))
    
    conn.commit()
    print(f"✓ Created {len(personas)} user personas")

def populate_knowledge_base(cur, conn, count=50):
    """Create knowledge base entries."""
    print(f"Creating {count} knowledge base entries...")
    
    categories = ['knowledge', 'skill', 'process']
    
    for i in range(count):
        user_id = random.choice(USERS)
        topic = random.choice(TOPICS)
        knowledge_item = random.choice(KNOWLEDGE_ITEMS)
        
        content = f"{knowledge_item} - {topic}"
        category = random.choice(categories)
        tags = random.sample(TOPICS, k=random.randint(2, 4))
        importance = round(random.uniform(0.3, 1.0), 2)
        embedding = generate_embedding()
        
        metadata = json.dumps({
            'source': 'user_interaction',
            'verified': random.choice([True, False]),
            'confidence': round(random.uniform(0.7, 1.0), 2)
        })
        
        cur.execute("""
            INSERT INTO knowledge_base 
            (user_id, content, category, tags, importance_score, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, content, category, tags, importance, embedding, metadata))
    
    conn.commit()
    print(f"✓ Created {count} knowledge base entries")

def populate_conversations(cur, conn, count=150):
    """Create super chat conversations and messages."""
    print(f"Creating conversations with ~{count} messages...")
    
    # Create super chats for each user
    super_chat_ids = {}
    for user_id in USERS:
        cur.execute("""
            INSERT INTO super_chat (user_id)
            VALUES (%s)
            RETURNING id
        """, (user_id,))
        super_chat_ids[user_id] = cur.fetchone()[0]
    
    conn.commit()
    print(f"✓ Created {len(USERS)} super chats")
    
    # Create messages distributed over time
    base_date = datetime.now() - timedelta(days=45)  # Start 45 days ago
    messages_created = 0
    
    for i in range(count):
        user_id = random.choice(USERS)
        super_chat_id = super_chat_ids[user_id]
        
        # Randomly distribute messages over 45 days
        days_offset = random.uniform(0, 45)
        hours_offset = random.uniform(0, 24)
        created_at = base_date + timedelta(days=days_offset, hours=hours_offset)
        
        # Create user message
        topic = random.choice(TOPICS)
        detail = random.choice(TOPICS)
        user_content = random.choice(CONVERSATION_TEMPLATES).format(topic=topic, detail=detail)
        
        cur.execute("""
            INSERT INTO super_chat_messages 
            (super_chat_id, role, content, created_at, episodized)
            VALUES (%s, %s, %s, %s, %s)
        """, (super_chat_id, 'user', user_content, created_at, False))
        
        messages_created += 1
        
        # Create assistant response
        response_content = random.choice(RESPONSE_TEMPLATES).format(topic=topic, detail=detail)
        response_time = created_at + timedelta(seconds=random.randint(2, 30))
        
        cur.execute("""
            INSERT INTO super_chat_messages 
            (super_chat_id, role, content, created_at, episodized)
            VALUES (%s, %s, %s, %s, %s)
        """, (super_chat_id, 'assistant', response_content, response_time, False))
        
        messages_created += 1
    
    conn.commit()
    print(f"✓ Created {messages_created} messages")

def populate_deepdive_conversations(cur, conn, count=20):
    """Create deep dive conversations with messages."""
    print(f"Creating {count} deep dive conversations...")
    
    deepdive_titles = [
        "Project Alpha Architecture Review",
        "Database Migration Strategy",
        "API Security Implementation",
        "Performance Optimization Sprint",
        "New Feature Design Discussion",
        "Code Review Best Practices",
        "Testing Strategy for Microservices",
        "CI/CD Pipeline Enhancement",
        "Monitoring and Alerting Setup",
        "Tech Stack Evaluation"
    ]
    
    messages_created = 0
    base_date = datetime.now() - timedelta(days=60)
    
    for i in range(count):
        user_id = random.choice(USERS)
        tenant_id = f"tenant_{random.randint(1, 3)}"
        title = random.choice(deepdive_titles) + f" #{i+1}"
        
        conv_date = base_date + timedelta(days=random.uniform(0, 60))
        
        cur.execute("""
            INSERT INTO deepdive_conversations 
            (user_id, tenant_id, title, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_id, tenant_id, title, conv_date))
        
        deepdive_id = cur.fetchone()[0]
        
        # Create 5-15 messages per conversation
        num_messages = random.randint(5, 15)
        for j in range(num_messages):
            topic = random.choice(TOPICS)
            detail = random.choice(TOPICS)
            
            # User message
            user_content = random.choice(CONVERSATION_TEMPLATES).format(topic=topic, detail=detail)
            msg_time = conv_date + timedelta(minutes=j*10)
            
            cur.execute("""
                INSERT INTO deepdive_messages 
                (deepdive_conversation_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
            """, (deepdive_id, 'user', user_content, msg_time))
            
            messages_created += 1
            
            # Assistant response
            response_content = random.choice(RESPONSE_TEMPLATES).format(topic=topic, detail=detail)
            response_time = msg_time + timedelta(seconds=random.randint(2, 20))
            
            cur.execute("""
                INSERT INTO deepdive_messages 
                (deepdive_conversation_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
            """, (deepdive_id, 'assistant', response_content, response_time))
            
            messages_created += 1
    
    conn.commit()
    print(f"✓ Created {count} deep dive conversations with {messages_created} messages")

def main():
    """Main data population function."""
    print("=" * 60)
    print("BAP Memory System - Data Population")
    print("=" * 60)
    print()
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Populate all tables
        populate_user_personas(cur, conn)
        populate_knowledge_base(cur, conn, count=50)
        populate_conversations(cur, conn, count=150)
        populate_deepdive_conversations(cur, conn, count=20)
        
        # Get total counts
        cur.execute("SELECT COUNT(*) FROM user_persona")
        persona_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM knowledge_base")
        knowledge_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM super_chat_messages")
        sc_msg_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM deepdive_messages")
        dd_msg_count = cur.fetchone()[0]
        
        total = persona_count + knowledge_count + sc_msg_count + dd_msg_count
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Data population completed successfully!")
        print("=" * 60)
        print(f"\nTotal records created: {total}")
        print(f"  - User Personas: {persona_count}")
        print(f"  - Knowledge Base: {knowledge_count}")
        print(f"  - Super Chat Messages: {sc_msg_count}")
        print(f"  - Deep Dive Messages: {dd_msg_count}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during data population: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
