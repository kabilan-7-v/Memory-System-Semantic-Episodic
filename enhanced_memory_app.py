#!/usr/bin/env python3
"""
Enhanced Memory System with Groq LLM Integration
- Chat responses using Groq
- Automatic classification into user_persona, knowledge, process, skill
- Separate table storage and retrieval
"""
import os
import sys
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment
load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("[WARNING] Groq package not installed. Install with: pip install groq")


class EnhancedMemoryApp:
    """Enhanced memory system with LLM integration"""
    
    def __init__(self):
        self.conn = None
        self.user_id = "default_user"
        self.groq_client = None
        self.connect_db()
        self.setup_groq()
    
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5435)),
                database=os.getenv('DB_NAME', 'semantic_memory'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', '2191'),
                cursor_factory=RealDictCursor
            )
            print("[DB] Connected to database")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            sys.exit(1)
    
    def setup_groq(self):
        """Setup Groq API client"""
        if not GROQ_AVAILABLE:
            return
        
        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            self.groq_client = Groq(api_key=api_key)
            print("[LLM] Groq API connected")
        else:
            print("[WARNING] GROQ_API_KEY not found")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate deterministic embedding from text"""
        embedding = []
        for i in range(1536):
            seed = text.encode('utf-8') + i.to_bytes(4, 'big')
            hash_val = hashlib.sha256(seed).digest()
            int_val = int.from_bytes(hash_val[:8], byteorder='big')
            normalized = (int_val % 2000000) / 1000000.0 - 1.0
            embedding.append(normalized)
        
        # Normalize to unit vector
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        else:
            embedding = [1.0 / (1536 ** 0.5)] * 1536
        
        return embedding
    
    def chat_response(self, user_input: str) -> str:
        """Generate chat response using Groq LLM"""
        if not self.groq_client:
            return f"I understand: {user_input}"
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a friendly AI assistant. Respond warmly and naturally to the user's statements. Keep responses brief and conversational."},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] Chat response failed: {e}")
            return f"Nice to know: {user_input}"
    
    def classify_input(self, user_input: str) -> Dict[str, Any]:
        """Classify input into user_persona, knowledge, process, or skill using LLM"""
        if not self.groq_client:
            # Fallback classification
            return self._fallback_classify(user_input)
        
        try:
            classification_prompt = f"""Analyze this user input and classify it into ONE category:
- user_persona: Personal information (name, age, preferences, traits, interests)
- knowledge: Facts, concepts, information, learnings
- process: Procedures, workflows, how-to steps
- skill: Abilities, expertise, competencies

User input: "{user_input}"

