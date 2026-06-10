# Background Jobs API

Monitor and manage asynchronous tasks like file uploads, downloads, and system maintenance.

## List Jobs

Retrieves a history of all background jobs.

- **Endpoint**: `GET /jobs`
- **Query Parameters**:
  - `status` (optional): Filter by `pending`, `running`, `completed`, or `failed`.
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": [
      {
        "job_id": "abc...",
        "type": "upload",
        "status": "running",
        "progress": 45.5,
        "total_size": 1048576,
        "current_size": 476928,
        "error": null,
        "created_at": "2026-06-06T12:00:00Z"
      }
    ]
  }
  ```

## Get Job Detail

Retrieves detailed information about a specific job.

- **Endpoint**: `GET /jobs/{job_id}`
- **Success Response (200 OK)**: Returns a single Job object.

## Clear Job History

Removes a job record from the database.

- **Endpoint**: `DELETE /jobs/{job_id}`
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": null
  }
  ```

## Job Types

1.  **upload**: Encrypting and sending file chunks to Telegram.
2.  **download**: Fetching and decrypting file chunks from Telegram.
3.  **rebuild**: Reconstructing the database from Telegram message history.
