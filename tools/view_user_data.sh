#!/bin/bash
# Quick script to view all user data samples

echo "=================================================="
echo "📊 ALL USERS AND THEIR DATA"
echo "=================================================="

PGPASSWORD=2191 psql -h localhost -p 5435 -U postgres -d semantic_memory << 'EOF'

\echo ''
\echo '=== 👥 ALL USERS ==='
SELECT 
    name as "Name",
    user_id as "User ID",
    array_to_string(expertise_areas, ', ') as "Expertise"
FROM user_persona 
ORDER BY name;

\echo ''
\echo '=== 📊 ENTRY COUNTS ==='
SELECT 
    up.name as "User",
    COALESCE(kb.count, 0) as "Knowledge",
    COALESCE(msg.count, 0) as "Messages",
    COALESCE(ep.count, 0) as "Episodes",
    COALESCE(kb.count, 0) + COALESCE(msg.count, 0) + COALESCE(ep.count, 0) + 1 as "Total"
FROM user_persona up
LEFT JOIN (SELECT user_id, COUNT(*) as count FROM knowledge_base GROUP BY user_id) kb ON up.user_id = kb.user_id
LEFT JOIN (SELECT sc.user_id, COUNT(*) as count FROM super_chat_messages scm JOIN super_chat sc ON scm.super_chat_id = sc.id GROUP BY sc.user_id) msg ON up.user_id = msg.user_id
LEFT JOIN (SELECT user_id, COUNT(*) as count FROM episodes GROUP BY user_id) ep ON up.user_id = ep.user_id
ORDER BY up.name;

\echo ''
\echo '=== 📚 SAMPLE KNOWLEDGE - Sarah Mitchell (HR) ==='
SELECT content FROM knowledge_base WHERE user_id = 'hr_manager_001' ORDER BY created_at DESC LIMIT 5;

\echo ''
\echo '=== 💻 SAMPLE KNOWLEDGE - Michael Chen (Tech Lead) ==='
SELECT content FROM knowledge_base WHERE user_id = 'tech_lead_001' ORDER BY created_at DESC LIMIT 5;

\echo ''
\echo '=== 📋 SAMPLE KNOWLEDGE - Emily Rodriguez (PM) ==='
SELECT content FROM knowledge_base WHERE user_id = 'project_manager_001' ORDER BY created_at DESC LIMIT 5;

\echo ''
\echo '=== 🎯 SAMPLE KNOWLEDGE - James Williams (Dept Head) ==='
SELECT content FROM knowledge_base WHERE user_id = 'department_head_001' ORDER BY created_at DESC LIMIT 5;

\echo ''
\echo '=== 👥 SAMPLE KNOWLEDGE - Priya Sharma (Team Lead) ==='
SELECT content FROM knowledge_base WHERE user_id = 'team_lead_001' ORDER BY created_at DESC LIMIT 5;

\echo ''
\echo '=== 📊 KNOWLEDGE CATEGORIES ==='
SELECT 
    category as "Category",
    COUNT(*) as "Total Entries"
FROM knowledge_base 
GROUP BY category 
ORDER BY COUNT(*) DESC;

EOF

echo ""
echo "=================================================="
echo "💡 QUESTIONS YOU CAN ASK:"
echo "=================================================="
echo ""
echo "For Michael Chen (tech_lead_001):"
echo "  - What are my skills?"
echo "  - What is my expertise?"
echo "  - What is the code review process?"
echo "  - What are the sprint planning guidelines?"
echo ""
echo "For Sarah Mitchell (hr_manager_001):"
echo "  - What is the harassment policy?"
echo "  - How many vacation days do I have?"
echo "  - What are the recruitment procedures?"
echo ""
echo "For Emily Rodriguez (project_manager_001):"
echo "  - What is my project management approach?"
echo "  - How do I handle stakeholders?"
echo ""
echo "For James Williams (department_head_001):"
echo "  - What is my strategic vision?"
echo "  - How do I manage budgets?"
echo ""
echo "For Priya Sharma (team_lead_001):"
echo "  - How do I coach team members?"
echo "  - What workflow optimizations have I done?"
echo ""
echo "=================================================="
