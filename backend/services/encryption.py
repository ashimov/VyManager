"""
Encryption Service

Provides symmetric encryption for sensitive data like API keys.
Uses Fernet (AES-128-CBC with HMAC) from the cryptography library.

IMPORTANT: Encryption is REQUIRED in production. The ENCRYPTION_KEY environment
variable must be set. Generate a key with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import os
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption operations fail."""
    pass


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.

    Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
    The encryption key should be a 32-byte URL-safe base64-encoded key.

    Environment variable: ENCRYPTION_KEY (REQUIRED in production)
    Generate a key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """

    def __init__(self, key: Optional[str] = None):
        """
        Initialize the encryption service.

        Args:
            key: Optional encryption key. If not provided, reads from ENCRYPTION_KEY env var.

        Raises:
            EncryptionError: If no encryption key is configured in production.
        """
        self._key = key or os.getenv("ENCRYPTION_KEY")
        self._cipher: Optional[Fernet] = None
        self._is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

        if self._key:
            try:
                self._cipher = Fernet(self._key.encode() if isinstance(self._key, str) else self._key)
                logger.info("Encryption service initialized successfully")
            except Exception as e:
                error_msg = f"Invalid ENCRYPTION_KEY format: {e}"
                logger.error(error_msg)
                if self._is_production:
                    raise EncryptionError(error_msg)
        elif self._is_production:
            raise EncryptionError(
                "ENCRYPTION_KEY environment variable is REQUIRED in production. "
                "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        else:
            logger.warning(
                "ENCRYPTION_KEY not set - running in development mode without encryption. "
                "This is NOT safe for production!"
            )

    @property
    def is_configured(self) -> bool:
        """Check if encryption is properly configured."""
        return self._cipher is not None

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Base64-encoded encrypted string.

        Raises:
            EncryptionError: If encryption is not configured in production.
        """
        if not self._cipher:
            if self._is_production:
                raise EncryptionError("Cannot store sensitive data without encryption in production")
            logger.warning("Encryption not configured - storing as plaintext (development only)")
            return plaintext

        encrypted = self._cipher.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: The encrypted string to decrypt.

        Returns:
            Decrypted plaintext string.

        Raises:
            EncryptionError: If decryption fails in production.
        """
        if not self._cipher:
            if self._is_production:
                raise EncryptionError("Cannot decrypt data without encryption key in production")
            logger.warning("Encryption not configured - returning data as-is (development only)")
            return ciphertext

        # Check if this looks like encrypted data (Fernet tokens start with 'gAAAAA')
        if not ciphertext.startswith('gAAAAA'):
            # Likely plaintext from before encryption was enabled
            if self._is_production:
                logger.error("Found unencrypted data in production - data migration required")
            else:
                logger.warning("Data appears to be plaintext (not encrypted)")
            return ciphertext

        try:
            decrypted = self._cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            if self._is_production:
                raise EncryptionError("Decryption failed - invalid token or wrong key")
            logger.warning("Decryption failed, returning as-is (may be plaintext)")
            return ciphertext
        except Exception as e:
            logger.error(f"Decryption error: {type(e).__name__}: {e}")
            if self._is_production:
                raise EncryptionError(f"Decryption failed: {e}")
            return ciphertext

    def is_encrypted(self, data: str) -> bool:
        """
        Check if data appears to be encrypted.

        Fernet tokens have a specific format starting with 'gAAAAA'.

        Args:
            data: The string to check.

        Returns:
            True if data appears to be encrypted.
        """
        return data.startswith('gAAAAA')

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.

        Returns:
            A new 32-byte URL-safe base64-encoded key.
        """
        return Fernet.generate_key().decode()


# Global singleton instance
encryption_service = EncryptionService()
