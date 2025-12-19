import pytest
import time
from app.services.token_service import token_service


class TestTokenService:
    """Test token service."""

    def test_generate_reset_token(self, app):
        """Test generating reset token."""
        with app.app_context():
            token = token_service.generate_reset_token(user_id=1)
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 0

    def test_validate_reset_token_valid(self, app):
        """Test validating a valid reset token."""
        with app.app_context():
            user_id = 123
            token = token_service.generate_reset_token(user_id)

            # Validate immediately
            validated_id = token_service.validate_reset_token(token)
            assert validated_id == user_id

    def test_validate_reset_token_expired(self, app):
        """Test validating an expired reset token."""
        import time
        with app.app_context():
            user_id = 123
            token = token_service.generate_reset_token(user_id)

            # Wait for token to be old enough
            time.sleep(2)
            # Validate with max_age shorter than token age
            validated_id = token_service.validate_reset_token(token, max_age=1)
            assert validated_id is None

    def test_validate_reset_token_invalid(self, app):
        """Test validating an invalid reset token."""
        with app.app_context():
            validated_id = token_service.validate_reset_token('invalid-token')
            assert validated_id is None

    def test_generate_signup_token(self, app):
        """Test generating signup token."""
        with app.app_context():
            token = token_service.generate_signup_token(user_id=1)
            assert token is not None
            assert isinstance(token, str)
            assert len(token) > 0

    def test_validate_signup_token_valid(self, app):
        """Test validating a valid signup token."""
        with app.app_context():
            user_id = 456
            token = token_service.generate_signup_token(user_id)

            # Validate immediately
            validated_id = token_service.validate_signup_token(token)
            assert validated_id == user_id

    def test_validate_signup_token_expired(self, app):
        """Test validating an expired signup token."""
        import time
        with app.app_context():
            user_id = 456
            token = token_service.generate_signup_token(user_id)

            # Wait for token to be old enough
            time.sleep(2)
            # Validate with max_age shorter than token age
            validated_id = token_service.validate_signup_token(token, max_age=1)
            assert validated_id is None

    def test_validate_signup_token_invalid(self, app):
        """Test validating an invalid signup token."""
        with app.app_context():
            validated_id = token_service.validate_signup_token('invalid-token')
            assert validated_id is None

    def test_hash_token(self, app):
        """Test hashing a token."""
        with app.app_context():
            token = 'test-token-123'
            hashed = token_service.hash_token(token)

            assert hashed is not None
            assert isinstance(hashed, str)
            assert len(hashed) == 64  # SHA256 produces 64 character hex string
            assert hashed != token  # Hash should be different from original

    def test_hash_token_consistency(self, app):
        """Test that hashing the same token produces the same hash."""
        with app.app_context():
            token = 'test-token-123'
            hash1 = token_service.hash_token(token)
            hash2 = token_service.hash_token(token)

            assert hash1 == hash2

    def test_hash_token_different_tokens(self, app):
        """Test that different tokens produce different hashes."""
        with app.app_context():
            token1 = 'test-token-123'
            token2 = 'test-token-456'
            hash1 = token_service.hash_token(token1)
            hash2 = token_service.hash_token(token2)

            assert hash1 != hash2

    def test_reset_and_signup_tokens_different_salts(self, app):
        """Test that reset and signup tokens use different salts."""
        with app.app_context():
            user_id = 789
            reset_token = token_service.generate_reset_token(user_id)
            signup_token = token_service.generate_signup_token(user_id)

            # Reset token should not validate as signup token
            assert token_service.validate_signup_token(reset_token) is None
            # Signup token should not validate as reset token
            assert token_service.validate_reset_token(signup_token) is None

    def test_token_contains_user_id(self, app):
        """Test that different user IDs produce different tokens."""
        with app.app_context():
            token1 = token_service.generate_reset_token(1)
            token2 = token_service.generate_reset_token(2)

            assert token1 != token2
            assert token_service.validate_reset_token(token1) == 1
            assert token_service.validate_reset_token(token2) == 2
