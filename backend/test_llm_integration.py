#!/usr/bin/env python3
"""
Test script for LLM integration with MCP servers.

This script demonstrates how the LLM service processes messages and calls tools.
"""

import asyncio
import os
from typing import List, Dict, Any

# Ensure we can import from app
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import LLMService
from app.core.logging import logger


# Sample calculator tool definition (as returned by MCP server)
CALCULATOR_TOOLS = [
    {
        "name": "calculate",
        "description": "Perform basic arithmetic operations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')"
                }
            },
            "required": ["expression"]
        }
    }
]


async def test_llm_service():
    """Test the LLM service with various messages."""
    
    # Initialize service
    llm_service = LLMService()
    
    if not llm_service.enabled:
        logger.warning("LLM service not enabled. Set OPENAI_API_KEY to test with OpenAI.")
        logger.info("Testing with fallback pattern matching...")
    
    # Test messages
    test_messages = [
        "What is 2 + 2?",
        "Calculate 15 * 3",
        "Can you help me with 100 divided by 4?",
        "Hello, how are you?",
        "What's the result of 7 + 8 - 3?",
    ]
    
    logger.info("=" * 60)
    logger.info("Testing LLM Service Tool Detection")
    logger.info("=" * 60)
    
    for message in test_messages:
        logger.info(f"\nUser Message: {message}")
        
        # Process message with LLM
        result = await llm_service.process_message_with_tools(
            message=message,
            available_tools=CALCULATOR_TOOLS
        )
        
        logger.info(f"Should call tools: {result['should_call_tools']}")
        
        if result['should_call_tools']:
            logger.info(f"Tool calls: {result['tool_calls']}")
            logger.info(f"Reasoning: {result['reasoning']}")
            
            # Simulate tool execution
            tool_results = []
            for tool_call in result['tool_calls']:
                if tool_call['name'] == 'calculate':
                    expression = tool_call['arguments']['expression']
                    try:
                        # Simple evaluation for testing
                        calc_result = eval(expression)
                        tool_results.append({
                            "result": str(calc_result),
                            "expression": expression
                        })
                        logger.info(f"Tool result: {expression} = {calc_result}")
                    except Exception as e:
                        tool_results.append({
                            "error": str(e)
                        })
            
            # Format the response
            if tool_results:
                formatted_response = await llm_service.format_tool_results(
                    original_message=message,
                    tool_calls=result['tool_calls'],
                    tool_results=tool_results
                )
                logger.info(f"Formatted response: {formatted_response}")
        else:
            logger.info(f"Reasoning: {result['reasoning']}")
            if result.get('suggested_response'):
                logger.info(f"Suggested response: {result['suggested_response']}")
        
        logger.info("-" * 40)


async def test_complex_conversations():
    """Test with conversation history."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing with Conversation History")
    logger.info("=" * 60)
    
    llm_service = LLMService()
    
    conversation_history = [
        {"role": "user", "content": "I need help with some calculations"},
        {"role": "assistant", "content": "I'd be happy to help you with calculations! What would you like me to compute?"},
        {"role": "user", "content": "First, what's 50 + 30?"},
        {"role": "assistant", "content": "50 + 30 = 80"},
    ]
    
    new_message = "Now multiply that result by 2"
    
    logger.info("Conversation history provided")
    logger.info(f"New message: {new_message}")
    
    result = await llm_service.process_message_with_tools(
        message=new_message,
        available_tools=CALCULATOR_TOOLS,
        conversation_history=conversation_history
    )
    
    logger.info(f"\nResult: {result}")


async def main():
    """Run all tests."""
    await test_llm_service()
    await test_complex_conversations()


if __name__ == "__main__":
    # Set up basic logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())