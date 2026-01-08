#!/usr/bin/env python3
"""
Populate database with complete user profiles
Each user gets:
- User persona with name
- ~50 knowledge entries
- ~150 messages
- ~50 episodes (from messages)
Total: ~250 entries per user
"""
import os
import sys
import random
import hashlib
import json
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Office Users with Names
USERS = [
    {"user_id": "hr_manager_001", "name": "Sarah Mitchell", "role": "HR Manager", "expertise": ["recruitment", "employee_relations", "policy_development"]},
    {"user_id": "tech_lead_001", "name": "Michael Chen", "role": "Technical Lead", "expertise": ["system_architecture", "code_review", "team_mentoring"]},
    {"user_id": "project_manager_001", "name": "Emily Rodriguez", "role": "Project Manager", "expertise": ["agile_methodology", "stakeholder_management", "risk_mitigation"]},
    {"user_id": "department_head_001", "name": "James Williams", "role": "Department Head", "expertise": ["strategic_planning", "budget_management", "cross_functional_leadership"]},
    {"user_id": "team_lead_001", "name": "Priya Sharma", "role": "Team Lead", "expertise": ["sprint_planning", "performance_coaching", "workflow_optimization"]},
]

# Knowledge topics by category
KNOWLEDGE_TOPICS = {
    "HR Policies": [
        "Employee onboarding: Complete documentation within first week, including IT setup and security training",
        "Annual leave policy: 20 vacation days, 10 sick days, 5 personal days with 2-week advance notice",
        "Performance review framework: Quarterly check-ins with annual comprehensive 360-degree feedback",
        "Remote work policy: Hybrid schedule with minimum 2 office days, core hours 10 AM - 3 PM",
        "Benefits package: Health insurance, 401k matching up to 6%, gym membership, professional development",
        "Harassment policy: Zero tolerance with confidential reporting and mandatory annual training",
        "Salary review: Annual reviews in January with merit-based increases and market benchmarking",
        "Termination procedures: Two-week notice, exit interviews, and knowledge transfer protocols",
        "Wellness programs: Mental health support, fitness subsidies, flexible hours for work-life balance",
        "Diversity initiatives: Unconscious bias training, resource groups, inclusive hiring practices",
    ],
    "Management": [
        "Team leadership: Regular 1-on-1s, transparent communication, clear goals, and recognition programs",
        "Conflict resolution: Active listening, mediation techniques, documentation, and HR escalation paths",
        "Project planning: Agile framework with sprint planning, daily standups, and bi-weekly retrospectives",
        "Budget management: Quarterly reviews, expense tracking, vendor negotiations, and ROI analysis",
        "Stakeholder communication: Weekly status reports, monthly executive summaries, risk updates",
        "Team building: Quarterly offsites, monthly team lunches, recognition events, skill-sharing sessions",
        "Performance improvement: 30-60-90 day plans with weekly check-ins and support resources",
        "Cross-functional collaboration: Regular sync meetings, shared tools, clear ownership matrices",
        "Change management: Communication strategy, training programs, feedback loops, phased rollouts",
        "Resource allocation: Capacity planning, priority matrices, workload balancing, skill gap analysis",
    ],
    "Employee Development": [
        "Training programs: Technical workshops, leadership development, certification reimbursement up to $5K",
        "Career progression: IC vs management tracks with clear level expectations and promotion criteria",
        "Mentorship program: Quarterly matching, structured meetings, and goal-setting frameworks",
        "Internal mobility: Job shadowing, lateral moves encouraged, 6-month minimum before transfers",
        "Conference attendance: Annual budget of $2K per employee with post-conference knowledge sharing",
        "Learning management: Online courses, lunch-and-learns, monthly expert speaker sessions",
        "Skill assessment: Technical competency matrices, soft skills evaluation, gap identification",
        "Succession planning: High-potential identification, development plans, leadership pipeline",
        "Performance metrics: KPI tracking, OKR framework, quarterly reviews, peer feedback integration",
        "Professional certifications: Study leave, exam fee reimbursement, completion bonuses",
    ],
    "Team Operations": [
        "Daily standup: 15 minutes max, blockers first, round-robin updates, documented action items",
        "Sprint planning: Story pointing, capacity calculation, dependency mapping, acceptance criteria",
        "Code review: Max 400 lines, 24-hour turnaround, constructive feedback, approval requirements",
        "Incident management: Severity levels, escalation paths, postmortem requirements, on-call rotation",
        "Documentation standards: README templates, API docs, architecture decision records, runbooks",
        "Release management: Bi-weekly deployments, feature flags, rollback procedures, release notes",
        "Tool stack: Jira for tracking, Slack for communication, GitHub for code, Confluence for docs",
        "Meeting efficiency: Required agendas, time-boxed discussions, action items, optional attendance",
        "Knowledge sharing: Wiki maintenance, monthly tech talks, pair programming, demo days",
        "Quality assurance: Test coverage requirements, automated testing, UAT process, weekly bug triage",
    ],
    "Office Operations": [
        "Workspace: Hot-desking system, desk booking app, quiet zones, collaboration areas available",
        "IT support: Helpdesk ticketing system, 24-hour SLA, equipment refresh cycle every 3 years",
        "Security: Badge access, VPN for remote work, password policies, quarterly security training",
        "Facilities: Building hours 7 AM - 7 PM, cleaning schedules, maintenance requests via portal",
        "Supply ordering: Quarterly bulk orders, individual requests via procurement, $100 approval limit",
        "Visitor policy: Reception check-in, badge issuance, host notification, NDAs for sensitive areas",
        "Emergency procedures: Quarterly fire drills, first aid kit locations, posted emergency contacts",
        "Parking: Permit system, EV charging stations, bike storage, carpooling incentives available",
        "Kitchen facilities: Shared refrigerators, dishwasher etiquette, coffee service, meeting catering",
        "Event spaces: Conference room booking system, A/V equipment, capacity limits clearly posted",
    ]
}

