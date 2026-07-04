from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_demo_flow():
    print("Testing /auth/demo...")
    response = client.get("/auth/demo", follow_redirects=False)
    print(f"Status Code: {response.status_code}")
    print(f"Redirect URL: {response.headers.get('location')}")
    
    assert response.status_code == 303
    assert response.headers['location'] == "/dashboard"
    
    print("\nTesting /dashboard (after login)...")
    # In TestClient, cookies/session might not persist automatically if using global dict in memory 
    # because TestClient runs in the same process.
    # Let's check if the global dict was updated.
    from app.routers.auth import user_sessions
    print(f"Session Data: {user_sessions}")
    
    response = client.get("/dashboard")
    print(f"Dashboard Status: {response.status_code}")
    if "Demo Mode" in response.text or "DEMO MODE" in response.text:
        print("SUCCESS: Dashboard loaded in Demo Mode")
    elif "Please login first" in response.text:
        print("FAILED: Dashboard asks for login")
    else:
        print("UNKNOWN: Check response content")

if __name__ == "__main__":
    try:
        test_demo_flow()
    except Exception as e:
        print(f"ERROR: {e}")
