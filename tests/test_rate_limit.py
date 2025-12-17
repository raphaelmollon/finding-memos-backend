"""
Test script to verify rate limiting is working
"""
import requests
import time

BASE_URL = "http://localhost:5000"

def test_rate_limit():
    print("Testing Rate Limiter")
    print("=" * 50)

    # Test sign-in endpoint (5 per minute)
    print("\n1. Testing /auth/sign-in (limit: 5 per minute)")
    print("-" * 50)

    for i in range(7):
        response = requests.post(
            f"{BASE_URL}/auth/sign-in",
            json={"email": "test@example.com", "password": "test123"}
        )

        print(f"Request {i+1}: Status {response.status_code}", end="")

        if response.status_code == 429:
            print(" - RATE LIMITED! ✓")
            print(f"  Response: {response.json()}")
            break
        elif response.status_code in [400, 401]:
            print(" - OK (auth failed as expected)")
        else:
            print(f" - {response.status_code}")

        time.sleep(0.5)  # Small delay between requests

    print("\n" + "=" * 50)
    print("\nIf you saw 'RATE LIMITED!' above, the limiter is working!")
    print("\nTo test other endpoints:")
    print("  - /auth/sign-up: 3 per hour")
    print("  - /auth/forgot-password: 3 per hour")
    print("  - /auth/reset-password: 10 per hour")

if __name__ == "__main__":
    try:
        test_rate_limit()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server.")
        print("Make sure the Flask app is running: python run.py")
    except Exception as e:
        print(f"ERROR: {e}")
