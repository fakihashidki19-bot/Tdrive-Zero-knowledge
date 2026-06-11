# TDrive (Telegram Drive)

TDrive is a personal cloud storage system that utilizes Telegram Private Channels as a storage backend. It provides a self-hosted alternative to traditional cloud storage providers by leveraging Telegram's MTProto protocol for data transmission and AES-256-GCM for local data encryption.

![TDrive Dashboard](screenshot/For-readme-md.png)

## Features

- **Encrypted Storage**: Files are encrypted locally using AES-256-GCM before being transmitted to Telegram. Encryption keys are derived from your Master Password and never leave your local environment.
- **Streaming Support**: TDrive supports the upload and download of large files without exhausting system memory, using a chunk-based streaming pipeline.
- **Task Management**: A background task system manages file transfers with real-time progress tracking and error handling.
- **Index Recovery**: The system can reconstruct its metadata database by scanning the Telegram channel history, using signed metadata tags embedded in message captions.
- **Unified Interface**: Modern Web Dashboard built with Next.js, a Command Line Interface (CLI) for administrative tasks, and a **Telegram Bot Interface** for remote file access.
- **Security & Integrity**: Includes CSRF protection, rate limiting, and the **Repository Integrity Guard** (Instance Fingerprinting) to prevent unauthorized modifications in unknown environments.
- **Automated Maintenance**: Background workers handle trash purging, preview cache cleaning, and metadata healing.

## Technical Architecture

- **Backend**: Python 3.12+, FastAPI, Telethon (MTProto), SQLAlchemy (SQLite).
- **Frontend**: Next.js 14 (App Router), TanStack Query, Zustand, TailwindCSS.
- **Deployment**: Supports systemd services and Docker Compose.

## Documentation

Detailed documentation is available in the `docs/` directory:
- [Security Architecture](docs/security.md)
- [Repository Integrity Guard](docs/integrity.md)
- [Windows Setup Guide](docs/windows_setup.md)
- [CLI Reference](docs/cli.md)
- [API Documentation](docs/README.md)

## Installation and Configuration

### 1. Prerequisites
- **Python**: Version 3.12 or higher.
- **Node.js**: Version 20.x or higher.
- **Telegram API**: Obtain `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org).
- **Storage Channel**: Create a **Private Channel** in Telegram and get its ID (e.g., `-100...`).

### 2. Backend Setup
Clone the repository and initialize the environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Initialize configuration:
```bash
python3 -m cli.main init init-cmd
```

Authenticate with Telegram:
```bash
python3 -m cli.main login login-cmd
```

### 3. Frontend Setup
```bash
cd web
npm install
npm run build
```

### 4. Deployment (Linux)
```bash
sudo ./scripts/finalize.sh
```

## Usage

### Accessing the Dashboard
The dashboard is accessible via `http://localhost:3000`.

### Security Best Practices
- **Master Password**: Keep your Master Password safe. If lost, your encrypted data on Telegram cannot be recovered.
- **Private Channel**: Keep your storage channel **Private**. Do not set it to "Public" as it will expose your data.
- **Access Control**: Use a secure tunnel (like Tailscale or Cloudflare) if exposing the dashboard to the internet.

## Fuel the Engine

TDrive is open-source and free, but my coffee machine is neither. If this project has made your life easier (or at least more interesting), feel free to support the ongoing development:

[**Fuel the Project via Saweria**](https://saweria.co/dimasla)

*P.S. Donating won't technically make me a better coder, but it will definitely reduce the number of 'fixed stuff' commit messages.*

## License

This project is licensed under the MIT License.
