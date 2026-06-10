# Developer Mode

Tools for system diagnostics, monitoring, and maintenance.

## Overview

Developer Mode provides access to internal state information and real-time logs. It is intended for troubleshooting and performance auditing.

### Key Features
- **System Metrics**: Monitor CPU and RAM usage of the agent.
- **Log Viewer**: Access recent logs directly from the dashboard.
- **Database Tools**: Monitor database size and perform maintenance like VACUUM.
- **Telegram Connection**: Verify connectivity and channel access.

---

## Security Model

Developer Mode is **disabled by default**.

1.  **Isolation**: API endpoints under `/api/v1/developer` are restricted if `developer_mode` is false in the configuration.
2.  **Sensitive Data**: Diagnostic tools do not expose master passwords or encryption keys.

---

## Configuration

### Enabling via Dashboard
Go to **Settings** > **Administrative Utilities** and click **Enable Console**.

### Enabling via Config File
Edit `~/.tdrive/config.json`:
```json
{
    "developer_mode": true
}
```
*A restart of the `tdrive-agent` may be required.*
