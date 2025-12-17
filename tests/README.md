# Finding Memo - Tests

## Available Tests

### Rate Limiter Tests

**test_rate_limit.py** - Tests rate limiting with a running server
```bash
# Start the server first
python run.py

# Then in another terminal
python tests/test_rate_limit.py
```

**test_rate_limit_direct.py** - Tests rate limiting directly without running server
```bash
python tests/test_rate_limit_direct.py
```

## Expected Results

When rate limiting is working correctly, you should see:
- First N requests succeed (or fail with auth errors, which is expected)
- Request N+1 returns HTTP 429 "Too Many Requests"

## Rate Limits

- `/auth/sign-in`: 5 per minute
- `/auth/sign-up`: 3 per hour
- `/auth/forgot-password`: 3 per hour
- `/auth/reset-password`: 10 per hour
- `/auth/resend-validation`: 3 per hour
- Global default: 200 per day, 50 per hour
