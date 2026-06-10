# TDrive API Documentation

Technical documentation for the TDrive API and system components. TDrive uses a Telegram backend for storage with local encryption.

## API Architecture

The API is built using **FastAPI (Python 3.12)**. It acts as a bridge between the web dashboard and the Telegram MTProto backend.

### Core Principles
- **Local Encryption**: Encryption and decryption occur locally. Master passwords are not stored on the server.
- **Asynchronous Tasks**: Large transfers are handled in the background with progress tracking.
- **Security**: Includes CSRF protection and HMAC-signed metadata.

## Table of Contents

1. [Authentication](./authentication.md) - Login and session security.
2. [File Management](./files.md) - Browsing, uploads, and file operations.
3. [Background Jobs](./jobs.md) - Tracking transfer tasks.
4. [System Operations](./system.md) - Health checks and maintenance.
5. [Developer Mode](./developer.md) - Diagnostic and monitoring tools.
6. [Security Architecture](./security.md) - Encryption and integrity details.
7. [Integrity Guard](./integrity.md) - Environment protection.
8. [Windows Setup](./windows_setup.md) - Installation on Windows.

## Base URL
`http://localhost:8000/api/v1`

## Response Format
Standard JSON structure:
```json
{
  "success": true,
  "data": { ... }
}
```
