#!/usr/bin/env python3
"""
Quick Demo: How to use the memory system for personal queries
"""

print("""
================================================================================
                    PERSONAL MEMORY QUERIES - DEMO
================================================================================

Now that you've stored "hi I am Sharan" in the database, here's how to use it:

1. START THE APP
   $ python3 memory_app.py

2. ASK QUESTIONS DIRECTLY (New Feature!)
   Just type your question - the system will search automatically:
   
   >>> what is my name
   
   [ANSWER] hi I am Sharan
            (Confidence: 85%)
   
   [RESULTS] Found 1 relevant memories:
   
   [1] hi I am Sharan
       Category: general
       Score: 0.8542 (Keyword: 0.3201, Semantic: 0.9123)
       
       hi I am Sharan

3. OTHER QUESTIONS YOU CAN ASK
   >>> who am I
   >>> tell me about Sharan
   >>> what do you know about me
   >>> show me information about Sharan

4. ADD MORE PERSONAL INFO
   >>> add
   Content: I am 25 years old and I live in Mumbai
   Title: Personal Info - Age and Location
   Category: personal
   Tags: age, location, personal
   
   >>> add
   Content: I work as a software developer specializing in Python and AI
   Title: Professional Info
   Category: career
   Tags: job, python, AI, developer

5. THEN ASK MORE COMPLEX QUESTIONS
   >>> how old am I
   >>> where do I live
   >>> what do I do for work
   >>> tell me about my career

================================================================================
                            KEY FEATURES
================================================================================

✨ DIRECT ANSWERS
   - High-confidence results show the answer immediately
   - No need to type 'search' command

✨ NATURAL LANGUAGE
   - Ask questions like you would ask a person
   - System understands: what, who, where, when, why, how, tell, show

✨ SMART MATCHING
   - Keyword matching: Finds exact words like "Sharan", "name"
   - Semantic matching: Understands meaning even without exact words
   - Hybrid score: Combines both for best results

✨ ORGANIZED STORAGE
   - Use categories: personal, career, health, goals, etc.
   - Add tags: name, age, location, job, hobby, etc.
   - Search by category or tags later

================================================================================
                            TRY IT NOW!
================================================================================

Run: python3 memory_app.py

Then ask: what is my name

You should see your answer immediately! 🎉

================================================================================
""")