CONVERSATION_TEMPLATES = [
    ("Manager", "Let's discuss your Q4 performance and goals for next quarter."),
    ("Employee", "I've completed the API integration project ahead of schedule."),
    ("Manager", "Great work! How did you manage the tight deadline?"),
    ("Employee", "I collaborated closely with the frontend team and prioritized core features."),
    ("HR", "Reminder: Performance reviews are due by end of month."),
    ("Team Lead", "Team standup at 10 AM. Please prepare your updates."),
    ("Employee", "I'm blocked on the database migration. Need senior dev support."),
    ("Tech Lead", "I'll pair with you this afternoon to resolve the migration issues."),
    ("Project Manager", "Budget review meeting scheduled for Thursday at 2 PM."),
    ("Department Head", "Excellent progress on the Q4 initiatives. Keep up the momentum."),
]

def generate_embedding(text: str, dimensions: int = 1536) -> list:
    """Generate deterministic embedding"""
    embedding = []
    for i in range(dimensions):
        seed = text.encode('utf-8') + i.to_bytes(4, 'big')
        hash_val = hashlib.sha256(seed).digest()
        value = int.from_bytes(hash_val[:4], 'big') / (2**32)
        value = (value * 2) - 1
        embedding.append(value)
    
    norm = np.linalg.norm(embedding)
    return [float(v / norm) for v in embedding]

def clear_existing_data(conn):
    """Clear all existing data"""
    print("\n🗑️  Clearing existing data...")
    cur = conn.cursor()
    
    tables = [
        'semantic_memory_index',
        'super_chat_messages',
        'deepdive_messages',
        'episodes',
        'instances',
        'super_chat',
        'deepdive_conversations',
        'knowledge_base',
        'user_persona'
    ]
    
    for table in tables:
        cur.execute(f"DELETE FROM {table}")
        print(f"  ✓ Cleared {table}")
    
    conn.commit()
    cur.close()
    print("✓ All data cleared\n")

