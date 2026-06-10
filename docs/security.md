# Security Architecture

Overview of the encryption and data integrity measures in TDrive.

## Local Encryption

TDrive uses local encryption to ensure that file contents are never visible to the storage provider (Telegram) or the database.

1.  **Key Derivation**: The Master Password is not stored. It is processed using **PBKDF2-HMAC-SHA256** (100,000 iterations) with a local salt to derive a 256-bit key.
2.  **Algorithm**: Files are encrypted with **AES-256-GCM**.
3.  **Local Processing**: Encryption and decryption happen on the local machine. Only encrypted data is sent to Telegram.

## Metadata Integrity

To prevent tampering with file metadata on Telegram, TDrive uses HMAC signatures.

- **HMAC-SHA256**: Metadata tags in Telegram message captions are signed using your Master Key.
- **Verification**: The agent verifies these signatures during index rebuilds.

## Transport & Access Security

- **Telegram MTProto**: Data transmission is protected by Telegram's encryption layer.
- **CSRF Protection**: The API requires CSRF tokens for state-changing requests (POST, PATCH, DELETE).
- **Rate Limiting**: Applied to API endpoints to prevent brute-force attacks.

## Data Recovery

If the local database is lost, you can recover data using:
1.  Access to the **Telegram Account**.
2.  The **Master Password**.

The metadata stored on Telegram allows the agent to reconstruct the file index.
