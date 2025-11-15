# 🧠 Agent Memory & Cache Management

## Memory Features

### ✅ Conversation Memory ENABLED
- Agent remembers last 10 exchanges (20 messages) per user
- Each user has their own isolated memory
- Enables context-aware conversations

### 🗑️ Clear Memory Commands

You can clear the agent's memory in **3 ways**:

---

## 1. **Via Telegram (Easiest)**

Send any of these commands in Telegram:

```
/clear
/clear_cache
clear cache
clear memory
forget everything
reset memory
```

**What happens:**
- ✅ Clears your conversation history
- ✅ Clears processed message cache
- ✅ Agent starts fresh with you
- ✅ Other users' memories are NOT affected

**Response:**
```
✅ Memory cleared! I've forgotten our previous conversations. Starting fresh!
```

---

## 2. **Via API (Specific User)**

Clear memory for a specific user:

```bash
curl -X POST "http://localhost:8000/clear-memory?user_id=123456789"
```

Response:
```json
{
  "status": "success",
  "message": "Memory cleared for user 123456789"
}
```

---

## 3. **Via API (All Users)**

Clear memory for ALL users:

```bash
curl -X POST "http://localhost:8000/clear-memory"
```

Response:
```json
{
  "status": "success",
  "message": "Memory cleared for all users"
}
```

---

## How Memory Works

### Conversation Flow:

**Example with Memory:**
```
You: Hi, my name is Karan
Bot: Nice to meet you, Karan!

You: What's my name?
Bot: Your name is Karan

You: /clear
Bot: ✅ Memory cleared! Starting fresh!

You: What's my name?
Bot: I don't have that information
```

### Memory Limits:
- **Per User:** Last 10 exchanges (20 messages)
- **Processed Messages:** Last 100 message IDs tracked
- **Automatic Cleanup:** Old messages auto-deleted

---

## Use Cases

### When to Clear Memory:

1. **Starting New Topic** - Fresh context needed
2. **Privacy** - Remove personal information shared
3. **Agent Confused** - Reset stuck conversation
4. **Testing** - Clean slate for new tests
5. **Context Switch** - Move to different project/task

### When NOT to Clear:

1. **Multi-step Tasks** - Let agent remember context
2. **Ongoing Projects** - Keep task continuity
3. **Building on Previous Info** - Use conversation history

---

## Technical Details

**What Gets Cleared:**

1. `conversation_history[user_id]` - Your chat messages
2. `processed_messages[user_id]` - Duplicate detection cache

**What Stays:**

1. Other users' memories (user-specific clearing)
2. Cosmos DB data (contacts, notes)
3. Browser sessions (cookies, logins)
4. Email/Calendar data

---

## Quick Reference

| Command | Scope | Method |
|---------|-------|--------|
| `/clear` in Telegram | Your memory only | Telegram |
| API with user_id | Specific user | HTTP POST |
| API without user_id | All users | HTTP POST |

**Memory Status:** ✅ ENABLED with manual clear option
