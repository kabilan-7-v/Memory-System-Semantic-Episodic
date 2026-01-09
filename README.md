# 🧠 Interactive Memory System

A dual-layer semantic + episodic memory system with **Redis cache** and intelligent AI-powered Q&A capabilities.

## 🚀 Quick Start

```bash
# 1. Install Redis (if not already installed)
brew install redis  # macOS
# or: sudo apt-get install redis-server  # Linux

# 2. Start Redis
brew services start redis  # macOS
# or: sudo systemctl start redis  # Linux

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your PostgreSQL and Groq API credentials

# 5. Run the application
python3 interactive_memory_app.py
```

## 📋 Features

✅ **Redis Temporary Cache**
- **Actual Redis server** for last 15 chats per user
- **4-8x faster** response times for recent messages
- Persistent across application restarts
- 24-hour TTL with automatic refresh
- See [REDIS_INTEGRATION.md](docs/REDIS_INTEGRATION.md) for details

✅ **Dual-Layer Memory Architecture**
- **Semantic Layer**: Long-term facts (user personas, knowledge base)
- **Episodic Layer**: Temporal events (conversations, episodes)

✅ **Intelligent Storage & Retrieval**
- Auto-classify and store information in appropriate layers
- Hybrid search across all memory types + temporary cache
- Context-aware AI responses using Groq API

✅ **Conversation History**
- Full timestamp tracking
- Time-aware question answering
- View conversation history with `history` command

✅ **Multi-User Support**
- 5 pre-populated users with ~240 entries each
- Switch between users seamlessly (auto-reloads cache)
- Isolated memory per user

## 💡 Commands

| Command | Description |
|---------|-------------|
| `<text>` | Auto-store statement in appropriate layers |
| `search <query>` | Hybrid search across all layers + temp cache |
| `chat <message>` | Chat with AI using full context (prioritizes temp cache) |
| `history` | View conversation history with timestamps |
| `status` | Show detailed memory statistics |
| `user <id>` | Switch to different user (reloads temp cache) |
| `quit` | Exit application |

## 📊 Example Usage

```bash
# Start the app
python3 interactive_memory_app.py

# Switch to a user
user tech_lead_001

# Ask questions (automatic AI responses)
what are my skills?
what is the sprint planning process?
what did we discuss at 7:40pm yesterday?

# Add knowledge
I completed the API refactoring today

# Search memory
search architecture

# View history
history
```

## 🗂️ Project Structure

```
September-Test/
├── interactive_memory_app.py  # Main application
├── requirements.txt           # Python dependencies
├── .env                       # Configuration (not in git)
├── .env.example              # Configuration template
│
├── database/                 # Database schemas
│   ├── schema.sql
│   ├── enhanced_schema.sql
│   └── unified_schema.sql
│
├── scripts/                  # Utility scripts
│   ├── populate_complete_users.py
│   ├── populate_office_data.py
│   └── jobs/                # Background jobs
│       ├── run_episodization.py
│       └── run_instancization.py
│
├── src/                     # Source modules
│   ├── config/
│   ├── episodic/
│   ├── models/
│   ├── repositories/
│   └── services/
│
├── docs/                    # Documentation
│   ├── QUICKSTART.md
│   ├── ALL_USER_DATA.md
│   ├── STORAGE_RETRIEVAL_DEMO.md
│   └── ...
│
├── tools/                   # Admin tools
│   ├── view_user_data.sh
│   ├── view_all_data.sql
│   └── quickstart.sh
│
└── archive/                 # Old versions
    └── ...
```

## 👥 Pre-populated Users

| Name | User ID | Role | Entries |
|------|---------|------|---------|
| Sarah Mitchell | hr_manager_001 | HR Manager | 239 |
| Michael Chen | tech_lead_001 | Technical Lead | 245 |
| Emily Rodriguez | project_manager_001 | Project Manager | 240 |
| James Williams | department_head_001 | Department Head | 240 |
| Priya Sharma | team_lead_001 | Team Lead | 252 |

## 🔧 Configuration

### Database (PostgreSQL)
```env
DB_HOST=localhost
DB_PORT=5435
DB_NAME=semantic_memory
DB_USER=postgres
DB_PASSWORD=your_password
```

### AI (Groq API)
```env
GROQ_API_KEY=your_groq_api_key
```

## 📚 Documentation

- **Quick Start**: [docs/QUICKSTART.md](docs/QUICKSTART.md)
- **User Data Guide**: [docs/ALL_USER_DATA.md](docs/ALL_USER_DATA.md)
- **Storage & Retrieval**: [docs/STORAGE_RETRIEVAL_DEMO.md](docs/STORAGE_RETRIEVAL_DEMO.md)
- **Memory Schema**: [docs/MEMORY_SYSTEM_SCHEMA.md](docs/MEMORY_SYSTEM_SCHEMA.md)

## 🛠️ Development

### View All User Data
```bash
./tools/view_user_data.sh
```

### Populate Test Data
```bash
python3 scripts/populate_complete_users.py
```

### Run Background Jobs
```bash
# Episodization (every 6 hours)
python3 scripts/jobs/run_episodization.py

# Instancization (after 30 days)
python3 scripts/jobs/run_instancization.py
```

## 🗄️ Database Schema

### Semantic Layer
- `user_persona` - User profile information
- `knowledge_base` - Long-term factual knowledge
- `semantic_memory_index` - Links between users and knowledge

### Episodic Layer
- `super_chat` - Chat sessions
- `super_chat_messages` - Individual messages
- `episodes` - Grouped conversation episodes (6-hour windows)
- `instances` - Long-term memory instances (30+ days)

## 🤝 Contributing

This is a demonstration project showcasing dual-layer memory architecture with AI integration.

## 📝 License

MIT License - See LICENSE file for details

---

**Built with**: Python, PostgreSQL, pgvector, Groq AI (llama-3.3-70b-versatile)
