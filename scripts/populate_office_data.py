#!/usr/bin/env python3
"""
Populate database with office/workplace-related data
HR, managers, employees, team leads, organizational topics
"""
import os
import sys
import random
import hashlib
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Office Users
OFFICE_USERS = [
    "hr_manager",
    "tech_lead", 
    "project_manager",
    "department_head",
    "employee_001"
]

# Office Topics & Content
KNOWLEDGE_TOPICS = {
    "HR Policies": [
        "Employee onboarding process: Complete documentation, IT setup, security training, and team introductions within first week",
        "Annual leave policy: 20 days vacation, 10 sick days, 5 personal days. Request approval 2 weeks in advance",
        "Performance review framework: Quarterly check-ins, annual comprehensive reviews, 360-degree feedback system",
        "Remote work policy: Hybrid schedule allowed, minimum 2 office days per week, core hours 10 AM - 3 PM",
        "Employee benefits package: Health insurance, retirement 401k matching, gym membership, professional development budget",
        "Workplace harassment policy: Zero tolerance, confidential reporting channels, mandatory annual training",
        "Salary review process: Annual reviews in January, merit-based increases, market benchmarking quarterly",
        "Termination procedures: Two-week notice standard, exit interviews required, knowledge transfer protocol",
        "Employee wellness programs: Mental health support, fitness subsidies, flexible working hours",
        "Diversity and inclusion initiatives: Unconscious bias training, employee resource groups, inclusive hiring practices"
    ],
    "Management": [
        "Team leadership best practices: Regular 1-on-1s, transparent communication, clear goal setting, recognition programs",
        "Conflict resolution strategies: Active listening, mediation techniques, documentation, HR escalation when needed",
        "Project planning methodology: Agile framework, sprint planning, daily standups, retrospectives every 2 weeks",
        "Budget management: Quarterly reviews, expense tracking, vendor negotiations, ROI analysis for initiatives",
        "Stakeholder communication: Weekly status reports, monthly executive summaries, risk mitigation updates",
        "Team building activities: Quarterly offsites, monthly team lunches, recognition ceremonies, skill-sharing sessions",
        "Performance improvement plans: 30-60-90 day goals, weekly check-ins, documentation, support resources",
        "Cross-functional collaboration: Regular sync meetings, shared project tools, clear ownership matrices",
        "Change management process: Communication strategy, training programs, feedback loops, phased rollouts",
        "Resource allocation: Capacity planning, priority matrix, workload balancing, skill gap analysis"
    ],
    "Employee Development": [
        "Training programs: Technical skills workshops, leadership development, certification reimbursement up to $5000/year",
        "Career progression paths: Individual contributor vs management tracks, level expectations, promotion criteria",
        "Mentorship program: Quarterly mentor matching, structured meeting cadence, goal-setting framework",
        "Internal mobility: Job shadowing opportunities, lateral moves encouraged, 6-month role minimum before transfers",
        "Conference attendance: Annual budget $2000 per employee, knowledge sharing required post-attendance",
        "Learning management system: Online courses, lunch-and-learn series, expert speaker sessions monthly",
        "Skill assessment framework: Technical competency matrix, soft skills evaluation, gap identification",
        "Succession planning: High-potential identification, development plans, leadership pipeline programs",
        "Performance metrics: KPI tracking, OKR framework, quarterly goal reviews, peer feedback integration",
        "Professional certifications: Study leave provisions, exam fee reimbursement, bonus for completion"
    ],
    "Team Operations": [
        "Daily standup format: 15 minutes max, blockers first, round-robin updates, action items documented",
        "Sprint planning process: Story pointing, capacity calculation, dependency mapping, acceptance criteria definition",
        "Code review guidelines: Max 400 lines, 24-hour turnaround, constructive feedback, approval requirements",
        "Incident management protocol: Severity levels, escalation paths, postmortem requirements, on-call rotation",
        "Documentation standards: README templates, API documentation, architecture decision records, runbook creation",
        "Release management: Bi-weekly deployments, feature flags, rollback procedures, release notes required",
        "Tool stack: Jira for tracking, Slack for communication, GitHub for code, Confluence for documentation",
        "Meeting efficiency: Agenda required, time-boxed discussions, action items captured, optional attendance respected",
        "Knowledge sharing: Wiki maintenance, tech talks monthly, pair programming encouraged, demo days",
        "Quality assurance: Test coverage requirements, automated testing, UAT process, bug triage weekly"
    ],
    "Office Operations": [
        "Workspace allocation: Hot-desking system, desk booking app, quiet zones available, collaboration areas",
        "IT support process: Helpdesk ticketing, SLA 24-hour response, equipment refresh cycle every 3 years",
        "Security protocols: Badge access, VPN required for remote work, password policies, security training quarterly",
        "Facilities management: Building hours 7 AM - 7 PM, cleaning schedule, maintenance requests through portal",
        "Supply ordering: Quarterly bulk orders, individual requests via procurement system, approval for items over $100",
        "Visitor policy: Reception check-in required, badge issuance, host notification, NDA for sensitive areas",
        "Emergency procedures: Fire drills quarterly, first aid kits locations, emergency contacts posted",
        "Parking allocation: Permit system, EV charging stations, bike storage available, carpooling incentives",
        "Kitchen facilities: Shared refrigerators, dishwasher etiquette, coffee service, catering for meetings",
        "Event spaces: Conference room booking system, A/V equipment available, capacity limits posted"
    ]
}

