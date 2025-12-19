# Finding Memo - Test Suite

Comprehensive test suite for the Finding Memo backend application.

## Overview

This test suite provides extensive coverage for:
- Models (User, Memo, Category, Type, Config)
- Routes (Auth, Memos, Users, Categories, Types)
- Services (Token, Email, Avatar)
- Helpers and Middleware
- Integration workflows

## Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

This will install pytest and pytest-cov along with all application dependencies.

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Model tests
pytest tests/test_models.py

# Authentication tests
pytest tests/test_auth_routes.py

# Memo tests
pytest tests/test_memo_routes.py

# User tests
pytest tests/test_user_routes.py

# Service tests
pytest tests/test_services.py

# Helper tests
pytest tests/test_helpers.py

# Middleware tests
pytest tests/test_middleware.py

# Integration tests
pytest tests/test_integration.py
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/test_models.py::TestUserModel

# Run a specific test function
pytest tests/test_auth_routes.py::TestSignIn::test_sign_in_success

# Run tests matching a pattern
pytest -k "password"
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View coverage in terminal
pytest --cov=app --cov-report=term-missing

# Generate XML coverage report (for CI/CD)
pytest --cov=app --cov-report=xml
```

### Run with Verbose Output

```bash
pytest -v
pytest -vv  # Extra verbose
```

## Test Structure

### Unit Tests

#### test_models.py
Tests for database models:
- **TestUserModel**: User creation, to_dict, preferences management
- **TestMemoModel**: Memo creation, relationships, to_dict
- **TestCategoryModel**: Category creation and uniqueness
- **TestTypeModel**: Type creation and uniqueness
- **TestConfigModel**: Configuration management

#### test_helpers.py
Tests for helper functions:
- **TestGetOrCreateHelpers**: Category and type creation/retrieval
- **TestCleanupHelpers**: Cleanup of unused categories and types
- **TestValidatePassword**: Password validation rules

#### test_services.py
Tests for service layer:
- **TestTokenService**: Token generation, validation, and hashing for password reset and email validation

#### test_middleware.py
Tests for middleware:
- **TestAuthRequired**: Authentication decorator behavior
- **TestGetAuthConfig**: Configuration caching
- **TestSessionTimeout**: Session timeout functionality
- **TestCorsHeaders**: CORS header validation

### Route Tests

#### test_auth_routes.py
Tests for authentication endpoints:
- **TestSignIn**: Login functionality, validation, error handling
- **TestSignUp**: Registration, domain validation, duplicate handling
- **TestSignOut**: Logout functionality
- **TestForgotPassword**: Password reset request
- **TestResetPassword**: Password reset with token
- **TestSessionCheck**: Session validation
- **TestValidateEmail**: Email validation workflow
- **TestResendValidation**: Resending validation emails
- **TestToggleAuth**: Authentication toggle (superuser only)

#### test_memo_routes.py
Tests for memo endpoints:
- **TestMemoList**: Getting all memos
- **TestCreateMemo**: Creating memos with categories and types
- **TestUpdateMemo**: Updating memos, category changes
- **TestDeleteMemo**: Deleting memos, cleanup, permissions
- **TestBulkImport**: Bulk memo import
- **TestMemoStats**: Memo statistics

#### test_user_routes.py
Tests for user endpoints:
- **TestCurrentUser**: Profile management, password changes, account deletion
- **TestUserPreferences**: Preferences CRUD operations
- **TestUserList**: Listing users (superuser)
- **TestUserResource**: User management by ID
- **TestAvatars**: Avatar listing
- **TestAdminResetPassword**: Admin password reset

### Integration Tests

#### test_integration.py
End-to-end workflow tests:
- **TestUserSignupFlow**: Complete signup -> validation -> login flow
- **TestPasswordResetFlow**: Complete password reset workflow
- **TestMemoLifecycle**: Create -> Read -> Update -> Delete workflow
- **TestUserProfile**: Profile and preferences management workflow
- **TestAuthenticationStates**: Authentication toggle workflow
- **TestBulkOperations**: Bulk operations testing
- **TestSessionManagement**: Session persistence across requests
- **TestErrorHandling**: Error handling across the application

### Rate Limiter Tests (Legacy)

#### test_rate_limit.py
Tests rate limiting with a running server:
```bash
# Start the server first
python run.py

# Then in another terminal
python tests/test_rate_limit.py
```

#### test_rate_limit_direct.py
Tests rate limiting directly without running server:
```bash
python tests/test_rate_limit_direct.py
```

## Fixtures

The test suite uses pytest fixtures defined in `conftest.py`:

### Application Fixtures
- `app`: Test Flask application with temporary database
- `client`: Test client for making requests
- `db_session`: Clean database session for each test

### User Fixtures
- `test_user`: Regular validated user
- `superuser`: Superuser account
- `new_user`: Unvalidated user (NEW status)

### Data Fixtures
- `test_category`: Sample category
- `test_type`: Sample type
- `test_memo`: Sample memo with all relationships

### Client Fixtures
- `authenticated_client`: Client with authenticated session
- `superuser_client`: Client authenticated as superuser

### Configuration Fixtures
- `disable_auth`: Temporarily disable authentication

## Expected Test Coverage

The test suite aims for comprehensive coverage:
- **Models**: 90%+ coverage
- **Routes**: 85%+ coverage
- **Services**: 90%+ coverage
- **Helpers**: 95%+ coverage
- **Integration**: Key workflows covered

## Rate Limits (for manual testing)

When testing rate limiting functionality:
- `/auth/sign-in`: 5 per minute
- `/auth/sign-up`: 3 per hour
- `/auth/forgot-password`: 3 per hour
- `/auth/reset-password`: 10 per hour
- `/auth/resend-validation`: 3 per hour
- Global default: 200 per day, 50 per hour

## Continuous Integration

For CI/CD pipelines:

```bash
# Run tests with coverage and generate XML report
pytest --cov=app --cov-report=xml --cov-report=term

# Return exit code based on minimum coverage (e.g., 80%)
pytest --cov=app --cov-fail-under=80
```

## Troubleshooting

### Tests Failing Due to Email Service
Some tests may fail if email service is not configured. This is expected in test environments. Tests handle this gracefully by checking for 200 or 500 status codes where email sending is involved.

### Database Issues
Tests use a temporary SQLite database that is created and destroyed for each test session. If you encounter database errors, ensure:
- You have write permissions in the test directory
- No stale database files exist

### Session Issues
If tests fail due to session management:
- Ensure Flask's SECRET_KEY is set (handled automatically in tests)
- Check that session cookie settings are correct

## Contributing

When adding new features:
1. Add unit tests for new models, helpers, or services
2. Add route tests for new endpoints
3. Add integration tests for new workflows
4. Ensure test coverage remains above 80%
5. Run the full test suite before committing

## Test Best Practices

- **Isolation**: Each test is independent and doesn't rely on others
- **Cleanup**: Database is cleaned between tests via fixtures
- **Clarity**: Test names clearly describe what is being tested
- **Coverage**: Both happy paths and error cases are tested
- **Speed**: Unit tests are fast; integration tests are marked appropriately
