"""
Test endpoints for MCP WebSocket functionality.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()


@router.get("/test", response_class=HTMLResponse)
async def mcp_test_page():
    """
    Serve the MCP WebSocket test page.
    
    Access at: http://localhost:8000/api/v1/mcp/test
    """
    # Read the HTML file
    html_path = Path(__file__).parent.parent.parent.parent / "test_websocket.html"
    
    if html_path.exists():
        with open(html_path, "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse(content="<h1>Test page not found</h1>", status_code=404)