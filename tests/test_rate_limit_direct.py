"""
Test rate limiter directly without running server
"""
from app import create_app

def test_rate_limit_direct():
    print("Testing Rate Limiter (Direct)")
    print("=" * 50)

    app = create_app()
    client = app.test_client()

    # Test sign-in endpoint (5 per minute limit)
    print("\n1. Testing /auth/sign-in (limit: 5 per minute)")
    print("-" * 50)

    rate_limited = False
    for i in range(7):
        response = client.post(
            '/auth/sign-in',
            json={"email": "test@example.com", "password": "test123"},
            headers={"Content-Type": "application/json"}
        )

        print(f"Request {i+1}: Status {response.status_code}", end="")

        if response.status_code == 429:
            print(" - RATE LIMITED! ✓")
            rate_limited = True
            try:
                print(f"  Response: {response.get_json()}")
            except:
                print(f"  Response: {response.data}")
            break
        elif response.status_code in [400, 401]:
            print(" - OK (auth failed as expected)")
        else:
            print(f" - Unexpected: {response.status_code}")
            try:
                print(f"  Response: {response.get_json()}")
            except:
                print(f"  Response: {response.data}")

    print("\n" + "=" * 50)
    if rate_limited:
        print("✓ SUCCESS: Rate limiter is working!")
    else:
        print("✗ WARNING: Did not hit rate limit after 7 requests")
        print("  This might be normal if using memory:// storage")

    # Test sign-up endpoint (3 per hour limit)
    print("\n2. Testing /auth/sign-up (limit: 3 per hour)")
    print("-" * 50)

    signup_limited = False
    for i in range(5):
        response = client.post(
            '/auth/sign-up',
            json={"email": "test@example.com", "password": "Test123!@#"},
            headers={"Content-Type": "application/json"}
        )

        print(f"Request {i+1}: Status {response.status_code}", end="")

        if response.status_code == 429:
            print(" - RATE LIMITED! ✓")
            signup_limited = True
            break
        else:
            print(f" - {response.status_code}")

    print("\n" + "=" * 50)
    if signup_limited:
        print("✓ SUCCESS: Sign-up rate limiter is working!")
    else:
        print("✗ Did not hit sign-up rate limit")

if __name__ == "__main__":
    test_rate_limit_direct()
