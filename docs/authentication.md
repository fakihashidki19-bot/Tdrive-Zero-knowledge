# Authentication API

TDrive uses a dual-token authentication system to ensure both session validity and protection against Cross-Site Request Forgery (CSRF).

## Login

Validates the Master Password and initiates a secure session.

- **Endpoint**: `POST /auth/login`
- **Authentication**: None required.
- **Request Body**:
  ```json
  {
    "password": "your_master_password"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": {
      "access_token": "dynamic_session_token",
      "csrf_token": "random_csrf_token",
      "token_type": "bearer"
    }
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: Invalid master password.
  - `429 Too Many Requests`: Triggered after 3 failed attempts (Progressive lockout).

## Logout

Terminates the current session and clears server-side memory for the session.

- **Endpoint**: `POST /auth/logout`
- **Authentication**: Bearer Token required.
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": null
  }
  ```

## Session Security

### Session Token (JWT-like)
The `access_token` must be included in the `Authorization` header for all protected endpoints:
`Authorization: Bearer <access_token>`

### CSRF Protection
The `csrf_token` must be included in the `X-CSRF-Token` header for all state-changing requests (POST, PATCH, DELETE):
`X-CSRF-Token: <csrf_token>`

### Brute Force Protection
The API implements a progressive lockout strategy:
1. **3 Fails**: 5-second delay.
2. **5 Fails**: 30-second delay.
3. **10 Fails**: 10-minute complete lockout.