def create_user_persona(conn, user_info):
    """Create user persona in BOTH persona and knowledge tables"""
    cur = conn.cursor()
    
    raw_content = f"{user_info['name']} is a {user_info['role']} with expertise in {', '.join(user_info['expertise'][:2])}"
    interests = [user_info['role'].lower(), "team_collaboration", "continuous_improvement"]
    
    embedding = generate_embedding(raw_content)
    
    # 1. Store in user_persona table
    cur.execute("""
        INSERT INTO user_persona 
        (user_id, name, raw_content, interests, expertise_areas, embedding)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        user_info['user_id'],
        user_info['name'],
        raw_content,
        interests,
        user_info['expertise'],
        embedding
    ))
    
    persona_id = cur.fetchone()['id']
    
    # 2. ALSO store persona info in knowledge_base for searchability
    cur.execute("""
        INSERT INTO knowledge_base 
        (user_id, content, category, tags, embedding)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        user_info['user_id'],
        f"Personal Info: {raw_content}. Role: {user_info['role']}. Expertise: {', '.join(user_info['expertise'])}",
        "User Persona",
        ["personal_info", "user_data", user_info['role'].lower().replace(' ', '_')],
        embedding
    ))
    
    kb_id = cur.fetchone()['id']
    
    # Create semantic memory index
    cur.execute("""
        INSERT INTO semantic_memory_index (user_id, knowledge_id)
        VALUES (%s, %s)
    """, (user_info['user_id'], kb_id))
    
    conn.commit()
    cur.close()
    
    return persona_id, kb_id

