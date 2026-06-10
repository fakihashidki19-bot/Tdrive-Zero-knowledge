# System Operations API

Administrative tasks and health monitoring for the TDrive Agent.

## System Status

Returns the current operational health of the agent and its connections.

- **Endpoint**: `GET /system/status`
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": {
      "telegram_connected": true,
      "sqlite_healthy": true,
      "session_valid": true,
      "config_exists": true,
      "channel_accessible": true
    }
  }
  ```

## Rebuild Index

Triggers a full scan of the Telegram storage channel to reconstruct the local metadata database. This is a critical recovery feature.

- **Endpoint**: `POST /system/rebuild`
- **Query Parameters**:
  - `full` (boolean): Whether to perform a full scan (default: `false`).
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": {
      "scanned_messages": 150,
      "recovered_chunks": 12,
      "status": "completed"
    }
  }
  ```

## Audit Integrity

Scans the local database against the remote Telegram channel to find missing chunks or inconsistencies.

- **Endpoint**: `GET /system/audit`
- **Success Response (200 OK)**: Returns a summary report of database-remote consistency.

## Maintenance Cleanup

Performs housekeeping by deleting orphaned file chunks from Telegram and purging old temporary local files.

- **Endpoint**: `POST /system/cleanup`
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": {
      "deleted_count": 5
    }
  }
  ```
