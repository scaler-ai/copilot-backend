# Testing LLM Integration

Quick guide to test the LLM-based tool calling feature.

## Prerequisites

1. OpenAI API Key (get from https://platform.openai.com/api-keys)
2. Calculator server available at `backend/examples/calculator_server.py`
3. Backend and frontend running

## Quick Setup

### 1. Install OpenAI dependency

```bash
cd copilot-backend/backend
uv sync  # This will install the new openai dependency
```

### 2. Set OpenAI API Key

Add to your `.env` file:
```bash
OPENAI_API_KEY=sk-...your-key-here
LLM_MODEL=gpt-4-turbo-preview  # Optional, this is the default
```

### 3. Test LLM Service (Optional)

Run the test script to verify LLM integration:
```bash
cd copilot-backend/backend
python test_llm_integration.py
```

Expected output:
- Shows tool detection for math queries
- Demonstrates fallback when no API key is set

### 4. Start Services

```bash
# Terminal 1: Backend
cd copilot-backend/backend
source .venv/bin/activate
fastapi run --reload app/main.py

# Terminal 2: Frontend
cd copilot-frontend
npm run dev

# Terminal 3: Calculator Server (for testing)
cd copilot-backend/backend
python examples/calculator_server.py
```

### 5. Register Calculator Server

1. Go to http://localhost:5173/mcp
2. Click "Add Server"
3. Fill in:
   - Name: Calculator
   - Type: STDIO
   - Command: `python`
   - Args: `/path/to/copilot-backend/backend/examples/calculator_server.py`

### 6. Test Tool Calling

Start a chat and try these messages:

**Basic Math:**
- "What is 2 + 2?"
- "Calculate 15 * 8"
- "What's 100 divided by 4?"

**Natural Language:**
- "Can you help me calculate the sum of 25 and 37?"
- "I need to know what 50 plus 30 equals"
- "Multiply 7 by 9 for me"

**Non-Math (no tools):**
- "Hello, how are you?"
- "What can you do?"

## Expected Behavior

### With OpenAI API Key:
1. Natural language is understood
2. Tools are called automatically
3. Results are formatted nicely
4. Tool execution is shown in UI

### Without OpenAI API Key (Fallback):
1. Simple pattern matching detects math
2. Basic expressions like "2+2" work
3. Complex requests may not be understood

## Debugging

### Check Logs

Backend logs show:
```
INFO:     LLM decision: {'should_call_tools': True, 'tool_calls': [...]}
INFO:     Calling tool: calculate with args: {'expression': '2 + 2'}
```

### Common Issues

1. **No tools shown**: Ensure Calculator server is running and registered
2. **No tool calling**: Check OpenAI API key is set correctly
3. **Connection errors**: Verify all services are running

## Cost Considerations

- Each message uses ~100-500 tokens
- GPT-4 Turbo costs ~$0.01 per 1K input tokens
- Monitor usage at https://platform.openai.com/usage