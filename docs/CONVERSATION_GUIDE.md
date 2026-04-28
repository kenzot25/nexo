# Conversation Graph Guide

This guide explains how to use nexo's conversation graph features for building robust chatbots.

## Overview

Nexo now supports **conversation graphs** - a hybrid approach combining:
1. **LLM** for natural language understanding and generation
2. **Graph State Machine** for controlling valid conversation paths
3. **SQLite Session Store** for state persistence

This architecture handles the 8 common failure modes identified in chatbot systems:
- The Confidence Trap (26.4%)
- The Drift (37.2%)
- The Silent Mismatch (9.0%)
- The Death Spiral (6.9%)
- The Contradiction Unravel (7.6%)
- The Walkaway (5.9%)
- The Partial Recovery (6.3%)
- The Mystery Failure (12.0%)

## Quick Start

### 1. Create a Conversation Template

Create a JSON file defining your conversation flow:

```json
{
  "id": "booking_flow",
  "name": "Tour Booking",
  "nodes": [
    {
      "id": "intent_greeting",
      "type": "intent",
      "label": "User greets",
      "triggers": ["hello", "hi", "xin chào"],
      "confidence_threshold": 0.7
    },
    {
      "id": "resp_welcome",
      "type": "response",
      "label": "Welcome message",
      "templates": ["Chào bạn!", "Hello!"]
    },
    {
      "id": "state_collecting",
      "type": "state",
      "label": "Collecting info",
      "required_slots": ["name", "phone"]
    },
    {
      "id": "failure_ambiguity",
      "type": "failure_state",
      "label": "Ambiguous input",
      "recovery_path": "ask_clarification",
      "max_retries": 2
    }
  ],
  "edges": [
    {
      "source": "intent_greeting",
      "target": "resp_welcome",
      "relation": "triggers"
    },
    {
      "source": "resp_welcome",
      "target": "state_collecting",
      "relation": "leads_to"
    }
  ]
}
```

### 2. Build the Graph

```bash
# Extract templates into the graph
nexo update .

# Verify the graph was built
nexo query "booking flow"
```

### 3. Query via MCP Tools

In Claude Code, use the conversation tools:

```
/nexo conversation_detect_ambiguity "hello"
/nexo conversation_next_states "intent_greeting"
/nexo conversation_find_paths "booking_complete"
/nexo conversation_get_recovery_path "failure_ambiguity"
```

### 4. Monitor with Dashboard

```bash
# View conversation metrics
nexo conversation-status

# Export as JSON
nexo conversation-status --json

# Export all sessions
nexo conversation-export --output conversations.json
```

## Node Types

### Intent Nodes

Detect user intent from input text.

```json
{
  "id": "intent_booking",
  "type": "intent",
  "label": "Booking request",
  "triggers": ["đặt", "book", "booking", "mua"],
  "confidence_threshold": 0.6
}
```

**Fields:**
- `triggers`: List of words/phrases that trigger this intent
- `confidence_threshold`: Minimum confidence score (0.0-1.0)

### Response Nodes

Define response templates.

```json
{
  "id": "resp_welcome",
  "type": "response",
  "label": "Welcome message",
  "templates": ["Hello!", "Hi there!"],
  "tone": "casual",
  "context": ["general", "support"]
}
```

**Fields:**
- `templates`: List of response variations
- `tone`: casual, formal, empathetic, etc.
- `context`: When this response is appropriate

### State Nodes

Track slot collection progress.

```json
{
  "id": "state_booking",
  "type": "state",
  "label": "Collecting booking info",
  "required_slots": ["date", "people", "budget"],
  "optional_slots": ["hotel_rating", "preferences"]
}
```

**Fields:**
- `required_slots`: Must collect before proceeding
- `optional_slots`: Nice to have but not required

### Failure State Nodes

Handle errors with recovery paths.

```json
{
  "id": "failure_ambiguity",
  "type": "failure_state",
  "label": "Ambiguous input",
  "recovery_path": "ask_clarification",
  "max_retries": 2
}
```

**Fields:**
- `recovery_path`: Node ID to transition to for recovery
- `max_retries`: Maximum retry attempts before escalation

## Edge Types