CONVERSATION_TEMPLATES = {
    "hr_discussions": [
        ("HR Manager", "I need to schedule your annual performance review. How does next Thursday at 2 PM work?"),
        ("Employee", "That works for me. Should I prepare anything specific?"),
        ("HR Manager", "Yes, please complete your self-assessment form and bring examples of your key achievements this year."),
        ("Employee", "Got it. I'll have that ready. Can we also discuss the new benefits package?"),
        ("HR Manager", "Absolutely. I'll prepare the updated benefits information for our meeting."),
    ],
    "team_meetings": [
        ("Team Lead", "Good morning team. Let's start with sprint planning. What's our capacity this week?"),
        ("Developer", "I have 32 hours available. I'm taking Friday off for personal reasons."),
        ("Team Lead", "Thanks for the heads up. Let's make sure critical tasks are covered before end of day Thursday."),
        ("Developer", "I'll prioritize the authentication module and aim to complete it by Wednesday."),
        ("Team Lead", "Perfect. Let me know if you need any support or run into blockers."),
    ],
    "manager_1on1": [
        ("Manager", "How are you feeling about your current workload and projects?"),
        ("Employee", "Honestly, I'm feeling a bit overwhelmed with the database migration on top of my regular duties."),
        ("Manager", "I appreciate you being honest. Let's see if we can redistribute some tasks or extend the timeline."),
        ("Employee", "That would help. I also wanted to discuss opportunities for professional development."),
        ("Manager", "Great topic. What specific skills or certifications are you interested in pursuing?"),
    ],
    "project_updates": [
        ("Project Manager", "Can you provide a status update on the Q1 deliverables?"),
        ("Team Lead", "We're 75% complete. The API integration is done, working on UI components now."),
        ("Project Manager", "Any risks or blockers I should be aware of?"),
        ("Team Lead", "The third-party vendor is delayed by a week. We may need to adjust our go-live date."),
        ("Project Manager", "Let me escalate that with the vendor. I'll update stakeholders on the potential delay."),
    ],
    "hr_inquiries": [
        ("Employee", "I'd like to know more about the parental leave policy."),
        ("HR", "We offer 12 weeks paid parental leave for primary caregivers and 4 weeks for secondary caregivers."),
        ("Employee", "Does that apply to adoption as well?"),
        ("HR", "Yes, absolutely. The same policy applies to adoption and foster care situations."),
        ("Employee", "That's great to hear. What's the process for requesting this leave?"),
    ]
}

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
    """Clear all existing data from tables"""
    print("\n🗑️  Clearing existing data...")
    
    cur = conn.cursor()
    
    # Clear in correct order due to foreign key constraints
    tables = [
        'semantic_memory_index',
        'super_chat_messages',
        'deepdive_messages',
        'episodes',
        'instances',
        'super_chat',
        'deepdive_conversations',
        'knowledge_base'
    ]
    
    for table in tables:
        cur.execute(f"DELETE FROM {table}")
        deleted = cur.rowcount
        print(f"  ✓ Cleared {table}: {deleted} rows")
    
    conn.commit()
    cur.close()
    print("✓ All data cleared\n")

def populate_knowledge_base(conn, num_entries=50):
    """Populate knowledge base with office-related content"""
    print(f"📚 Populating knowledge base with {num_entries} office-related entries...")
    
    cur = conn.cursor()
    entries = []
    
    for category, topics in KNOWLEDGE_TOPICS.items():
        for topic in topics:
            user = random.choice(OFFICE_USERS)
            embedding = generate_embedding(topic)
            
            cur.execute("""
                INSERT INTO knowledge_base 
                (user_id, content, category, tags, embedding)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user,
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
            """, (user, kb_id))
    
    conn.commit()
    cur.close()
    
    print(f"✓ Added {len(entries)} knowledge base entries")
    return entries

