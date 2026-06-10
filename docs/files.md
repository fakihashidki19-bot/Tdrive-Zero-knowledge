# File Management API

Manage files, folders, and transfers within the TDrive virtual filesystem.

## List Items

Retrieves a list of files and folders in a specific virtual path.

- **Endpoint**: `GET /files`
- **Query Parameters**:
  - `path` (optional): The virtual directory to list (default: `/`).
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": [
      {
        "file_id": "sha256_hash",
        "filename": "document.pdf",
        "virtual_path": "/",
        "size": 1048576,
        "is_folder": false,
        "thumbnail": "base64_string_if_image",
        "status": "completed",
        "created_at": "2026-06-06T12:00:00Z"
      }
    ]
  }
  ```

## Upload File

Initiates an asynchronous upload job. Files are buffered to disk locally before being encrypted and sent to Telegram.

- **Endpoint**: `POST /files/upload`
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  - `file`: The binary file data.
  - `vpath`: The target virtual path (e.g., `/Work/Projects`).
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": "job_id_hex"
  }
  ```
- **Note**: Monitor progress using the [Jobs API](./jobs.md).

## Create Folder

Creates a new virtual folder entry in the database.

- **Endpoint**: `POST /files/folder`
- **Request Body**:
  ```json
  {
    "name": "New Folder",
    "vpath": "/"
  }
  ```
- **Success Response (200 OK)**: Returns the created Folder object.

## Create Download Ticket

Generates a short-lived (5-minute) one-time ticket for file streaming. This protects direct download URLs.

- **Endpoint**: `POST /files/{file_id}/ticket`
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": {
      "ticket": "uuid_v4_ticket",
      "expires_in": 300
    }
  }
  ```

## Rename Item

Updates the filename or folder name.

- **Endpoint**: `PATCH /files/{file_id}`
- **Query Parameters**:
  - `new_name`: The new name for the item.
- **Success Response (200 OK)**: Returns the updated Item object.

## Delete Item

Permanently removes a file or folder. For files, all associated chunks are deleted from Telegram.

- **Endpoint**: `DELETE /files/{file_id}`
- **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": {
      "file_id": "abc123",
      "deleted_chunks": 12
    }
  }
  ```
