"""
Test MCP session archiving functionality.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings


def test_archive_session(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test archiving an MCP session."""
    # First create a server
    server_data = {
        "name": "Test Archive Server",
        "description": "Test server for archiving",
        "server_type": "stdio",
        "connection_config": {"command": "echo", "args": ["test"]},
        "is_public": False,
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/mcp/servers",
        headers=superuser_token_headers,
        json=server_data,
    )
    assert response.status_code == 200
    server = response.json()
    
    # Create a session
    session_data = {
        "server_id": server["id"],
        "title": "Test Session for Archiving",
        "context": {"test": "data"},
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/mcp/sessions",
        headers=superuser_token_headers,
        json=session_data,
    )
    assert response.status_code == 200
    session = response.json()
    session_id = session["id"]
    
    # Verify session is not archived initially
    assert session["archived"] is False
    assert session["archived_at"] is None
    
    # Archive the session
    response = client.put(
        f"{settings.API_V1_STR}/mcp/sessions/{session_id}/archive",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Session archived successfully"
    
    # Verify session is archived
    response = client.get(
        f"{settings.API_V1_STR}/mcp/sessions/{session_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    archived_session = response.json()
    assert archived_session["archived"] is True
    assert archived_session["archived_at"] is not None
    
    # Try to archive again (should fail)
    response = client.put(
        f"{settings.API_V1_STR}/mcp/sessions/{session_id}/archive",
        headers=superuser_token_headers,
    )
    assert response.status_code == 400
    assert "already be archived" in response.json()["detail"]


def test_unarchive_session(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test unarchiving an MCP session."""
    # First create and archive a session
    server_data = {
        "name": "Test Unarchive Server",
        "description": "Test server for unarchiving",
        "server_type": "stdio",
        "connection_config": {"command": "echo", "args": ["test"]},
        "is_public": False,
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/mcp/servers",
        headers=superuser_token_headers,
        json=server_data,
    )
    assert response.status_code == 200
    server = response.json()
    
    # Create a session
    session_data = {
        "server_id": server["id"],
        "title": "Test Session for Unarchiving",
        "context": {"test": "data"},
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/mcp/sessions",
        headers=superuser_token_headers,
        json=session_data,
    )
    assert response.status_code == 200
    session = response.json()
    session_id = session["id"]
    
    # Archive the session
    response = client.put(
        f"{settings.API_V1_STR}/mcp/sessions/{session_id}/archive",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    
    # Unarchive the session
    response = client.put(
        f"{settings.API_V1_STR}/mcp/sessions/{session_id}/unarchive",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Session unarchived successfully"
    
    # Verify session is unarchived
    response = client.get(
        f"{settings.API_V1_STR}/mcp/sessions/{session_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    unarchived_session = response.json()
    assert unarchived_session["archived"] is False
    assert unarchived_session["archived_at"] is None
    
    # Try to unarchive again (should fail)
    response = client.put(
        f"{settings.API_V1_STR}/mcp/sessions/{session_id}/unarchive",
        headers=superuser_token_headers,
    )
    assert response.status_code == 400
    assert "not be archived" in response.json()["detail"]


def test_filter_archived_sessions(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test filtering sessions by archived status."""
    # Create a server
    server_data = {
        "name": "Test Filter Server",
        "description": "Test server for filtering",
        "server_type": "stdio",
        "connection_config": {"command": "echo", "args": ["test"]},
        "is_public": False,
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/mcp/servers",
        headers=superuser_token_headers,
        json=server_data,
    )
    assert response.status_code == 200
    server = response.json()
    server_id = server["id"]
    
    # Create multiple sessions
    session_ids = []
    for i in range(3):
        session_data = {
            "server_id": server_id,
            "title": f"Test Session {i}",
            "context": {"index": i},
        }
        
        response = client.post(
            f"{settings.API_V1_STR}/mcp/sessions",
            headers=superuser_token_headers,
            json=session_data,
        )
        assert response.status_code == 200
        session_ids.append(response.json()["id"])
    
    # Archive first two sessions
    for session_id in session_ids[:2]:
        response = client.put(
            f"{settings.API_V1_STR}/mcp/sessions/{session_id}/archive",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
    
    # Get non-archived sessions (default)
    response = client.get(
        f"{settings.API_V1_STR}/mcp/sessions",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    active_sessions = response.json()
    assert len(active_sessions) >= 1
    assert all(not s["archived"] for s in active_sessions)
    
    # Get archived sessions
    response = client.get(
        f"{settings.API_V1_STR}/mcp/sessions?archived=true",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    archived_sessions = response.json()
    assert len(archived_sessions) >= 2
    assert all(s["archived"] for s in archived_sessions)


def test_archive_session_permissions(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    """Test archiving permissions for non-owner."""
    # Create a server as superuser
    server_data = {
        "name": "Test Permissions Server",
        "description": "Test server for permissions",
        "server_type": "stdio",
        "connection_config": {"command": "echo", "args": ["test"]},
        "is_public": True,
    }
    
    # Login as superuser to create server
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    superuser_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    response = client.post(
        f"{settings.API_V1_STR}/mcp/servers",
        headers=superuser_headers,
        json=server_data,
    )
    assert response.status_code == 200
    server = response.json()
    
    # Create a session as superuser
    session_data = {
        "server_id": server["id"],
        "title": "Superuser Session",
        "context": {},
    }
    
    response = client.post(
        f"{settings.API_V1_STR}/mcp/sessions",
        headers=superuser_headers,
        json=session_data,
    )
    assert response.status_code == 200
    session_id = response.json()["id"]
    
    # Try to archive as normal user (should fail)
    response = client.put(
        f"{settings.API_V1_STR}/mcp/sessions/{session_id}/archive",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
    assert "permissions" in response.json()["detail"].lower()