# Storage & Retrieval Demo

## ✨ New Feature: Intelligent Storage + Retrieval + AI Response

The system now performs **3 steps** when you input any statement:

### 1. **STORAGE** 📚
- Stores your input in appropriate layers (SEMANTIC + EPISODIC)
- Shows exactly where it's stored

### 2. **RETRIEVAL** 🔍  
- Automatically searches through all storage layers
- Finds related information from your memory

### 3. **AI RESPONSE** 💡
- Generates contextual insight based on retrieved data
- Provides intelligent acknowledgment or suggestions

---

## Example Flow

```
[default_user] → Emily Rodriguez

✓ Stored in:
    📚 SEMANTIC → knowledge_base (ID: 6589d31c-f42e-4e18-adbf-ca45f7717c6c, Category: Knowledge)
    📅 EPISODIC → super_chat_messages (chat: 26)

   🔍 Retrieving from storage layers...
   ✓ Retrieved 3 related items from storage

   💡 You've stored the name "Emily Rodriguez", which is now available for future reference. 
      I'm ready to help you associate more information with this name or retrieve it when needed.
```

---

## How It Works

### Storage Phase
- **Input:** Any statement you type
- **Action:** Classifies and stores in appropriate layers
- **Output:** Shows storage location(s) with IDs and categories

### Retrieval Phase  
- **Action:** Searches knowledge_base for related items
- **Query:** Uses the input text to find matches
- **Output:** Shows count of retrieved items

### AI Response Phase
- **Context:** User persona + retrieved knowledge
- **Model:** Groq llama-3.3-70b-versatile
- **Output:** Brief, contextual acknowledgment (1-2 sentences)

---

## Try These Examples

### 1. Store User Information
```
user tech_lead_001
My name is Michael Chen
```
**Result:** 
- Stores in user_persona AND knowledge_base
- Retrieves existing Michael Chen data
- AI responds with personalized acknowledgment

### 2. Store Knowledge
```
I completed the API integration today
```
**Result:**
- Stores in knowledge_base + messages
- Retrieves related API/integration entries
- AI provides context about your work patterns

### 3. Ask Questions (Automatic Chat)
```
what is my name?
```
**Result:**
- Automatically routes to chat (no storage)
- Retrieves full context from all layers
- AI answers based on your complete memory

---

## Benefits

✅ **Instant Feedback:** Know exactly where data is stored  
✅ **Contextual Awareness:** AI sees related information immediately  
✅ **Intelligent Responses:** Get relevant insights with every input  
✅ **Seamless Flow:** No extra commands needed - it just works  
✅ **Full Transparency:** See storage → retrieval → response chain

---

## Technical Details

### Retrieval Query
```sql
SELECT id, content, category
FROM knowledge_base
WHERE user_id = %s 
  AND content ILIKE %s
ORDER BY created_at DESC
LIMIT 3
```

### AI Prompt
```
You are a helpful memory assistant. The user just stored: "{input}"

Based on their memory context, provide a brief, relevant 
acknowledgment or insight (1-2 sentences).

MEMORY CONTEXT:
{user_persona + related_knowledge}
```

### Error Handling
- Transaction rollback on failures
- Silent fallback if AI unavailable
- Graceful degradation to storage confirmation

---

## Switch Users to Test

All these users have ~240 entries ready for testing:

```
user hr_manager_001        # Sarah Mitchell
user tech_lead_001         # Michael Chen  
user project_manager_001   # Emily Rodriguez
user department_head_001   # James Williams
user team_lead_001         # Priya Sharma
```

Each user has:
- 1 persona entry
- ~51 knowledge entries
- ~150 messages
- ~38 episodes

Perfect for testing retrieval and context-aware responses!
