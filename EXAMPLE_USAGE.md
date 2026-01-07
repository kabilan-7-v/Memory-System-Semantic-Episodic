# Example Usage - Precise Answer Extraction

## How It Works Now

The system will extract **only the relevant answer** from your stored information!

## Example: Store Complete Profile

```bash
$ python3 memory_app.py

>>> add
Content: My name is Sharan. I am 25 years old and I live in Mumbai, India. I work as a software developer specializing in Python and AI. My hobbies include reading tech blogs and playing cricket.
Title: Personal Profile
Category: personal
Tags: name, age, location, job, hobbies

[SUCCESS] Memory added
```

## Now Ask Specific Questions

### Question 1: What is my name?
```
>>> what is my name

[ANSWER] My name is Sharan
         (Confidence: 89%)

[RESULTS] Found 1 relevant memories:
[1] Personal Profile
    ...full content shown below...
```

### Question 2: How old am I?
```
>>> how old am I

[ANSWER] I am 25 years old
         (Confidence: 91%)
```

### Question 3: Where do I live?
```
>>> where do I live

[ANSWER] I live in Mumbai, India
         (Confidence: 88%)
```

### Question 4: What do I do?
```
>>> what do I do

[ANSWER] I work as a software developer specializing in Python and AI
         (Confidence: 85%)
```

### Question 5: What are my hobbies?
```
>>> what are my hobbies

[ANSWER] My hobbies include reading tech blogs and playing cricket
         (Confidence: 87%)
```

## How The System Extracts Answers

1. **Splits your stored text into sentences**
2. **Identifies keywords** from your question (name, age, location, work, etc.)
3. **Finds the most relevant sentence** that contains those keywords
4. **Returns only that specific sentence** as the answer

## Tips for Best Results

### ✅ DO: Structure your information clearly
```
My name is Sharan. I am 25 years old. I live in Mumbai. I work as a developer.
```

### ✅ DO: Use complete sentences
```
I graduated from IIT Mumbai with a degree in Computer Science.
```

### ✅ DO: Add multiple related memories
```
>>> add
Content: My full name is Sharan Kumar. Friends call me Sharan.
Category: personal
Tags: name, identity

>>> add
Content: I was born on January 15, 1999, which makes me 25 years old.
Category: personal
Tags: age, birthday, date-of-birth
```

### ❌ DON'T: Store unstructured data
```
sharan 25 mumbai developer python
```
(System can't extract proper sentences from this)

## Advanced: Multiple Information Blocks

Store different types of information separately:

```bash
# Personal Info
>>> add
Content: My name is Sharan. I am 25 years old. I live in Mumbai, Maharashtra, India.
Category: personal-basic
Tags: name, age, location

# Professional Info
>>> add
Content: I work at Tech Corp as a Senior Software Developer. I specialize in Python, AI, and Machine Learning. I have 5 years of experience.
Category: career
Tags: job, company, skills, experience

# Education
>>> add
Content: I graduated from IIT Mumbai in 2020 with a Bachelor's degree in Computer Science. My GPA was 8.5/10.
Category: education
Tags: degree, college, university, graduation

# Contact
>>> add
Content: My email is sharan@email.com. My phone number is +91-9876543210.
Category: contact
Tags: email, phone, contact-info

# Hobbies & Interests
>>> add
Content: I enjoy reading tech blogs, especially about AI and machine learning. I also like playing cricket on weekends and traveling to new places.
Category: interests
Tags: hobbies, reading, sports, travel
```

Now ask any question:
- `what is my name` → "My name is Sharan"
- `where did I study` → "I graduated from IIT Mumbai in 2020"
- `what are my skills` → "I specialize in Python, AI, and Machine Learning"
- `how can someone contact me` → "My email is sharan@email.com"
- `what do I enjoy` → "I enjoy reading tech blogs, especially about AI and machine learning"

## The system is smart enough to:
- ✅ Extract just the relevant sentence
- ✅ Match similar questions (e.g., "age" matches "how old", "years")
- ✅ Handle variations (e.g., "where do you live" = "where do I live")
- ✅ Show confidence score for transparency
- ✅ Fall back to full content if sentence extraction isn't clear

Try it now! 🚀
