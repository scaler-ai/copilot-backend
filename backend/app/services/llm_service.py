"""
LLM Service for intelligent tool calling and message processing.

This service integrates with LLMs (OpenAI, Anthropic, etc.) to:
- Analyze user messages
- Decide which tools to call
- Format tool results for users
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.logging import logger
from app.schemas.mcp import MCPTool

# For this example, we'll use OpenAI, but this can be swapped for any LLM
try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not installed. LLM features will be limited.")


class LLMService:
    """Service for LLM-based tool orchestration."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the LLM service."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        
        if OPENAI_AVAILABLE and self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
            logger.warning("LLM service not enabled. Set OPENAI_API_KEY to enable.")
    
    def _convert_mcp_tools_to_openai_format(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tool definitions to OpenAI function format."""
        openai_tools = []
        
        for tool in mcp_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
            }
            openai_tools.append(openai_tool)
        
        return openai_tools
    
    async def process_message_with_tools(
        self,
        message: str,
        available_tools: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and determine if any tools should be called.
        
        Returns a dict with:
        - should_call_tools: bool
        - tool_calls: List of tools to call with arguments
        - reasoning: Why these tools were chosen
        - suggested_response: What to say to the user
        """
        if not self.enabled:
            # Fallback to simple pattern matching if LLM is not available
            return self._simple_tool_detection(message, available_tools)
        
        try:
            # Convert tools to OpenAI format
            openai_tools = self._convert_mcp_tools_to_openai_format(available_tools)
            
            # Build message history
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add system message
            messages.insert(0, {
                "role": "system",
                "content": """You are an AI assistant that helps users by calling appropriate tools.
                When a user asks something that can be answered using available tools, you should:
                1. Identify which tool(s) to call
                2. Extract the necessary parameters
                3. Call the tool(s)
                4. Provide a helpful response based on the results
                
                Always prefer using tools when they can provide accurate answers."""
            })
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Call OpenAI with tools
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto"  # Let the model decide
            )
            
            choice = response.choices[0]
            
            # Check if tools were called
            if choice.message.tool_calls:
                tool_calls = []
                for tool_call in choice.message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments)
                    })
                
                return {
                    "should_call_tools": True,
                    "tool_calls": tool_calls,
                    "reasoning": choice.message.content or "Using tools to answer your question.",
                    "suggested_response": None
                }
            else:
                # No tools needed, just return the response
                return {
                    "should_call_tools": False,
                    "tool_calls": [],
                    "reasoning": "No tools needed for this query.",
                    "suggested_response": choice.message.content
                }
                
        except Exception as e:
            logger.error(f"LLM processing error: {str(e)}")
            # Fallback to simple detection
            return self._simple_tool_detection(message, available_tools)
    
    async def format_tool_results(
        self,
        original_message: str,
        tool_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """Format tool results into a natural response for the user."""
        if not self.enabled:
            # Simple formatting
            return self._simple_format_results(tool_results)
        
        try:
            # Build context for the LLM
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Format the tool results into a clear, natural response for the user."
                },
                {
                    "role": "user",
                    "content": original_message
                },
                {
                    "role": "assistant",
                    "content": f"I'll help you with that. Let me use the available tools.",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"])
                            }
                        } for tc in tool_calls
                    ]
                }
            ]
            
            # Add tool results
            for i, result in enumerate(tool_results):
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                    "tool_call_id": tool_calls[i]["id"]
                })
            
            # Get formatted response
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error formatting tool results: {str(e)}")
            return self._simple_format_results(tool_results)
    
    def _simple_tool_detection(self, message: str, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple fallback tool detection when LLM is not available."""
        message_lower = message.lower()
        tool_calls = []
        
        # Check for calculator tool
        for tool in available_tools:
            if tool["name"] == "calculate":
                # Look for math expressions
                import re
                # Match patterns like "2+2", "10*5", "calculate 3+3"
                math_patterns = [
                    r'\b(\d+\s*[\+\-\*\/]\s*\d+(?:\s*[\+\-\*\/]\s*\d+)*)\b',
                    r'calculate\s+(.+)',
                    r'what is\s+(\d+\s*[\+\-\*\/].+)',
                ]
                
                for pattern in math_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        expression = match.group(1).strip()
                        tool_calls.append({
                            "id": f"call_{datetime.now().timestamp()}",
                            "name": "calculate",
                            "arguments": {"expression": expression}
                        })
                        break
        
        if tool_calls:
            return {
                "should_call_tools": True,
                "tool_calls": tool_calls,
                "reasoning": "Found a calculation request.",
                "suggested_response": None
            }
        
        return {
            "should_call_tools": False,
            "tool_calls": [],
            "reasoning": "No tools needed.",
            "suggested_response": None
        }
    
    def _simple_format_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """Simple formatting when LLM is not available."""
        if not tool_results:
            return "I couldn't get any results from the tools."
        
        responses = []
        for result in tool_results:
            if "error" in result:
                responses.append(f"Error: {result['error']}")
            elif "result" in result:
                responses.append(f"Result: {result['result']}")
            else:
                responses.append(str(result))
        
        return " ".join(responses)


# Global instance
llm_service = LLMService()