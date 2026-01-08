-- =====================================================
-- VIEW ALL ENTRIES FOR ALL USERS IN POSTGRESQL
-- =====================================================

-- 1. USER PERSONAS (Who are the users?)
SELECT 
    user_id,
    name,
    raw_content,
    interests,
    expertise_areas,
    created_at
FROM user_persona
ORDER BY name;

-- 2. KNOWLEDGE BASE (What do users know?)
SELECT 
    user_id,
    category,
    content,
    tags,
    created_at
FROM knowledge_base
ORDER BY user_id, created_at DESC
LIMIT 50;

-- 3. CHAT MESSAGES (What have users said?)
SELECT 
    sc.user_id,
    up.name as user_name,
    scm.role,
    scm.content,
    scm.created_at
FROM super_chat_messages scm
JOIN super_chat sc ON scm.super_chat_id = sc.id
LEFT JOIN user_persona up ON sc.user_id = up.user_id
ORDER BY scm.created_at DESC
LIMIT 50;

-- 4. EPISODES (Conversation summaries)
SELECT 
    user_id,
    message_count,
    source_type,
    messages,
    date_from,
    date_to
FROM episodes
ORDER BY created_at DESC
LIMIT 20;

-- =====================================================
-- SUMMARY COUNTS PER USER
-- =====================================================
SELECT 
    up.user_id,
    up.name,
    COALESCE(kb.kb_count, 0) as knowledge_entries,
    COALESCE(msg.msg_count, 0) as message_count,
    COALESCE(ep.ep_count, 0) as episode_count,
    COALESCE(kb.kb_count, 0) + COALESCE(msg.msg_count, 0) + COALESCE(ep.ep_count, 0) + 1 as total_entries
FROM user_persona up
LEFT JOIN (
    SELECT user_id, COUNT(*) as kb_count 
    FROM knowledge_base 
    GROUP BY user_id
) kb ON up.user_id = kb.user_id
LEFT JOIN (
    SELECT sc.user_id, COUNT(*) as msg_count 
    FROM super_chat_messages scm
    JOIN super_chat sc ON scm.super_chat_id = sc.id
    GROUP BY sc.user_id
) msg ON up.user_id = msg.user_id
LEFT JOIN (
    SELECT user_id, COUNT(*) as ep_count 
    FROM episodes 
    GROUP BY user_id
) ep ON up.user_id = ep.user_id
ORDER BY up.name;

-- =====================================================
-- SAMPLE DATA FROM EACH USER
-- =====================================================

-- Sarah Mitchell (HR Manager) - Sample data
SELECT 'SARAH MITCHELL (HR)' as user, category, content 
FROM knowledge_base 
WHERE user_id = 'hr_manager_001' 
LIMIT 5;

-- Michael Chen (Tech Lead) - Sample data
SELECT 'MICHAEL CHEN (TECH)' as user, category, content 
FROM knowledge_base 
WHERE user_id = 'tech_lead_001' 
LIMIT 5;

-- Emily Rodriguez (Project Manager) - Sample data
SELECT 'EMILY RODRIGUEZ (PM)' as user, category, content 
FROM knowledge_base 
WHERE user_id = 'project_manager_001' 
LIMIT 5;

-- James Williams (Department Head) - Sample data
SELECT 'JAMES WILLIAMS (DEPT HEAD)' as user, category, content 
FROM knowledge_base 
WHERE user_id = 'department_head_001' 
LIMIT 5;

-- Priya Sharma (Team Lead) - Sample data
SELECT 'PRIYA SHARMA (TEAM LEAD)' as user, category, content 
FROM knowledge_base 
WHERE user_id = 'team_lead_001' 
LIMIT 5;
