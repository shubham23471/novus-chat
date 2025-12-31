import pytest
import httpx
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.conversation_store import conversation_store
import asyncio
import concurrent.futures
from uuid import UUID


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_store():
    """Clear conversation store before each test"""
    conversation_store.clear()
    yield
    conversation_store.clear()


def test_single_message(client):
    """Test a single message works (debug test)"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "Hello"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "reply" in data


@pytest.mark.timeout(30)
def test_concurrent_messages_same_conversation(client):
    """Test that two simultaneous messages don't corrupt state"""
    
    # 1. Create a conversation
    response1 = client.post(
        "/api/v1/chat/message",
        json={"message": "Hello 1"}
    )
    assert response1.status_code == 200
    conversation_id = UUID(response1.json()["conversation_id"])  # Convert string to UUID
    print(f"Created conversation: {conversation_id}")
    
    # 2. Send two messages concurrently to same conversation
    def send_message(msg_text):
        print(f"Sending: {msg_text}")
        result = client.post(
            "/api/v1/chat/message",
            json={
                "conversation_id": str(conversation_id),  # Convert UUID to string for JSON
                "message": msg_text
            }
        )
        print(f"Received response for {msg_text}: {result.status_code}")
        return result
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(send_message, "Message 1")
        future2 = executor.submit(send_message, "Message 2")
        
        result1 = future1.result(timeout=30)
        result2 = future2.result(timeout=30)
    
    # 3. Verify both succeeded
    assert result1.status_code == 200
    assert result2.status_code == 200
    
    # 4. Verify conversation state is consistent
    conversation = conversation_store[conversation_id]
    
    # Should have: system message + initial "Hello 1" + response + message1 + response + message2 + response
    user_messages = [msg for msg in conversation if msg.role == "user"]
    assert len(user_messages) == 3, f"Expected 3 user messages, got {len(user_messages)}"
    
    # Verify no data loss
    user_texts = [msg.content for msg in user_messages]
    assert "Hello 1" in user_texts
    assert "Message 1" in user_texts
    assert "Message 2" in user_texts