Respond ONLY with a JSON object in this exact format:
{{"type": "user_persona|knowledge|process|skill", "subject": "brief subject", "confidence": 0.0-1.0}}"""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": classification_prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            result_text = response.choices[0].message.content.strip()
            # Extract JSON from response
            if '{' in result_text and '}' in result_text:
                json_start = result_text.index('{')
                json_end = result_text.rindex('}') + 1
                result = json.loads(result_text[json_start:json_end])
                return result
            else:
                return self._fallback_classify(user_input)
                
        except Exception as e:
            print(f"[WARNING] Classification failed: {e}, using fallback")
            return self._fallback_classify(user_input)
    
    def _fallback_classify(self, user_input: str) -> Dict[str, Any]:
        """Fallback classification based on keywords"""
        text_lower = user_input.lower()
        
        # User persona keywords
        persona_keywords = ['my name', 'i am', "i'm", 'my age', 'i live', 'i like', 'i prefer', 'i enjoy', 'my hobby']
        if any(kw in text_lower for kw in persona_keywords):
            return {"type": "user_persona", "subject": "personal information", "confidence": 0.8}
        
        # Skill keywords
        skill_keywords = ['i can', 'i know how to', 'expertise in', 'skilled at', 'proficient in', 'experience in']
        if any(kw in text_lower for kw in skill_keywords):
            return {"type": "skill", "subject": "skill or ability", "confidence": 0.8}
        
        # Process keywords
        process_keywords = ['how to', 'steps to', 'procedure', 'workflow', 'process for', 'method to']
        if any(kw in text_lower for kw in process_keywords):
            return {"type": "process", "subject": "process or procedure", "confidence": 0.8}
        
        # Default to knowledge
        return {"type": "knowledge", "subject": "general knowledge", "confidence": 0.7}
    
    def store_classified_data(self, user_input: str, classification: Dict[str, Any]) -> Optional[str]:
        """Store data in appropriate table based on classification"""
        data_type = classification.get('type', 'knowledge')
        subject = classification.get('subject', 'General')
        embedding = self.generate_embedding(user_input)
        
        try:
            cursor = self.conn.cursor()
            
            if data_type == 'user_persona':
                # Extract persona data
                persona_data = self._extract_persona_data(user_input)
                cursor.execute("""
                    INSERT INTO user_persona (
                        user_id, name, preferences, raw_content, embedding, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    self.user_id,
                    persona_data.get('name'),
                    json.dumps(persona_data.get('preferences', {})),
                    user_input,
                    embedding,
                    json.dumps({'confidence': classification.get('confidence', 0.8)})
                ))
                
            elif data_type == 'skill':
                cursor.execute("""
                    INSERT INTO semantic_skill (
                        user_id, skill_name, description, embedding, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    self.user_id,
                    subject,
                    user_input,
                    embedding,
                    json.dumps({'confidence': classification.get('confidence', 0.8)})
                ))
                
            elif data_type == 'process':
                cursor.execute("""
                    INSERT INTO semantic_process (
                        user_id, process_name, description, embedding, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    self.user_id,
                    subject,
                    user_input,
                    embedding,
                    json.dumps({'confidence': classification.get('confidence', 0.8)})
                ))
                
            else:  # knowledge
                cursor.execute("""
                    INSERT INTO semantic_knowledge (
                        user_id, subject, content, embedding, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    self.user_id,
                    subject,
                    user_input,
                    embedding,
                    json.dumps({'confidence': classification.get('confidence', 0.8)})
                ))
            
            result = cursor.fetchone()
            self.conn.commit()
            return str(result['id'])
            
        except Exception as e:
            self.conn.rollback()
            print(f"[ERROR] Storage failed: {e}")
            return None
    
    def _extract_persona_data(self, text: str) -> Dict[str, Any]:
        """Extract persona information from text"""
        persona_data = {'preferences': {}}
        text_lower = text.lower()
        
        # Extract name
        if 'my name is' in text_lower:
            name_start = text_lower.index('my name is') + 11
            name_part = text[name_start:].split('.')[0].split(',')[0].strip()
            persona_data['name'] = name_part
        elif 'i am' in text_lower and not 'years old' in text_lower:
            name_start = text_lower.index('i am') + 5
            name_part = text[name_start:].split('.')[0].split(',')[0].strip()
            if len(name_part.split()) <= 3:  # Likely a name
                persona_data['name'] = name_part
        
        return persona_data
    
    def search_all_tables(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search across all semantic memory tables using HYBRID search (keyword + vector)"""
        query_embedding = self.generate_embedding(query)
        all_results = []
        
        # Weights for hybrid scoring
        keyword_weight = 0.6  # 60% keyword matching (more reliable for exact matches)
        vector_weight = 0.4   # 40% semantic similarity
        
        try:
            cursor = self.conn.cursor()
            
            # Search user_persona with keyword matching on raw_content
            cursor.execute("""
                SELECT 
                    'user_persona' as table_type,
                    id, name, raw_content as content,
                    1 - (embedding <=> %s::vector) as vector_score,
                    CASE 
                        WHEN raw_content ILIKE %s THEN 1.0
                        WHEN similarity(LOWER(raw_content), LOWER(%s)) > 0.3 THEN similarity(LOWER(raw_content), LOWER(%s))
                        ELSE 0.0
                    END as keyword_score
                FROM user_persona
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, f'%{query}%', query, query, self.user_id, query_embedding, limit * 2))
            all_results.extend([dict(row) for row in cursor.fetchall()])
            
            # Search semantic_knowledge with full-text search
            cursor.execute("""
                SELECT 
                    'knowledge' as table_type,
                    id, subject, content,
                    1 - (embedding <=> %s::vector) as vector_score,
                    CASE 
                        WHEN content ILIKE %s OR subject ILIKE %s THEN 1.0
                        WHEN content_tsv @@ plainto_tsquery('english', %s) THEN 
                            ts_rank_cd(content_tsv, plainto_tsquery('english', %s), 32) * 10
                        WHEN similarity(LOWER(content), LOWER(%s)) > 0.3 THEN similarity(LOWER(content), LOWER(%s))
                        ELSE 0.0
                    END as keyword_score
                FROM semantic_knowledge
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, f'%{query}%', f'%{query}%', query, query, query, query, self.user_id, query_embedding, limit * 2))
            all_results.extend([dict(row) for row in cursor.fetchall()])
            
            # Search semantic_skill with keyword matching
            cursor.execute("""
                SELECT 
                    'skill' as table_type,
                    id, skill_name as subject, description as content,
                    1 - (embedding <=> %s::vector) as vector_score,
                    CASE 
                        WHEN description ILIKE %s OR skill_name ILIKE %s THEN 1.0
                        WHEN content_tsv @@ plainto_tsquery('english', %s) THEN 
                            ts_rank_cd(content_tsv, plainto_tsquery('english', %s), 32) * 10
                        WHEN similarity(LOWER(description), LOWER(%s)) > 0.3 THEN similarity(LOWER(description), LOWER(%s))
                        ELSE 0.0
                    END as keyword_score
                FROM semantic_skill
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, f'%{query}%', f'%{query}%', query, query, query, query, self.user_id, query_embedding, limit * 2))
            all_results.extend([dict(row) for row in cursor.fetchall()])
            
            # Search semantic_process with keyword matching
            cursor.execute("""
                SELECT 
                    'process' as table_type,
                    id, process_name as subject, description as content,
                    1 - (embedding <=> %s::vector) as vector_score,
                    CASE 
                        WHEN description ILIKE %s OR process_name ILIKE %s THEN 1.0
                        WHEN content_tsv @@ plainto_tsquery('english', %s) THEN 
                            ts_rank_cd(content_tsv, plainto_tsquery('english', %s), 32) * 10
                        WHEN similarity(LOWER(description), LOWER(%s)) > 0.3 THEN similarity(LOWER(description), LOWER(%s))
                        ELSE 0.0
                    END as keyword_score
                FROM semantic_process
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, f'%{query}%', f'%{query}%', query, query, query, query, self.user_id, query_embedding, limit * 2))
            all_results.extend([dict(row) for row in cursor.fetchall()])
            
            # Calculate hybrid score and sort
            for result in all_results:
                result['score'] = (
                    keyword_weight * result.get('keyword_score', 0) + 
                    vector_weight * result.get('vector_score', 0)
                )
            
            all_results.sort(key=lambda x: x['score'], reverse=True)
            return all_results[:limit]
            
        except Exception as e:
            print(f"[ERROR] Search failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def extract_answer(self, content: str, query: str) -> str:
        """Extract specific answer from content"""
        sentences = [s.strip() for s in content.replace('?', '.').replace('!', '.').split('.') if s.strip()]
        
        # If short content, return as is
        if len(content) < 100 or len(sentences) <= 2:
            return content
        
        query_words = set(query.lower().split()) - {'what', 'is', 'my', 'your', 'the', 'tell', 'me', 'about'}
        
        best_sentence = None
        best_score = 0
        
        for sentence in sentences:
            score = sum(1 for word in query_words if word in sentence.lower())
            if score > best_score:
                best_score = score
                best_sentence = sentence
        
        return best_sentence if best_sentence and best_score > 0 else sentences[0]
    
    def interactive_mode(self):
        """Run interactive mode with LLM integration"""
        print("\n" + "=" * 80)
        print(" " * 20 + "ENHANCED SEMANTIC MEMORY SYSTEM")
        print("=" * 80)
        print("\n[INFO] AI-Powered Memory with Auto-Classification")
        print("\nFeatures:")
        print("   - Natural conversation with Groq LLM")
        print("   - Automatic classification (persona/knowledge/process/skill)")
        print("   - Separate table storage for each type")
        print("   - Intelligent search across all memory types")
        print("\nJust type naturally - the system will:")
        print("   1. Respond conversationally")
        print("   2. Classify your input")
        print("   3. Store in the right table")
        print("   4. Answer questions from stored memories")
        print("\nType 'quit' to exit")
        print("=" * 80)
        
        # Show stats
        self.show_stats()
        
        while True:
            try:
                print("\n")
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n[INFO] Goodbye!\n")
                    break
                
                # Check if it's a question
                is_question = '?' in user_input or any(
                    user_input.lower().startswith(w) for w in 
                    ['what', 'who', 'where', 'when', 'why', 'how', 'tell me', 'show me']
                )
                
                if is_question:
                    # Search and answer
                    print("\n[AI] Searching memories...")
                    results = self.search_all_tables(user_input)
                    
                    if results:
                        # Extract answer from best match
                        best_match = results[0]
                        answer = self.extract_answer(best_match['content'], user_input)
                        print(f"\n[ANSWER] {answer}")
                        print(f"         (From: {best_match['table_type']}, Confidence: {best_match['score']:.1%})")
                        print(f"         [Keyword: {best_match.get('keyword_score', 0):.1%}, Vector: {best_match.get('vector_score', 0):.1%}]")
                        
                        # Show all results
                        if len(results) > 1:
                            print(f"\n[OTHER RESULTS] Found {len(results)-1} more:")
                            for i, result in enumerate(results[1:], 2):
                                print(f"\n  [{i}] Type: {result['table_type'].upper()}")
                                if result.get('name'):
                                    print(f"      Subject: {result['name']}")
                                elif result.get('subject'):
                                    print(f"      Subject: {result['subject']}")
                                print(f"      Score: {result['score']:.1%} (Keyword: {result.get('keyword_score', 0):.1%}, Vector: {result.get('vector_score', 0):.1%})")
                                print(f"      Content: {result['content'][:80]}...")
                    else:
                        print("\n[INFO] No memories found for this query.")
                
                else:
                    # It's a statement - store it
                    # 1. Generate friendly response
                    response = self.chat_response(user_input)
                    print(f"\n[AI] {response}")
                    
                    # 2. Classify the input
                    print("\n[PROCESSING] Classifying input...")
                    classification = self.classify_input(user_input)
                    print(f"[CLASSIFIED] Type: {classification['type'].upper()} "
                          f"(Confidence: {classification.get('confidence', 0.8):.1%})")
                    
                    # 3. Store in appropriate table
                    result_id = self.store_classified_data(user_input, classification)
                    if result_id:
                        print(f"[STORED] Saved to {classification['type']} table (ID: {result_id[:8]}...)")
                    else:
                        print("[ERROR] Failed to store")
                
            except KeyboardInterrupt:
                print("\n\n[INFO] Goodbye!\n")
                break
            except EOFError:
                print("\n\n[INFO] Goodbye!\n")
                break
            except Exception as e:
                print(f"\n[ERROR] {e}")
                import traceback
                traceback.print_exc()
    
    def show_stats(self):
        """Show statistics from all tables"""
        try:
            cursor = self.conn.cursor()
            
            stats = {}
            for table in ['user_persona', 'semantic_knowledge', 'semantic_skill', 'semantic_process']:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table} WHERE user_id = %s", (self.user_id,))
                stats[table] = cursor.fetchone()['count']
            
            print(f"\n[STATS] Memory Statistics:")
            print(f"   User Persona: {stats['user_persona']}")
            print(f"   Knowledge: {stats['semantic_knowledge']}")
            print(f"   Skills: {stats['semantic_skill']}")
            print(f"   Processes: {stats['semantic_process']}")
            print(f"   Total: {sum(stats.values())}")
        except Exception as e:
            print(f"[WARNING] Could not load stats: {e}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("[DB] Connection closed")


def main():
    """Main entry point"""
    app = EnhancedMemoryApp()
    try:
        app.interactive_mode()
    finally:
        app.close()


if __name__ == "__main__":
    main()
