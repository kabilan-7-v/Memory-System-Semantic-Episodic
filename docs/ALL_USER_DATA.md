# 📊 ALL USER DATA IN DATABASE

## 🎯 Quick Access

### In the App:
1. **View all users:** App shows this on startup
2. **Switch user:** `user tech_lead_001`
3. **View details:** `status` command
4. **Search:** `search <keyword>`

### In PostgreSQL:
```bash
# Connect to database
PGPASSWORD=2191 psql -h localhost -p 5435 -U postgres -d semantic_memory

# Then run queries from this file
```

---

## 👥 ALL USERS & THEIR DATA

### 1. **Sarah Mitchell** (hr_manager_001)
- **Role:** HR Manager
- **Expertise:** recruitment, employee_relations, policy_development
- **Total Entries:** 239
  - Knowledge: 51
  - Messages: 150
  - Episodes: 38

**Sample Knowledge:**
- HR policies (harassment, leave, benefits)
- Employee development programs
- Recruitment processes
- Team operations
- Office management

**Questions to Ask:**
- "What is the harassment policy?"
- "How many vacation days do I get?"
- "What are my recruitment responsibilities?"
- "What employee development programs do we have?"

---

### 2. **Michael Chen** (tech_lead_001)
- **Role:** Technical Lead
- **Expertise:** system_architecture, code_review, team_mentoring
- **Total Entries:** 243
  - Knowledge: 52
  - Messages: 152
  - Episodes: 38

**Sample Knowledge:**
- System architecture
- Code review processes
- Sprint planning
- Quality assurance
- Incident management
- Technical documentation

**Questions to Ask:**
- "What are my technical skills?"
- "What is my expertise?"
- "What is the sprint planning process?"
- "What are the code review guidelines?"
- "What is my role?"

---

### 3. **Emily Rodriguez** (project_manager_001)
- **Role:** Project Manager
- **Expertise:** agile_methodology, stakeholder_management, risk_mitigation
- **Total Entries:** 240
  - Knowledge: 51
  - Messages: 150
  - Episodes: 38

**Sample Knowledge:**
- Agile methodology
- Stakeholder management
- Project planning
- Risk mitigation
- Team collaboration
- Delivery processes

**Questions to Ask:**
- "What is my project management approach?"
- "How do I handle stakeholders?"
- "What agile practices do I follow?"
- "What are my responsibilities?"

---

### 4. **James Williams** (department_head_001)
- **Role:** Department Head
- **Expertise:** strategic_planning, budget_management, cross_functional_leadership
- **Total Entries:** 240
  - Knowledge: 51
  - Messages: 150
  - Episodes: 38

**Sample Knowledge:**
- Strategic planning
- Budget management
- Cross-functional leadership
- Department policies
- Team operations
- Executive decisions

**Questions to Ask:**
- "What is my strategic vision?"
- "How do I manage budgets?"
- "What are my leadership responsibilities?"
- "What departments do I oversee?"

---

### 5. **Priya Sharma** (team_lead_001)
- **Role:** Team Lead
- **Expertise:** sprint_planning, performance_coaching, workflow_optimization
- **Total Entries:** 242
  - Knowledge: 51
  - Messages: 150
  - Episodes: 38

**Sample Knowledge:**
- Sprint planning
- Performance coaching
- Workflow optimization
- Team management
- Task delegation
- Productivity metrics

**Questions to Ask:**
- "What is my team structure?"
- "How do I coach team members?"
- "What workflow optimizations have I implemented?"
- "What are my team lead duties?"

---

## 📋 KNOWLEDGE CATEGORIES

Each user has entries in these categories:
- **Management** (10 entries per user)
- **HR Policies** (10 entries per user)
- **Employee Development** (10 entries per user)
- **Team Operations** (10 entries per user)
- **Office Operations** (10 entries per user)
- **User Persona** (1 entry per user)

---

## 🔍 SQL QUERIES TO EXPLORE DATA

### See All Users
```sql
SELECT user_id, name, raw_content 
FROM user_persona 
ORDER BY name;
```

### See All Knowledge for One User
```sql
SELECT category, content 
FROM knowledge_base 
WHERE user_id = 'tech_lead_001'
ORDER BY created_at DESC;
```

### See Recent Messages for One User
```sql
SELECT scm.role, scm.content, scm.created_at
FROM super_chat_messages scm
JOIN super_chat sc ON scm.super_chat_id = sc.id
WHERE sc.user_id = 'tech_lead_001'
ORDER BY scm.created_at DESC
LIMIT 20;
```

### See Episodes for One User
```sql
SELECT message_count, messages, date_from, date_to
FROM episodes
WHERE user_id = 'tech_lead_001'
ORDER BY created_at DESC
LIMIT 10;
```

### Count Entries by Category
```sql
SELECT category, COUNT(*) as count
FROM knowledge_base
WHERE user_id = 'tech_lead_001'
GROUP BY category;
```

---

## 💡 HOW TO USE IN THE APP

### 1. Start the App
```bash
python3 interactive_memory_app.py
```

### 2. Switch to a User
```
user tech_lead_001
```

### 3. Ask Questions
```
what are my skills?
what is the sprint planning process?
what policies should I know about?
what is my role and expertise?
```

### 4. Add New Knowledge
```
I completed the API refactoring today
```

### 5. Search Across All Layers
```
search architecture
search policy
search team
```

---

## 📊 ENTRY DISTRIBUTION

```
Total Entries: ~1,204 across all users

Semantic Layer:
- Personas: 5 (1 per user)
- Knowledge: 255 (51 per user)

Episodic Layer:
- Messages: 750+ (150 per user)
- Episodes: 190 (38 per user)
```

---

## 🎯 TESTING RECOMMENDATIONS

### Best User for Testing: **tech_lead_001** (Michael Chen)
- Most entries (243)
- Technical background
- Rich knowledge base
- Good for technical questions

### Sample Test Flow:
```bash
# Start app
python3 interactive_memory_app.py

# Switch user
user tech_lead_001

# Ask questions
what are my skills?
what is my expertise?
what policies do I need to know?
how do I handle code reviews?

# Add knowledge
I reviewed the authentication module today

# Search
search architecture
search code review
```

---

## 📁 FILES TO EXPLORE

- `view_all_data.sql` - SQL queries to view all data
- `interactive_memory_app.py` - Main application
- `STORAGE_RETRIEVAL_DEMO.md` - Usage examples
- `FIX_EPISODES_QUERY.md` - Recent fixes

---

## 🔗 Database Connection

```bash
Host: localhost
Port: 5435
Database: semantic_memory
User: postgres
Password: 2191
```

Connect with:
```bash
PGPASSWORD=2191 psql -h localhost -p 5435 -U postgres -d semantic_memory
```