def populate_knowledge_for_user(conn, user_info, num_entries=50):
    """Populate knowledge base for a single user"""
    cur = conn.cursor()
    entries = []
    
    # Distribute entries across categories
    all_topics = []
    for category, topics in KNOWLEDGE_TOPICS.items():
        for topic in topics:
            all_topics.append((category, topic))
    
    # Sample topics
    selected_topics = random.sample(all_topics, min(num_entries, len(all_topics)))
    
    for category, topic in selected_topics:
        embedding = generate_embedding(topic)
        
        cur.execute("""
            INSERT INTO knowledge_base 
            (user_id, content, category, tags, embedding)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_info['user_id'],
            topic,
            category,
            [category.lower().replace(' ', '_')],
            embedding
        ))
        
        kb_id = cur.fetchone()['id']
        entries.append(kb_id)
        
        # Create semantic memory index
        cur.execute("""
            INSERT INTO semantic_memory_index (user_id, knowledge_id)
            VALUES (%s, %s)
        """, (user_info['user_id'], kb_id))
    
    conn.commit()
    cur.close()
    
    return entries

def populate_messages_for_user(conn, user_info, num_messages=150):
    """Populate messages for a single user"""
    cur = conn.cursor()
    
    # Create super chat session
    cur.execute("""
        INSERT INTO super_chat (user_id)
        VALUES (%s)
        RETURNING id
    """, (user_info['user_id'],))
    
    chat_id = cur.fetchone()['id']
    
    # Add messages
    message_count = 0
    base_time = datetime.now() - timedelta(days=25)  # Start 25 days ago
    
    while message_count < num_messages:
        for role, content in CONVERSATION_TEMPLATES:
            if message_count >= num_messages:
                break
            
            # Personalize content with user name
            personalized = f"{content} - {user_info['name']}"
            
            cur.execute("""
                INSERT INTO super_chat_messages 
                (super_chat_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
            """, (chat_id, role, personalized, base_time))
            
            message_count += 1
            base_time += timedelta(hours=random.randint(1, 6))
    
    conn.commit()
    cur.close()
    
    return message_count

def create_episodes_for_user(conn, user_info):
    """Create episodes from user's messages"""
    cur = conn.cursor()
    
    # Get all messages for user and chat id
    cur.execute("""
        SELECT sc.id as chat_id, scm.id, scm.content, scm.created_at
        FROM super_chat_messages scm
        JOIN super_chat sc ON scm.super_chat_id = sc.id
        WHERE sc.user_id = %s
        ORDER BY scm.created_at
    """, (user_info['user_id'],))
    
    messages = cur.fetchall()
    
    if not messages:
        return 0
    
    chat_id = messages[0]['chat_id']
    
    # Group into episodes (every 3-5 messages)
    episode_count = 0
    i = 0
    
    while i < len(messages):
        batch_size = random.randint(3, 5)
        batch = messages[i:i+batch_size]
        
        if not batch:
            break
        
        # Create episode with messages as JSONB
        messages_json = [{"role": "user", "content": msg['content']} for msg in batch]
        summary_text = f"Discussion about work topics - {user_info['role']} activities"
        embedding = generate_embedding(summary_text, dimensions=384)
        
        cur.execute("""
            INSERT INTO episodes 
            (user_id, source_type, source_id, messages, message_count, date_from, date_to, vector)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_info['user_id'],
            'super_chat',
            chat_id,
            json.dumps(messages_json),
            len(batch),
            batch[0]['created_at'],
            batch[-1]['created_at'],
            embedding
        ))
        
        episode_count += 1
        i += batch_size
    
    conn.commit()
    cur.close()
    
    return episode_count

def main():
    """Main execution"""
    print("\n" + "="*70)
    print("  COMPLETE USER DATA POPULATION")
    print("  Each user: persona + knowledge + messages + episodes = ~250 entries")
    print("="*70 + "\n")
    
    # Connect
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5435)),
            database=os.getenv('DB_NAME', 'semantic_memory'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '2191'),
            cursor_factory=RealDictCursor
        )
        print("✓ Connected to database\n")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    try:
        # Clear existing data
        clear_existing_data(conn)
        
        total_stats = {
            'personas': 0,
            'knowledge': 0,
            'messages': 0,
            'episodes': 0
        }
        
        # Process each user
        for user_info in USERS:
            print(f"\n{'='*70}")
            print(f"  Processing: {user_info['name']} ({user_info['user_id']})")
            print(f"  Role: {user_info['role']}")
            print(f"{'='*70}\n")
            
            # 1. Create persona
            persona_id, kb_persona_id = create_user_persona(conn, user_info)
            print(f"  ✓ Created persona (Persona ID: {persona_id}, Knowledge ID: {kb_persona_id})")
            total_stats['personas'] += 1
            total_stats['knowledge'] += 1  # Persona also stored in knowledge
            
            # 2. Add knowledge entries
            kb_entries = populate_knowledge_for_user(conn, user_info, 50)
            print(f"  ✓ Added {len(kb_entries)} knowledge entries")
            total_stats['knowledge'] += len(kb_entries)
            
            # 3. Add messages
            msg_count = populate_messages_for_user(conn, user_info, 150)
            print(f"  ✓ Created {msg_count} messages")
            total_stats['messages'] += msg_count
            
            # 4. Create episodes
            ep_count = create_episodes_for_user(conn, user_info)
            print(f"  ✓ Generated {ep_count} episodes")
            total_stats['episodes'] += ep_count
            
            total = 1 + len(kb_entries) + msg_count + ep_count
            print(f"\n  📊 Total for {user_info['name']}: {total} entries")
        
        # Final summary
        print("\n" + "="*70)
        print("  POPULATION COMPLETE")
        print("="*70)
        print(f"\n  Users Created:        {len(USERS)}")
        print(f"  Total Personas:       {total_stats['personas']}")
        print(f"  Total Knowledge:      {total_stats['knowledge']}")
        print(f"  Total Messages:       {total_stats['messages']}")
        print(f"  Total Episodes:       {total_stats['episodes']}")
        print(f"\n  Grand Total:          {sum(total_stats.values())}")
        print("\n" + "="*70)
        
        print("\n📋 Users with Names:")
        for user in USERS:
            print(f"  • {user['name']:20} → {user['user_id']}")
        
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during population: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
