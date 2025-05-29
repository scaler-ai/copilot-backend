# LLM Integration for MCP Tool Calling

This document explains how the LLM (Large Language Model) integration works for intelligent tool calling in MCP servers.

## Overview

The LLM integration allows the MCP chat interface to intelligently decide when and how to call tools based on user messages. Instead of requiring users to explicitly invoke tools, the system analyzes natural language and automatically determines the appropriate tools to use.

## Architecture

```
User Message → LLM Service → Tool Decision → MCP Server → Tool Execution → Response Formatting → User
```

### Components

1. **LLM Service** (`app/services/llm_service.py`):
   - Analyzes user messages using OpenAI GPT models
   - Decides which tools to call with appropriate parameters
   - Formats tool results into natural language responses

2. **WebSocket Handler** (`app/api/websockets/mcp.py`):
   - Intercepts user messages
   - Calls LLM service for tool orchestration
   - Executes tools via MCP protocol
   - Saves messages and tool calls to database

3. **Frontend** (`components/mcp/ChatInterface`):
   - Displays available tools
   - Shows tool execution status
   - Renders formatted responses

## Configuration

### Environment Variables

```bash
# Required for LLM features
OPENAI_API_KEY=your-openai-api-key-here

# Optional: Choose model (default: gpt-4-turbo-preview)
LLM_MODEL=gpt-4-turbo-preview
```

### Supported Models

- `gpt-4-turbo-preview` (recommended)
- `gpt-4`
- `gpt-3.5-turbo`

## How It Works

### 1. Message Analysis

When a user sends a message, the LLM service:

```python
result = await llm_service.process_message_with_tools(
    message="What is 25 + 37?",
    available_tools=[calculator_tool_definition]
)
```

### 2. Tool Decision

The LLM analyzes the message and returns:

```json
{
    "should_call_tools": true,
    "tool_calls": [
        {
            "id": "call_abc123",
            "name": "calculate",
            "arguments": {
                "expression": "25 + 37"
            }
        }
    ],
    "reasoning": "The user wants to perform addition.",
    "suggested_response": null
}
```

### 3. Tool Execution

The WebSocket handler executes the tool via MCP:

```python
tool_response = await manager.send_to_mcp_server(
    server_id,
    {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "calculate",
            "arguments": {"expression": "25 + 37"}
        },
        "id": msg_id
    }
)
```

### 4. Response Formatting

The LLM formats the tool results:

```python
formatted_response = await llm_service.format_tool_results(
    original_message="What is 25 + 37?",
    tool_calls=[...],
    tool_results=[{"result": "62"}]
)
# Returns: "25 + 37 equals 62."
```

## Fallback Behavior

When OpenAI API is unavailable:

1. **Pattern Matching**: Simple regex patterns detect common requests
2. **Direct Forwarding**: Messages are sent to MCP server without tool analysis
3. **Manual Tool Calling**: Users can still explicitly request tool usage

## Example Interactions

### Calculator Server

**User**: "What's 15 times 8?"
**System**: 
1. Detects calculation request
2. Calls `calculate` tool with `expression: "15 * 8"`
3. Returns: "15 times 8 equals 120."

**User**: "Hello, how are you?"
**System**: 
1. No tools needed
2. Forwards to MCP server for general response

### Complex Calculations

**User**: "Calculate 50 + 30, then multiply by 2"
**System**:
1. Calls `calculate` with `expression: "50 + 30"`
2. Calls `calculate` with `expression: "80 * 2"`
3. Returns: "First, 50 + 30 equals 80. Then, 80 multiplied by 2 equals 160."

## Testing

### Manual Testing

1. Set up environment:
   ```bash
   export OPENAI_API_KEY=your-key-here
   ```

2. Run test script:
   ```bash
   cd copilot-backend/backend
   python test_llm_integration.py
   ```

3. Start Calculator server:
   ```bash
   python examples/calculator_server.py
   ```

4. Test via UI:
   - Register the Calculator server
   - Start a chat session
   - Try messages like "What is 2 + 2?"

### Automated Testing

```python
# Test without OpenAI (pattern matching)
OPENAI_API_KEY="" pytest tests/test_llm_service.py

# Test with OpenAI
OPENAI_API_KEY="sk-..." pytest tests/test_llm_service.py
```

## Security Considerations

1. **API Key Protection**: Never commit OpenAI API keys
2. **Rate Limiting**: Implement rate limits for API calls
3. **Input Validation**: Sanitize tool arguments before execution
4. **Cost Management**: Monitor API usage to control costs

## Future Enhancements

1. **Multi-Tool Orchestration**: Execute multiple tools in sequence
2. **Context Awareness**: Use conversation history for better decisions
3. **Custom Models**: Support for local LLMs (Ollama, etc.)
4. **Tool Preferences**: User-specific tool calling preferences
5. **Caching**: Cache common tool decisions for performance