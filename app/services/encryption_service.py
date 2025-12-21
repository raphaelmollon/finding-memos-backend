"""
Encryption/Decryption Service for Connections Data

This service handles decryption of connection data using AES-256-GCM.
The encryption key is stored in the Config table.

Based on the encryption methodology from external_resources/decrypt_connections.py
"""

import base64
import logging
from Crypto.Cipher import AES
from app.models import Config
from app.database import db


class EncryptionService:
    """Service for encrypting and decrypting connection data"""

    def __init__(self):
        self._key_cache = None

    def get_encryption_key(self):
        """
        Get the encryption key from the Config table

        Returns:
            bytes: 32-byte encryption key, or None if not set
        """
        # Use cached key if available
        if self._key_cache:
            return self._key_cache

        # Fetch from database (Config is singleton, id=1)
        config = Config.query.filter_by(id=1).first()

        if not config or not config.encryption_key:
            logging.warning("Encryption key not found in Config table")
            return None

        try:
            # Convert hex string to bytes
            key = bytes.fromhex(config.encryption_key)

            if len(key) != 32:
                logging.error(f"Invalid encryption key length: {len(key)} bytes (expected 32)")
                return None

            # Cache the key
            self._key_cache = key
            return key

        except ValueError as e:
            logging.error(f"Invalid encryption key format in Config: {e}")
            return None

    def set_encryption_key(self, key_hex):
        """
        Set the encryption key in the Config table

        Args:
            key_hex (str): 64-character hex string (32 bytes)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate key format
            key = bytes.fromhex(key_hex)
            if len(key) != 32:
                logging.error(f"Invalid encryption key length: {len(key)} bytes (expected 32)")
                return False

            # Get or create Config (singleton, id=1)
            config = Config.query.filter_by(id=1).first()

            if not config:
                config = Config(id=1, enable_auth=True, allowed_domains='["example.com"]')
                db.session.add(config)

            config.encryption_key = key_hex
            db.session.commit()

            # Clear cache to force reload
            self._key_cache = None

            logging.info("Encryption key updated successfully")
            return True

        except ValueError as e:
            logging.error(f"Invalid hex key format: {e}")
            return False
        except Exception as e:
            logging.error(f"Error setting encryption key: {e}")
            db.session.rollback()
            return False

    def decrypt_field(self, encrypted_data, context=None):
        """
        Decrypt a field using AES-256-GCM (authenticated decryption)

        Args:
            encrypted_data (str): Base64-encoded encrypted data (nonce + ciphertext + tag)
            context (str, optional): Additional authenticated data (field name as AAD)

        Returns:
            str: Decrypted string, or None if input is None/empty or decryption fails
        """
        if encrypted_data is None or encrypted_data == "":
            return None

        key = self.get_encryption_key()
        if not key:
            logging.error("Cannot decrypt: encryption key not available")
            return None

        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_data)

            # Extract nonce (first 12 bytes), tag (last 16 bytes), and ciphertext (middle)
            nonce = combined[:12]
            tag = combined[-16:]
            ciphertext = combined[12:-16]

            # Create cipher with GCM mode
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

            # Add AAD (Additional Authenticated Data) if provided
            # Must match the context used during encryption (field name)
            if context:
                cipher.update(context.encode('utf-8'))

            # Decrypt and verify authentication tag
            decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)

            # Decode to string
            decrypted_str = decrypted_bytes.decode('utf-8')

            return decrypted_str

        except ValueError as e:
            # Authentication failed - data has been tampered with or wrong context
            logging.error(f"Decryption authentication failed for context '{context}': {e}")
            return None
        except Exception as e:
            logging.error(f"Error decrypting data: {e}")
            return None

    def decrypt_connection(self, connection_dict):
        """
        Decrypt all encrypted fields in a connection dictionary

        Args:
            connection_dict (dict): Connection data with encrypted fields

        Returns:
            dict: Connection data with decrypted fields
        """
        # Fields that need decryption with their AAD context
        encrypted_fields = {
            'comments': 'comments',
            'server_ip': 'ip',
            'url_type': 'url_type',
            'url': 'url',
            'user': 'user',
            'pwd': 'pwd'
        }

        decrypted = connection_dict.copy()

        for field_name, context in encrypted_fields.items():
            if field_name in decrypted and decrypted[field_name]:
                decrypted[field_name] = self.decrypt_field(decrypted[field_name], context=context)

        # Handle comment_urls array
        if 'comment_urls' in decrypted and isinstance(decrypted['comment_urls'], list):
            decrypted['comment_urls'] = [
                self.decrypt_field(url, context='comment_urls') if isinstance(url, str) else url
                for url in decrypted['comment_urls']
            ]

        return decrypted

    def clear_key_cache(self):
        """Clear the cached encryption key (useful after key updates)"""
        self._key_cache = None


# Global instance
encryption_service = EncryptionService()