def populate_conversations(conn, num_messages=200):
    """Populate super chat conversations"""
    print(f"💬 Creating office conversations with {num_messages} messages...")
    
    cur = conn.cursor()
    
    # Create super chat sessions
    chat_sessions = []
    for user in OFFICE_USERS:
        cur.execute("""
            INSERT INTO super_chat (user_id)
            VALUES (%s)
            RETURNING id
        """, (user,))
        
        chat_id = cur.fetchone()['id']
        chat_sessions.append((chat_id, user))
    
    # Add messages to conversations
    message_count = 0
    conversation_types = list(CONVERSATION_TEMPLATES.keys())
    
    while message_count < num_messages:
        chat_id, user = random.choice(chat_sessions)
        conv_type = random.choice(conversation_types)
        conversation = CONVERSATION_TEMPLATES[conv_type]
        
        # Add conversation thread
        timestamp = datetime.now() - timedelta(days=random.randint(1, 25), 
                                              hours=random.randint(0, 23))
        
        for role, content in conversation:
            if message_count >= num_messages:
                break
                
            cur.execute("""
                INSERT INTO super_chat_messages 
                (super_chat_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
            """, (chat_id, role, content, timestamp))
            
            message_count += 1
            timestamp += timedelta(minutes=random.randint(1, 15))
    
    conn.commit()
    cur.close()
    
    print(f"✓ Created {len(chat_sessions)} chat sessions with {message_count} messages")
    return message_count

def populate_deepdive_conversations(conn, num_conversations=20):
    """Populate deepdive conversations with detailed office discussions"""
    print(f"🔍 Creating {num_conversations} deepdive conversations...")
    
    cur = conn.cursor()
    
    deepdive_topics = [
        "Q1 Performance Review Discussion",
        "Career Development Planning",
        "Team Restructuring Proposal",
        "Budget Planning Session",
        "Conflict Resolution Meeting",
        "Onboarding Process Improvement",
        "Remote Work Policy Updates",
        "Employee Engagement Survey Results",
        "Succession Planning Strategy",
        "Compensation Review Meeting",
        "Training Program Development",
        "Cross-Department Collaboration",
        "Office Space Optimization",
        "Benefits Package Enhancement",
        "Leadership Development Program",
        "Diversity Initiative Planning",
        "Employee Retention Strategy",
        "Workflow Automation Discussion",
        "Team Building Event Planning",
        "Performance Metrics Review"
    ]
    
    total_messages = 0
    
    for i in range(num_conversations):
        user = random.choice(OFFICE_USERS)
        topic = deepdive_topics[i % len(deepdive_topics)]
        
        cur.execute("""
            INSERT INTO deepdive_conversations (user_id, title)
            VALUES (%s, %s)
            RETURNING id
        """, (user, topic))
        
        conv_id = cur.fetchone()['id']
        
        # Add 15-25 messages per conversation
        num_messages = random.randint(15, 25)
        timestamp = datetime.now() - timedelta(days=random.randint(1, 28))
        
        for j in range(num_messages):
            role = "user" if j % 3 == 0 else "assistant"
            
            if role == "user":
                content = f"Discussing {topic.lower()}: Point {j+1} regarding implementation and team impact."
            else:
                content = f"Analysis of {topic.lower()}: Recommendation {j+1} based on organizational best practices and data."
            
            cur.execute("""
                INSERT INTO deepdive_messages 
                (deepdive_conversation_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
            """, (conv_id, role, content, timestamp))
            
            total_messages += 1
            timestamp += timedelta(minutes=random.randint(2, 10))
    
    conn.commit()
    cur.close()
    
    print(f"✓ Created {num_conversations} deepdive conversations with {total_messages} messages")
    return total_messages

def main():
    """Main execution"""
    print("\n" + "="*70)
    print("  OFFICE DATA POPULATION - HR, Management, Employee Topics")
    print("="*70 + "\n")
    
    # Connect to database
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
        
        # Populate with office data
        kb_entries = populate_knowledge_base(conn, 50)
        messages = populate_conversations(conn, 200)
        deepdive_msgs = populate_deepdive_conversations(conn, 20)
        
        # Summary
        print("\n" + "="*70)
        print("  POPULATION COMPLETE")
        print("="*70)
        print(f"\n  Knowledge Base:       {len(kb_entries)} entries")
        print(f"  Chat Messages:        {messages} messages")
        print(f"  Deepdive Messages:    {deepdive_msgs} messages")
        print(f"  Total Records:        {len(kb_entries) + messages + deepdive_msgs}")
        print(f"\n  Users:                {', '.join(OFFICE_USERS)}")
        print("\n" + "="*70)
        print("\n✓ Run episodization job to create episodes:")
        print("  python3 scripts/episodization_job.py\n")
        
    except Exception as e:
        print(f"\n❌ Error during population: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
