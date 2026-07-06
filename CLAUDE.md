# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Cross-repo system map lives in `~/.claude/CLAUDE.md` (user-level, not committed).

## Overview

ApiPythonSample — a public sample project demonstrating how to authenticate with and consume the Qonic Public API using Python. Intended as a reference for third-party developers.

## Tech Stack

- **Python 3.10+**
- **requests 2.29** — HTTP client
- **python-dotenv** — environment variable loading

## Commands

```bash
# Setup
cp .env.example .env     # Copy env template, then fill in credentials
pip install -r requirements.txt

# Run
python sample.py         # Opens browser for OAuth login, then demonstrates API calls
```

## Project Structure

```
sample.py              # Main entry point — config, auth flow, example API requests
oauth.py               # OAuth authorization code flow with PKCE
QonicApi.py            # API client wrapper (high-level methods)
QonicApiLib.py         # Low-level API request helpers
printMethods.py        # Pretty-print utilities for API responses
requirements.txt       # Python dependencies
.env.example           # Environment variable template
```

## Key Conventions

- Uses OAuth **authorization code flow with PKCE** — a local HTTP server on `QONIC_LOCAL_PORT` (default 8765) captures the callback
- The `QONIC_REDIRECT_URI` must exactly match a whitelisted redirect URI in the Qonic Developer Portal
- Scopes are space-separated in `QONIC_SCOPES` (e.g., `projects:read models:read`)

## Environment Variables

| Variable | Purpose |
|---|---|
| `QONIC_CLIENT_ID` | OAuth client ID from Developer Portal |
| `QONIC_CLIENT_SECRET` | OAuth client secret |
| `QONIC_REDIRECT_URI` | Must match a whitelisted redirect URI exactly |
| `QONIC_LOCAL_PORT` | Local callback server port (default: 8765) |
| `QONIC_SCOPES` | Space-separated API scopes |

## How This Repo Interfaces With Others

- **Consumes**: Qonic Public API (`https://api.qonic.com` or environment-specific URL)
- **Public repo**: Hosted at `github.com/QonicOpen/ApiPythonSample`
- **Complements**: `api-docs` (documentation) and `dashboard-developer` (app management portal)