| Relation | Description | Example |
|----------|-------------|---------|
| `triggers` | Intent triggers response | greeting → welcome |
| `leads_to` | One node leads to another | welcome → booking |
| `requires` | State requires information | booking → ask_date |
| `collects_response` | Response collects user input | ask_date → booking |
| `transitions_when` | Conditional transition | booking → complete (all_slots_filled) |
| `can_become` | Normal state can become failure | booking → failure_missing |
| `requires_recovery` | Failure needs recovery | failure → clarification |
| `resumes_at` | Resume after recovery | clarification → greeting |

## CLI Commands

### conversation-status

Show conversation metrics dashboard.

```bash
nexo conversation-status
nexo conversation-status --json
nexo conversation-status --db ~/.nexo/sessions.db
```

**Metrics tracked:**
- Total sessions and turns
- Completion rate
- Ambiguity rate
- Fallback rate
- Failure mode distribution
- Drop-off points

### conversation-export

Export conversation sessions.

```bash
nexo conversation-export
nexo conversation-export --output my_conversations.json
nexo conversation-export --format md --output report.md
```

### conversation-session

View details of a specific session.

```bash
nexo conversation-session session_123
nexo conversation-session session_123 --db ~/.nexo/sessions.db
```

### conversation-list

List all sessions.

```bash
nexo conversation-list
nexo conversation-list --db ~/.nexo/sessions.db
```

## Session Management

Sessions are stored in SQLite at `~/.nexo/sessions.db`.

### Checkpoint Structure

```python
from nexo.session import Checkpoint

checkpoint = Checkpoint(
    turn_id=5,
    current_node="state_collecting",
    collected_slots={"name": "An", "phone": "0123"},
    path_history=["greeting", "inquiry", "collecting"],
    failure_count=0,
)
```

### Programmatic Usage

```python
from nexo.session import SessionStore

store = SessionStore()  # Uses ~/.nexo/sessions.db

# Save checkpoint
store.save_checkpoint("session_123", checkpoint)

# Load checkpoint
checkpoint = store.load_checkpoint("session_123")

# Save turn
store.save_turn(
    session_id="session_123",
    turn_id=1,
    user_input="Hello",
    ai_response="Hi there!",
    matched_nodes=["intent_greeting"],
)

# Get turns
turns = store.get_turns("session_123")
```

## Context Compression

For long conversations, use compression to manage token budget:

```python
from nexo.compression import compress_conversation, Turn, should_compress

turns = [Turn(turn_id=i, user_input=f"input {i}", ai_response=f"resp {i}") for i in range(20)]

# Check if compression needed (triggers at 80% of budget)
if should_compress(turns, token_budget=2000):
    compressed = compress_conversation(
        turns,
        token_budget=2000,
        keep_recent_turns=5,  # Keep last 5 turns intact
    )
```

## API Reference

### Query Functions

```python
from nexo.query_service import (
    detect_ambiguity,
    get_valid_next_states,
    find_conversation_paths,
    get_recovery_path,
)

# Check if input is ambiguous
result = detect_ambiguity("hello", graph_path="nexo-out/graph.json")

# Get valid next states
result = get_valid_next_states("intent_greeting")

# Find paths to goal
result = find_conversation_paths("booking_complete")

# Get recovery path for failure
result = get_recovery_path("failure_ambiguity")
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `conversation_detect_ambiguity` | Check if input matches multiple intents |
| `conversation_next_states` | Get valid next states from current position |
| `conversation_find_paths` | Find paths to reach a goal state |
| `conversation_get_recovery_path` | Get recovery path for failure state |

## Sample Templates

See `docs/conversation_templates/` for examples:
- `booking_flow.json` - Tour booking conversation
- `support_flow.json` - Customer support with escalation

## Best Practices

1. **Define clear triggers**: Each intent should have distinct trigger words
2. **Set appropriate thresholds**: Start with 0.7 confidence, adjust based on testing
3. **Add recovery paths**: Every failure state needs a recovery path
4. **Monitor drop-off points**: Use dashboard to identify problematic nodes
5. **Keep templates modular**: Separate concerns into different template files
6. **Test edge cases**: Use the test suite to verify conversation flows

## Troubleshooting

### "No sessions found"
- Sessions are only created when your chatbot saves turns
- Call `store.save_turn()` after each conversation turn

### "Graph not found"
- Run `nexo update .` to rebuild the graph
- Ensure template files are in the project directory

### High ambiguity rate
- Review trigger words for overlap
- Increase `confidence_threshold` for sensitive intents
- Add more specific triggers

### High drop-off at a node
- Simplify the conversation step
- Add escape options (e.g., "speak to human")
- Review if required slots are reasonable
